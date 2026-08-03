from fastapi import FastAPI, APIRouter, HTTPException, Response
import difflib
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO
from fastapi.responses import StreamingResponse
from tavily import TavilyClient
from openai import AsyncOpenAI
import asyncio
import re

from models.schemas import RegionConfig, PricingRequest
from core.constants import (
    DEFAULT_REGIONAL_PRICES_BY_INDICATION,
    REGIONAL_CONSTANTS,
    PAYER_SEGMENTS,
    PAP_SCHEMES,
    LOCAL_DRUG_METADATA,
    SETTING_COVERAGE_RULES,
    MODEL_ASSUMPTIONS,
    unsourced_assumptions,
)
from core.therapy_areas import (
    resolve_indication,
    get_category,
    event_probability_from_primary,
    build_endpoints_summary,
    INDICATION_REGISTRY,
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Setup logging early
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

mongo_url = os.environ.get('MONGO_URL')
if not mongo_url:
    logger.warning("MONGO_URL not set — set it in the environment (do not hard-code credentials).")
    mongo_url = "mongodb://localhost:27017"
client = AsyncIOMotorClient(mongo_url)
db_name = os.environ.get('DB_NAME', 'droptax')
frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
db = client[db_name]

# Initialize Tavily client with explicit key
tavily_api_key = os.environ.get('TAVILY_API_KEY', '')
if tavily_api_key:
    tavily_client = TavilyClient(api_key=tavily_api_key)
else:
    tavily_client = None
    logger.warning("TAVILY_API_KEY not found - web search will use fallbacks")

# Initialize OpenAI client (used for strategic briefing LLM synthesis)
openai_api_key = os.environ.get('OPENAI_API_KEY', '')
if openai_api_key:
    openai_client = AsyncOpenAI(api_key=openai_api_key)
    logger.info("OpenAI client initialized — strategic briefing will use GPT-4")
else:
    openai_client = None
    logger.info("OPENAI_API_KEY not found — strategic briefing will use rule-based fallback")


def get_drug_category_by_indication(indication: str) -> str:
    """Therapy-area category for an indication, via the registry (single source of truth)."""
    return get_category(indication)


async def execute_web_search(query: str, max_results: int = 5) -> dict:
    """
    Unified search executor.
    Prioritizes Google Custom Search JSON API if GOOGLE_API_KEY and GOOGLE_CSE_ID are set,
    otherwise falls back to TavilyClient.
    """
    google_api_key = os.environ.get('GOOGLE_API_KEY') or os.environ.get('GOOGLE_SEARCH_API_KEY')
    google_cse_id = os.environ.get('GOOGLE_CSE_ID') or os.environ.get('GOOGLE_CUSTOM_SEARCH_ENGINE_ID')

    if google_api_key and google_cse_id:
        logger.info(f"[SearchEngine] Executing Google Custom Search for: {query}")
        import httpx
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": google_api_key,
            "cx": google_cse_id,
            "q": query,
            "num": min(max_results, 10)
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("items", [])
                    results = []
                    for item in items:
                        results.append({
                            "title": item.get("title", ""),
                            "content": item.get("snippet", ""),
                            "url": item.get("link", "")
                        })
                    return {"results": results}
                else:
                    logger.error(f"[SearchEngine] Google Search API error {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"[SearchEngine] Google Search exception: {e}")

    if tavily_client:
        logger.info(f"[SearchEngine] Executing Tavily Search for: {query}")
        import asyncio as _asyncio
        try:
            res = await _asyncio.to_thread(
                tavily_client.search,
                query,
                max_results=max_results
            )
            return res if isinstance(res, dict) else {"results": []}
        except Exception as e:
            logger.error(f"[SearchEngine] Tavily Search exception: {e}")

    logger.warning(f"[SearchEngine] No active search engine keys found for query: {query}")
    return {"results": []}


app = FastAPI()
api_router = APIRouter(prefix="/api")

# ============== REGIONAL MARKET AVAILABILITY ==============
# Tracks whether a drug is actually available in each market
# global_approval != regional_availability

REGIONAL_DRUG_AVAILABILITY = {
    # Semaglutide (Wegovy)
    "semaglutide": {
        "global_approval": {"agency": "FDA", "date": "2021-06-04", "status": "approved"},
        "IN": {"status": "launched", "local_approval": "2023-08", "launch_date": "2024-01", "notes": "Fully available. Novo Nordisk India distribution."},
        "SG": {"status": "launched", "local_approval": "2022-04", "launch_date": "2022-07", "notes": "Fully available."},
        "AE": {"status": "launched", "local_approval": "2022-10", "launch_date": "2023-01", "notes": "Fully available."},
    },
    "wegovy": {
        "global_approval": {"agency": "FDA", "date": "2021-06-04", "status": "approved"},
        "IN": {"status": "launched", "local_approval": "2023-08", "launch_date": "2024-01", "notes": "Available via imports and local Novo Nordisk channels."},
        "SG": {"status": "launched", "local_approval": "2022-04", "launch_date": "2022-07", "notes": "Fully available."},
        "AE": {"status": "launched", "local_approval": "2022-10", "launch_date": "2023-01", "notes": "Fully available."},
    },
    
    # Tirzepatide (Zepbound / Mounjaro)
    "tirzepatide": {
        "global_approval": {"agency": "FDA", "date": "2022-05-13", "status": "approved"},
        "IN": {"status": "limited", "local_approval": "2024-10", "notes": "CDSCO approved. Limited availability via authorized importers."},
        "SG": {"status": "launched", "local_approval": "2023-06", "launch_date": "2023-09", "notes": "Available. Eli Lilly Singapore."},
        "AE": {"status": "launched", "local_approval": "2023-01", "launch_date": "2023-04", "notes": "Fully available."},
    },
    "zepbound": {
        "global_approval": {"agency": "FDA", "date": "2023-11-08", "status": "approved"},
        "IN": {"status": "limited", "local_approval": "2024-10", "notes": "Approved for chronic weight management. Limited import."},
        "SG": {"status": "launched", "local_approval": "2023-06", "launch_date": "2023-09", "notes": "Available."},
        "AE": {"status": "launched", "local_approval": "2023-01", "launch_date": "2023-04", "notes": "Available."},
    },
    
    # Sacubitril/Valsartan (Entresto)
    "entresto": {
        "global_approval": {"agency": "FDA", "date": "2015-07-07", "status": "approved"},
        "IN": {"status": "launched", "local_approval": "2016-02", "launch_date": "2016-04", "notes": "Fully available. Novartis India and local generic versions."},
        "SG": {"status": "launched", "local_approval": "2015-12", "launch_date": "2016-02", "notes": "Fully available."},
        "AE": {"status": "launched", "local_approval": "2016-01", "launch_date": "2016-03", "notes": "Fully available."},
    },
    
    # Tenecteplase (Metalyse)
    "tenecteplase": {
        "global_approval": {"agency": "FDA", "date": "2000-06-02", "status": "approved"},
        "IN": {"status": "launched", "local_approval": "2021-12", "launch_date": "2022-02", "notes": "Fully available. Boehringer Ingelheim & Gennova (Elaxim)."},
        "SG": {"status": "launched", "local_approval": "2001-08", "launch_date": "2001-11", "notes": "Fully available in stroke units."},
        "AE": {"status": "launched", "local_approval": "2002-04", "launch_date": "2002-07", "notes": "Fully available in hospital formulary."},
    },
    
    # Fezolinetant (Veozah)
    "fezolinetant": {
        "global_approval": {"agency": "FDA", "date": "2023-05-12", "status": "approved"},
        "IN": {"status": "not_launched", "local_approval": None, "notes": "Pending CDSCO registration. Not commercially available."},
        "SG": {"status": "limited", "local_approval": None, "notes": "Named patient program only via Astellas Singapore."},
        "AE": {"status": "launched", "local_approval": "2024-05", "notes": "Available in selected premium hospital networks."},
    },
    "veozah": {
        "global_approval": {"agency": "FDA", "date": "2023-05-12", "status": "approved"},
        "IN": {"status": "not_launched", "local_approval": None, "notes": "Under registration review."},
        "SG": {"status": "limited", "local_approval": None, "notes": "Under HSA review."},
        "AE": {"status": "launched", "local_approval": "2024-05", "notes": "Available."},
    },
    
    # Romosozumab (Evenity)
    "romosozumab": {
        "global_approval": {"agency": "FDA", "date": "2019-04-09", "status": "approved"},
        "IN": {"status": "launched", "local_approval": "2021-06", "launch_date": "2021-09", "notes": "Available via Amgen India distribution channels."},
        "SG": {"status": "launched", "local_approval": "2019-11", "launch_date": "2020-02", "notes": "Fully available."},
        "AE": {"status": "launched", "local_approval": "2020-05", "launch_date": "2020-08", "notes": "Fully available."},
    },
    "evenity": {
        "global_approval": {"agency": "FDA", "date": "2019-04-09", "status": "approved"},
        "IN": {"status": "launched", "local_approval": "2021-06", "launch_date": "2021-09", "notes": "Distributed via Amgen."},
        "SG": {"status": "launched", "local_approval": "2019-11", "launch_date": "2020-02", "notes": "Fully available."},
        "AE": {"status": "launched", "local_approval": "2020-05", "launch_date": "2020-08", "notes": "Fully available."},
    },
}

# ============== MULTI-INDICATION DRUGS ==============
# Comprehensive FDA-approved indications for major immunotherapy/targeted therapy drugs
# These are used to provide accurate indication selection instead of relying on web search

# MULTI_INDICATION_DRUGS has been migrated to the DB


# ============== PRICING HELPER ==============

LOCAL_DRUG_PRICES = {
    "calpol": {"IN": 14, "SG": 2, "AE": 5},
    "crocin": {"IN": 15, "SG": 2, "AE": 5},
    "paracetamol": {"IN": 12, "SG": 2, "AE": 5},
    "acetaminophen": {"IN": 12, "SG": 2, "AE": 5},
    "semaglutide": {"IN": 25000, "SG": 450, "AE": 1200},
    "wegovy": {"IN": 25000, "SG": 450, "AE": 1200},
    "mounjaro": {"IN": 35000, "SG": 550, "AE": 1500},
    "zepbound": {"IN": 35000, "SG": 550, "AE": 1500},
    "tirzepatide": {"IN": 35000, "SG": 550, "AE": 1500},
    "entresto": {"IN": 4500, "SG": 180, "AE": 450},
    "metalyse": {"IN": 80000, "SG": 2000, "AE": 5000},
    "veozah": {"IN": 6000, "SG": 250, "AE": 650},
    "evenity": {"IN": 18000, "SG": 600, "AE": 1600}
}

def parse_price_from_string(price_str: Optional[str]) -> Optional[float]:
    if not price_str:
        return None
    try:
        import re
        cleaned = price_str.replace(',', '').strip()
        match = re.search(r'\d+(?:\.\d+)?', cleaned)
        if match:
            return float(match.group(0))
    except Exception as e:
        logger.warning(f"Error parsing price string '{price_str}': {e}")
    return None

async def get_regional_price(drug_name: str, indication: str, region_code: str) -> dict:
    """
    Get the regional list price for a drug.
    Priority:
      0. LOCAL_DRUG_PRICES mapping
      1. MongoDB db.drugs - field 'regional_prices', 'list_price', or 'global_price_inr'
      2. DEFAULT_REGIONAL_PRICES_BY_INDICATION - lookup by indication keyword
      3. Hard fallback: 250,000 INR / 9,000 SGD / 28,000 AED
    Returns: { "monthly_price": int, "is_estimated": bool }
    """
    region = region_code.upper()

    # 0. Local Audited Price List
    name_lower = drug_name.lower()
    if name_lower in LOCAL_DRUG_PRICES:
        price = LOCAL_DRUG_PRICES[name_lower].get(region)
        if price:
            return {"monthly_price": price, "is_estimated": False}

    # 1. MongoDB lookup
    try:
        drug_doc = await db.drugs.find_one(
            {"name": {"$regex": f"^{drug_name}$", "$options": "i"}},
            {"_id": 0, "regional_prices": 1, "list_price": 1, "global_price_inr": 1, "indication": 1}
        )
        if drug_doc:
            regional_prices = drug_doc.get("regional_prices", {})
            if regional_prices and region in regional_prices:
                price = int(regional_prices[region])
                if price > 0:
                    return {"monthly_price": price, "is_estimated": False}
            # Flat list_price (not region-keyed)
            if drug_doc.get("list_price"):
                price = int(drug_doc["list_price"])
                if price > 0:
                    return {"monthly_price": price, "is_estimated": True}
            # global_price_inr field
            if drug_doc.get("global_price_inr"):
                price = int(drug_doc["global_price_inr"])
                if price > 0:
                    if region == "IN":
                        return {"monthly_price": price, "is_estimated": False}
                    elif region == "SG":
                        return {"monthly_price": max(1, int(price / 60)), "is_estimated": True}
                    elif region == "AE":
                        return {"monthly_price": max(1, int(price / 22)), "is_estimated": True}
                    else:
                        return {"monthly_price": price, "is_estimated": True}
    except Exception:
        pass

    # 2. Indication-matched class price — a labelled estimate, not a guess at
    #    this specific drug's price.
    indication_lower = (indication or "").lower()
    matched_price = next(
        (DEFAULT_REGIONAL_PRICES_BY_INDICATION[k].get(region)
         for k in DEFAULT_REGIONAL_PRICES_BY_INDICATION
         if k != "default" and k in indication_lower),
        None
    )
    if matched_price:
        return {"monthly_price": matched_price, "is_estimated": True,
                "price_note": "Indication-class average — not this drug's actual price."}

    # 3. No price could be resolved. Return None rather than a fabricated
    #    figure; callers surface this as "Data unavailable" and flag it.
    return {"monthly_price": None, "is_estimated": True,
            "price_note": "No price found for this drug in the selected region — enter manually."}


async def get_payer_segments_for_region(region_code: str) -> list:
    """
    Return the list of payer segment definitions for a given region.
    Checks MongoDB db.regions first, then falls back to PAYER_SEGMENTS constants.
    """
    from core.constants import PAYER_SEGMENTS
    region = region_code.upper()

    # 1. MongoDB lookup
    try:
        region_doc = await db.regions.find_one({"code": region}, {"_id": 0, "payer_segments": 1})
        if region_doc and region_doc.get("payer_segments"):
            segs = region_doc["payer_segments"]
            if isinstance(segs, list):
                return segs
            # object/dict form → flatten to list
            return [{"code": k, **v} for k, v in segs.items()]
    except Exception:
        pass

    # 2. Constants fallback
    region_segs = PAYER_SEGMENTS.get(region, PAYER_SEGMENTS.get("IN", {}))
    return [{"code": code, **seg} for code, seg in region_segs.items()]


async def calculate_period_costs(
    list_price: float,
    region_code: str,
    payer_segment: str,
    num_periods: int = 12,
    drug_pap_code: Optional[str] = None,
    patient_program: Optional[str] = None,
) -> dict:
    """
    Calculate period-by-period patient cost based on payer segment + PAP scheme.
    A "period" is one dispensing/dosing interval (e.g. a month of therapy).
    Returns a dict with period_data, totals, effective_monthly_cost, and deal advice.
    """
    region = region_code.upper()
    constants = REGIONAL_CONSTANTS.get(region, REGIONAL_CONSTANTS["IN"])

    # ── Map MongoDB segment codes to internal legacy keys ────────────────────
    code_map = {
        "OOP": "oop",
        "CORP": "private_insurance",
        "GOVT": "cghs",
        "PRIVATE": "private_insurance",
        "DAMAN": "daman",
        "MEDISAVE": "medishield_life"
    }
    internal_segment = code_map.get(payer_segment.upper(), payer_segment.lower())

    # ── Resolve payer segment ────────────────────────────────────────────────
    region_payers = PAYER_SEGMENTS.get(region, PAYER_SEGMENTS.get("IN", {}))
    seg_data = region_payers.get(internal_segment, region_payers.get("oop", {}))
    copay_pct = seg_data.get("copay_percent", 1.0)
    govt_discount = seg_data.get("govt_rate_discount", 0.0)
    annual_cap = seg_data.get("annual_cap")
    pap_eligible = seg_data.get("pap_eligible", False)
    if pap_eligible:
        if (region == "IN" and list_price < 2000) or (region == "SG" and list_price < 50) or (region == "AE" and list_price < 150):
            pap_eligible = False
    insurer_pct = max(0.0, 1.0 - copay_pct - govt_discount)

    # ── Resolve the patient-assistance scheme ──────────────────────────────
    # A scheme is applied ONLY when this specific drug has a verified,
    # structured programme (pap_scheme_code on the drug record). Free-text
    # programme descriptions are surfaced as context but never used to infer
    # a discount, and no generic scheme is auto-applied — otherwise every
    # out-of-pocket drug would appear to be half price.
    best_pap = None
    if pap_eligible and drug_pap_code:
        region_paps = PAP_SCHEMES.get(region, [])
        best_pap = next((sch for sch in region_paps if sch["code"] == drug_pap_code), None)

    # ── Build period data ────────────────────────────────────────────────────
    period_data = []
    annual_oop = 0
    annual_insurer = 0
    annual_govt = 0
    total_patient_effective = 0

    for i in range(1, num_periods + 1):
        is_free = False
        patient_pay = list_price * copay_pct
        insurer_pay = list_price * insurer_pct
        govt_pay = list_price * govt_discount
        subsidy = 0

        # Apply PAP period logic (paid vs free intervals)
        if best_pap:
            span = best_pap["paid_periods"] + best_pap["free_periods"]
            position_in_span = (i - 1) % span
            if position_in_span >= best_pap["paid_periods"]:
                is_free = True
                subsidy = patient_pay
                patient_pay = 0

        # Apply annual cap if set
        if annual_cap and (annual_oop + patient_pay) > annual_cap:
            patient_pay = max(0, annual_cap - annual_oop)

        annual_oop += patient_pay
        annual_insurer += insurer_pay
        annual_govt += govt_pay
        total_patient_effective += patient_pay

        period_data.append({
            "period": i,
            "patient_pay": round(patient_pay),
            "insurer_pay": round(insurer_pay),
            "govt_pay": round(govt_pay),
            "subsidy": round(subsidy),
            "is_free_period": is_free,
        })

    effective_monthly = round(total_patient_effective / num_periods)

    # ── Deal Architect advice ────────────────────────────────────────────────
    deal_advice = None
    if best_pap:
        deal_advice = (f"Verified scheme '{best_pap['name']}' applied. "
                       f"Effective discount: {int(best_pap['effective_discount'] * 100)}% on list price.")
    elif patient_program:
        # A real programme exists but is not a verified price discount (e.g.
        # zero-interest EMI spreads the cost without reducing it).
        deal_advice = (f"Programme on record: {patient_program}. Instalment or support programmes "
                       f"do not reduce the total cost, so the list price is shown unchanged. "
                       f"Verify terms before modelling a discount.")
    elif pap_eligible:
        deal_advice = ("No verified patient-assistance scheme on record for this drug. "
                       "Full out-of-pocket cost shown.")

    return {
        "segment": seg_data.get("name", payer_segment),
        "segment_code": payer_segment,
        "period_data": period_data,
        "annual_oop_impact": round(annual_oop),
        "annual_insurer_impact": round(annual_insurer),
        "annual_govt_impact": round(annual_govt),
        "effective_monthly_cost": effective_monthly,
        "pap_scheme_applied": best_pap["name"] if best_pap else None,
        "pap_scheme_code": best_pap["code"] if best_pap else None,
        "deal_architect_advice": deal_advice,
    }


@api_router.get("/regions", response_model=List[RegionConfig])
async def get_regions():
    regions = await db.regions.find({}, {"_id": 0}).to_list(100)
    return regions


@api_router.get("/regions/{region_code}/payer-segments")
async def get_region_payer_segments(region_code: str):
    """Get available payer segments for a region"""
    segments = await get_payer_segments_for_region(region_code)
    return {
        "region_code": region_code.upper(),
        "segments": segments
    }


@api_router.post("/pricing/calculate")
async def calculate_pricing(request: PricingRequest):
    """
    Dynamic Pricing Engine - Calculate period-based costs for a drug
    Respects payer segment and regional pricing
    """
    # Get regional price (not conversion)
    _drug = await db.drugs.find_one({"name": {"$regex": f"^{request.drug_name}$", "$options": "i"}}, {"_id": 0})
    price_info = await get_regional_price(request.drug_name, "", request.region_code)
    list_price = price_info["monthly_price"] or 0
    
    # Calculate period costs
    period_result = await calculate_period_costs(
        list_price=list_price,
        region_code=request.region_code,
        payer_segment=request.payer_segment,
        num_periods=request.num_periods,
        drug_pap_code=(_drug.get("pap_scheme_code") if _drug else None),
        patient_program=(_drug.get("patient_program") if _drug else None),
    )

    regional_constants = REGIONAL_CONSTANTS.get(request.region_code.upper(), REGIONAL_CONSTANTS["IN"])

    return {
        "drug_name": request.drug_name,
        "region_code": request.region_code.upper(),
        "pricing_model": {
            "segment": period_result["segment"],
            "segment_code": period_result["segment_code"],
            "currency": regional_constants["currency"],
            "currency_symbol": regional_constants["currency_symbol"],
            "list_price_per_period": list_price,
            "period_data": period_result["period_data"],
            "annual_oop_impact": period_result["annual_oop_impact"],
            "annual_insurer_impact": period_result["annual_insurer_impact"],
            "annual_govt_impact": period_result["annual_govt_impact"],
            "effective_monthly_cost": period_result["effective_monthly_cost"],
            "pap_scheme_applied": period_result["pap_scheme_applied"],
            "pap_scheme_code": period_result["pap_scheme_code"],
            "deal_architect_advice": period_result["deal_architect_advice"],
            "is_price_estimated": price_info["is_estimated"]
        }
    }


@api_router.get("/pricing/{drug_name}")
async def get_drug_pricing(drug_name: str, region_code: str = "IN", payer_segment: str = "oop"):
    """
    Get pricing model for a drug (GET version for dashboard)
    """
    # Try to get indication from cached drug
    drug = await db.drugs.find_one({"name": {"$regex": f"^{drug_name}$", "$options": "i"}}, {"_id": 0})
    indication = drug.get("indication", "") if drug else ""
    
    price_info = await get_regional_price(drug_name, indication, region_code)
    list_price = price_info["monthly_price"] or 0
    
    period_result = await calculate_period_costs(
        list_price=list_price,
        region_code=region_code,
        payer_segment=payer_segment,
        num_periods=12,
        drug_pap_code=(drug.get("pap_scheme_code") if drug else None),
        patient_program=(drug.get("patient_program") if drug else None),
    )

    regional_constants = REGIONAL_CONSTANTS.get(region_code.upper(), REGIONAL_CONSTANTS["IN"])

    return {
        "drug_name": drug_name,
        "region_code": region_code.upper(),
        "pricing_model": {
            "segment": period_result["segment"],
            "segment_code": period_result["segment_code"],
            "currency": regional_constants["currency"],
            "currency_symbol": regional_constants["currency_symbol"],
            "list_price_per_period": list_price,
            "period_data": period_result["period_data"],
            "annual_oop_impact": period_result["annual_oop_impact"],
            "annual_insurer_impact": period_result["annual_insurer_impact"],
            "annual_govt_impact": period_result["annual_govt_impact"],
            "effective_monthly_cost": period_result["effective_monthly_cost"],
            "pap_scheme_applied": period_result["pap_scheme_applied"],
            "pap_scheme_code": period_result["pap_scheme_code"],
            "deal_architect_advice": period_result["deal_architect_advice"],
            "is_price_estimated": price_info["is_estimated"]
        }
    }

# ============== FUZZY MATCHING ("Did you mean?") ==============
def _build_drug_corpus() -> list:
    """Build a corpus of all known drug brand/generic names for fuzzy matching."""
    names = set()
    for key in LOCAL_DRUG_METADATA:
        names.add(key)
    for key in REGIONAL_DRUG_AVAILABILITY:
        names.add(key)
    return sorted(names)

DRUG_NAME_CORPUS = _build_drug_corpus()

def fuzzy_suggest(query: str, corpus: list = None, cutoff: float = 0.55) -> Optional[str]:
    """Return the best fuzzy match for a query, or None."""
    if corpus is None:
        corpus = DRUG_NAME_CORPUS
    q = query.lower().strip()
    # Exact match means no suggestion needed
    if q in corpus:
        return None
    matches = difflib.get_close_matches(q, corpus, n=1, cutoff=cutoff)
    if matches:
        # Return the title-cased canonical name
        best = matches[0]
        # Look up the proper display name from LOCAL_DRUG_METADATA
        meta = LOCAL_DRUG_METADATA.get(best)
        if meta:
            return best.title()  # e.g. "jemperli" -> "Jemperli"
        return best.title()
    return None


@api_router.get("/drugs/search")
async def search_drugs(q: str = "", indication: Optional[str] = None):
    """Search drugs - fully dynamic via web search for ANY drug. Returns { results, did_you_mean }."""
    if not q or len(q) < 2:
        return {"results": [], "did_you_mean": None}

    q_lower = q.lower().strip()
    if "vyamada" in q_lower:
        q_lower = q_lower.replace("vyamada", "vymada")
        q = q.replace("vyamada", "vymada").replace("Vyamada", "Vymada")

    # 1. Check database cache — includes both single and multi-indication drugs
    query = {"$or": [
        {"name": {"$regex": q, "$options": "i"}},
        {"indication": {"$regex": q, "$options": "i"}},
        {"key_brands": {"$regex": q, "$options": "i"}}
    ]}
    drugs = await db.drugs.find(
        query,
        {"_id": 0, "id": 1, "name": 1, "indication": 1, "has_multiple_indications": 1, "key_brands": 1}
    ).to_list(10)

    if drugs:
        for drug in drugs:
            # Check if query matched a brand name
            brand_match = None
            if "key_brands" in drug and drug["key_brands"]:
                brands = [b.strip() for b in drug["key_brands"].split(",")]
                for b in brands:
                    if q_lower in b.lower():
                        brand_match = b
                        break
            if brand_match:
                drug["name"] = f"{brand_match} ({drug['name']})"

            # Apply indication override if provided
            if drug.get("has_multiple_indications") and not indication:
                drug["indication"] = "Multiple Indications recognized. Click to select."
            elif indication:
                drug["indication"] = indication
            # Ensure is_dynamic flag is absent for DB results
            drug.pop("is_dynamic", None)
            drug.pop("key_brands", None)
        return {"results": drugs, "did_you_mean": None}

    # 2. Check multi-indication drugs stored separately in DB
    multi_doc = await db.drugs.find_one(
        {"has_multiple_indications": True, "name": {"$regex": q, "$options": "i"}},
        {"_id": 0, "id": 1, "name": 1, "indications": 1}
    )
    if multi_doc:
        indications_list = multi_doc.get("indications", [])
        primary = next(
            (ind["indication"] for ind in indications_list if ind.get("is_primary")),
            indications_list[0]["indication"] if indications_list and len(indications_list) == 1 else "Multiple Indications recognized. Click to select."
        )
        return {"results": [{
            "id": multi_doc.get("id", f"dynamic-{uuid.uuid4()}"),
            "name": multi_doc["name"],
            "indication": indication or primary,
            "has_multiple_indications": True,
        }], "did_you_mean": None}

    # 3. Not in DB → create a live web-search stub AND check for fuzzy match
    suggestion = fuzzy_suggest(q_lower)
    
    # Also try to expand the corpus with DB names at runtime
    if not suggestion:
        try:
            db_names = await db.drugs.distinct("name")
            db_corpus = [n.lower() for n in db_names if n]
            suggestion = fuzzy_suggest(q_lower, corpus=db_corpus + DRUG_NAME_CORPUS)
        except Exception:
            pass

    return {
        "results": [{
            "id": f"dynamic-{uuid.uuid4()}",
            "name": q.title(),
            "indication": indication or "Click to analyze via real-time web search",
            "is_dynamic": True
        }],
        "did_you_mean": suggestion
    }


# ============== WEB SWEEPER PROTOCOL HELPERS ==============

async def web_search_drug_info(drug_name: str) -> dict:
    """
    Step 1 of Commercial Brain: Get basic drug information (indication, mechanism, launch date).
    Uses Tavily search + GPT-4 parsing when available, falls back to defaults.
    """
    import asyncio as _asyncio, json as _json

    default = {
        "indication": "Therapeutic Asset (Awaiting Verification)",
        "mechanism_of_action": "Clinical Data Pending Verification",
        "launch_date": None,
        "indications_available": [],
    }

    if not ((tavily_client or os.environ.get('GOOGLE_API_KEY') or os.environ.get('GOOGLE_SEARCH_API_KEY')) and openai_client):
        logger.warning("[WebSweeper/drug_info] No API keys — checking local metadata")
        lookup = LOCAL_DRUG_METADATA.get(drug_name.lower())
        if lookup:
            logger.info(f"[WebSweeper/drug_info] Found local metadata for {drug_name}")
            return lookup
        return default

    try:
        results = await execute_web_search(
            f'"{drug_name}" FDA approval indication mechanism of action site:fda.gov OR clinicaltrials.gov OR drugs.com',
            max_results=5
        )
        content = "\n".join(r.get("content", "") for r in results.get("results", []))[:4000]

        resp = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": "You are a clinical pharmacology expert. Extract structured drug information as JSON."},
                {"role": "user", "content": (
                    f"From this text about {drug_name}, extract:\n"
                    "{\n"
                    '  "indication": "primary FDA/EMA-approved indication",\n'
                    '  "mechanism_of_action": "brief mechanism (e.g. GLP-1 Receptor Agonist)",\n'
                    '  "launch_date": "YYYY or YYYY-MM",\n'
                    '  "indications_available": [{"indication": "Indication 1"}, {"indication": "Indication 2"}] // EXHAUSTIVE list of up to 15 FDA/EMA approved indications\n'
                    "}\n\nText:\n" + content
                )}
            ]
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        parsed = _json.loads(raw)
        
        # Merge carefully to avoid wiping out keys if AI hallucinated
        final_info = default.copy()
        for k, v in parsed.items():
            if v and v != "Unknown":
                final_info[k] = v
                
        return final_info
        
    except Exception as e:
        logger.warning(f"[WebSweeper/drug_info] Error: {e} — checking local metadata")
        lookup = LOCAL_DRUG_METADATA.get(drug_name.lower())
        if lookup:
            logger.info(f"[WebSweeper/drug_info] Found local metadata for {drug_name} after error")
            return lookup
        return default

    # ---------------------------------------------------------
    # End Step 1
    # ---------------------------------------------------------


async def run_web_sweeper(drug_name: str, indication: str, region_code: str) -> dict:
    """
    Step 2 of Commercial Brain: Run the Web Sweeper Protocol.
    Returns clinical, competitor and safety data from search + LLM extraction.
    """
    import asyncio as _asyncio, json as _json

    region = region_code.upper()
    entry = resolve_indication(indication)
    pe = entry["primary_endpoint"] if entry else {
        "key": "primary_endpoint", "label": "Primary Efficacy Endpoint", "unit": "", "direction": "higher_better"}
    sec_specs = entry.get("secondary_endpoints", []) if entry else []

    def _empty(reason: str, tier: str = "tier_3", confidence: float = 0.0):
        """Anti-hallucination baseline: everything null, flagged as unavailable.
        NEVER fabricates a clinical value when real data can't be resolved."""
        issues = []
        if not entry:
            issues.append({"field": "indication", "severity": "warning",
                           "message": f"Indication '{indication}' not in the therapy-area registry — endpoints not structured."})
        issues.append({"field": pe["key"], "severity": "warning",
                       "message": f"{pe['label']} could not be resolved from a source ({reason}). Enter manually."})
        return {
            "clinical": {
                "primary_endpoint_key": pe["key"],
                "primary_endpoint_label": pe["label"],
                "primary_endpoint_unit": pe["unit"],
                "primary_endpoint_value": None,
                "primary_endpoint_method": None,
                "comparator_primary_value": None,
                "hazard_ratio": None,
                "secondary_endpoints": [
                    {"key": s["key"], "label": s["label"], "unit": s["unit"], "value": None} for s in sec_specs
                ],
                "data_available": False,
                "confidence": confidence,
                "source_url": None,
                "source_tier": tier,
            },
            "competitor": {"name": None, "source_url": None, "source_tier": tier},
            "safety": {"severe_ae_rate": None, "is_estimated": True, "adverse_events": [],
                         "source_url": None, "source_tier": tier},
            "drug_safety": {"severe_ae_rate": None, "is_estimated": True, "adverse_events": [],
                              "source_url": None},
            "data_quality": {"status": "unavailable", "missing_fields": [pe["key"], "severe_ae_rate"], "issues": issues},
            "local_hero_applied": False,
        }

    if not ((tavily_client or os.environ.get('GOOGLE_API_KEY') or os.environ.get('GOOGLE_SEARCH_API_KEY')) and openai_client):
        logger.warning("[WebSweeper/sweeper] No search/LLM keys — returning unavailable (no fabrication)")
        return _empty("no search/LLM configured")

    try:
        # Registry-driven search terms (fall back to a generic efficacy query)
        term_tpls = entry["search_terms"] if entry else [f'"{{drug}}" {indication} primary endpoint clinical trial results']
        clinical_queries = [t.replace("{drug}", drug_name) for t in term_tpls[:2]]
        tasks = [execute_web_search(q, max_results=5) for q in clinical_queries]
        tasks.append(execute_web_search(
            f'"{drug_name}" {indication} standard of care comparator randomized trial', max_results=5))
        tasks.append(execute_web_search(
            f'"{drug_name}" serious adverse events safety prescribing information', max_results=5))
        results = await _asyncio.gather(*tasks, return_exceptions=True)

        def safe(r):
            if isinstance(r, Exception) or not r:
                return ""
            return "\n".join(x.get("content", "") for x in r.get("results", []))[:2000]

        combined = "\n\n---\n\n".join([safe(r) for r in results])
        if not combined.strip():
            return _empty("no search results")

        sec_lines = "".join(
            f'      {{ "key": "{s["key"]}", "value": number|null }},\n' for s in sec_specs
        )
        resp = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": (
                    "You are a clinical data analyst for CardioMetabolic and Women's Health therapies. "
                    "Extract ONLY values explicitly supported by the provided text. Use null for anything not "
                    "clearly stated — NEVER guess or infer a number. Return drug names as commercial brand names.")},
                {"role": "user", "content": (
                    f"Drug: {drug_name}\nIndication: {indication}\n"
                    f"Primary endpoint to extract: {pe['label']} (unit: {pe['unit']}).\n\n"
                    "Return this JSON (null where the text does not state a value):\n"
                    "{\n"
                    '  "clinical": {\n'
                    f'    "primary_endpoint_value": number|null,   // {pe["label"]} in {pe["unit"]}\n'
                    '    "comparator_primary_value": number|null,\n'
                    '    "hazard_ratio": number|null,\n'
                    '    "secondary_endpoints": [\n' + sec_lines +
                    '    ],\n'
                    '    "confidence": 0-1, "source_url": "url"|null },\n'
                    '  "competitor": { "name": "brand name"|null, "source_url": "url"|null },\n'
                    '  "safety": { "severe_ae_rate": 0-1|null, "adverse_events": ["ae1"], "source_url": "url"|null },\n'
                    '  "drug_safety": { "severe_ae_rate": 0-1|null, "adverse_events": ["ae1"], "source_url": "url"|null }\n'
                    "}\n\nText:\n" + combined
                )}
            ]
        )
        raw = re.sub(r"```json|```", "", resp.choices[0].message.content.strip())
        parsed = _json.loads(raw)

        base = _empty("parsing", tier="tier_1")
        c_in = parsed.get("clinical", {}) or {}
        pv = c_in.get("primary_endpoint_value")
        base["clinical"]["primary_endpoint_value"] = pv
        base["clinical"]["comparator_primary_value"] = c_in.get("comparator_primary_value")
        base["clinical"]["hazard_ratio"] = c_in.get("hazard_ratio")
        base["clinical"]["confidence"] = c_in.get("confidence") or 0.0
        base["clinical"]["source_url"] = c_in.get("source_url")
        base["clinical"]["source_tier"] = "tier_1"
        base["clinical"]["data_available"] = pv is not None
        base["clinical"]["primary_endpoint_method"] = "Extracted from source" if pv is not None else None
        # Merge secondary values by key
        sec_by_key = {s.get("key"): s.get("value") for s in (c_in.get("secondary_endpoints") or [])}
        for s in base["clinical"]["secondary_endpoints"]:
            s["value"] = sec_by_key.get(s["key"])

        comp = parsed.get("competitor", {}) or {}
        base["competitor"]["name"] = comp.get("name")
        base["competitor"]["source_url"] = comp.get("source_url")
        base["competitor"]["source_tier"] = "tier_1"

        tox = parsed.get("safety", {}) or {}
        base["safety"]["severe_ae_rate"] = tox.get("severe_ae_rate")
        base["safety"]["adverse_events"] = tox.get("adverse_events") or []
        base["safety"]["is_estimated"] = tox.get("severe_ae_rate") is None
        base["safety"]["source_url"] = tox.get("source_url")
        base["safety"]["source_tier"] = "tier_1"

        dtox = parsed.get("drug_safety", {}) or {}
        base["drug_safety"]["severe_ae_rate"] = dtox.get("severe_ae_rate")
        base["drug_safety"]["adverse_events"] = dtox.get("adverse_events") or []
        base["drug_safety"]["is_estimated"] = dtox.get("severe_ae_rate") is None

        # Recompute data quality from what we actually got
        missing = []
        if base["clinical"]["primary_endpoint_value"] is None:
            missing.append(pe["key"])
        if base["safety"]["severe_ae_rate"] is None:
            missing.append("severe_ae_rate")
        issues = [{"field": m, "severity": "warning",
                   "message": f"{m} not found in sources — enter manually or verify."} for m in missing]
        status = "complete" if not missing else ("partial" if base["clinical"]["primary_endpoint_value"] is not None else "unavailable")
        base["data_quality"] = {"status": status, "missing_fields": missing, "issues": issues}
        return base

    except Exception as e:
        logger.warning(f"[WebSweeper/sweeper] Error: {e} — returning unavailable (no fabrication)")
        return _empty(f"error: {e}")


async def web_sweeper_regional_availability(drug_name: str, region_code: str) -> dict:
    """
    Step 3 of Commercial Brain: Check regional market availability via Tavily.
    Returns { is_available: bool|None, local_approval_date, notes, price_found, source_url }
    """
    import asyncio as _asyncio, json as _json

    region = region_code.upper()
    region_label = {"IN": "India CDSCO DCGI", "SG": "Singapore HSA", "AE": "UAE DOH MOHAP"}.get(region, region)

    default = {"is_available": None, "local_approval_date": None,
               "notes": "Availability data not confirmed", "price_found": None, "source_url": None}

    if not ((tavily_client or os.environ.get('GOOGLE_API_KEY') or os.environ.get('GOOGLE_SEARCH_API_KEY')) and openai_client):
        return default

    try:
        results = await execute_web_search(
            f'"{drug_name}" {region_label} approved available licensed launch therapeutic',
            max_results=5
        )
        content = "\n".join(r.get("content", "") for r in results.get("results", []))[:3000]
        source_url = next(
            (r.get("url") for r in results.get("results", []) if r.get("url")), None
        )

        resp = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": "You are a drug regulatory expert. Return only JSON."},
                {"role": "user", "content": (
                    f"Is {drug_name} available in {region_label}? Extract:\n"
                    '{ "is_available": true/false/null, "local_approval_date": "YYYY-MM or null", '
                    '"notes": "brief status", "price_found": "price string or null" }\n\nText:\n' + content
                )}
            ]
        )
        raw = re.sub(r"```json|```", "", resp.choices[0].message.content.strip())
        parsed = _json.loads(raw)
        return {**default, **parsed, "source_url": source_url}
    except Exception as e:
        logger.warning(f"[WebSweeper/availability] Error: {e} — using defaults")
        return default


def get_indication_default_price(indication: str) -> dict:
    """
    Return default price estimates (INR) for a given indication.
    Used as a pricing fallback when no specific price data is available.
    """
    from core.constants import DEFAULT_REGIONAL_PRICES_BY_INDICATION
    ind_lower = (indication or "").lower()
    matched = next(
        (DEFAULT_REGIONAL_PRICES_BY_INDICATION[k]["IN"]
         for k in DEFAULT_REGIONAL_PRICES_BY_INDICATION
         if k != "default" and k in ind_lower),
        DEFAULT_REGIONAL_PRICES_BY_INDICATION["default"]["IN"]
    )
    return {
        "global_price_inr": matched,
        "competitor_price_inr": round(matched * 0.5)
    }



async def web_sweeper_news(drug_name: str, region: str = "Global") -> list:
    """
    WEB SWEEPER - News Search Protocol
    Queries Tavily for patent challenges, generic filings, and market threats.
    """
    if not (tavily_client or os.environ.get('GOOGLE_API_KEY') or os.environ.get('GOOGLE_SEARCH_API_KEY')):
        logger.warning("[News Sweeper] No search clients — returning empty news")
        return []

    queries = [
        f'"{drug_name}" patent challenge generic filing',
        f'"{drug_name}" FDA approval news {region}',
        f'"{drug_name}" market withdrawal competition'
    ]
    
    news_items = []
    
    try:
        results = await asyncio.gather(*[
            execute_web_search(q, max_results=3) for q in queries
        ])
        
        seen_urls = set()
        raw_contents = []
        for r in results:
            for item in r.get("results", []):
                url = item.get("url")
                if url and url not in seen_urls:
                    content_slice = item.get("content", "")[:500]
                    news_items.append({
                        "title": item.get("title", "Market Intelligence Report"),
                        "source": url.split("//")[-1].split("/")[0],
                        "source_url": url, # Frontend expects source_url
                        "description": item.get("content", "")[:200] + "...",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "category": "Competitive" if "challenge" in item.get("title", "").lower() or "generic" in item.get("title", "").lower() else "Regulatory"
                    })
                    raw_contents.append(f"Source: {item.get('title')}\nContent: {content_slice}")
                    seen_urls.add(url)
        
        # Generate AI Summary if we have content
        summary = "The market landscape for this asset remains stable with no immediate patent or generic threats detected in recent intelligence audits."
        if news_items and openai_client:
            try:
                combined_text = "\n\n".join(raw_contents[:5])
                prompt = f"Synthesize these news items for {drug_name} into a 2-sentence 'Threat Landscape Summary'. Focus on patent challenges, generic entries, or regulatory risks. Be direct and executive-level:\n\n{combined_text}"
                
                response = await loop.run_in_executor(None, lambda: openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=100
                ))
                summary = response.choices[0].message.content.strip()
            except Exception as ai_err:
                logger.error(f"AI Summary generation error: {ai_err}")

        return {
            "summary": summary,
            "sources": news_items[:10]
        }
                    
    except Exception as e:
        logger.error(f"[News Sweeper] Error fetching news: {e}")
        return {"summary": "Unable to fetch real-time threats.", "sources": []}


@api_router.post("/drugs/analyze")

async def analyze_drug_dynamically(
    drug_name: str, 
    indication: Optional[str] = None, 
    region_code: str = "IN",
    force_refresh: bool = False
):
    """
    COMMERCIAL BRAIN - Dynamic drug analysis using Web Sweeper Protocol
    
    1. Gets basic drug info (indication, mechanism, status)
    2. Runs Web Sweeper for clinical, competitor and safety data
    3. Gets regional market availability (checks web for real availability)
    4. Calculates liability using the new formula
    """
    logger.info(f"[Commercial Brain] Analyzing: {drug_name} (indication={indication}, region={region_code}, force_refresh={force_refresh})")
    
    # ── Normalize drug_name for database lookup ──────────────────────────────
    search_term = drug_name.strip()
    
    # Extract generic name from formatted suggestion "Brand (Generic)"
    import re
    paren_match = re.search(r'\((.*?)\)', search_term)
    if paren_match:
        search_term = paren_match.group(1).strip()
        
    # Check spelling fallbacks
    if search_term.lower() == "vyamada":
        search_term = "vymada"
        
    # Query database checking name AND key_brands
    query = {
        "$or": [
            {"name": {"$regex": f"^{re.escape(search_term)}$", "$options": "i"}},
            {"key_brands": {"$regex": f"\\b{re.escape(search_term)}\\b", "$options": "i"}},
            {"key_brands": {"$regex": re.escape(search_term), "$options": "i"}}
        ]
    }
    
    db_drug = None
    if indication:
        ind_query = {"$and": [query, {"indication": {"$regex": f"^{re.escape(indication)}$", "$options": "i"}}]}
        db_drug = await db.drugs.find_one(ind_query, {"_id": 0})
        
    if not db_drug:
        db_drug = await db.drugs.find_one(query, {"_id": 0})
        if db_drug and indication:
            db_drug["indication"] = indication

    # Update drug_name parameter to generic name if we found a match
    if db_drug and "name" in db_drug:
        logger.info(f"[Commercial Brain] Resolved '{drug_name}' to generic drug record: '{db_drug['name']}'")
        # Keep user brand name visual if needed, but let's use the DB generic name as canonical
        drug_name = db_drug["name"]
    
    # Cache Invalidation Check (30 Days)
    is_stale = False
    if force_refresh:
        is_stale = True
        logger.info(f"[Commercial Brain] Manual Force-Refresh requested for {drug_name}. Invalidating Cache.")
    elif db_drug and "last_updated" in db_drug:
        from datetime import datetime, timezone, timedelta
        try:
            last_up = db_drug["last_updated"]
            if isinstance(last_up, str):
                last_up = datetime.fromisoformat(last_up.replace('Z', '+00:00'))
            if last_up.tzinfo is None:
                last_up = last_up.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - last_up > timedelta(days=30):
                is_stale = True
        except:
            is_stale = True
    else:
        is_stale = True

    # If cache is valid and contains a full profile, return it immediately to save API calls
    if not is_stale and db_drug and "epidemiology" in db_drug:
        logger.info(f"[Commercial Brain] Cached drug profile for {drug_name} is fresh. Bypassing WebSweeper.")
        from bson.json_util import dumps
        import json
        return json.loads(dumps(db_drug))

    # --- Cache Miss or Stale: Run Web Sweeper Pipeline ---
    logger.info(f"[Commercial Brain] Cache Miss / Stale Data for {drug_name}. Booting WebSweeper AI.")
    
    # Step 1: Get basic drug information (provides fallbacks like Targeted Therapy)
    drug_info = await web_search_drug_info(drug_name)
    
    # Prioritize: 1) Explicit route param 2) Web sweep fallback
    selected_indication = indication or drug_info["indication"]
    
    # Registry entry for this indication (drives endpoint structuring; None if unknown)
    _resolved_entry = resolve_indication(selected_indication)

    # Step 2: Run Web Sweeper Protocol
    sweeper_data = await run_web_sweeper(drug_name, selected_indication, region_code)
    
    # Step 3: Get regional market availability via Web Sweeper
    logger.info("[Commercial Brain] Checking web for regional availability...")
    web_availability = await web_sweeper_regional_availability(drug_name, region_code)
    
    regional_constants = REGIONAL_CONSTANTS.get(region_code.upper(), REGIONAL_CONSTANTS["IN"])
    
    # Priority: 1. Audited Local Metadata (REGIONAL_DRUG_AVAILABILITY) 2. Dynamic Web Sweeper 3. Unknown Fallback
    is_major_drug = drug_name.lower() in REGIONAL_DRUG_AVAILABILITY
    static_data = REGIONAL_DRUG_AVAILABILITY.get(drug_name.lower(), {}).get(region_code.upper())
    
    if static_data and static_data.get("status") == "launched":
        regional_availability = {
            "global_approval": {"agency": "FDA", "date": drug_info.get("launch_date"), "status": "approved"},
            "regional_status": "launched",
            "local_regulator": regional_constants["regulator"],
            "local_approval_date": static_data.get("local_approval"),
            "launch_date": static_data.get("launch_date"),
            "display_status": f"{regional_constants['regulator']} Approved",
            "availability_text": "Commercially Available (Audited)",
            "availability_color": "green",
            "notes": static_data.get("notes", "Standard of Care available."),
            "is_available": True
        }
    elif web_availability["is_available"] is True:
        regional_availability = {
            "global_approval": {"agency": "FDA", "date": drug_info.get("launch_date"), "status": "approved"},
            "regional_status": "launched",
            "local_regulator": regional_constants["regulator"],
            "local_approval_date": web_availability["local_approval_date"],
            "launch_date": web_availability["local_approval_date"],
            "display_status": f"{regional_constants['regulator']} Approved",
            "availability_text": "Commercially Available",
            "availability_color": "green",
            "notes": web_availability["notes"],
            "is_available": True,
            "price_found": web_availability.get("price_found"),
            "source_url": web_availability.get("source_url")
        }
    elif web_availability["is_available"] is False:
        regional_availability = {
            "global_approval": {"agency": "FDA", "date": drug_info.get("launch_date"), "status": "approved"},
            "regional_status": "not_launched",
            "local_regulator": regional_constants["regulator"],
            "local_approval_date": None,
            "launch_date": None,
            "display_status": f"FDA Approved (Not in {region_code})",
            "availability_text": f"Not launched in {region_code}",
            "availability_color": "red",
            "notes": web_availability["notes"],
            "is_available": False
        }
    else:
        # Unknown status from sweeper - default to conservative but professional estimate
        regional_availability = {
            "global_approval": {"agency": "FDA", "date": drug_info.get("launch_date"), "status": "approved"},
            "regional_status": "launched" if is_major_drug else "unknown",
            "local_regulator": regional_constants["regulator"],
            "local_approval_date": "2018-01-01" if is_major_drug else None,
            "launch_date": "2018-01-01" if is_major_drug else None,
            "display_status": f"{regional_constants['regulator']} Approved" if is_major_drug else "Pending Verification",
            "availability_text": "Commercially Available (Audited)" if is_major_drug else "Pending Regional Verification",
            "availability_color": "green" if is_major_drug else "yellow",
            "notes": "Standard of Care available via specialized care centers." if is_major_drug else "Data under procurement. Check back soon.",
            "is_available": True if is_major_drug else None
        }
    
    # Step 4: Get pricing defaults based on indication
    name_lower = drug_name.lower()
    pricing = {"global_price_inr": 15000, "competitor_price_inr": 7500}
    
    # Priority: 1) Local audited drug price list 2) Web search extracted price 3) Indication default fallback
    # Check if generic name or any key brand is in LOCAL_DRUG_PRICES
    local_price = None
    names_to_check = [name_lower]
    if db_drug and "key_brands" in db_drug and db_drug["key_brands"]:
        brands = [b.strip().lower() for b in db_drug["key_brands"].split(",")]
        names_to_check.extend(brands)
        
    for n in names_to_check:
        if n in LOCAL_DRUG_PRICES:
            local_price = LOCAL_DRUG_PRICES[n].get("IN")
            break
            
    extracted_price = parse_price_from_string(regional_availability.get("price_found"))
    
    if local_price:
        pricing["global_price_inr"] = local_price
        pricing["competitor_price_inr"] = max(1.0, round(local_price * 0.5))
        logger.info(f"[Commercial Brain] Set pricing for {drug_name} via local pricing list: {local_price} INR")
    elif extracted_price and extracted_price > 0:
        pricing["global_price_inr"] = extracted_price
        pricing["competitor_price_inr"] = max(1.0, round(extracted_price * 0.5))
        logger.info(f"[Commercial Brain] Set pricing for {drug_name} via Web Search price extraction: {extracted_price} INR")
    else:
        pricing = get_indication_default_price(selected_indication)
    
    # Determine display dates - use regional launch date if available
    display_launch_date = regional_availability.get("launch_date") or drug_info["launch_date"]
    
    # Create complete drug profile with Commercial Brain data
    # Safe Fallback: If WebSweeper failed (API down), preserve existing database intelligence instead of wiping it
    safe_moa = drug_info["mechanism_of_action"]
    if safe_moa.startswith("Clinical") and db_drug and "mechanism_of_action" in db_drug:
        safe_moa = db_drug["mechanism_of_action"]
        
    safe_regulatory = regional_availability["display_status"]
    if safe_regulatory.startswith("Pending") and db_drug and "regulatory_status" in db_drug:
        safe_regulatory = db_drug["regulatory_status"]
        
    safe_regional = regional_availability
    if regional_availability.get("is_available") is None and db_drug and "regional_availability" in db_drug:
        safe_regional = db_drug["regional_availability"]

    drug_profile = {
        "id": db_drug["id"] if db_drug and "id" in db_drug else f"dynamic-{str(uuid.uuid4())}",
        "name": drug_name,
        "indication": selected_indication,
        "indications_available": (
            drug_info.get("indications_available") if drug_info.get("indications_available") 
            else (db_drug.get("indications_available", []) if db_drug else [])
        ),
        "has_multiple_indications": (
            True if (drug_info.get("indications_available") and len(drug_info["indications_available"]) > 1) 
            or (db_drug and db_drug.get("indications_available") and len(db_drug["indications_available"]) > 1)
            else False
        ),
        "mechanism_of_action": safe_moa,
        "launch_date": display_launch_date,
        "regulatory_status": safe_regulatory,
        
        # Regional Availability (NEW)
        "regional_availability": {
            "global_approval": safe_regional.get("global_approval", regional_availability["global_approval"]),
            "regional_status": safe_regional.get("regional_status", regional_availability["regional_status"]),
            "local_regulator": safe_regional.get("local_regulator", regional_availability["local_regulator"]),
            "local_approval_date": safe_regional.get("local_approval_date", regional_availability["local_approval_date"]),
            "availability_text": safe_regional.get("availability_text", regional_availability["availability_text"]),
            "availability_color": safe_regional.get("availability_color", regional_availability["availability_color"]),
            "notes": safe_regional.get("notes", regional_availability["notes"]),
            "is_available": safe_regional.get("is_available", regional_availability["is_available"])
        },
        
        # From Web Sweeper - Clinical Endpoints (generic, registry-driven)
        "competitor_name": sweeper_data["competitor"]["name"] or "Standard of Care",
        "primary_endpoint_key": sweeper_data["clinical"].get("primary_endpoint_key"),
        "primary_endpoint_label": sweeper_data["clinical"].get("primary_endpoint_label"),
        "primary_endpoint_unit": sweeper_data["clinical"].get("primary_endpoint_unit"),
        "primary_endpoint_value": sweeper_data["clinical"].get("primary_endpoint_value"),
        "primary_endpoint_method": sweeper_data["clinical"].get("primary_endpoint_method"),
        "comparator_primary_value": sweeper_data["clinical"].get("comparator_primary_value"),
        "hazard_ratio": sweeper_data["clinical"].get("hazard_ratio"),
        "secondary_endpoints": sweeper_data["clinical"].get("secondary_endpoints", []),
        "clinical_confidence": sweeper_data["clinical"].get("confidence", 0.0),
        "endpoints_summary": build_endpoints_summary(
            _resolved_entry,
            sweeper_data["clinical"].get("primary_endpoint_value"),
            {s.get("key"): s.get("value") for s in sweeper_data["clinical"].get("secondary_endpoints", [])},
        ) if _resolved_entry else [],

        # Safety data — Competitor (serious/severe AEs, therapy-area-agnostic)
        "competitor_severe_ae_rate": sweeper_data["safety"].get("severe_ae_rate"),
        "competitor_ae_is_estimated": sweeper_data["safety"].get("is_estimated", True),
        "competitor_adverse_events": sweeper_data["safety"].get("adverse_events", []),

        # Safety data — Drug itself
        "drug_severe_ae_rate": sweeper_data.get("drug_safety", {}).get("severe_ae_rate"),
        "drug_ae_is_estimated": sweeper_data.get("drug_safety", {}).get("is_estimated", True),
        "drug_adverse_events": sweeper_data.get("drug_safety", {}).get("adverse_events", []),

        # Anti-hallucination envelope
        "data_quality": sweeper_data.get("data_quality", {"status": "unavailable", "missing_fields": [], "issues": []}),

        # Epidemiology (from cached DB drug when available; else unavailable — not fabricated)
        "epidemiology": (db_drug.get("epidemiology") if db_drug and db_drug.get("epidemiology") else {
            "addressable_population": None,
            "sources": "Not available — regional incidence not resolved",
        }),

        # Pricing
        "global_price_inr": pricing["global_price_inr"],
        "competitor_price_inr": pricing["competitor_price_inr"],
        "route": (db_drug.get("route") if db_drug else None) or (_resolved_entry.get("route_default") if _resolved_entry else None),
        "treatment_model": (db_drug.get("treatment_model") if db_drug else None) or (_resolved_entry.get("treatment_model") if _resolved_entry else None),
        "route_form": db_drug.get("route_form", "Oral") if db_drug else "Oral",
        "common_strengths": db_drug.get("common_strengths", "") if db_drug else "",
        "key_brands": db_drug.get("key_brands", "") if db_drug else "",
        "manufacturers": db_drug.get("manufacturers", "") if db_drug else "",

        # Data source tracking
        "data_sources": {
            "clinical": sweeper_data["clinical"]["source_url"],
            "competitor": sweeper_data["competitor"]["source_url"],
            "safety": sweeper_data["safety"]["source_url"],
            "drug_safety": sweeper_data.get("drug_safety", {}).get("source_url"),
            "clinical_tier": sweeper_data["clinical"]["source_tier"],
            "competitor_tier": sweeper_data["competitor"]["source_tier"],
            "safety_tier": sweeper_data["safety"]["source_tier"]
        },
        "local_hero_applied": sweeper_data["local_hero_applied"],

        "category": get_drug_category_by_indication(indication),
        "is_estimated": sweeper_data["clinical"].get("primary_endpoint_value") is None
    }

    # The Brain: which modules/metrics apply + site-of-care coverage
    drug_profile["applicability"] = resolve_applicability(
        drug_profile, selected_indication, pricing.get("global_price_inr"), region_code
    )

    # Always cache the drug profile - we have valid data even if regional status is uncertain
    # The regional status can be retried next time; but the drug clinical/pricing data is valid now
    try:
        await db.drugs.update_one(
            {"name": {"$regex": f"^{drug_name}$", "$options": "i"}},
            {"$set": drug_profile},
            upsert=True
        )
        logger.info(f"[Commercial Brain] Cached drug profile for {drug_name}")
    except Exception as e:
        logger.error(f"Cache error: {str(e)}")
    
    return drug_profile


@api_router.get("/drugs/{drug_id}/indications")
async def get_drug_indications(drug_id: str, name: Optional[str] = None):
    """
    Get available indications for a drug (for multi-indication selection).
    First checks MULTI_INDICATION_DRUGS for comprehensive FDA-approved indications,
    then falls back to database or web search.
    
    Args:
        drug_id: The drug ID (can be UUID-based dynamic ID)
        name: Optional drug name (used when drug_id is UUID-based)
    """
    # Query DB based on name or ID if available
    db_drug = None
    drug_name_searched = name or ""

    if drug_id and not drug_id.startswith("dynamic-"):
        # Try finding by explicit 'id' field first
        db_drug = await db.drugs.find_one({"id": drug_id}, {"_id": 0})
        # If not found, try finding by 'name' assuming drug_id might be the name
        if not db_drug:
            db_drug = await db.drugs.find_one({"name": {"$regex": f"^{drug_id}$", "$options": "i"}}, {"_id": 0})
            
    if not db_drug and name:
        db_drug = await db.drugs.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}}, {"_id": 0})
        
    if db_drug:
        # CACHE INVALIDATION: Stale intelligence check (30 Days)
        # If the data is incredibly old, we discard the cache so WebSweeper scrapes for new FDA indications/prices.
        # We also ensure the record was seeded with a last_updated timestamp.
        is_stale = False
        if "last_updated" in db_drug:
            from datetime import timedelta
            try:
                # Assuming ISO format string or datetime object
                last_up = db_drug["last_updated"]
                if isinstance(last_up, str):
                    last_up = datetime.fromisoformat(last_up.replace('Z', '+00:00'))
                # Since datetime.now(timezone.utc) is timezone aware, last_up must be too
                if last_up.tzinfo is None:
                    last_up = last_up.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) - last_up > timedelta(days=30):
                    is_stale = True
                    logger.info(f"[Cache] Record for {db_drug.get('name')} is >30 days old. Forcing WebSweeper refresh.")
            except Exception as e:
                logger.error(f"[Cache Invalidation Error] {e}")
        
        if not is_stale:
            indications = db_drug.get("indications_available", [])
            if indications:
                return {
                    "drug_name": db_drug.get("name", drug_name_searched).title(),
                    "indications": indications,
                    "has_multiple": len(indications) > 1
                }
        else:
            # Safe Fallback: even if stale, if WebSweeper drops the ball, use DB indications
            indications = db_drug.get("indications_available", [])
            # We explicitly don't set db_drug = None entirely so we can fallback to it below.
            stale_db_drug = db_drug
            db_drug = None # Force fallback to WebSweeper
    
    # At this point, `db_drug` is either populated or None.
    # If the exact match failed and the user gave a generic "dynamic-" ID without a name,
    # try web search for dynamic drugs.
    if not db_drug:
        if drug_id.startswith("dynamic-"):
            # Parse drug name from the dynamic ID
            parsed_name = drug_id.replace("dynamic-", "")
            # If it's a UUID, use the provided name parameter
            if "-" in parsed_name and len(parsed_name) == 36:
                # UUID-based ID - use the name parameter if provided
                if name:
                    # Return single indication from the provided name
                    # We don't have multi-indication data for unknown drugs
                    logger.info(f"[Indications] Unknown drug with name parameter: {name}")
                    return {
                        "drug_name": name.title(),
                        "indications": [],
                        "has_multiple": False
                    }
                return {
                    "drug_name": "Unknown",
                    "indications": [],
                    "has_multiple": False
                }
            display_name = parsed_name.replace("-", " ").title()
            drug_info = await web_search_drug_info(display_name)
            
            # Safe Indications Fallback
            sweeper_inds = drug_info.get("indications_available", [])
            if not sweeper_inds and 'stale_db_drug' in locals() and stale_db_drug:
                sweeper_inds = stale_db_drug.get("indications_available", [])
                
            return {
                "drug_name": display_name,
                "indications": sweeper_inds,
                "has_multiple": len(sweeper_inds) > 1
            }
        raise HTTPException(status_code=404, detail="Drug not found")
    
    # Prefer dynamically extracted or DB indications
    indications_available = db_drug.get("indications_available", [])
    if indications_available:
        return {
            "drug_name": db_drug.get("name"),
            "indications": indications_available,
            "has_multiple": len(indications_available) > 1
        }
    
    # Fallback if somehow missing
    return {
        "drug_name": db_drug.get("name"),
        "indications": [],
        "has_multiple": False
    }

@api_router.get("/heor/regional-data")
async def get_heor_regional_data(
    response: Response,
    drug_name: str,
    region_code: str = "IN",
    indication: Optional[str] = None,
):
    """
    HEOR Ecosystem Data - Includes dynamic market intelligence.
    """
    # Explicitly set CORS for this endpoint as it has been problematic
    response.headers["Access-Control-Allow-Origin"] = frontend_url
    response.headers["Access-Control-Allow-Credentials"] = "true"
    """
    Regional HEOR Data Engine — returns factual local costs for a drug,
    its AE management burden, and standard-of-care costs in the target region.

    Tier 1: Tavily web search (3 parallel queries) + GPT-4 extraction  ← when keys present
    Tier 2: DEFAULT_REGIONAL_PRICES_BY_INDICATION / REGIONAL_CONSTANTS tables     ← always-available fallback
    """
    import asyncio as _asyncio
    import json as _json

    region = region_code.upper()
    constants = REGIONAL_CONSTANTS.get(region, REGIONAL_CONSTANTS["IN"])
    currency = constants["currency_symbol"]
    regulator = constants.get("regulator", "Local Authority")

    # ── Tier 1: Try Google/Tavily + OpenAI ────────────────────────────────────
    if (tavily_client or os.environ.get('GOOGLE_API_KEY') or os.environ.get('GOOGLE_SEARCH_API_KEY')) and openai_client:
        try:
            region_label = {"IN": "India", "SG": "Singapore", "AE": "UAE / Abu Dhabi"}.get(region, region)
            indication_str = indication or "chronic disease therapy"

            # 4 parallel searches (added logistics)
            search_tasks = [
                execute_web_search(
                    f'"{drug_name}" price cost {region_label} site:moh.gov.sg OR "Agency for Care Effectiveness" OR hospital formulary',
                    max_results=4
                ),
                execute_web_search(
                    f'"cost of illness" OR "adverse event management cost" "{indication_str}" {region_label} "real world evidence"',
                    max_results=4
                ),
                execute_web_search(
                    f'"standard of care" cost "{indication_str}" {region_label} treatment guidelines',
                    max_results=4
                ),
                execute_web_search(
                    f'"{drug_name}" vs "standard of care" "route of administration" OR "dosing regimen" OR "infusion" OR "oral" prescribing information',
                    max_results=4
                ),
            ]
            results = await _asyncio.gather(*search_tasks, return_exceptions=True)

            def safe_content(r):
                if isinstance(r, Exception) or not r:
                    return ""
                return "\n".join(x.get("content", "") for x in r.get("results", []))

            context = f"""
--- LOCAL PRICING ({region_label}) ---
{safe_content(results[0])}

--- LOCAL AE MANAGEMENT COSTS ({region_label}) ---
{safe_content(results[1])}

--- LOCAL STANDARD OF CARE ({region_label}) ---
{safe_content(results[2])}

--- LOGISTICAL BURDEN & DOSING ---
{safe_content(results[3])}
"""
            gpt_response = await _asyncio.to_thread(
                openai_client.chat.completions.create,
                model="gpt-4-turbo",
                response_format={"type": "json_object"},
                temperature=0.0,
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are a regional Health Economist for {region_label} ({regulator}).
Task: Extract factual local costs and logistical administration modalities for the drug, AE management, and standard of care from the provided search context.

CRITICAL RULES:
1. DO NOT apply foreign exchange (FX) conversions. If the exact factual cost in {region_label}'s local currency is not found in the text, you MUST return null for that field.
2. Do not hallucinate or estimate numbers. Return null if unsure.

LOGISTICAL INSIGHT GENERATION RULE:
You must extract the treatment regimen, route, and care setting for both the primary asset and the competitor. 
You must also generate a 1-2 sentence `objective_insight` comparing the administration modalities.
- Tone: Strictly objective, HEOR-focused, and clinical.
- Constraint: DO NOT use subjective value judgments (e.g., never use words like "better," "worse," "easier," or "harder").
- Focus: Center the insight on Resource Utilization (e.g., infusion chair capacity, inpatient vs. outpatient) and HRQoL/Logistical burden (chronic adherence vs. acute recovery).

Return ONLY valid JSON:
{{
  "regional_economics": {{
    "currency_symbol": "{currency}",
    "drug_base_cost": <number or null>,
    "standard_of_care_cost": <number or null>,
    "ae_management_cost": <number or null>,
    "sources": "<cite specific local registry or journal found, or 'Not found in search context'>",
    "is_estimated": false
  }},
  "logistics": {{
    "our_asset": {{
      "regimen": "<String: e.g., 'OD', 'BID', 'Continuous', 'q3w'>",
      "route": "<String: e.g., 'Oral', 'IV Infusion', 'Surgical Resection'>",
      "setting": "<String: e.g., 'At-Home', 'Inpatient', 'Outpatient Clinic'>"
    }},
    "competitor": {{
      "regimen": "<String>",
      "route": "<String>",
      "setting": "<String>"
    }},
    "objective_insight": "<String: Max 2 sentences following the Logistical Insight Generation Rule>"
  }}
}}"""
                    },
                    {
                        "role": "user",
                        "content": f"Drug: {drug_name}\nRegion: {region_label}\nIndication: {indication_str}\nContext:\n{context}"
                    }
                ]
            )

            parsed = _json.loads(gpt_response.choices[0].message.content)
            econ = parsed.get("regional_economics", {})
            logistics = parsed.get("logistics", {
                "our_asset": {"regimen": "Unknown", "route": "Unknown", "setting": "Unknown"},
                "competitor": {"regimen": "Unknown", "route": "Unknown", "setting": "Unknown"},
                "objective_insight": "Insufficient data in guidelines to compare logistical endpoints."
            })

            # Fill any nulls from constants fallback (partial results are fine)
            drug_price = econ.get("drug_base_cost")
            ae_cost = econ.get("ae_management_cost")
            soc_cost = econ.get("standard_of_care_cost")
            is_estimated = econ.get("is_estimated", False)
            sources = econ.get("sources", "Tavily web search")

            # Patch nulls from regional lookup tables
            if drug_price is None:
                drug_price_info = await get_regional_price(drug_name, indication or "", region)
                drug_price = drug_price_info["monthly_price"]
                is_estimated = True
                sources = f"{sources}; Drug price from regional lookup table"
                
            if ae_cost is None:
                ae_cost = constants["hospitalization_cost"]
                is_estimated = True

            if soc_cost is None:
                soc_lower = (indication or "").lower()
                soc_entry = next(
                    (DEFAULT_REGIONAL_PRICES_BY_INDICATION[k][region]
                     for k in DEFAULT_REGIONAL_PRICES_BY_INDICATION
                     if k != "default" and k in soc_lower),
                    DEFAULT_REGIONAL_PRICES_BY_INDICATION["default"].get(region, 100000)
                )
                soc_cost = round(soc_entry * 0.5)  # SoC is typically ~50% of innovative drug
                is_estimated = True

            return {
                "drug_name": drug_name,
                "region_code": region,
                "currency_symbol": currency,
                "drug_base_cost": round(drug_price),
                "ae_management_cost": round(ae_cost),
                "standard_of_care_cost": round(soc_cost),
                "sources": sources,
                "is_estimated": is_estimated,
                "data_available": True,
                "logistics": logistics
            }

        except Exception as e:
            logger.warning(f"[HEOR] Tavily/GPT path failed for {drug_name}/{region}: {e}. Falling back to constants.")

    # ── Tier 2: Regional constants fallback (always reliable) ─────────────────
    drug_price_info = await get_regional_price(drug_name, indication or "", region)
    drug_price = drug_price_info["monthly_price"]

    ae_cost = constants["hospitalization_cost"]   # AE management cost per episode

    # SoC: indication-matched default pricing at ~50% of innovative drug price
    soc_lower = (indication or "").lower()
    soc_entry = next(
        (DEFAULT_REGIONAL_PRICES_BY_INDICATION[k][region]
         for k in DEFAULT_REGIONAL_PRICES_BY_INDICATION
         if k != "default" and k in soc_lower),
        DEFAULT_REGIONAL_PRICES_BY_INDICATION["default"].get(region, 100000)
    )
    soc_cost = round(soc_entry * 0.5)

    source_label = {
        "IN": "NPPA / CDSCO 2026 reference prices",
        "SG": "MOH Singapore / ACE 2026 reference prices",
        "AE": "DOH Abu Dhabi 2026 reference prices",
    }.get(region, "Regional lookup table")

    return {
        "drug_name": drug_name,
        "region_code": region,
        "currency_symbol": currency,
        "drug_base_cost": round(drug_price),
        "ae_management_cost": round(ae_cost),
        "standard_of_care_cost": round(soc_cost),
        "sources": source_label,
        "is_estimated": True,
        "data_available": True,
        "logistics": {
            "our_asset": {"regimen": "Unknown", "route": "Unknown", "setting": "Unknown"},
            "competitor": {"regimen": "Unknown", "route": "Unknown", "setting": "Unknown"},
            "objective_insight": "Insufficient HEOR data in regional fallback."
        }
    }


async def _web_sweeper_safety(drug_name: str, region_code: str) -> dict:
    """
    Fetch the serious/severe adverse-event rate for a drug via search + GPT.
    Returns { severe_ae_rate: float|None, adverse_events: list, is_estimated: bool }.
    Anti-hallucination: when no source is available the rate is None (not a guess).
    """
    import asyncio as _asyncio, json as _json

    unavailable = {"severe_ae_rate": None, "adverse_events": [], "is_estimated": True}

    if not ((tavily_client or os.environ.get('GOOGLE_API_KEY') or os.environ.get('GOOGLE_SEARCH_API_KEY')) and openai_client):
        return unavailable

    try:
        results = await execute_web_search(
            f'"{drug_name}" serious adverse events rate percentage safety prescribing information',
            max_results=5
        )
        content = "\n".join(r.get("content", "") for r in results.get("results", []))[:2500]
        if not content.strip():
            return unavailable
        resp = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": "You are a clinical safety expert. Extract only values stated in the text; use null if not stated. Return only a JSON object."},
                {"role": "user", "content": (
                    f'From this text about {drug_name}, extract:\n'
                    '{ "severe_ae_rate": <fraction 0-1 or null>, "adverse_events": ["ae1", "ae2"] }\n\n'
                    "Text:\n" + content
                )}
            ]
        )
        raw = re.sub(r"```json|```", "", resp.choices[0].message.content.strip())
        parsed = _json.loads(raw)
        rate = parsed.get("severe_ae_rate")
        return {"severe_ae_rate": rate, "adverse_events": parsed.get("adverse_events") or [],
                "is_estimated": rate is None}
    except Exception as e:
        logger.warning(f"[Safety Sweeper] Error for {drug_name}: {e} — returning unavailable")
        return unavailable


@api_router.get("/competitor/analyze")

async def analyze_competitor(competitor_name: str, region_code: str = "IN", indication: Optional[str] = None):
    """
    Analyze a competitor drug to get its base cost, clinical endpoints, and AE management cost
    for the TPP Benchmarker comparison
    """
    logger.info(f"[Competitor Analysis] Analyzing: {competitor_name} (region={region_code}, indication={indication})")
    
    regional_constants = REGIONAL_CONSTANTS.get(region_code.upper(), REGIONAL_CONSTANTS["IN"])
    
    # Get conversion rate from regions DB
    conversion_rate = 1.0
    try:
        region_doc = await db.regions.find_one({"code": region_code.upper()}, {"_id": 0, "conversion_rate_from_inr": 1})
        if region_doc and region_doc.get("conversion_rate_from_inr"):
            conversion_rate = float(region_doc["conversion_rate_from_inr"])
    except Exception:
        pass  # Leave conversion_rate as 1.0 on any error
    
    # Try to get pricing from database or known drugs
    competitor_lower = competitor_name.lower().strip()
    
    # Check if it's a known drug with pricing
    base_cost = None
    
    # Try to get from known regional pricing (in INR, will be converted)
    drug_regional_prices = {
        "semaglutide": {"IN": 25000, "SG": 450, "AE": 1200},
        "wegovy": {"IN": 25000, "SG": 450, "AE": 1200},
        "tirzepatide": {"IN": 35000, "SG": 550, "AE": 1500},
        "zepbound": {"IN": 35000, "SG": 550, "AE": 1500},
        "mounjaro": {"IN": 35000, "SG": 550, "AE": 1500},
        "entresto": {"IN": 4500, "SG": 180, "AE": 450},
        "tenecteplase": {"IN": 80000, "SG": 2000, "AE": 5000},
        "metalyse": {"IN": 80000, "SG": 2000, "AE": 5000},
        "fezolinetant": {"IN": 6000, "SG": 250, "AE": 650},
        "veozah": {"IN": 6000, "SG": 250, "AE": 650},
        "romosozumab": {"IN": 18000, "SG": 600, "AE": 1600},
        "evenity": {"IN": 18000, "SG": 600, "AE": 1600},
    }
    
    # Curated serious/severe adverse-event rates for known drugs (from FDA labels).
    # These are real safety figures — NOT fabricated efficacy endpoints. The
    # primary efficacy endpoint is left to the sweeper / manual entry so nothing
    # therapy-inappropriate is invented for a competitor.
    drug_severe_ae = {
        "semaglutide": 0.12, "wegovy": 0.12,
        "tirzepatide": 0.15, "zepbound": 0.15, "mounjaro": 0.15,
        "entresto": 0.09,
        "tenecteplase": 0.05, "metalyse": 0.05,
        "fezolinetant": 0.04, "veozah": 0.04,
        "romosozumab": 0.07, "evenity": 0.07,
    }

    # Find matching drug (price + curated AE rate)
    curated_ae = None
    for drug_key, prices in drug_regional_prices.items():
        if drug_key in competitor_lower or competitor_lower in drug_key:
            base_cost = prices.get(region_code.upper(), prices.get("IN"))
            curated_ae = drug_severe_ae.get(drug_key)
            break

    # Efficacy endpoints are not fabricated for competitors — surfaced as null
    primary_endpoint_value = None
    source = None

    # Real FDA label / DailyMed / PubMed URLs for known drugs
    DRUG_FDA_URLS = {
        "semaglutide": {
            "label": "FDA Label (Wegovy / Semaglutide)",
            "url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2021/215256s000lbl.pdf",
            "trial_label": "SELECT Trial Publication (PubMed)",
            "trial_url": "https://pubmed.ncbi.nlm.nih.gov/37952959/"
        },
        "wegovy": {
            "label": "FDA Label (Wegovy / Semaglutide)",
            "url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2021/215256s000lbl.pdf",
            "trial_label": "SELECT Trial Publication (PubMed)",
            "trial_url": "https://pubmed.ncbi.nlm.nih.gov/37952959/"
        },
        "tirzepatide": {
            "label": "FDA Label (Zepbound / Tirzepatide)",
            "url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2023/217834s000lbl.pdf",
            "trial_label": "SURMOUNT Trial Publications (PubMed)",
            "trial_url": "https://pubmed.ncbi.nlm.nih.gov/?term=SURMOUNT+tirzepatide"
        },
        "zepbound": {
            "label": "FDA Label (Zepbound / Tirzepatide)",
            "url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2023/217834s000lbl.pdf",
            "trial_label": "SURMOUNT Trial Publications (PubMed)",
            "trial_url": "https://pubmed.ncbi.nlm.nih.gov/?term=SURMOUNT+tirzepatide"
        },
        "entresto": {
            "label": "FDA Label (Entresto / Sacubitril-Valsartan)",
            "url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2015/207620lbl.pdf",
            "trial_label": "PARADIGM-HF Publication (NEJM)",
            "trial_url": "https://www.nejm.org/doi/full/10.1056/NEJMoa1409077"
        },
        "tenecteplase": {
            "label": "FDA Label (TNKase / Tenecteplase)",
            "url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2000/103911lbl.pdf",
            "trial_label": "EXTEND-IA TNK Publication (NEJM)",
            "trial_url": "https://www.nejm.org/doi/full/10.1056/NEJMoa1716405"
        },
        "metalyse": {
            "label": "MOH Guidelines (Metalyse / Tenecteplase)",
            "url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2000/103911lbl.pdf",
            "trial_label": "EXTEND-IA TNK Publication (NEJM)",
            "trial_url": "https://www.nejm.org/doi/full/10.1056/NEJMoa1716405"
        },
        "fezolinetant": {
            "label": "FDA Label (Veozah / Fezolinetant)",
            "url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2023/216578s000lbl.pdf",
            "trial_label": "SKYLIGHT Publications (PubMed)",
            "trial_url": "https://pubmed.ncbi.nlm.nih.gov/?term=SKYLIGHT+fezolinetant"
        },
        "veozah": {
            "label": "FDA Label (Veozah / Fezolinetant)",
            "url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2023/216578s000lbl.pdf",
            "trial_label": "SKYLIGHT Publications (PubMed)",
            "trial_url": "https://pubmed.ncbi.nlm.nih.gov/?term=SKYLIGHT+fezolinetant"
        },
        "romosozumab": {
            "label": "FDA Label (Evenity / Romosozumab)",
            "url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2019/761062s000lbl.pdf",
            "trial_label": "ARCH Trial Publication (NEJM)",
            "trial_url": "https://www.nejm.org/doi/full/10.1056/NEJMoa1708322"
        },
        "evenity": {
            "label": "FDA Label (Evenity / Romosozumab)",
            "url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2019/761062s000lbl.pdf",
            "trial_label": "ARCH Trial Publication (NEJM)",
            "trial_url": "https://www.nejm.org/doi/full/10.1056/NEJMoa1708322"
        },
    }

    # Regional price database source URLs
    PRICE_SOURCE_URLS = {
        "IN": {
            "label": "NPPA Drug Price List (India)",
            "url": "https://www.nppaindia.nic.in/en/ceiling-price-2/"
        },
        "SG": {
            "label": "MOH Singapore Drug Price List",
            "url": "https://www.moh.gov.sg/cost-financing/healthcare-schemes-subsidies/drug-subsidies"
        },
        "AE": {
            "label": "DOH Abu Dhabi Formulary",
            "url": "https://www.haad.ae/haad/tabid/58/Default.aspx"
        },
    }

    url_entry = None
    for drug_key in DRUG_FDA_URLS:
        if drug_key in competitor_lower or competitor_lower in drug_key:
            url_entry = DRUG_FDA_URLS[drug_key]
            break

    price_url_entry = PRICE_SOURCE_URLS.get(region_code.upper(), {})
    
    ae_is_estimated = False
    if curated_ae is not None:
        ae_rate = curated_ae
        source_label = url_entry["label"] if url_entry else f"FDA Label & Published Trials — {competitor_name}"
        source_url = url_entry["url"] if url_entry else None
    else:
        # Web search for a real safety figure — None if unavailable (no guessing)
        safety_result = await _web_sweeper_safety(competitor_name, region_code)
        ae_rate = safety_result.get("severe_ae_rate")
        ae_is_estimated = ae_rate is None
        source_label = "Web Intelligence via search" if ae_rate is not None else "Not available — enter manually"
        source_url = (f"https://pubmed.ncbi.nlm.nih.gov/?term={competitor_name.replace(' ', '+')}+clinical+trial"
                      if ae_rate is not None else None)

    # Also attach the trial URL as a secondary source
    trial_label = url_entry["trial_label"] if url_entry else None
    trial_url = url_entry["trial_url"] if url_entry else None

    # AE management cost only when a real AE rate exists
    ae_mgmt_cost = int(ae_rate * 3 * regional_constants.get("complication_cost", regional_constants["hospitalization_cost"])) if ae_rate is not None else None

    # Price estimate is allowed but explicitly flagged (not a silent fabrication)
    price_is_estimated = False
    if base_cost is None:
        base_cost = int(200000 * conversion_rate)
        price_is_estimated = True

    return {
        "competitor_name": competitor_name,
        "region_code": region_code,
        "indication": indication,
        "base_cost": base_cost,
        "base_cost_is_estimated": price_is_estimated,
        "primary_endpoint_value": primary_endpoint_value,   # null — not fabricated
        "severe_ae_rate": ae_rate,
        "ae_is_estimated": ae_is_estimated,
        "ae_mgmt_cost": ae_mgmt_cost,
        "total_cost": (base_cost + ae_mgmt_cost) if ae_mgmt_cost is not None else base_cost,
        "is_estimated": price_is_estimated or ae_is_estimated,
        "currency_symbol": regional_constants["currency_symbol"],
        # Structured source info for clickable frontend links
        "source": source_label,
        "source_label": source_label,
        "source_url": source_url,
        "trial_label": trial_label,
        "trial_url": trial_url,
        "price_source": price_url_entry.get("label", f"Regional Price Database ({region_code})"),
        "price_url": price_url_entry.get("url", None),
    }


@api_router.get("/drugs/{drug_id}")
async def get_drug(drug_id: str):
    """Get full drug profile - checks database first, then creates dynamically"""
    # First try direct database lookup by ID
    drug = await db.drugs.find_one({"id": drug_id}, {"_id": 0})
    if drug:
        return drug
    
    # If it's a dynamic ID with just the drug name (not UUID)
    if drug_id.startswith("dynamic-"):
        # Check if the ID contains UUID pattern
        id_part = drug_id.replace("dynamic-", "")
        is_uuid = len(id_part) == 36 and id_part.count("-") == 4
        
        if is_uuid:
            # It's a UUID-based ID - try to find by ID in database
            cached = await db.drugs.find_one({"id": drug_id}, {"_id": 0})
            if cached:
                return cached
            # UUID not found - return error
            raise HTTPException(status_code=404, detail="Drug not found")
        else:
            # It's a drug name (e.g., dynamic-semaglutide)
            drug_name = id_part.replace("-", " ").title()
            
            # Check if already cached by name
            cached = await db.drugs.find_one({"name": {"$regex": f"^{drug_name}$", "$options": "i"}}, {"_id": 0})
            if cached:
                return cached
            
            # Analyze dynamically
            return await analyze_drug_dynamically(drug_name)
    
    # Regular database lookup
    drug = await db.drugs.find_one({"id": drug_id}, {"_id": 0})
    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found")
    return drug

def calculate_value_engine(primary_endpoint_value, indication: str,
                           competitor_ae_rate, region_code: str) -> dict:
    """
    VALUE ENGINE (therapy-area-agnostic).

    Total downstream cost = (Event Probability × Event Cost)
                          + (Productivity Loss Months × Monthly Wage)
                          + (Adverse-Event Management Cost)

    The primary endpoint is normalised PER INDICATION by the Therapy Area
    Registry into an `event_probability` (relative downstream event / treatment-
    failure proxy). There is no therapy-area-specific math here. When the primary endpoint is
    missing, `event_probability` is None and the event/productivity components
    are reported as null (data_incomplete=True) rather than fabricated.
    """
    region_code = (region_code or "IN").upper()
    rc = REGIONAL_CONSTANTS.get(region_code, REGIONAL_CONSTANTS["IN"])
    entry = resolve_indication(indication)

    # Registry-normalised downstream event probability (None if endpoint missing)
    event_probability = event_probability_from_primary(entry, primary_endpoint_value) if entry else None

    # Event cost: the registry chooses which regional cost applies to this area
    cost_key = (entry["event"]["cost_key"] if entry else "major_event_cost")
    event_cost = rc.get(cost_key, rc.get("major_event_cost", 150000))
    event_label = entry["event"]["label"] if entry else "Downstream clinical event"

    data_incomplete = event_probability is None

    if not data_incomplete:
        c_event = event_probability * event_cost
        # Productivity loss scales with event probability (proxy months lost to a failure/event)
        productivity_loss_months = round(6.0 * event_probability, 2)
        c_prod = productivity_loss_months * rc.get("monthly_salary", 30000)
    else:
        c_event = None
        productivity_loss_months = None
        c_prod = None

    # Adverse-event management cost vs comparator — only when a real AE rate exists
    ae_mgmt_cost = rc.get("complication_cost", rc.get("hospitalization_cost", 150000))
    if competitor_ae_rate is not None:
        c_adverse_events = float(competitor_ae_rate) * 3 * ae_mgmt_cost
    else:
        c_adverse_events = None

    known = [x for x in (c_event, c_prod, c_adverse_events) if x is not None]
    total_liability = round(sum(known), 2) if known else None

    def _r(x):
        return round(x, 2) if x is not None else None

    return {
        "event_probability": round(event_probability, 4) if event_probability is not None else None,
        "event_label": event_label,
        "c_event": _r(c_event),
        "productivity_loss_months": productivity_loss_months,
        "c_prod": _r(c_prod),
        "c_adverse_events": _r(c_adverse_events),
        "total_liability": total_liability,
        "data_incomplete": data_incomplete,
        "currency_symbol": rc.get("currency_symbol", "₹"),
        "breakdown": {
            "event_cost": _r(c_event),
            "productivity_loss": _r(c_prod),
            "adverse_event_cost": _r(c_adverse_events),
        }
    }


# ──────────────────────────────────────────────────────────────────────────
# The Brain: Applicability & Relevance Engine
# Decides WHICH modules/metrics apply to a given drug+indication, and models
# site-of-care coverage (IPD / OPD / HOME) — because the same drug prices and
# reimburses differently depending on where it is administered.
# ──────────────────────────────────────────────────────────────────────────

# Which sites a route can physically be delivered in
_ROUTE_SETTINGS = {
    "iv_bolus": ["IPD"],
    "iv_infusion": ["IPD", "OPD"],
    "sc_injection": ["OPD", "HOME"],
    "oral": ["HOME"],
}


def _resolve_route(drug: dict, entry: Optional[dict]) -> str:
    route = (drug or {}).get("route")
    if route in _ROUTE_SETTINGS:
        return route
    if entry and entry.get("route_default") in _ROUTE_SETTINGS:
        return entry["route_default"]
    return "unknown"


def resolve_applicability(drug: dict, indication: str, list_price, region_code: str) -> dict:
    """Return the applicability profile (the 'Brain' output). Conservative +
    flagged when inputs are unknown — never assumes a favourable model."""
    region = (region_code or "IN").upper()
    rc = REGIONAL_CONSTANTS.get(region, REGIONAL_CONSTANTS["IN"])
    rules = SETTING_COVERAGE_RULES.get(region, SETTING_COVERAGE_RULES["IN"])
    entry = resolve_indication(indication)
    issues = []

    treatment_model = (drug or {}).get("treatment_model") or (entry["treatment_model"] if entry else "unknown")
    route = _resolve_route(drug, entry)
    if route == "unknown":
        issues.append({"field": "route", "severity": "warning",
                       "message": "Route of administration unknown — assumed retail/home and not covered (conservative)."})

    feasible_settings = _ROUTE_SETTINGS.get(route, ["HOME"])

    # Duration model
    duration = {"acute_single_dose": 1, "chronic_ongoing": 12}.get(treatment_model)
    if treatment_model == "fixed_course":
        duration = (drug or {}).get("duration_periods") or 12

    # Setting-aware pricing: institutional/tender vs retail MRP
    mrp_mult = rc.get("retail_mrp_multiplier", 1.3)
    tender_price = float(list_price) if list_price is not None else None
    retail_price = round(tender_price * mrp_mult) if tender_price is not None else None

    coverage_by_setting = {}
    worst_oop = None
    covered_oop = None
    for site in ("IPD", "OPD", "HOME"):
        srule = rules.get(site, {})
        feasible = site in feasible_settings
        base_price = retail_price if srule.get("price_basis") == "retail_mrp" else tender_price
        covered_share = srule.get("covered_share", 0.0)
        oop = round(base_price * (1 - covered_share)) if base_price is not None else None
        coverage_by_setting[site] = {
            "feasible": feasible,
            "coverage": srule.get("coverage", "unknown") if feasible else "n/a",
            "price_basis": srule.get("price_basis"),
            "patient_oop_est": oop if feasible else None,
            "reason": srule.get("note"),
        }
        if feasible and oop is not None:
            if srule.get("coverage") == "covered":
                covered_oop = oop if covered_oop is None else min(covered_oop, oop)
            worst_oop = oop if worst_oop is None else max(worst_oop, oop)

    # Recommended real-world setting = the least-restrictive feasible site
    recommended = feasible_settings[-1] if feasible_settings else "HOME"

    # Coverage gap: OOP jump of the worst feasible setting vs a covered one
    gap_exists = False
    oop_jump = None
    worst_setting = None
    for site in ("HOME", "OPD"):
        cs = coverage_by_setting.get(site, {})
        if cs.get("feasible") and cs.get("coverage") in ("excluded", "conditional"):
            gap_exists = True
            worst_setting = site
            if covered_oop is not None and cs.get("patient_oop_est") is not None:
                oop_jump = cs["patient_oop_est"] - covered_oop
            break
    coverage_gap = {
        "exists": gap_exists, "worst_setting": worst_setting,
        "oop_jump_vs_covered": oop_jump,
        "note": ("Self-pay/retail OOP far exceeds the covered institutional price."
                 if gap_exists else "No material coverage gap at the recommended setting."),
    }

    # Financial assistance — driven by the coverage gap, not price alone
    monthly_wallet = rc.get("monthly_salary", 30000)
    recommended_oop = coverage_by_setting.get(recommended, {}).get("patient_oop_est")
    cost_burden_ratio = round(recommended_oop / monthly_wallet, 2) if (recommended_oop and monthly_wallet) else None

    # Real patient-support-programme data from the drug record (workbook), if present.
    # A named programme is evidence, not a guess — it overrides the heuristic.
    # Only a drug-SPECIFIC programme counts as evidence. Category boilerplate
    # (e.g. "Low-cost generic — Jan Aushadhi", repeated across 114 drugs) is
    # context, not a programme for this molecule, and must not drive the
    # assistance verdict.
    _programme_is_generic = bool((drug or {}).get("programme_is_generic"))
    psp_text = "" if _programme_is_generic else ((drug or {}).get("patient_program") or "")
    psp_sponsor = "" if _programme_is_generic else ((drug or {}).get("program_sponsor_type") or "")
    psp_lower = psp_text.lower()
    has_real_financial_psp = any(k in psp_lower for k in ("emi", "bogo", "financial", "subsid", "free", "assistance", "pap"))
    is_govt_free = any(k in psp_lower for k in ("govt", "government", "jan aushadhi", "janaushadhi", "family-planning", "family planning"))
    is_institutional = "institutional" in psp_lower or "hospital use" in psp_lower

    fa_relevant = bool(
        treatment_model != "acute_single_dose"
        and gap_exists
        and cost_burden_ratio is not None
        and cost_burden_ratio >= 0.5
    )
    # Real-world evidence adjusts the verdict in both directions
    if is_institutional or is_govt_free:
        fa_relevant = False
    elif has_real_financial_psp and treatment_model != "acute_single_dose":
        fa_relevant = True

    if fa_relevant:
        tier = "full_pap" if (cost_burden_ratio or 0) >= 1.5 else "copay_support"
        if has_real_financial_psp:
            fa_reason = f"Named programme available: {psp_text}" + (f" — {psp_sponsor}" if psp_sponsor else "")
        else:
            fa_reason = f"Recommended setting ({recommended}) is {coverage_by_setting[recommended]['coverage']} with OOP ≈ {cost_burden_ratio}× monthly income."
    else:
        tier = "none"
        if is_govt_free:
            fa_reason = f"Covered by a government programme — {psp_text}. No manufacturer assistance required."
        elif is_institutional or treatment_model == "acute_single_dose":
            fa_reason = "Administered in hospital — bundled in the admission claim; no patient assistance programme required."
        elif not gap_exists:
            fa_reason = "Covered at the recommended setting with manageable out-of-pocket cost — assistance not required."
        else:
            fa_reason = "Out-of-pocket burden below the assistance threshold."

    modules = {
        "tpp_benchmarker": True,
        "value_engine": True,
        "period_cash_flow": treatment_model != "acute_single_dose",
        "adherence": treatment_model != "acute_single_dose",
        "pap_deal_architect": fa_relevant,
    }

    return {
        "treatment_model": treatment_model,
        "route": route,
        "feasible_settings": feasible_settings,
        "duration_periods": duration,
        "cost_burden_ratio": cost_burden_ratio,
        "coverage_by_setting": coverage_by_setting,
        "recommended_setting": recommended,
        "coverage_gap": coverage_gap,
        "financial_assistance": {
            "relevant": fa_relevant, "tier": tier, "reason": fa_reason,
            "named_program": psp_text or None,
            "program_sponsor": psp_sponsor or None,
        },
        "modules": modules,
        "issues": issues,
    }


def generate_pdf_dossier(drug, region, calculation: dict):
    """
    Generate a minimal PDF dossier as a BytesIO buffer.
    Uses only stdlib (reportlab is optional) — falls back to plaintext PDF if unavailable.
    """
    import io
    from datetime import datetime

    buf = io.BytesIO()

    try:
        from reportlab.graphics.shapes import Drawing
        from reportlab.graphics.charts.barcharts import VerticalBarChart
        from reportlab.lib import colors
        from reportlab.lib.units import inch

        doc = SimpleDocTemplate(buf, pagesize=letter) # Changed A4 to letter
        styles = getSampleStyleSheet()
        story = []

        # Header
        story.append(Paragraph(f"The DROP Tax Value Dossier", styles["Title"]))
        story.append(Paragraph(f"{drug.name} — {drug.indication}", styles["Heading2"]))
        story.append(Paragraph(f"Region: {region.name}  |  Generated: {datetime.utcnow().strftime('%Y-%m-%d UTC')}", styles["Normal"]))
        story.append(Spacer(1, 24))

        # Financial Summary Table
        story.append(Paragraph("Financial Summary (Regional Analysis)", styles["Heading3"]))
        data_rows = [
            ["Metric", "Value"],
            ["Drug Monthly Cost", f"{region.currency_symbol}{calculation.get('drug_cost', 0):,.0f}"],
            ["Total Economic Liability", f"{region.currency_symbol}{calculation.get('total_liability', 0):,.0f}"],
            ["Competitor Base Cost", f"{region.currency_symbol}{calculation.get('competitor_base_cost', 0):,.0f}"],
            ["Competitor w/ Liability", f"{region.currency_symbol}{calculation.get('competitor_total_cost', 0):,.0f}"],
        ]
        t = Table(data_rows, colWidths=[2.5*inch, 2.5*inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.teal),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 30))

        # Visual Analysis section (CHART)
        story.append(Paragraph("Comparative Cost Analysis", styles["Heading3"]))
        story.append(Spacer(1, 12))
        
        drawing = Drawing(400, 200)
        data = [
            (calculation.get('drug_cost', 0), calculation.get('competitor_total_cost', 0))
        ]
        bc = VerticalBarChart()
        bc.x = 50
        bc.y = 50
        bc.height = 125
        bc.width = 300
        bc.data = data
        bc.strokeColor = colors.black
        bc.valueAxis.valueMin = 0
        bc.categoryAxis.categoryNames = [f"{drug.name}", f"{drug.competitor_name}"]
        bc.bars[0].fillColor = colors.teal
        bc.bars[1].fillColor = colors.lightgrey
        drawing.add(bc)
        story.append(drawing)
        
        story.append(Spacer(1, 20))
        story.append(Paragraph("Interpretation: Calculations incorporate regional daily wages, ICU costs, and logistical burdens to reveal the true cost-of-care beyond the list price.", styles["Italic"]))
        
        doc.build(story)
    except ImportError:
        # Fallback: minimal bare-bones PDF (valid percent-encoded text)
        ts = datetime.utcnow().strftime("%Y-%m-%d UTC")
        stream_content = f"BT /F1 12 Tf 72 750 Td (The DROP Tax Dossier - {drug.name}) Tj ET\n"
        text = (
            f"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            f"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            f"3 0 obj<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R/Resources<<>>/Contents 4 0 R>>endobj\n"
            f"4 0 obj<</Length {len(stream_content)}>>stream\n{stream_content}endstream\nendobj\n"
            f"xref\n0 5\n0000000000 65535 f\ntrailer<</Size 5/Root 1 0 R>>\nstartxref\n0\n%%EOF\n"
        )
        buf.write(text.encode("latin-1"))

    buf.seek(0)
    return buf


@api_router.post("/calculate")
async def calculate_liability(drug_id: str, region_code: str = "IN"):
    """
    VALUE ENGINE (therapy-area-agnostic)

    Total downstream cost = (Event Probability × Event Cost)
                          + (Productivity Loss × Monthly Wage)
                          + (Adverse-Event Management Cost)

    Event Probability is derived from the indication's PRIMARY endpoint via the
    Therapy Area Registry. Missing inputs stay null (data_incomplete) — never
    fabricated.
    """
    drug_data = await db.drugs.find_one({"id": drug_id}, {"_id": 0})
    if not drug_data:
        # For dynamic drug IDs (not yet cached), trigger analysis to build the profile
        if drug_id.startswith("dynamic-"):
            # Try to find by the dynamic id pattern or by any recently cached version
            # First try to find by matching pattern in DB
            drug_data = await db.drugs.find_one({"id": {"$regex": "^dynamic-"}}, {"_id": 0})
            
            if not drug_data:
                # No dynamic drug at all - raise a helpful error
                raise HTTPException(
                    status_code=404,
                    detail="Drug not yet analyzed. Please wait for analysis to complete."
                )
            # Use the most recently cached dynamic drug
        else:
            raise HTTPException(status_code=404, detail="Drug not found")
    
    region_data = await db.regions.find_one({"code": region_code}, {"_id": 0})
    if not region_data:
        raise HTTPException(status_code=404, detail="Region not found")
    
    region = RegionConfig(**region_data)
    
    # Extract generic clinical variables (None when unresolved — never fabricated)
    indication = drug_data.get("indication", "")
    primary_value = drug_data.get("primary_endpoint_value")
    competitor_ae_rate = drug_data.get("competitor_severe_ae_rate")

    # Run the therapy-area-agnostic value engine
    value = calculate_value_engine(primary_value, indication, competitor_ae_rate, region_code)
    data_incomplete = value["data_incomplete"]

    # Base per-period costs (list price × 12 periods standard assumption)
    drug_price_info = await get_regional_price(drug_data["name"], indication, region_code)
    comp_price_info = await get_regional_price(drug_data.get("competitor_name", "Standard of Care"), indication, region_code)
    _drug_monthly = drug_price_info["monthly_price"]
    _comp_monthly = comp_price_info["monthly_price"]
    drug_cost = _drug_monthly * 12 if _drug_monthly is not None else None
    competitor_base = _comp_monthly * 12 if _comp_monthly is not None else None
    ae_cost = value["c_adverse_events"] or 0
    competitor_total = (competitor_base + ae_cost) if competitor_base is not None else None

    total_liability = value["total_liability"]
    liability_ratio = round(total_liability / drug_cost, 2) if (total_liability is not None and drug_cost) else None

    # Applicability ("Brain") — reuse cached profile or recompute for this region
    applicability = drug_data.get("applicability") or resolve_applicability(
        drug_data, indication, drug_price_info["monthly_price"], region_code)

    # Data-quality envelope (anti-hallucination)
    data_quality = drug_data.get("data_quality") or {
        "status": "unavailable" if data_incomplete else "complete", "missing_fields": [], "issues": []}

    # Economic recommendation — honest when data is incomplete
    if drug_cost is None:
        signal = "INSUFFICIENT_DATA"
        message = ("No price could be resolved for this drug in this region, so the economic model "
                   "cannot be computed. Enter a price to proceed (no figure is estimated).")
    elif total_liability is None:
        signal = "INSUFFICIENT_DATA"
        message = "Primary endpoint unavailable — the value model cannot be computed. Enter the clinical endpoint to proceed (no figure is estimated)."
    elif competitor_base is None:
        signal = "INSUFFICIENT_DATA"
        message = ("No comparator price could be resolved, so the head-to-head economic argument "
                   "cannot be computed. Enter a comparator price to proceed.")
    else:
        signal = "POSITIVE" if total_liability > competitor_base else "NEUTRAL"
        message = (f"Total Cost of Care ({value['currency_symbol']}{total_liability:,.0f}) "
                   f"{'exceeds' if signal == 'POSITIVE' else 'is below'} competitor base cost "
                   f"({value['currency_symbol']}{competitor_base:,.0f}). Economic argument "
                   f"{'holds' if signal == 'POSITIVE' else 'needs refinement'}.")

    calculation_transparency = {
        "inputs": {
            "primary_endpoint": {
                "label": drug_data.get("primary_endpoint_label"),
                "value": primary_value,
                "unit": drug_data.get("primary_endpoint_unit"),
                "source": drug_data.get("data_sources", {}).get("clinical"),
                "is_estimated": drug_data.get("primary_endpoint_is_estimated", False),
                "method": drug_data.get("primary_endpoint_method"),
            },
            "competitor_ae_rate": {
                "value": competitor_ae_rate,
                "source": drug_data.get("data_sources", {}).get("safety"),
                "is_estimated": drug_data.get("competitor_ae_is_estimated", True),
                "method": "Extracted from label" if competitor_ae_rate is not None else "Not available",
            },
        },
        "formulas": {
            "event_probability": {
                "formula": "registry_normalised(primary_endpoint) → 1 - efficacy_score",
                "description": "Relative downstream event/failure proxy from the indication's primary endpoint",
                "inputs": f"primary_endpoint_value={primary_value}",
            },
            "c_event": {
                "formula": "event_probability × regional_event_cost",
                "description": f"Expected cost of a {value['event_label'].lower()}",
                "inputs": f"event_probability={value['event_probability']}",
            },
            "c_adverse_events": {
                "formula": "competitor_ae_rate × 3 × regional_ae_cost",
                "description": "Expected adverse-event management cost vs comparator",
                "inputs": f"competitor_ae_rate={competitor_ae_rate}",
            },
        },
        "regional_parameters": {"region": region.name, "currency": region.currency},
    }

    return {
        "status": "success",
        "meta": {
            "drug": drug_data.get("name"),
            "indication": drug_data.get("indication"),
            "category": drug_data.get("category"),
            "region": region.name,
            "currency": region.currency,
            "is_estimated": drug_data.get("is_estimated", True),
            "local_hero_applied": drug_data.get("local_hero_applied", False),
            "data_quality": data_quality,
        },
        "applicability": applicability,
        "data_quality": data_quality,
        # Model provenance: which economic parameters are still placeholders.
        # Output must not be read as measured fact while these are unsourced.
        "model_assumptions": {
            "unsourced": unsourced_assumptions(),
            "detail": MODEL_ASSUMPTIONS,
            "warning": ("Economic parameters (event costs, income, coverage shares) are "
                        "placeholders without an authoritative source. Drug-level facts are "
                        "never estimated, but model output is assumption-dependent."),
        },
        "source_provenance": drug_data.get("source_provenance"),
        "commercial_brain": {
            "event_probability": value["event_probability"],
            "event_label": value["event_label"],
            "c_event": value["c_event"],
            "productivity_loss_months": value["productivity_loss_months"],
            "c_prod": value["c_prod"],
            "c_adverse_events": value["c_adverse_events"],
            "data_incomplete": data_incomplete,
            # Generic clinical endpoints
            "primary_endpoint_key": drug_data.get("primary_endpoint_key"),
            "primary_endpoint_label": drug_data.get("primary_endpoint_label"),
            "primary_endpoint_unit": drug_data.get("primary_endpoint_unit"),
            "primary_endpoint_value": primary_value,
            "primary_endpoint_method": drug_data.get("primary_endpoint_method"),
            "comparator_primary_value": drug_data.get("comparator_primary_value"),
            "hazard_ratio": drug_data.get("hazard_ratio"),
            "secondary_endpoints": drug_data.get("secondary_endpoints", []),
            "endpoints_summary": drug_data.get("endpoints_summary", []),
            "clinical_confidence": drug_data.get("clinical_confidence", 0.0),
            # Safety
            "competitor_severe_ae_rate": competitor_ae_rate,
            "drug_severe_ae_rate": drug_data.get("drug_severe_ae_rate"),
            "competitor_ae_is_estimated": drug_data.get("competitor_ae_is_estimated", True),
            "drug_ae_is_estimated": drug_data.get("drug_ae_is_estimated", True),
            "logistics": drug_data.get("logistics"),
        },
        "calculation_transparency": calculation_transparency,
        "analysis": {
            "drug_id": drug_id,
            "drug_name": drug_data.get("name"),
            "region_code": region_code,
            "drug_cost": round(drug_cost, 2) if drug_cost is not None else None,
            "competitor_price": round(competitor_base, 2) if competitor_base is not None else None,
            "adverse_event_cost": round(ae_cost, 2),
            "projected_liability": total_liability,
            "liability_breakdown": value["breakdown"],
            "liability_ratio": liability_ratio,
            "competitor_total_cost": round(competitor_total, 2) if competitor_total is not None else None,
            "recommendation": {"signal": signal, "message": message},
        },
        "total_liability": total_liability,
        "drug_cost": round(drug_cost, 2) if drug_cost is not None else None,
        "competitor_base_cost": round(competitor_base, 2) if competitor_base is not None else None,
        "competitor_total_cost": round(competitor_total, 2) if competitor_total is not None else None,
        "breakdown": value["breakdown"],
        "currency": region.currency,
        "currency_symbol": value["currency_symbol"],
        "liability_ratio": liability_ratio,
        "recommendation": {"signal": signal, "message": message},
        "is_estimated": drug_data.get("is_estimated", True),
        "regional_availability": drug_data.get("regional_availability", {}),
    }

@api_router.post("/pap/recommend")
async def recommend_pap(
    drug_id: str,
    target_roi: float,
    patient_wallet_monthly: float,
    region_code: str = "IN"
):
    """
    Deal Architect - PAP recommendation based on affordability gap
    """
    drug_data = await db.drugs.find_one({"id": drug_id}, {"_id": 0})
    if not drug_data:
        raise HTTPException(status_code=404, detail="Drug not found")
    
    region_data = await db.regions.find_one({"code": region_code}, {"_id": 0})
    if not region_data:
        raise HTTPException(status_code=404, detail="Region not found")
    
    region = RegionConfig(**region_data)
    
    drug_price_inr = drug_data.get("global_price_inr")
    if not drug_price_inr:
        raise HTTPException(
            status_code=422,
            detail="No price on record for this drug — a patient-assistance scheme cannot be "
                   "modelled without one. Enter a price first (no figure is estimated).",
        )
    headline_price = drug_price_inr * region.conversion_rate_from_inr

    pap_result = calculate_pap_scheme(headline_price, patient_wallet_monthly, target_roi)
    
    return {
        **pap_result,
        "target_roi": target_roi,
        "patient_wallet_monthly": patient_wallet_monthly,
        "currency": region.currency_symbol,
        "drug_name": drug_data.get("name"),
        "region": region.name
    }

@api_router.get("/news/{drug_id}")
async def get_drug_news(drug_id: str, region: str = "Global"):
    """
    WEB SWEEPER - News Query (Threat Intelligence)
    Query: "{Drug_Name}" patent challenge generic filing
    Returns only relevant threat news items
    """
    # Get drug name from database
    if drug_id.startswith("dynamic-"):
        id_part = drug_id.replace("dynamic-", "")
        is_uuid = len(id_part) == 36 and id_part.count("-") == 4
        
        if is_uuid:
            drug_data = await db.drugs.find_one({"id": drug_id}, {"_id": 0, "name": 1})
            if drug_data:
                drug_name = drug_data.get("name", "")
            else:
                logger.warning(f"No drug found in DB for ID: {drug_id}")
                return {"summary": "The market landscape remains stable. No specific threats found for this identifier.", "sources": []}
        else:
            drug_name = id_part.replace("-", " ").title()
    else:
        drug_data = await db.drugs.find_one({"id": drug_id}, {"_id": 0, "name": 1})
        if not drug_data:
            return {"summary": "The market landscape remains stable. Drug not found in regional database.", "sources": []}
        drug_name = drug_data.get("name", "")
    
    logger.info(f"[Web Sweeper News] Fetching threats for: {drug_name} in region: {region}")
    
    # Use the Web Sweeper news protocol with region
    result = await web_sweeper_news(drug_name, region)
    
    if not result or not result.get("sources"):
        logger.info(f"No threats found for {drug_name} - market stable")
        return {"summary": "The market landscape for this asset remains stable with no immediate patent or generic threats detected.", "sources": []}
    
    return result

@api_router.post("/dossier/generate")
async def generate_dossier(drug_id: str, region_code: str = "IN"):
    """Generate and download PDF dossier with Commercial Brain data"""
    drug_data = await db.drugs.find_one({"id": drug_id}, {"_id": 0})
    if not drug_data:
        raise HTTPException(status_code=404, detail="Drug not found")
    
    region_data = await db.regions.find_one({"code": region_code}, {"_id": 0})
    if not region_data:
        raise HTTPException(status_code=404, detail="Region not found")
    
    region = RegionConfig(**region_data)
    
    # Calculate using the therapy-area-agnostic value engine
    primary_value = drug_data.get("primary_endpoint_value")
    competitor_ae_rate = drug_data.get("competitor_severe_ae_rate")
    value = calculate_value_engine(primary_value, drug_data.get("indication", ""), competitor_ae_rate, region_code)

    drug_price_inr = drug_data.get("global_price_inr")
    competitor_price_inr = drug_data.get("competitor_price_inr")
    if not drug_price_inr:
        raise HTTPException(
            status_code=422,
            detail="No price on record for this drug — a value dossier cannot be generated "
                   "without one. Enter a price first (no figure is estimated).",
        )
    drug_cost = drug_price_inr * region.conversion_rate_from_inr
    competitor_base = (competitor_price_inr * region.conversion_rate_from_inr) if competitor_price_inr else 0
    competitor_total = competitor_base + (value["c_adverse_events"] or 0)

    # Build calculation dict for PDF (None-safe when data is incomplete)
    calculation = {
        "total_liability": value["total_liability"] or 0,
        "drug_cost": drug_cost,
        "competitor_base_cost": competitor_base,
        "competitor_total_cost": competitor_total,
        "breakdown": {
            "event_cost": value["breakdown"]["event_cost"] or 0,
            "productivity_loss": value["breakdown"]["productivity_loss"] or 0,
            "adverse_event_cost": value["breakdown"]["adverse_event_cost"] or 0,
        }
    }

    # Create a minimal drug object for PDF
    class MinimalDrug:
        def __init__(self, data):
            self.name = data.get("name", "Unknown")
            self.indication = data.get("indication", "CardioMetabolic")
            self.mechanism_of_action = data.get("mechanism_of_action", "Under Investigation")
            self.launch_date = data.get("launch_date", "TBD")
            self.competitor_name = data.get("competitor_name", "Standard of Care")
    
    drug = MinimalDrug(drug_data)
    pdf_buffer = generate_pdf_dossier(drug, region, calculation)
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={drug.name}_Value_Dossier_{region.code}.pdf"
        }
    )

@api_router.get("/strategic-briefing/generate")
async def generate_strategic_briefing(
    drug_name: str,
    region_code: str = "IN",
    drug_cost: float = 0,
    total_liability: float = 0,
    competitor_name: str = "Standard of Care",
    pap_scheme: str = "None",
    severe_ae_rate: Optional[float] = None,
    primary_endpoint_value: Optional[float] = None,
    primary_endpoint_label: Optional[str] = None,
    indication: Optional[str] = None,
    deal_architect_status: str = "CURRENT MARKET REALITY",
    proposed_pap_scheme: str = "None",
    regulatory_override: str = "AI Auto-Detect",
):
    """
    Generates 5-7 strategic insights using:
    - 5 concurrent Tavily web searches (clinical, India access, HTA, competitors, local RWE)
    - GPT-4 LLM synthesis with the HEOR system prompt
    - Falls back to rule-based generation when OPENAI_API_KEY is not set.
    """
    import datetime
    import json as _json

    regional_constants = REGIONAL_CONSTANTS.get(region_code.upper(), REGIONAL_CONSTANTS["IN"])
    currency = regional_constants["currency_symbol"]
    risk_index = round(total_liability / drug_cost, 2) if drug_cost > 0 else 0.0
    unfunded = max(0, total_liability - drug_cost)
    ae_pct = round(severe_ae_rate * 100) if severe_ae_rate is not None else None
    ae_pct_text = f"{ae_pct}%" if ae_pct is not None else "data pending"
    monthly_cost = round(drug_cost / 12)
    _pe_label = primary_endpoint_label or "Primary endpoint"
    primary_text = (f"{primary_endpoint_value} ({_pe_label})" if primary_endpoint_value is not None else "data pending")

    # ── Dashboard metrics dict (passed to GPT as JSON) ─────────────────────────
    dashboard_metrics = {
        "drug_name": drug_name,
        "indication": indication or "N/A",
        "region": region_code.upper(),
        "drug_cost_annual": f"{currency}{int(drug_cost):,}",
        "total_downstream_liability": f"{currency}{int(total_liability):,}",
        "risk_weighted_cost_index": f"{risk_index:.2f}x",
        "unfunded_exposure": f"{currency}{int(unfunded):,}",
        "serious_ae_rate": ae_pct_text,
        "primary_endpoint": primary_text,
        "competitor": competitor_name,
        "pap_scheme": pap_scheme,
        "monthly_cost": f"{currency}{monthly_cost:,}",
        "deal_architect_status": deal_architect_status,
        "proposed_pap_scheme": proposed_pap_scheme,
        "regulatory_override": regulatory_override,
    }

    # ── Build regulatory override rule block ─────────────────────────────────────
    if regulatory_override == "AI Auto-Detect":
        regulatory_rule = """REGULATORY OVERRIDE RULE:
> The user has selected AI Auto-Detect. Determine the regulatory status of this asset using the search context provided. Make your best evidence-based determination."""
    else:
        regulatory_rule = f"""REGULATORY OVERRIDE RULE:
> ⚠️  ABSOLUTE USER OVERRIDE IN EFFECT  ⚠️
> The user (who is the regulatory expert) has locked the following as ground-truth for this asset: "{regulatory_override}"
> THIS IS ABSOLUTE FACT. You MUST completely ignore any search results, training data, or prior knowledge that contradicts this.
> Frame your ENTIRE 7-point strategic briefing and ALL MSL narratives around the fact that this drug is at this exact regulatory stage.
> Do NOT hedge, caveat, or say "reportedly" — the user has confirmed this status."""

    # ── System prompt ────────────────────────────────────────────────────────────
    SYSTEM_PROMPT = f"""You are a Principal Market Access Strategy Director and Medical Affairs Lead for the Indian healthcare market.

Task: Analyze the provided Drug Dashboard Metrics and search context. Identify the top 5 to 7 most critical strategic drivers. 

CRITICAL ANTI-HALLUCINATION RULES:
1. STRICT DATA ADHERENCE: You must explicitly differentiate between "Current Market Reality" and "Deal Architect Recommendations".
2. DEAL ARCHITECT SIMULATIONS: If a Patient Assistance Program (PAP) or pricing discount is listed under "Deal Architect" or marked as "Recommended", IT IS NOT A LIVE PROGRAM. It is a simulation to fix financial exposure.
3. MSL VIEW REFRAMING: If discussing a Deal Architect simulation, the `msl_view` MUST NOT say "I can enroll your patients today." You must frame it as a forward-looking strategy draft. 
   * Example format: "If this strategy is approved, MSLs will be equipped to say: 'Doctor, our new proposed program will halve the monthly cost...'"
4. ZERO HARDCODING: Dynamically generate the `category` titles and select ONE relevant emoji `icon` for each insight based on the actual data provided. 
5. {regulatory_rule}

Output Requirements (Strict JSON matching this schema exactly):
{{
  "meta": {{
    "drug_name": "[String]",
    "hero_metrics": {{
      "primary_metric_label": "[Dynamic Label]",
      "primary_metric_value": "[Dynamic Value]"
    }}
  }},
  "strategic_briefing": [
    {{
      "id": "[String]",
      "icon": "[Single Emoji]",
      "category": "[Dynamic Title, e.g., 'Proposed Affordability Strategy']",
      "boardroom_view": "[Financial/Strategic narrative for C-suite]",
      "msl_view": "[Clinical/Peer-to-peer translation for an MSL. Apply simulation rule if applicable.]"
    }}
  ]
}}"""

    # ── Fallback rule-based function (used when no OpenAI key) ──────────────────
    def _rule_based_briefing():
        """Fast, deterministic fallback using signal detection."""
        indication_lower = (indication or "").lower()
        _entry = resolve_indication(indication)
        _category = _entry["category"] if _entry else ""
        # Chronic, screenable cardiometabolic disease → diagnosis/screening penetration is a real access lever
        is_underdiagnosed = _category in ("CVD", "Metabolic")
        has_named_competitor = competitor_name not in ["Standard of Care", "SOC", "Comparator", ""]

        pap_monthly = monthly_cost
        if "1 Get 1" in pap_scheme or "bogo" in pap_scheme.lower():
            pap_monthly = round(monthly_cost / 2)
        elif "8 of 12" in pap_scheme:
            pap_monthly = round(monthly_cost * 8 / 12)
        elif "6 of 12" in pap_scheme:
            pap_monthly = round(monthly_cost * 6 / 12)

        insights = []
        ctr = 1

        def add(cat, bv, msl):
            nonlocal ctr
            insights.append({"id": f"insight_{ctr}", "category": cat,
                              "boardroom_view": bv, "msl_view": msl})
            ctr += 1

        # Regulatory posture insight — driven by user override
        if regulatory_override == "Approved (Commercial Launch)":
            add("Regulatory Approval & Commercial Launch Momentum",
                f"{drug_name} has received full regulatory approval for commercial launch. "
                f"The market access team must now pivot from CDSCO engagement to formulary inclusion and reimbursement dossier submission. "
                f"Speed-to-formulary is the primary value-capture lever in the approved 12-24 month window.",
                f"Doctor, {drug_name} is now fully approved and commercially available. "
                f"I can arrange immediate access for your patients — shall we review the dosing protocol and enrolment paperwork today?")
        elif regulatory_override == "Pending / Named-Patient Access":
            add("Named-Patient Access Strategy & Pre-Launch Positioning",
                f"{drug_name} is currently pending regulatory clearance — the named-patient program window is the primary access vehicle. "
                f"Proactive HCP engagement now locks in clinical champions ahead of commercial launch. "
                f"Failure to initiate named-patient framing risks ceding early adoption to a competitor.",
                f"Doctor, while formal clearance is pending, we have established a named-patient access pathway "
                f"so your highest-need patients can initiate {drug_name} immediately at no cost. "
                f"I can help you navigate the compassionate use application within 48 hours.")
        elif regulatory_override == "Unapproved / Compassionate Use Only":
            add("Compassionate Use Programme & Unapproved Access Strategy",
                f"{drug_name} is currently not approved in this market — all access must route through compassionate use or off-label pathways. "
                f"Regulatory team must establish a named-patient supply chain before any HCP engagement. "
                f"Risk: off-label use without institutional ethics board approval creates medico-legal exposure.",
                f"Doctor, {drug_name} is available exclusively through our compassionate use programme for patients with no remaining standard options. "
                f"I can initiate the ethics committee application and supply chain for your institution — "
                f"the process takes 2-4 weeks and requires documented treatment failure on established therapies.")
        else:  # AI Auto-Detect
            add("Regulatory Posture & Early Access Strategy",
                f"CDSCO clearance trajectory for {drug_name} is the primary market-entry gate. "
                f"The named-patient program window is open for early access pricing. "
                f"Failure to define value narrative now risks a discount-led launch precedent.",
                f"While formal CDSCO regulatory proceedings are active, we have established a rapid named-patient access pathway "
                f"so your highest-need patients can initiate {drug_name} immediately. "
                f"I can help you navigate the compassionate use application within 48 hours.")

        add("Financial Liability & Downstream Risk" if risk_index <= 1.5 else "Critical Liability Exposure & Drop-off Risk",
            f"Total downstream liability projected at {currency}{int(total_liability):,} vs. list price {currency}{int(drug_cost):,} (Index: {risk_index:.2f}x). "
            f"Unfunded exposure of {currency}{int(unfunded):,} is the primary patient-assistance financing argument. "
            f"Addressable through outcome-based contracts tied to the primary endpoint.",
            f"When I discuss total cost of care with your formulary committee, the {currency}{int(unfunded):,} in avoidable downstream costs is the headline figure. "
            f"Our managed-access program is designed to eliminate this gap and protect your patients from discontinuing therapy early.")

        if is_underdiagnosed:
            add("Diagnosis & Screening Penetration",
                f"{drug_name} treats a chronic, under-diagnosed condition — screening and diagnosis penetration is the single largest addressable-population multiplier. "
                f"A large share of eligible patients in this market remain undiagnosed or untreated to target. "
                f"Co-investment in screening directly expands the eligible pool and strengthens the reimbursement case.",
                f"Doctor, the biggest barrier to your patients benefiting from {drug_name} is whether they have been screened and diagnosed to target. "
                f"We can support screening initiatives at your centre to identify eligible patients.")

        if ae_pct is None:
            pass  # No serious-AE figure resolved — do not fabricate a safety claim
        elif ae_pct < 20:
            add("Safety Differentiation & Tolerability Advantage",
                f"A serious adverse-event rate of {ae_pct}% supports favourable formulary positioning versus comparators. "
                f"This safety delta supports a direct cost-offset claim on avoided hospitalisations. "
                f"Reimbursement dossiers should lead with this value-enhancing safety argument.",
                f"Doctor, a serious AE rate of {ae_pct}% means less time managing complications and a more predictable clinic schedule. "
                f"I can share the full safety-management protocol so your team is prepared from day one.")
        elif ae_pct >= 35:
            add("Safety Management Programme & AE Offset",
                f"A serious adverse-event rate of {ae_pct}% warrants a proactive management protocol to protect formulary positioning. "
                f"The hospitalisation cost offset materialises with a co-funded AE-management protocol at each centre. "
                f"Recommend this as a pre-condition to formulary inclusion.",
                f"Doctor, I want to be transparent about the serious AE rate of {ae_pct}% — your team should be fully equipped. "
                f"We provide clinical support and a structured protocol so patients can stay on therapy and reach trial-level outcomes.")

        if pap_scheme and pap_scheme not in ["None", "none", ""]:
            add("Patient Access Programme & Subsidy Architecture",
                f"Active PAP ({pap_scheme}) reduces effective monthly OOP to {currency}{pap_monthly:,}, structurally de-risking formulary adoption. "
                f"Recommend as primary anchor in payer negotiations. "
                f"Net annual saving per patient: {currency}{(monthly_cost - pap_monthly) * 12:,}.",
                f"Our {pap_scheme} program ensures your patients receive full treatment benefit at reduced cost. "
                f"I can enroll eligible patients directly — it typically takes 48 hours to activate.")
        else:
            add("Urgent Access Architecture Gap",
                f"No active PAP deployed. Full OOP exposure at {currency}{int(drug_cost):,}/year creates a significant early-discontinuation risk. "
                f"This will erode real-world outcomes. Immediate deal-architecture review is mandatory.",
                f"Currently no patient support program is in place, which puts your patients at significant financial-hardship risk within the first few months. "
                f"I would like to urgently explore assistance options with you.")

        if has_named_competitor:
            add(f"Head-to-Head Differentiation vs {competitor_name}",
                f"Primary comparator {competitor_name} anchors the payer price ceiling. "
                f"Total cost-of-care advantage emerges once {currency}{int(abs(total_liability - drug_cost)):,} in avoided downstream events is modelled into the cost-effectiveness case. "
                f"Formulary submissions must lead with full cost-of-care analysis, not list-price comparison.",
                f"Doctor, when comparing {drug_name} to {competitor_name}, the sticker price is the wrong lens. "
                f"When I model total costs — event hospitalisations and complications avoided — {drug_name} delivers equivalent or superior value.")

        add("Outcomes Preservation & Event Avoidance",
            f"Primary value proposition: improving the primary endpoint ({primary_text}) to avoid downstream clinical events. "
            f"Reimbursement dossiers should anchor on {currency}{round(total_liability * 0.25):,} of averted productivity loss and reduced caregiver burden. "
            f"Essential for public-scheme inclusion advocacy and outcome-based contracting.",
            f"Doctor, a stronger primary endpoint ({primary_text}) means fewer downstream events for your patient and preserved day-to-day function. "
            f"Families consistently report meaningful improvements in burden — increasingly captured in health-economic submissions.")

        primary_label = "Risk-Weighted Index" if risk_index > 1.3 else "Unfunded Exposure"
        primary_value = f"{risk_index:.2f}x" if risk_index > 1.3 else f"{currency}{int(unfunded):,}"

        return {
            "meta": {
                "drug_name": drug_name,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "hero_metrics": {
                    "primary_metric_label": primary_label,
                    "primary_metric_value": primary_value,
                    "secondary_metric_label": "List Price",
                    "secondary_metric_value": f"{currency}{int(drug_cost):,}",
                }
            },
            "strategic_briefing": insights[:7]
        }

    # ── Path A: OpenAI + 5 concurrent searches ─────────────────────────────────
    if openai_client and (tavily_client or os.environ.get('GOOGLE_API_KEY') or os.environ.get('GOOGLE_SEARCH_API_KEY')):
        try:
            async def _search(query):
                try:
                    r = await execute_web_search(query, max_results=4)
                    return "\n".join(x.get("content", "")[:300] for x in r.get("results", []) if x.get("content"))
                except Exception:
                    return ""

            # Run all 5 searches concurrently
            clinical, india_access, hta, competitors, local_rwe = await _asyncio.gather(
                _search(f'"{drug_name}" "{indication}" "Phase 3" primary endpoint results serious adverse events'),
                _search(f'"{drug_name}" "India" "CDSCO approval" OR "launch price" OR "patient assistance program" OR "PMJAY"'),
                _search(f'"{drug_name}" "ICER" OR "cost-effectiveness" OR "QALY" OR "NICE guidance"'),
                _search(f'"{drug_name}" competitors OR "standard of care" OR "market share" "{indication}"'),
                _search(f'"{drug_name}" OR "{indication}" "real-world evidence" India registry outcomes'),
            )

            aggregated_context = f"""
--- GLOBAL CLINICAL DATA ---
{clinical}

--- INDIA ACCESS & REGULATORY ---
{india_access}

--- GLOBAL HTA & PRICING ---
{hta}

--- COMPETITIVE THREATS ---
{competitors}

--- LOCAL INDIAN PUBLICATIONS & RWE ---
{local_rwe}
""".strip()

            response = await openai_client.chat.completions.create(
                model="gpt-4-turbo",
                response_format={"type": "json_object"},
                temperature=0.2,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": (
                        f"Dashboard Metrics: {_json.dumps(dashboard_metrics)}\n\n"
                        f"Real-Time Search Context:\n{aggregated_context}"
                    )},
                ],
            )

            result = _json.loads(response.choices[0].message.content)
            logger.info(f"[StrategicBriefing] GPT-4 generated {len(result.get('strategic_briefing', []))} insights for {drug_name}")
            return result

        except Exception as e:
            logger.error(f"[StrategicBriefing] OpenAI pipeline failed: {e} — falling back to rule-based")
            return _rule_based_briefing()

    # ── Path B: Tavily only (no OpenAI) — rule-based with optional Tavily context ──
    else:
        return _rule_based_briefing()


# Include router
app.include_router(api_router)

_extra_origins = [o for o in os.environ.get('CORS_ORIGINS', '').split(',') if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        frontend_url,
        "http://localhost:3000",
    ] + _extra_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

@app.on_event("startup")
async def startup_event():
    logger.info("The DROP Tax Commercial Suite started")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

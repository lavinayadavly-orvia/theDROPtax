"""
Seed script: Populate the MongoDB Atlas `regions` collection.
Run with: ./venv/bin/python seed_regions.py
"""
import os
import asyncio
import motor.motor_asyncio

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "droptax")

REGIONS = [
    {
        "code": "IN",
        "name": "India",
        "currency": "INR",
        "currency_symbol": "₹",
        "conversion_rate_from_inr": 1.0,
        "competitor_focus": "Generic & Biosimilar Competitors",
        "strategic_focus": "Affordability & Access Programs",
        "regulatory_body": "CDSCO",
        "hospitalization_cost": 45000,
        "outpatient_cost": 1500,
        "physician_fee_per_visit": 800,
        "administration_cost_per_period": 2500,
        "payer_segments": [
            {"code": "GOVT", "name": "Government Scheme", "description": "CGHS/ECHS Govt Rate", "copay_percent": 0.0, "pap_eligible": False, "net_price_pct": 0.40},
            {"code": "CORP", "name": "Corporate Insurance", "description": "Private Insurance", "copay_percent": 0.20, "pap_eligible": False, "net_price_pct": 0.80},
            {"code": "OOP", "name": "Out of Pocket", "description": "Patient Pays Full", "copay_percent": 1.0, "pap_eligible": True, "net_price_pct": 1.00},
        ]
    },
    {
        "code": "SG",
        "name": "Singapore",
        "currency": "SGD",
        "currency_symbol": "S$",
        "conversion_rate_from_inr": 0.016,
        "competitor_focus": "Innovative Therapies & Branded Generics",
        "strategic_focus": "Clinical Differentiation & HTA Submissions",
        "regulatory_body": "HSA",
        "hospitalization_cost": 8000,
        "outpatient_cost": 300,
        "physician_fee_per_visit": 150,
        "administration_cost_per_period": 400,
        "payer_segments": [
            {"code": "MEDISAVE", "name": "MediSave / MediShield", "description": "National Scheme", "copay_percent": 0.10, "pap_eligible": False, "net_price_pct": 0.60},
            {"code": "PRIVATE", "name": "Private Insurance", "description": "Shield Plan", "copay_percent": 0.15, "pap_eligible": False, "net_price_pct": 0.85},
            {"code": "OOP", "name": "Out of Pocket", "name": "Out of Pocket", "description": "Patient Pays Full", "copay_percent": 1.0, "pap_eligible": True, "net_price_pct": 1.00},
        ]
    },
    {
        "code": "AE",
        "name": "UAE",
        "currency": "AED",
        "currency_symbol": "د.إ",
        "conversion_rate_from_inr": 0.044,
        "competitor_focus": "Premium Innovative Therapies",
        "strategic_focus": "Reimbursement Listing & KOL Engagement",
        "regulatory_body": "DOH/MOHAP",
        "hospitalization_cost": 25000,
        "outpatient_cost": 500,
        "physician_fee_per_visit": 300,
        "administration_cost_per_period": 1200,
        "payer_segments": [
            {"code": "DAMAN", "name": "Daman / ADNIC", "description": "Government Insurance", "copay_percent": 0.20, "pap_eligible": False, "net_price_pct": 0.75},
            {"code": "PRIVATE", "name": "Private Insurance", "description": "Employer Coverage", "copay_percent": 0.10, "pap_eligible": False, "net_price_pct": 0.90},
            {"code": "OOP", "name": "Out of Pocket", "description": "Patient Pays Full", "copay_percent": 1.0, "pap_eligible": True, "net_price_pct": 1.00},
        ]
    },
]


async def seed():
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    # Clear old and re-seed
    await db.regions.delete_many({})
    result = await db.regions.insert_many(REGIONS)
    print(f"✅ Inserted {len(result.inserted_ids)} regions: IN, SG, AE")

    # Verify
    count = await db.regions.count_documents({})
    print(f"✅ Verified: {count} regions in MongoDB")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed())

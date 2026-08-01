"""
Core configuration and constants for the DROP Tax Commercial Suite
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from tavily import TavilyClient

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("droptax")

# Database
mongo_url = os.environ['MONGO_URL']
mongo_client = AsyncIOMotorClient(mongo_url)
db = mongo_client[os.environ['DB_NAME']]

# Tavily client
tavily_api_key = os.environ.get('TAVILY_API_KEY', '')
if tavily_api_key:
    tavily_client = TavilyClient(api_key=tavily_api_key)
else:
    tavily_client = None
    logger.warning("TAVILY_API_KEY not found - web search will use fallbacks")

import os
import pymongo
import sys

try:
    mongo_url = os.environ.get("MONGO_URL")
    if not mongo_url:
        print("SKIP: MONGO_URL not set — export it to test the connection (no hard-coded credentials).")
        sys.exit(0)
    print("Connecting to MongoDB...")
    client = pymongo.MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
    info = client.server_info()
    print("SUCCESS: Connected to MongoDB Atlas!")
    print(info)
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)

import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

mongo_db_url = os.getenv("MONGO_DB_URL")
mongo_db_name = os.getenv("MONGO_DB_NAME")

client = AsyncIOMotorClient(mongo_db_url)
database = client[mongo_db_name]

def get_mongo_client():
    return client

def get_database():
    return database
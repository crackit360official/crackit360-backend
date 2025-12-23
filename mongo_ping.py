import asyncio, certifi
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv()
MONGO_URL = os.getenv("MONGO_URL")
async def main():
    client = AsyncIOMotorClient(
        MONGO_URL,
        tls=True,
        tlsCAFile=certifi.where()
    )
    await client.admin.command("ping")
    print("✅ MongoDB TLS connection successful")
asyncio.run(main())

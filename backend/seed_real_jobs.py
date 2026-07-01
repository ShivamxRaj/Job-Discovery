import asyncio
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="d:\\ai\\.env")

from app.db.session import async_session_maker
from app.services.job_service import job_service

async def seed():
    print("Connecting to database and fetching real jobs from APIs...")
    async with async_session_maker() as db:
        count = await job_service.aggregate_jobs_from_remote_apis(db)
        print(f"Successfully fetched and ingested {count} real jobs into the database!")

if __name__ == "__main__":
    asyncio.run(seed())

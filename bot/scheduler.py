from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

# Persistent job store — jobs survive restarts
jobstores = {
    "default": SQLAlchemyJobStore(url="sqlite:///jobs.sqlite")
}

scheduler = AsyncIOScheduler(jobstores=jobstores)

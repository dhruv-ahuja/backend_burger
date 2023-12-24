import datetime as dt

from apscheduler.job import Job
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from src.config import utils


def schedule_tokens_deletion(delete_older_than: dt.datetime, scheduler: AsyncIOScheduler) -> Job:
    """Schedules the expired blacklisted tokens' deletion function to run daily."""

    job_id = "delete_expired_blacklisted_tokens"
    trigger = CronTrigger(hour=00, minute=5)

    job = utils.setup_job(
        scheduler,
        "src.services.auth:delete_expired_blacklisted_tokens",
        job_id,
        trigger,
        delete_older_than=delete_older_than,
    )
    logger.info(f"scheduled '{job_id}' job to run daily")

    return job

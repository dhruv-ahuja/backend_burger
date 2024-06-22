import datetime as dt
import subprocess


from apscheduler.job import Job
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from mypy_boto3_s3.service_resource import Bucket

from src.utils import config


def schedule_logs_upload_job(bucket: Bucket, scheduler: BackgroundScheduler) -> Job:
    """Schedules the S3 log upload job to run once a week."""

    job_id = "upload_s3_logs"
    trigger = CronTrigger(day_of_week="sun", hour=00, minute=5)

    job = config.setup_job(
        scheduler, lambda: config.gather_and_upload_s3_logs(bucket), job_id, trigger, max_instances=1
    )
    logger.info(f"scheduled '{job_id}' job to run weekly")

    return job


def schedule_tokens_deletion(delete_older_than: dt.datetime, scheduler: AsyncIOScheduler) -> Job:
    """Schedules the expired blacklisted tokens' deletion function to run daily."""

    job_id = "delete_expired_blacklisted_tokens"
    trigger = CronTrigger(hour=00, minute=5)

    job = config.setup_job(
        scheduler,
        "src.services.auth:delete_expired_blacklisted_tokens",
        job_id,
        trigger,
        delete_older_than=delete_older_than,
    )
    logger.info(f"scheduled '{job_id}' job to run daily")

    return job


def _run_price_prediction_script():
    """Runs the price prediction script, capturing any output and errors that happen during the process call."""

    script_path = "src/scripts/price_prediction.py"
    try:
        logger.info("running price prediction script")
        # Run the script and wait for it to complete
        result = subprocess.run(["python", script_path], capture_output=True, text=True, check=True)

        # Print the output from the script
        logger.info(f"Output from price prediction script: {result.stdout}")

        if result.stderr:
            logger.error(f"Errors or log ouputs from script: {result.stderr}")

    except subprocess.CalledProcessError as exc:
        logger.error(f"Error while running price prediction script: {exc}")
    else:
        logger.info("price prediction script ran successfully")


def schedule_price_prediction_run(scheduler: AsyncIOScheduler) -> Job:
    """Schedules the price prediction function to run daily."""

    job_id = "price_prediction_run"
    trigger = CronTrigger(hour=5, timezone=dt.UTC)

    job = config.setup_job(scheduler, _run_price_prediction_script, job_id, trigger)
    logger.info(f"scheduled '{job_id}' job to run daily")

    return job

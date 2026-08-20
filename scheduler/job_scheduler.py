"""
APScheduler-based Job Scheduler with randomized time-window execution and retry guards.
"""

import random
import time
import threading
from datetime import datetime, timedelta, time as dt_time
from typing import List
from loguru import logger
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger

from config.config_loader import AppConfig, TimeWindowConfig
from scheduler.tasks import SnapTaskExecutor


class JobScheduler:
    """Schedules and manages daily Snapchat execution jobs at randomized window minutes."""

    def __init__(self, config: AppConfig, task_executor: SnapTaskExecutor):
        self.config = config
        self.executor = task_executor
        self.scheduler = BackgroundScheduler()
        self._execution_lock = threading.Lock()

    def start(self) -> None:
        """Starts the APScheduler engine and registers daily random window triggers."""
        logger.info("Starting JobScheduler engine...")
        self.scheduler.start()
        
        # Schedule daily midnight recalculation of random execution minutes
        self.scheduler.add_job(
            self.schedule_daily_jobs,
            trigger=CronTrigger(hour=0, minute=1),
            id="daily_rescheduler_job",
            replace_existing=True,
        )

        # Immediately schedule jobs for today upon startup
        self.schedule_daily_jobs()
        logger.success("JobScheduler started successfully.")

    def shutdown(self) -> None:
        """Shuts down scheduler background threads."""
        logger.info("Shutting down JobScheduler...")
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def calculate_random_execution_time(self, window: TimeWindowConfig, target_date: datetime) -> datetime:
        """Calculates a random datetime within the window [start_time, end_time] for target_date."""
        start_h, start_m = map(int, window.start_time.split(":"))
        end_h, end_m = map(int, window.end_time.split(":"))

        start_dt = target_date.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
        end_dt = target_date.replace(hour=end_h, minute=end_m, second=0, microsecond=0)

        if end_dt <= start_dt:
            # Handle window spanning across midnight if configured
            end_dt += timedelta(days=1)

        total_seconds = int((end_dt - start_dt).total_seconds())
        random_offset_seconds = random.randint(0, max(0, total_seconds))

        return start_dt + timedelta(seconds=random_offset_seconds)

    def schedule_daily_jobs(self) -> None:
        """Generates random execution timestamps for configured time windows today."""
        now = datetime.now()
        logger.info(f"Generating randomized execution schedule for date: {now.strftime('%Y-%m-%d')}")

        for idx, window in enumerate(self.config.schedule.time_windows):
            run_time = self.calculate_random_execution_time(window, now)
            job_id = f"snap_job_window_{idx}_{now.strftime('%Y%m%d')}"

            if run_time < now:
                logger.info(f"Randomized run time {run_time.strftime('%H:%M:%S')} for window [{window.start_time}-{window.end_time}] has already passed today. Skipping.")
                continue

            logger.info(f"Scheduled Snap Job #{idx+1} for [{window.start_time} - {window.end_time}] at random time: {run_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            self.scheduler.add_job(
                self._guarded_execution_wrapper,
                trigger=DateTrigger(run_date=run_time),
                id=job_id,
                replace_existing=True,
            )

    def _guarded_execution_wrapper(self) -> None:
        """Lock-guarded execution wrapper to prevent duplicate runs and perform retries."""
        if not self._execution_lock.acquire(blocking=False):
            logger.warning("Another Snap Job execution is currently in progress. Skipping duplicate run.")
            return

        try:
            max_retries = self.config.schedule.max_retries
            retry_delay = self.config.schedule.retry_delay_seconds
            attempt = 0
            success = False

            while attempt <= max_retries and not success:
                attempt += 1
                logger.info(f"Executing Snap Job (Attempt {attempt}/{max_retries + 1})...")
                success = self.executor.run_snap_workflow()

                if not success and attempt <= max_retries:
                    logger.warning(f"Snap Job attempt {attempt} failed. Waiting {retry_delay}s before retry...")
                    time.sleep(retry_delay)

            if success:
                logger.success("Snap Job completed successfully.")
            else:
                logger.error(f"Snap Job failed after {max_retries + 1} attempts.")
        finally:
            self._execution_lock.release()

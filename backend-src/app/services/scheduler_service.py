import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
import schedule
import time
from threading import Thread
from ..services.job_scraper_service import JobScraperService
from ..core.config import settings

logger = logging.getLogger(__name__)

class JobSchedulerService:
    """Service for scheduling automated job fetching"""
    
    def __init__(self):
        self.job_scraper = JobScraperService()
        self.scheduler_thread = None
        self.is_running = False
        self.scheduled_jobs = {}
    
    def start_scheduler(self):
        """Start the background scheduler"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.is_running = True
        self.scheduler_thread = Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("Job scheduler started")
    
    def stop_scheduler(self):
        """Stop the background scheduler"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("Job scheduler stopped")
    
    def _run_scheduler(self):
        """Run the scheduler in a separate thread"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
                time.sleep(60)
    
    def schedule_daily_job_fetch(
        self, 
        queries: List[str], 
        location: str = None,
        limit_per_source: int = 50,
        time_str: str = "09:00"
    ):
        """
        Schedule daily job fetching
        
        Args:
            queries: List of job search queries
            location: Location filter
            limit_per_source: Number of jobs to fetch per source
            time_str: Time to run (format: "HH:MM")
        """
        def job_fetch_task():
            asyncio.run(self._fetch_jobs_task(queries, location, limit_per_source))
        
        schedule.every().day.at(time_str).do(job_fetch_task)
        
        self.scheduled_jobs["daily_fetch"] = {
            "queries": queries,
            "location": location,
            "limit_per_source": limit_per_source,
            "time": time_str,
            "type": "daily"
        }
        
        logger.info(f"Scheduled daily job fetch at {time_str} for queries: {queries}")
    
    def schedule_weekly_job_fetch(
        self, 
        queries: List[str], 
        location: str = None,
        limit_per_source: int = 100,
        day: str = "monday",
        time_str: str = "10:00"
    ):
        """
        Schedule weekly job fetching
        
        Args:
            queries: List of job search queries
            location: Location filter
            limit_per_source: Number of jobs to fetch per source
            day: Day of the week
            time_str: Time to run (format: "HH:MM")
        """
        def job_fetch_task():
            asyncio.run(self._fetch_jobs_task(queries, location, limit_per_source))
        
        getattr(schedule.every(), day.lower()).at(time_str).do(job_fetch_task)
        
        self.scheduled_jobs["weekly_fetch"] = {
            "queries": queries,
            "location": location,
            "limit_per_source": limit_per_source,
            "day": day,
            "time": time_str,
            "type": "weekly"
        }
        
        logger.info(f"Scheduled weekly job fetch on {day} at {time_str} for queries: {queries}")
    
    def schedule_custom_interval(
        self,
        job_id: str,
        queries: List[str],
        location: str = None,
        limit_per_source: int = 50,
        interval_hours: int = 6
    ):
        """
        Schedule custom interval job fetching
        
        Args:
            job_id: Unique identifier for this scheduled job
            queries: List of job search queries
            location: Location filter
            limit_per_source: Number of jobs to fetch per source
            interval_hours: Hours between runs
        """
        def job_fetch_task():
            asyncio.run(self._fetch_jobs_task(queries, location, limit_per_source))
        
        schedule.every(interval_hours).hours.do(job_fetch_task)
        
        self.scheduled_jobs[job_id] = {
            "queries": queries,
            "location": location,
            "limit_per_source": limit_per_source,
            "interval_hours": interval_hours,
            "type": "custom_interval"
        }
        
        logger.info(f"Scheduled custom job fetch every {interval_hours} hours for queries: {queries}")
    
    async def _fetch_jobs_task(self, queries: List[str], location: str, limit_per_source: int):
        """Background task to fetch jobs"""
        try:
            logger.info(f"Starting scheduled job fetch for queries: {queries}")
            
            total_jobs = 0
            for query in queries:
                result = await self.job_scraper.fetch_and_store_jobs(
                    query=query,
                    location=location,
                    limit_per_source=limit_per_source
                )
                total_jobs += result["total_jobs"]
                logger.info(f"Fetched {result['total_jobs']} jobs for query: {query}")
            
            logger.info(f"Scheduled job fetch completed. Total jobs: {total_jobs}")
            
        except Exception as e:
            logger.error(f"Error in scheduled job fetch: {e}")
    
    def get_scheduled_jobs(self) -> Dict[str, Any]:
        """Get information about all scheduled jobs"""
        return {
            "scheduler_running": self.is_running,
            "scheduled_jobs": self.scheduled_jobs,
            "next_run_times": [
                {
                    "job": str(job.job_func),
                    "next_run": job.next_run.isoformat() if job.next_run else None
                }
                for job in schedule.jobs
            ]
        }
    
    def cancel_scheduled_job(self, job_id: str):
        """Cancel a specific scheduled job"""
        if job_id in self.scheduled_jobs:
            # Note: schedule library doesn't have a direct way to cancel specific jobs
            # This is a limitation - you'd need to clear all jobs and reschedule
            del self.scheduled_jobs[job_id]
            logger.info(f"Cancelled scheduled job: {job_id}")
        else:
            logger.warning(f"Scheduled job not found: {job_id}")
    
    def clear_all_scheduled_jobs(self):
        """Clear all scheduled jobs"""
        schedule.clear()
        self.scheduled_jobs.clear()
        logger.info("Cleared all scheduled jobs")

# Global scheduler instance
scheduler_service = JobSchedulerService()

def setup_default_schedules():
    """Setup default job fetching schedules"""
    
    # Default job categories to fetch
    default_queries = [
        "software engineer",
        "data scientist",
        "machine learning engineer",
        "product manager",
        "devops engineer",
        "frontend developer",
        "backend developer",
        "full stack developer"
    ]
    
    # Schedule daily fetch at 9 AM
    scheduler_service.schedule_daily_job_fetch(
        queries=default_queries,
        limit_per_source=25,
        time_str="09:00"
    )
    
    # Schedule weekly comprehensive fetch on Monday at 10 AM
    scheduler_service.schedule_weekly_job_fetch(
        queries=default_queries,
        limit_per_source=100,
        day="monday",
        time_str="10:00"
    )
    
    logger.info("Default job schedules configured")

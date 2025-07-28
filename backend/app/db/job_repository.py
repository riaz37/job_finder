"""
Repository for job-related database operations
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from prisma import Prisma
from prisma.models import JobPost as DBJobPost
from app.models.job import JobPost, JobPostData, JobSite


class JobRepository:
    def __init__(self, db: Prisma):
        self.db = db
    
    async def create_job_post(self, job_data: JobPostData, embedding_id: str) -> DBJobPost:
        """Create a new job post in the database"""
        # Convert JobPostData to database format
        location_data = {}
        if job_data.location:
            location_data = {
                "city": job_data.location.city,
                "state": job_data.location.state,
                "country": job_data.location.country,
                "display_location": job_data.location.display_location,
                "is_remote": job_data.location.is_remote
            }
        
        requirements_data = {
            "job_types": [jt.value for jt in job_data.job_type] if job_data.job_type else [],
            "skills": job_data.skills or [],
            "experience_range": job_data.experience_range,
            "job_level": job_data.job_level,
            "job_function": job_data.job_function,
            "work_from_home_type": job_data.work_from_home_type
        }
        
        salary_data = {}
        if job_data.compensation:
            salary_data = {
                "min_amount": job_data.compensation.min_amount,
                "max_amount": job_data.compensation.max_amount,
                "currency": job_data.compensation.currency,
                "interval": job_data.compensation.interval.value if job_data.compensation.interval else None,
                "salary_source": job_data.compensation.salary_source
            }
        
        return await self.db.jobpost.create({
            "title": job_data.title,
            "companyName": job_data.company_name or "Unknown",
            "jobUrl": job_data.job_url,
            "location": location_data,
            "description": job_data.description or "",
            "requirements": requirements_data,
            "salaryInfo": salary_data,
            "embeddingId": embedding_id
        })
    
    async def get_job_by_url(self, job_url: str) -> Optional[DBJobPost]:
        """Get a job post by its URL to check for duplicates"""
        return await self.db.jobpost.find_first(
            where={"jobUrl": job_url}
        )
    
    async def get_jobs_by_urls(self, job_urls: List[str]) -> List[DBJobPost]:
        """Get multiple job posts by their URLs for batch duplicate checking"""
        return await self.db.jobpost.find_many(
            where={"jobUrl": {"in": job_urls}}
        )
    
    async def get_recent_jobs(self, hours: int = 24) -> List[DBJobPost]:
        """Get jobs scraped within the last N hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return await self.db.jobpost.find_many(
            where={"scrapedAt": {"gte": cutoff_time}},
            order_by={"scrapedAt": "desc"}
        )
    
    async def get_jobs_by_company(self, company_name: str) -> List[DBJobPost]:
        """Get all jobs from a specific company"""
        return await self.db.jobpost.find_many(
            where={"companyName": {"contains": company_name, "mode": "insensitive"}},
            order_by={"scrapedAt": "desc"}
        )
    
    async def search_jobs_by_title(self, title_keywords: List[str]) -> List[DBJobPost]:
        """Search jobs by title keywords"""
        # Create OR conditions for each keyword
        title_conditions = [
            {"title": {"contains": keyword, "mode": "insensitive"}}
            for keyword in title_keywords
        ]
        
        return await self.db.jobpost.find_many(
            where={"OR": title_conditions},
            order_by={"scrapedAt": "desc"}
        )
    
    async def get_jobs_with_salary_range(self, min_salary: Optional[int] = None, max_salary: Optional[int] = None) -> List[DBJobPost]:
        """Get jobs within a salary range"""
        conditions = []
        
        if min_salary is not None:
            conditions.append({
                "OR": [
                    {"salaryInfo": {"path": ["min_amount"], "gte": min_salary}},
                    {"salaryInfo": {"path": ["max_amount"], "gte": min_salary}}
                ]
            })
        
        if max_salary is not None:
            conditions.append({
                "OR": [
                    {"salaryInfo": {"path": ["min_amount"], "lte": max_salary}},
                    {"salaryInfo": {"path": ["max_amount"], "lte": max_salary}}
                ]
            })
        
        where_clause = {"AND": conditions} if conditions else {}
        
        return await self.db.jobpost.find_many(
            where=where_clause,
            order_by={"scrapedAt": "desc"}
        )
    
    async def get_applied_job_urls(self, user_id: str) -> List[str]:
        """Get URLs of jobs the user has already applied to"""
        applications = await self.db.application.find_many(
            where={"userId": user_id},
            include={"jobPost": True}
        )
        return [app.jobPost.jobUrl for app in applications]
    
    async def delete_old_jobs(self, days: int = 30) -> int:
        """Delete jobs older than specified days"""
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        result = await self.db.jobpost.delete_many(
            where={"scrapedAt": {"lt": cutoff_time}}
        )
        return result
    
    async def get_job_count_by_site(self) -> Dict[str, int]:
        """Get count of jobs by site for analytics"""
        # This would require raw SQL or aggregation - simplified version
        all_jobs = await self.db.jobpost.find_many()
        site_counts = {}
        
        for job in all_jobs:
            # Extract site from job_url or requirements
            site = "unknown"
            if "linkedin.com" in job.jobUrl:
                site = "linkedin"
            elif "indeed.com" in job.jobUrl:
                site = "indeed"
            elif "ziprecruiter.com" in job.jobUrl:
                site = "zip_recruiter"
            elif "glassdoor.com" in job.jobUrl:
                site = "glassdoor"
            
            site_counts[site] = site_counts.get(site, 0) + 1
        
        return site_counts
    
    async def update_job_embedding(self, job_id: str, embedding_id: str) -> Optional[DBJobPost]:
        """Update the embedding ID for a job post"""
        return await self.db.jobpost.update(
            where={"id": job_id},
            data={"embeddingId": embedding_id}
        )
    
    async def batch_create_jobs(self, jobs_data: List[tuple]) -> List[DBJobPost]:
        """Batch create multiple job posts for better performance"""
        created_jobs = []
        
        for job_data, embedding_id in jobs_data:
            try:
                job = await self.create_job_post(job_data, embedding_id)
                created_jobs.append(job)
            except Exception as e:
                # Log error but continue with other jobs
                print(f"Error creating job {job_data.title}: {e}")
                continue
        
        return created_jobs
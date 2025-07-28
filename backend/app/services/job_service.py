"""
Service for job searching and management using JobSpy integration
"""
import asyncio
from typing import List, Optional, Dict, Any, Set
from datetime import datetime, date
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import hashlib

from jobspy import scrape_jobs
from jobspy.model import Site as JobSpySite, JobType as JobSpyJobType, Country

from app.models.job import (
    JobSearchCriteria, JobPostData, JobSearchResult, JobMatchResult,
    JobSearchFilters, JobSite, JobTypeEnum, JobLocation, JobCompensation,
    CompensationInterval
)
from app.models.preferences import UserPreferencesData
from app.db.job_repository import JobRepository
from app.services.embedding_service import EmbeddingService


class JobService:
    def __init__(self, job_repo: JobRepository, embedding_service: EmbeddingService):
        self.job_repo = job_repo
        self.embedding_service = embedding_service
        self._site_mapping = {
            JobSite.LINKEDIN: JobSpySite.LINKEDIN,
            JobSite.INDEED: JobSpySite.INDEED,
            JobSite.ZIP_RECRUITER: JobSpySite.ZIP_RECRUITER,
            JobSite.GLASSDOOR: JobSpySite.GLASSDOOR,
            JobSite.GOOGLE: JobSpySite.GOOGLE,
            JobSite.BAYT: JobSpySite.BAYT,
            JobSite.NAUKRI: JobSpySite.NAUKRI
        }
        self._job_type_mapping = {
            JobTypeEnum.FULL_TIME: JobSpyJobType.FULL_TIME,
            JobTypeEnum.PART_TIME: JobSpyJobType.PART_TIME,
            JobTypeEnum.CONTRACT: JobSpyJobType.CONTRACT,
            JobTypeEnum.TEMPORARY: JobSpyJobType.TEMPORARY,
            JobTypeEnum.INTERNSHIP: JobSpyJobType.INTERNSHIP,
            JobTypeEnum.PER_DIEM: JobSpyJobType.PER_DIEM,
            JobTypeEnum.NIGHTS: JobSpyJobType.NIGHTS,
            JobTypeEnum.OTHER: JobSpyJobType.OTHER,
            JobTypeEnum.SUMMER: JobSpyJobType.SUMMER,
            JobTypeEnum.VOLUNTEER: JobSpyJobType.VOLUNTEER
        }
    
    async def search_jobs(self, criteria: JobSearchCriteria) -> JobSearchResult:
        """Search for jobs using JobSpy with the given criteria"""
        search_timestamp = datetime.utcnow()
        all_jobs = []
        errors = []
        sites_searched = []
        
        # Convert our criteria to JobSpy format
        jobspy_sites = [self._site_mapping[site] for site in criteria.sites]
        jobspy_job_types = [self._job_type_mapping[jt] for jt in criteria.job_types] if criteria.job_types else None
        
        # Search each location and search term combination
        for search_term in criteria.search_terms:
            for location in criteria.locations if criteria.locations else [None]:
                try:
                    # Run JobSpy scraping in thread pool to avoid blocking
                    loop = asyncio.get_event_loop()
                    with ThreadPoolExecutor() as executor:
                        df_result = await loop.run_in_executor(
                            executor,
                            self._scrape_jobs_sync,
                            jobspy_sites,
                            search_term,
                            location,
                            criteria.distance,
                            criteria.is_remote,
                            jobspy_job_types[0] if jobspy_job_types else None,
                            criteria.easy_apply,
                            criteria.results_per_site,
                            criteria.hours_old
                        )
                    
                    if not df_result.empty:
                        jobs = self._convert_dataframe_to_jobs(df_result)
                        all_jobs.extend(jobs)
                        sites_searched.extend([job.site for job in jobs])
                
                except Exception as e:
                    error_msg = f"Error searching {search_term} in {location}: {str(e)}"
                    errors.append(error_msg)
                    print(error_msg)
        
        # Remove duplicates based on job URL
        unique_jobs = self._deduplicate_jobs(all_jobs)
        
        return JobSearchResult(
            jobs=unique_jobs,
            total_found=len(unique_jobs),
            search_criteria=criteria,
            search_timestamp=search_timestamp,
            sites_searched=list(set(sites_searched)),
            errors=errors
        )
    
    def _scrape_jobs_sync(self, sites: List[JobSpySite], search_term: str, location: Optional[str],
                         distance: int, is_remote: bool, job_type: Optional[JobSpyJobType],
                         easy_apply: Optional[bool], results_wanted: int, hours_old: Optional[int]) -> pd.DataFrame:
        """Synchronous wrapper for JobSpy scraping"""
        return scrape_jobs(
            site_name=sites,
            search_term=search_term,
            location=location,
            distance=distance,
            is_remote=is_remote,
            job_type=job_type.value if job_type else None,
            easy_apply=easy_apply,
            results_wanted=results_wanted,
            hours_old=hours_old,
            country_indeed="usa",
            description_format="markdown"
        )
    
    def _convert_dataframe_to_jobs(self, df: pd.DataFrame) -> List[JobPostData]:
        """Convert JobSpy DataFrame to our JobPostData models"""
        jobs = []
        
        for _, row in df.iterrows():
            try:
                # Parse location
                location = None
                if pd.notna(row.get('location')):
                    location_str = str(row['location'])
                    location = JobLocation(
                        display_location=location_str,
                        is_remote=bool(row.get('is_remote', False))
                    )
                    # Try to parse city, state, country from location string
                    location_parts = location_str.split(', ')
                    if len(location_parts) >= 1:
                        location.city = location_parts[0]
                    if len(location_parts) >= 2:
                        location.state = location_parts[1]
                    if len(location_parts) >= 3:
                        location.country = location_parts[2]
                
                # Parse compensation
                compensation = None
                if any(pd.notna(row.get(field)) for field in ['min_amount', 'max_amount', 'interval']):
                    compensation = JobCompensation(
                        min_amount=float(row['min_amount']) if pd.notna(row.get('min_amount')) else None,
                        max_amount=float(row['max_amount']) if pd.notna(row.get('max_amount')) else None,
                        currency=str(row.get('currency', 'USD')),
                        interval=CompensationInterval(row['interval']) if pd.notna(row.get('interval')) else None,
                        salary_source=str(row.get('salary_source')) if pd.notna(row.get('salary_source')) else None
                    )
                
                # Parse job types
                job_types = []
                if pd.notna(row.get('job_type')):
                    job_type_str = str(row['job_type'])
                    # JobSpy returns comma-separated job types
                    for jt in job_type_str.split(', '):
                        try:
                            job_types.append(JobTypeEnum(jt.lower().replace(' ', '')))
                        except ValueError:
                            # Skip unknown job types
                            continue
                
                # Parse date
                date_posted = None
                if pd.notna(row.get('date_posted')):
                    if isinstance(row['date_posted'], date):
                        date_posted = row['date_posted']
                    else:
                        try:
                            date_posted = pd.to_datetime(row['date_posted']).date()
                        except:
                            pass
                
                # Parse skills
                skills = []
                if pd.notna(row.get('skills')):
                    skills_str = str(row['skills'])
                    skills = [skill.strip() for skill in skills_str.split(', ') if skill.strip()]
                
                # Parse emails
                emails = []
                if pd.notna(row.get('emails')):
                    emails_str = str(row['emails'])
                    emails = [email.strip() for email in emails_str.split(', ') if email.strip()]
                
                job = JobPostData(
                    title=str(row.get('title', '')),
                    company_name=str(row.get('company', '')) if pd.notna(row.get('company')) else None,
                    job_url=str(row.get('job_url', '')),
                    job_url_direct=str(row.get('job_url_direct')) if pd.notna(row.get('job_url_direct')) else None,
                    location=location,
                    description=str(row.get('description', '')) if pd.notna(row.get('description')) else None,
                    company_url=str(row.get('company_url')) if pd.notna(row.get('company_url')) else None,
                    company_url_direct=str(row.get('company_url_direct')) if pd.notna(row.get('company_url_direct')) else None,
                    job_type=job_types if job_types else None,
                    compensation=compensation,
                    date_posted=date_posted,
                    emails=emails if emails else None,
                    is_remote=bool(row.get('is_remote', False)),
                    listing_type=str(row.get('listing_type')) if pd.notna(row.get('listing_type')) else None,
                    site=JobSite(row.get('site', 'unknown')),
                    
                    # Site-specific fields
                    job_level=str(row.get('job_level')) if pd.notna(row.get('job_level')) else None,
                    company_industry=str(row.get('company_industry')) if pd.notna(row.get('company_industry')) else None,
                    company_addresses=str(row.get('company_addresses')) if pd.notna(row.get('company_addresses')) else None,
                    company_num_employees=str(row.get('company_num_employees')) if pd.notna(row.get('company_num_employees')) else None,
                    company_revenue=str(row.get('company_revenue')) if pd.notna(row.get('company_revenue')) else None,
                    company_description=str(row.get('company_description')) if pd.notna(row.get('company_description')) else None,
                    company_logo=str(row.get('company_logo')) if pd.notna(row.get('company_logo')) else None,
                    banner_photo_url=str(row.get('banner_photo_url')) if pd.notna(row.get('banner_photo_url')) else None,
                    job_function=str(row.get('job_function')) if pd.notna(row.get('job_function')) else None,
                    skills=skills if skills else None,
                    experience_range=str(row.get('experience_range')) if pd.notna(row.get('experience_range')) else None,
                    company_rating=float(row.get('company_rating')) if pd.notna(row.get('company_rating')) else None,
                    company_reviews_count=int(row.get('company_reviews_count')) if pd.notna(row.get('company_reviews_count')) else None,
                    vacancy_count=int(row.get('vacancy_count')) if pd.notna(row.get('vacancy_count')) else None,
                    work_from_home_type=str(row.get('work_from_home_type')) if pd.notna(row.get('work_from_home_type')) else None
                )
                
                jobs.append(job)
                
            except Exception as e:
                print(f"Error converting job row to JobPostData: {e}")
                continue
        
        return jobs
    
    def _deduplicate_jobs(self, jobs: List[JobPostData]) -> List[JobPostData]:
        """Remove duplicate jobs based on job URL"""
        seen_urls: Set[str] = set()
        unique_jobs = []
        
        for job in jobs:
            if job.job_url not in seen_urls:
                seen_urls.add(job.job_url)
                unique_jobs.append(job)
        
        return unique_jobs
    
    async def filter_and_match_jobs(self, jobs: List[JobPostData], 
                                  user_preferences: UserPreferencesData,
                                  user_id: str) -> List[JobMatchResult]:
        """Filter jobs based on user preferences and calculate match scores"""
        # Get jobs user has already applied to
        applied_job_urls = await self.job_repo.get_applied_job_urls(user_id)
        applied_urls_set = set(applied_job_urls)
        
        # Create filters from user preferences
        filters = JobSearchFilters(
            min_salary=user_preferences.salary_range.min_salary if user_preferences.salary_range else None,
            max_salary=user_preferences.salary_range.max_salary if user_preferences.salary_range else None,
            required_keywords=user_preferences.required_keywords,
            excluded_keywords=user_preferences.excluded_keywords,
            preferred_companies=user_preferences.preferred_companies,
            excluded_companies=user_preferences.excluded_companies,
            preferred_industries=user_preferences.preferred_industries,
            excluded_industries=user_preferences.excluded_industries,
            min_match_score=user_preferences.automation_settings.min_match_score_threshold,
            exclude_applied_jobs=True
        )
        
        results = []
        
        for job in jobs:
            # Check if already applied
            if filters.exclude_applied_jobs and job.job_url in applied_urls_set:
                results.append(JobMatchResult(
                    job=job,
                    match_score=0.0,
                    match_reasons=[],
                    filtered_out=True,
                    filter_reasons=["Already applied to this job"]
                ))
                continue
            
            # Calculate match score and check filters
            match_result = await self._calculate_job_match(job, user_preferences, filters)
            results.append(match_result)
        
        return results
    
    async def _calculate_job_match(self, job: JobPostData, 
                                 user_preferences: UserPreferencesData,
                                 filters: JobSearchFilters) -> JobMatchResult:
        """Calculate match score and apply filters for a single job"""
        match_score = 0.0
        match_reasons = []
        filtered_out = False
        filter_reasons = []
        
        # Check exclusion filters first
        if self._check_exclusion_filters(job, filters):
            filtered_out = True
            filter_reasons = self._get_filter_reasons(job, filters)
            return JobMatchResult(
                job=job,
                match_score=0.0,
                match_reasons=[],
                filtered_out=filtered_out,
                filter_reasons=filter_reasons
            )
        
        # Calculate match score based on various factors
        
        # 1. Job title match (30% weight)
        title_score = self._calculate_title_match(job.title, user_preferences.job_titles)
        match_score += title_score * 0.3
        if title_score > 0.5:
            match_reasons.append(f"Job title matches preferences ({title_score:.2f})")
        
        # 2. Location match (20% weight)
        location_score = self._calculate_location_match(job, user_preferences)
        match_score += location_score * 0.2
        if location_score > 0.5:
            match_reasons.append(f"Location matches preferences ({location_score:.2f})")
        
        # 3. Salary match (20% weight)
        salary_score = self._calculate_salary_match(job, user_preferences.salary_range)
        match_score += salary_score * 0.2
        if salary_score > 0.5:
            match_reasons.append(f"Salary matches preferences ({salary_score:.2f})")
        
        # 4. Company preference (15% weight)
        company_score = self._calculate_company_match(job, user_preferences)
        match_score += company_score * 0.15
        if company_score > 0.5:
            match_reasons.append(f"Company matches preferences ({company_score:.2f})")
        
        # 5. Keywords match (15% weight)
        keyword_score = self._calculate_keyword_match(job, user_preferences)
        match_score += keyword_score * 0.15
        if keyword_score > 0.5:
            match_reasons.append(f"Keywords match preferences ({keyword_score:.2f})")
        
        # Check if match score meets minimum threshold
        if match_score < filters.min_match_score:
            filtered_out = True
            filter_reasons.append(f"Match score {match_score:.2f} below threshold {filters.min_match_score}")
        
        return JobMatchResult(
            job=job,
            match_score=min(match_score, 1.0),  # Cap at 1.0
            match_reasons=match_reasons,
            filtered_out=filtered_out,
            filter_reasons=filter_reasons
        )
    
    def _check_exclusion_filters(self, job: JobPostData, filters: JobSearchFilters) -> bool:
        """Check if job should be filtered out based on exclusion criteria"""
        # Check excluded companies
        if filters.excluded_companies and job.company_name:
            company_lower = job.company_name.lower()
            if any(excluded.lower() in company_lower for excluded in filters.excluded_companies):
                return True
        
        # Check excluded keywords in description
        if filters.excluded_keywords and job.description:
            description_lower = job.description.lower()
            if any(keyword in description_lower for keyword in filters.excluded_keywords):
                return True
        
        # Check excluded industries
        if filters.excluded_industries and job.company_industry:
            industry_lower = job.company_industry.lower()
            if any(excluded.lower() in industry_lower for excluded in filters.excluded_industries):
                return True
        
        return False
    
    def _get_filter_reasons(self, job: JobPostData, filters: JobSearchFilters) -> List[str]:
        """Get reasons why job was filtered out"""
        reasons = []
        
        if filters.excluded_companies and job.company_name:
            company_lower = job.company_name.lower()
            for excluded in filters.excluded_companies:
                if excluded.lower() in company_lower:
                    reasons.append(f"Company '{job.company_name}' is in excluded list")
                    break
        
        if filters.excluded_keywords and job.description:
            description_lower = job.description.lower()
            for keyword in filters.excluded_keywords:
                if keyword in description_lower:
                    reasons.append(f"Contains excluded keyword '{keyword}'")
                    break
        
        if filters.excluded_industries and job.company_industry:
            industry_lower = job.company_industry.lower()
            for excluded in filters.excluded_industries:
                if excluded.lower() in industry_lower:
                    reasons.append(f"Industry '{job.company_industry}' is in excluded list")
                    break
        
        return reasons
    
    def _calculate_title_match(self, job_title: str, preferred_titles: List[str]) -> float:
        """Calculate how well job title matches user preferences"""
        if not preferred_titles:
            return 0.5  # Neutral score if no preferences
        
        job_title_lower = job_title.lower()
        max_score = 0.0
        
        for preferred in preferred_titles:
            preferred_lower = preferred.lower()
            if preferred_lower in job_title_lower:
                # Exact substring match gets high score
                score = 0.9
            elif any(word in job_title_lower.split() for word in preferred_lower.split()):
                # Word-level match gets medium score
                score = 0.7
            else:
                # No match
                score = 0.0
            
            max_score = max(max_score, score)
        
        return max_score
    
    def _calculate_location_match(self, job: JobPostData, user_preferences: UserPreferencesData) -> float:
        """Calculate location match score"""
        if user_preferences.remote_work_preference and job.is_remote:
            return 1.0
        
        if not user_preferences.locations:
            return 0.5  # Neutral if no location preference
        
        if not job.location or not job.location.display_location:
            return 0.3  # Low score for unknown location
        
        job_location_lower = job.location.display_location.lower()
        
        for preferred_location in user_preferences.locations:
            preferred_lower = preferred_location.lower()
            if preferred_lower in job_location_lower or job_location_lower in preferred_lower:
                return 0.9
        
        return 0.1  # Low score if location doesn't match
    
    def _calculate_salary_match(self, job: JobPostData, salary_range) -> float:
        """Calculate salary match score"""
        if not salary_range or not job.compensation:
            return 0.5  # Neutral if no salary info
        
        job_min = job.compensation.min_amount
        job_max = job.compensation.max_amount
        user_min = salary_range.min_salary
        user_max = salary_range.max_salary
        
        if not job_min and not job_max:
            return 0.5  # Neutral if no job salary info
        
        # Convert to annual if needed (simplified)
        if job.compensation.interval == CompensationInterval.HOURLY:
            if job_min:
                job_min *= 2080  # 40 hours * 52 weeks
            if job_max:
                job_max *= 2080
        
        # Check overlap
        if user_min and job_max and job_max < user_min:
            return 0.1  # Job pays too little
        
        if user_max and job_min and job_min > user_max:
            return 0.3  # Job pays more than expected (not necessarily bad)
        
        return 0.8  # Good salary match
    
    def _calculate_company_match(self, job: JobPostData, user_preferences: UserPreferencesData) -> float:
        """Calculate company preference match"""
        if not job.company_name:
            return 0.5
        
        company_lower = job.company_name.lower()
        
        # Check preferred companies
        if user_preferences.preferred_companies:
            for preferred in user_preferences.preferred_companies:
                if preferred.lower() in company_lower:
                    return 1.0
            return 0.3  # Not in preferred list
        
        return 0.5  # Neutral if no company preferences
    
    def _calculate_keyword_match(self, job: JobPostData, user_preferences: UserPreferencesData) -> float:
        """Calculate keyword match in job description"""
        if not job.description:
            return 0.5
        
        description_lower = job.description.lower()
        
        # Check required keywords
        if user_preferences.required_keywords:
            required_found = sum(1 for keyword in user_preferences.required_keywords 
                               if keyword in description_lower)
            required_score = required_found / len(user_preferences.required_keywords)
            return required_score
        
        return 0.5  # Neutral if no keyword requirements
    
    async def store_jobs(self, jobs: List[JobPostData]) -> List[str]:
        """Store jobs in database with embeddings"""
        stored_job_ids = []
        
        # Check for existing jobs to avoid duplicates
        job_urls = [job.job_url for job in jobs]
        existing_jobs = await self.job_repo.get_jobs_by_urls(job_urls)
        existing_urls = {job.jobUrl for job in existing_jobs}
        
        # Filter out existing jobs
        new_jobs = [job for job in jobs if job.job_url not in existing_urls]
        
        # Generate embeddings and store jobs
        for job in new_jobs:
            try:
                # Create embedding for job content
                job_content = f"{job.title} {job.company_name or ''} {job.description or ''}"
                embedding_id = await self.embedding_service.create_embedding(
                    job_content, 
                    metadata={
                        "type": "job",
                        "job_url": job.job_url,
                        "company": job.company_name,
                        "title": job.title
                    }
                )
                
                # Store in database
                db_job = await self.job_repo.create_job_post(job, embedding_id)
                stored_job_ids.append(db_job.id)
                
            except Exception as e:
                print(f"Error storing job {job.title}: {e}")
                continue
        
        return stored_job_ids
    
    async def search_and_filter_jobs_for_user(self, user_preferences: UserPreferencesData, 
                                            user_id: str) -> List[JobMatchResult]:
        """Complete workflow: search jobs based on user preferences and filter/match them"""
        # Create search criteria from user preferences
        criteria = JobSearchCriteria(
            search_terms=user_preferences.job_titles,
            locations=user_preferences.locations,
            sites=[JobSite.LINKEDIN, JobSite.INDEED],  # Default sites
            is_remote=user_preferences.remote_work_preference,
            results_per_site=20
        )
        
        # Search for jobs
        search_result = await self.search_jobs(criteria)
        
        # Filter and match jobs
        match_results = await self.filter_and_match_jobs(
            search_result.jobs, 
            user_preferences, 
            user_id
        )
        
        # Store new jobs in database
        jobs_to_store = [result.job for result in match_results if not result.filtered_out]
        if jobs_to_store:
            await self.store_jobs(jobs_to_store)
        
        return match_results
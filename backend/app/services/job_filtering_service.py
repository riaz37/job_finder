"""
Job filtering service for applying user criteria and quality thresholds
"""
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
import re

from app.models.job import JobPostData, JobMatchResult, JobSearchFilters
from app.models.preferences import UserPreferencesData

logger = logging.getLogger(__name__)


class JobFilteringService:
    """Service for filtering jobs based on user criteria and quality thresholds"""
    
    def __init__(self):
        pass
    
    def apply_filters(
        self, 
        jobs: List[JobPostData],
        user_preferences: UserPreferencesData,
        applied_job_urls: Set[str] = None,
        additional_filters: Optional[JobSearchFilters] = None
    ) -> List[JobMatchResult]:
        """Apply comprehensive filtering to job list"""
        try:
            applied_urls = applied_job_urls or set()
            results = []
            
            for job in jobs:
                # Create base match result
                match_result = JobMatchResult(
                    job=job,
                    match_score=0.0,  # Will be calculated later
                    match_reasons=[],
                    filtered_out=False,
                    filter_reasons=[]
                )
                
                # Apply filters
                filter_results = self._apply_all_filters(
                    job, user_preferences, applied_urls, additional_filters
                )
                
                match_result.filtered_out = filter_results["filtered_out"]
                match_result.filter_reasons = filter_results["reasons"]
                
                results.append(match_result)
            
            filtered_count = sum(1 for r in results if r.filtered_out)
            logger.info(f"Filtered {filtered_count} out of {len(jobs)} jobs")
            
            return results
            
        except Exception as e:
            logger.error(f"Error applying filters: {e}")
            # Return unfiltered results on error
            return [
                JobMatchResult(job=job, match_score=0.0, match_reasons=[], filtered_out=False, filter_reasons=[])
                for job in jobs
            ]
    
    def _apply_all_filters(
        self, 
        job: JobPostData,
        user_preferences: UserPreferencesData,
        applied_urls: Set[str],
        additional_filters: Optional[JobSearchFilters]
    ) -> Dict[str, Any]:
        """Apply all filters to a single job"""
        reasons = []
        
        # Check if already applied
        if job.job_url in applied_urls:
            reasons.append("Already applied to this job")
            return {"filtered_out": True, "reasons": reasons}
        
        # Apply exclusion filters
        exclusion_result = self._apply_exclusion_filters(job, user_preferences)
        if exclusion_result["filtered_out"]:
            reasons.extend(exclusion_result["reasons"])
            return {"filtered_out": True, "reasons": reasons}
        
        # Apply quality filters
        quality_result = self._apply_quality_filters(job)
        if quality_result["filtered_out"]:
            reasons.extend(quality_result["reasons"])
            return {"filtered_out": True, "reasons": reasons}
        
        # Apply salary filters
        salary_result = self._apply_salary_filters(job, user_preferences)
        if salary_result["filtered_out"]:
            reasons.extend(salary_result["reasons"])
            return {"filtered_out": True, "reasons": reasons}
        
        # Apply location filters
        location_result = self._apply_location_filters(job, user_preferences)
        if location_result["filtered_out"]:
            reasons.extend(location_result["reasons"])
            return {"filtered_out": True, "reasons": reasons}
        
        # Apply employment type filters
        employment_result = self._apply_employment_type_filters(job, user_preferences)
        if employment_result["filtered_out"]:
            reasons.extend(employment_result["reasons"])
            return {"filtered_out": True, "reasons": reasons}
        
        # Apply keyword filters
        keyword_result = self._apply_keyword_filters(job, user_preferences)
        if keyword_result["filtered_out"]:
            reasons.extend(keyword_result["reasons"])
            return {"filtered_out": True, "reasons": reasons}
        
        # Apply additional filters if provided
        if additional_filters:
            additional_result = self._apply_additional_filters(job, additional_filters)
            if additional_result["filtered_out"]:
                reasons.extend(additional_result["reasons"])
                return {"filtered_out": True, "reasons": reasons}
        
        return {"filtered_out": False, "reasons": []}
    
    def _apply_exclusion_filters(
        self, 
        job: JobPostData, 
        user_preferences: UserPreferencesData
    ) -> Dict[str, Any]:
        """Apply exclusion filters (companies, industries, keywords)"""
        reasons = []
        
        # Check excluded companies
        if user_preferences.excluded_companies and job.company_name:
            company_lower = job.company_name.lower()
            for excluded in user_preferences.excluded_companies:
                if excluded.lower() in company_lower:
                    reasons.append(f"Company '{job.company_name}' is in excluded list")
                    return {"filtered_out": True, "reasons": reasons}
        
        # Check excluded industries
        if user_preferences.excluded_industries and job.company_industry:
            industry_lower = job.company_industry.lower()
            for excluded in user_preferences.excluded_industries:
                if excluded.lower() in industry_lower:
                    reasons.append(f"Industry '{job.company_industry}' is in excluded list")
                    return {"filtered_out": True, "reasons": reasons}
        
        # Check excluded keywords in description
        if user_preferences.excluded_keywords and job.description:
            description_lower = job.description.lower()
            for keyword in user_preferences.excluded_keywords:
                if keyword in description_lower:
                    reasons.append(f"Contains excluded keyword '{keyword}'")
                    return {"filtered_out": True, "reasons": reasons}
        
        # Check excluded keywords in title
        if user_preferences.excluded_keywords and job.title:
            title_lower = job.title.lower()
            for keyword in user_preferences.excluded_keywords:
                if keyword in title_lower:
                    reasons.append(f"Job title contains excluded keyword '{keyword}'")
                    return {"filtered_out": True, "reasons": reasons}
        
        return {"filtered_out": False, "reasons": []}
    
    def _apply_quality_filters(self, job: JobPostData) -> Dict[str, Any]:
        """Apply quality-based filters"""
        reasons = []
        
        # Filter out jobs with missing critical information
        if not job.title or job.title.strip() == "":
            reasons.append("Missing job title")
            return {"filtered_out": True, "reasons": reasons}
        
        if not job.company_name or job.company_name.strip() == "":
            reasons.append("Missing company name")
            return {"filtered_out": True, "reasons": reasons}
        
        # Filter out very old job postings (older than 90 days)
        if job.date_posted:
            days_old = (datetime.now().date() - job.date_posted).days
            if days_old > 90:
                reasons.append(f"Job posting is too old ({days_old} days)")
                return {"filtered_out": True, "reasons": reasons}
        
        # Filter out jobs with suspicious characteristics
        if self._is_suspicious_job(job):
            reasons.append("Job appears to be spam or low quality")
            return {"filtered_out": True, "reasons": reasons}
        
        return {"filtered_out": False, "reasons": []}
    
    def _is_suspicious_job(self, job: JobPostData) -> bool:
        """Check if job has suspicious characteristics"""
        # Check for spam indicators in title
        spam_indicators = [
            "work from home", "make money fast", "no experience required",
            "earn $", "guaranteed income", "pyramid", "mlm"
        ]
        
        title_lower = job.title.lower()
        if any(indicator in title_lower for indicator in spam_indicators):
            return True
        
        # Check for unrealistic salary ranges
        if job.compensation and job.compensation.min_amount and job.compensation.max_amount:
            min_amount = job.compensation.min_amount
            max_amount = job.compensation.max_amount
            
            # Convert to annual if needed
            if job.compensation.interval and job.compensation.interval.value == "hourly":
                min_amount *= 2080
                max_amount *= 2080
            
            # Flag unrealistic salaries
            if min_amount > 500000 or max_amount > 1000000:  # Very high salaries
                return True
            
            if max_amount > 0 and min_amount > 0 and (max_amount / min_amount) > 5:  # Huge range
                return True
        
        # Check for missing description
        if not job.description or len(job.description.strip()) < 50:
            return True
        
        return False
    
    def _apply_salary_filters(
        self, 
        job: JobPostData, 
        user_preferences: UserPreferencesData
    ) -> Dict[str, Any]:
        """Apply salary-based filters"""
        reasons = []
        
        if not user_preferences.salary_range:
            return {"filtered_out": False, "reasons": []}
        
        if not job.compensation:
            # If user has salary requirements but job has no salary info, filter out
            if user_preferences.salary_range.min_salary:
                reasons.append("No salary information provided")
                return {"filtered_out": True, "reasons": reasons}
            return {"filtered_out": False, "reasons": []}
        
        job_min = job.compensation.min_amount
        job_max = job.compensation.max_amount
        user_min = user_preferences.salary_range.min_salary
        user_max = user_preferences.salary_range.max_salary
        
        if not job_min and not job_max:
            if user_min:
                reasons.append("No salary range specified")
                return {"filtered_out": True, "reasons": reasons}
            return {"filtered_out": False, "reasons": []}
        
        # Convert to annual
        annual_multiplier = self._get_annual_multiplier(job.compensation.interval)
        if job_min:
            job_min *= annual_multiplier
        if job_max:
            job_max *= annual_multiplier
        
        # Check minimum salary requirement
        if user_min:
            job_salary = job_max or job_min  # Use max if available, otherwise min
            if job_salary and job_salary < user_min * 0.8:  # Allow 20% flexibility
                reasons.append(f"Salary too low (${job_salary:,.0f} < ${user_min:,.0f})")
                return {"filtered_out": True, "reasons": reasons}
        
        # Check maximum salary (if user has a strict upper limit)
        if user_max and job_min and job_min > user_max * 1.5:  # Allow 50% flexibility upward
            reasons.append(f"Salary too high (${job_min:,.0f} > ${user_max * 1.5:,.0f})")
            return {"filtered_out": True, "reasons": reasons}
        
        return {"filtered_out": False, "reasons": []}
    
    def _apply_location_filters(
        self, 
        job: JobPostData, 
        user_preferences: UserPreferencesData
    ) -> Dict[str, Any]:
        """Apply location-based filters"""
        reasons = []
        
        # If user prefers remote and job is remote, always pass
        if user_preferences.remote_work_preference and job.is_remote:
            return {"filtered_out": False, "reasons": []}
        
        # If user has no location preferences, pass
        if not user_preferences.locations:
            return {"filtered_out": False, "reasons": []}
        
        # If job has no location info, filter out if user has location preferences
        if not job.location or not job.location.display_location:
            if not job.is_remote:  # Remote jobs without location are OK
                reasons.append("No location information provided")
                return {"filtered_out": True, "reasons": reasons}
            return {"filtered_out": False, "reasons": []}
        
        # Check if job location matches user preferences
        job_location_lower = job.location.display_location.lower()
        
        for preferred_location in user_preferences.locations:
            preferred_lower = preferred_location.lower()
            
            # Exact match or substring match
            if (preferred_lower in job_location_lower or 
                job_location_lower in preferred_lower):
                return {"filtered_out": False, "reasons": []}
            
            # Check city/state matching
            job_parts = [part.strip() for part in job_location_lower.split(',')]
            pref_parts = [part.strip() for part in preferred_lower.split(',')]
            
            if any(jp in pref_parts for jp in job_parts):
                return {"filtered_out": False, "reasons": []}
        
        # If no location match found
        if not user_preferences.remote_work_preference or not job.is_remote:
            reasons.append(f"Location '{job.location.display_location}' not in preferred locations")
            return {"filtered_out": True, "reasons": reasons}
        
        return {"filtered_out": False, "reasons": []}
    
    def _apply_employment_type_filters(
        self, 
        job: JobPostData, 
        user_preferences: UserPreferencesData
    ) -> Dict[str, Any]:
        """Apply employment type filters"""
        reasons = []
        
        if not user_preferences.employment_types:
            return {"filtered_out": False, "reasons": []}
        
        if not job.job_type:
            return {"filtered_out": False, "reasons": []}  # Neutral if no job type info
        
        # Convert job types to comparable format
        job_types_str = [jt.value for jt in job.job_type]
        pref_types_str = [pt.value for pt in user_preferences.employment_types]
        
        # Check for matches
        for job_type in job_types_str:
            if job_type in pref_types_str:
                return {"filtered_out": False, "reasons": []}
        
        # No employment type match
        reasons.append(f"Employment type {job_types_str} not in preferences {pref_types_str}")
        return {"filtered_out": True, "reasons": reasons}
    
    def _apply_keyword_filters(
        self, 
        job: JobPostData, 
        user_preferences: UserPreferencesData
    ) -> Dict[str, Any]:
        """Apply required keyword filters"""
        reasons = []
        
        if not user_preferences.required_keywords:
            return {"filtered_out": False, "reasons": []}
        
        if not job.description:
            reasons.append("No job description to check required keywords")
            return {"filtered_out": True, "reasons": reasons}
        
        description_lower = job.description.lower()
        title_lower = job.title.lower()
        
        # Check if all required keywords are present
        missing_keywords = []
        for keyword in user_preferences.required_keywords:
            if keyword not in description_lower and keyword not in title_lower:
                missing_keywords.append(keyword)
        
        if missing_keywords:
            reasons.append(f"Missing required keywords: {', '.join(missing_keywords)}")
            return {"filtered_out": True, "reasons": reasons}
        
        return {"filtered_out": False, "reasons": []}
    
    def _apply_additional_filters(
        self, 
        job: JobPostData, 
        filters: JobSearchFilters
    ) -> Dict[str, Any]:
        """Apply additional custom filters"""
        reasons = []
        
        # Apply minimum match score filter (if match score is available)
        # This would typically be applied after match score calculation
        
        # Apply custom salary filters
        if filters.min_salary and job.compensation:
            job_salary = job.compensation.max_amount or job.compensation.min_amount
            if job_salary:
                annual_multiplier = self._get_annual_multiplier(job.compensation.interval)
                job_salary_annual = job_salary * annual_multiplier
                
                if job_salary_annual < filters.min_salary:
                    reasons.append(f"Salary below minimum threshold")
                    return {"filtered_out": True, "reasons": reasons}
        
        if filters.max_salary and job.compensation:
            job_salary = job.compensation.min_amount or job.compensation.max_amount
            if job_salary:
                annual_multiplier = self._get_annual_multiplier(job.compensation.interval)
                job_salary_annual = job_salary * annual_multiplier
                
                if job_salary_annual > filters.max_salary:
                    reasons.append(f"Salary above maximum threshold")
                    return {"filtered_out": True, "reasons": reasons}
        
        # Apply custom keyword filters
        if filters.required_keywords and job.description:
            description_lower = job.description.lower()
            for keyword in filters.required_keywords:
                if keyword not in description_lower:
                    reasons.append(f"Missing required keyword: {keyword}")
                    return {"filtered_out": True, "reasons": reasons}
        
        if filters.excluded_keywords and job.description:
            description_lower = job.description.lower()
            for keyword in filters.excluded_keywords:
                if keyword in description_lower:
                    reasons.append(f"Contains excluded keyword: {keyword}")
                    return {"filtered_out": True, "reasons": reasons}
        
        return {"filtered_out": False, "reasons": []}
    
    def _get_annual_multiplier(self, interval) -> float:
        """Get multiplier to convert salary to annual"""
        if not interval:
            return 1.0
        
        multipliers = {
            "hourly": 2080,  # 40 hours * 52 weeks
            "daily": 260,    # ~260 working days
            "weekly": 52,
            "monthly": 12,
            "yearly": 1
        }
        
        return multipliers.get(interval.value if hasattr(interval, 'value') else str(interval), 1.0)
    
    def get_filter_statistics(
        self, 
        filter_results: List[JobMatchResult]
    ) -> Dict[str, Any]:
        """Get statistics about filtering results"""
        total_jobs = len(filter_results)
        filtered_jobs = [r for r in filter_results if r.filtered_out]
        valid_jobs = [r for r in filter_results if not r.filtered_out]
        
        # Count filter reasons
        reason_counts = {}
        for result in filtered_jobs:
            for reason in result.filter_reasons:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        return {
            "total_jobs": total_jobs,
            "filtered_jobs": len(filtered_jobs),
            "valid_jobs": len(valid_jobs),
            "filter_rate": len(filtered_jobs) / total_jobs if total_jobs > 0 else 0,
            "top_filter_reasons": dict(sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        }
    
    def create_filters_from_preferences(
        self, 
        user_preferences: UserPreferencesData
    ) -> JobSearchFilters:
        """Create JobSearchFilters from user preferences"""
        return JobSearchFilters(
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


# Global job filtering service instance
job_filtering_service = JobFilteringService()
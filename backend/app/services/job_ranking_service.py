"""
Job ranking service for sorting and prioritizing job matches
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

from app.models.job import JobPostData, JobMatchResult
from app.models.preferences import UserPreferencesData
from app.models.resume import ResumeData, ParsedResume

logger = logging.getLogger(__name__)


class RankingCriteria(str, Enum):
    """Available ranking criteria"""
    MATCH_SCORE = "match_score"
    DATE_POSTED = "date_posted"
    SALARY = "salary"
    COMPANY_RATING = "company_rating"
    LOCATION_PREFERENCE = "location_preference"
    COMBINED = "combined"


class JobRankingService:
    """Service for ranking and sorting job matches based on various criteria"""
    
    def __init__(self):
        pass
    
    def rank_job_matches(
        self, 
        job_matches: List[JobMatchResult],
        user_preferences: UserPreferencesData,
        ranking_criteria: RankingCriteria = RankingCriteria.COMBINED,
        limit: Optional[int] = None
    ) -> List[JobMatchResult]:
        """Rank job matches based on specified criteria"""
        try:
            # Filter out jobs that were filtered out
            valid_matches = [match for match in job_matches if not match.filtered_out]
            
            if not valid_matches:
                return []
            
            # Apply ranking based on criteria
            if ranking_criteria == RankingCriteria.MATCH_SCORE:
                ranked_matches = self._rank_by_match_score(valid_matches)
            elif ranking_criteria == RankingCriteria.DATE_POSTED:
                ranked_matches = self._rank_by_date_posted(valid_matches)
            elif ranking_criteria == RankingCriteria.SALARY:
                ranked_matches = self._rank_by_salary(valid_matches, user_preferences)
            elif ranking_criteria == RankingCriteria.COMPANY_RATING:
                ranked_matches = self._rank_by_company_rating(valid_matches)
            elif ranking_criteria == RankingCriteria.LOCATION_PREFERENCE:
                ranked_matches = self._rank_by_location_preference(valid_matches, user_preferences)
            else:  # COMBINED
                ranked_matches = self._rank_by_combined_score(valid_matches, user_preferences)
            
            # Apply limit if specified
            if limit and limit > 0:
                ranked_matches = ranked_matches[:limit]
            
            logger.info(f"Ranked {len(ranked_matches)} job matches using {ranking_criteria.value} criteria")
            return ranked_matches
            
        except Exception as e:
            logger.error(f"Error ranking job matches: {e}")
            return job_matches  # Return original list on error
    
    def _rank_by_match_score(self, job_matches: List[JobMatchResult]) -> List[JobMatchResult]:
        """Rank jobs by match score (highest first)"""
        return sorted(job_matches, key=lambda x: x.match_score, reverse=True)
    
    def _rank_by_date_posted(self, job_matches: List[JobMatchResult]) -> List[JobMatchResult]:
        """Rank jobs by date posted (newest first)"""
        def get_date_score(match: JobMatchResult) -> float:
            if not match.job.date_posted:
                return 0.0  # Unknown date gets lowest priority
            
            days_ago = (datetime.now().date() - match.job.date_posted).days
            
            # Score decreases with age, but not linearly
            if days_ago <= 1:
                return 1.0  # Posted today or yesterday
            elif days_ago <= 7:
                return 0.8  # Posted this week
            elif days_ago <= 30:
                return 0.6  # Posted this month
            elif days_ago <= 90:
                return 0.4  # Posted in last 3 months
            else:
                return 0.2  # Older posts
        
        return sorted(job_matches, key=get_date_score, reverse=True)
    
    def _rank_by_salary(
        self, 
        job_matches: List[JobMatchResult], 
        user_preferences: UserPreferencesData
    ) -> List[JobMatchResult]:
        """Rank jobs by salary alignment with user preferences"""
        def get_salary_score(match: JobMatchResult) -> float:
            job = match.job
            
            if not job.compensation or not user_preferences.salary_range:
                return 0.5  # Neutral score if no salary info
            
            job_min = job.compensation.min_amount
            job_max = job.compensation.max_amount
            user_min = user_preferences.salary_range.min_salary
            user_max = user_preferences.salary_range.max_salary
            
            if not job_min and not job_max:
                return 0.5  # Neutral if no job salary
            
            # Convert to annual
            annual_multiplier = self._get_annual_multiplier(job.compensation.interval)
            if job_min:
                job_min *= annual_multiplier
            if job_max:
                job_max *= annual_multiplier
            
            # Calculate salary alignment score
            if user_min and user_max:
                # Use job max for comparison if available, otherwise job min
                job_salary = job_max or job_min
                
                if job_salary >= user_min and job_salary <= user_max * 1.2:
                    # Within or slightly above preferred range
                    return 1.0
                elif job_salary >= user_min * 0.8:
                    # Close to minimum
                    return 0.8
                elif job_salary > user_max * 1.2:
                    # Higher than preferred (still good)
                    return 0.9
                else:
                    # Below minimum
                    return 0.3
            
            return 0.5  # Default neutral score
        
        return sorted(job_matches, key=get_salary_score, reverse=True)
    
    def _rank_by_company_rating(self, job_matches: List[JobMatchResult]) -> List[JobMatchResult]:
        """Rank jobs by company rating (highest first)"""
        def get_rating_score(match: JobMatchResult) -> float:
            if match.job.company_rating:
                return match.job.company_rating / 5.0  # Normalize to 0-1
            return 0.5  # Neutral score if no rating
        
        return sorted(job_matches, key=get_rating_score, reverse=True)
    
    def _rank_by_location_preference(
        self, 
        job_matches: List[JobMatchResult], 
        user_preferences: UserPreferencesData
    ) -> List[JobMatchResult]:
        """Rank jobs by location preference alignment"""
        def get_location_score(match: JobMatchResult) -> float:
            job = match.job
            
            # Remote work gets highest score if preferred
            if user_preferences.remote_work_preference and job.is_remote:
                return 1.0
            
            if not user_preferences.locations:
                return 0.5  # Neutral if no location preference
            
            if not job.location or not job.location.display_location:
                return 0.3  # Low score for unknown location
            
            job_location_lower = job.location.display_location.lower()
            
            # Check for exact or partial matches
            for preferred_location in user_preferences.locations:
                preferred_lower = preferred_location.lower()
                
                if preferred_lower == job_location_lower:
                    return 1.0  # Exact match
                elif preferred_lower in job_location_lower or job_location_lower in preferred_lower:
                    return 0.8  # Partial match
            
            return 0.2  # No location match
        
        return sorted(job_matches, key=get_location_score, reverse=True)
    
    def _rank_by_combined_score(
        self, 
        job_matches: List[JobMatchResult], 
        user_preferences: UserPreferencesData
    ) -> List[JobMatchResult]:
        """Rank jobs using a combined scoring approach"""
        def get_combined_score(match: JobMatchResult) -> float:
            # Base match score (50% weight)
            base_score = match.match_score * 0.50
            
            # Date freshness (20% weight)
            date_score = self._get_date_freshness_score(match.job) * 0.20
            
            # Salary alignment (15% weight)
            salary_score = self._get_salary_alignment_score(match.job, user_preferences) * 0.15
            
            # Company quality (10% weight)
            company_score = self._get_company_quality_score(match.job) * 0.10
            
            # Application ease (5% weight)
            ease_score = self._get_application_ease_score(match.job) * 0.05
            
            return base_score + date_score + salary_score + company_score + ease_score
        
        return sorted(job_matches, key=get_combined_score, reverse=True)
    
    def _get_date_freshness_score(self, job: JobPostData) -> float:
        """Calculate freshness score based on posting date"""
        if not job.date_posted:
            return 0.3  # Low score for unknown date
        
        days_ago = (datetime.now().date() - job.date_posted).days
        
        if days_ago <= 1:
            return 1.0
        elif days_ago <= 3:
            return 0.9
        elif days_ago <= 7:
            return 0.7
        elif days_ago <= 14:
            return 0.5
        elif days_ago <= 30:
            return 0.3
        else:
            return 0.1
    
    def _get_salary_alignment_score(
        self, 
        job: JobPostData, 
        user_preferences: UserPreferencesData
    ) -> float:
        """Calculate salary alignment score"""
        if not job.compensation or not user_preferences.salary_range:
            return 0.5
        
        job_min = job.compensation.min_amount
        job_max = job.compensation.max_amount
        user_min = user_preferences.salary_range.min_salary
        user_max = user_preferences.salary_range.max_salary
        
        if not (job_min or job_max) or not (user_min or user_max):
            return 0.5
        
        # Convert to annual
        annual_multiplier = self._get_annual_multiplier(job.compensation.interval)
        if job_min:
            job_min *= annual_multiplier
        if job_max:
            job_max *= annual_multiplier
        
        # Use job max for comparison if available
        job_salary = job_max or job_min
        
        if user_min and user_max:
            if user_min <= job_salary <= user_max * 1.1:
                return 1.0  # Perfect range
            elif job_salary >= user_min * 0.9:
                return 0.8  # Close to minimum
            elif job_salary > user_max * 1.1:
                return 0.7  # Above range (still good)
            else:
                return 0.2  # Below range
        
        return 0.5
    
    def _get_company_quality_score(self, job: JobPostData) -> float:
        """Calculate company quality score"""
        score = 0.5  # Base score
        
        # Company rating
        if job.company_rating:
            score += (job.company_rating / 5.0) * 0.4
        
        # Company size (larger companies might be more stable)
        if job.company_num_employees:
            try:
                # Parse employee count (e.g., "1000-5000")
                if '-' in job.company_num_employees:
                    max_employees = int(job.company_num_employees.split('-')[1])
                else:
                    max_employees = int(job.company_num_employees.replace('+', '').replace(',', ''))
                
                if max_employees >= 10000:
                    score += 0.2  # Large company
                elif max_employees >= 1000:
                    score += 0.15  # Medium-large company
                elif max_employees >= 100:
                    score += 0.1  # Medium company
                
            except (ValueError, AttributeError):
                pass
        
        # Company reviews count (more reviews = more established)
        if job.company_reviews_count and job.company_reviews_count > 100:
            score += 0.1
        
        return min(score, 1.0)
    
    def _get_application_ease_score(self, job: JobPostData) -> float:
        """Calculate application ease score"""
        score = 0.5  # Base score
        
        # Direct application URL
        if job.job_url_direct:
            score += 0.3
        
        # Site-specific bonuses (some sites are easier to apply through)
        site_bonuses = {
            "linkedin": 0.2,
            "indeed": 0.15,
            "glassdoor": 0.1
        }
        
        site_bonus = site_bonuses.get(job.site.value if hasattr(job.site, 'value') else str(job.site), 0)
        score += site_bonus
        
        return min(score, 1.0)
    
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
    
    def get_ranking_statistics(
        self, 
        job_matches: List[JobMatchResult]
    ) -> Dict[str, Any]:
        """Get statistics about the ranked job matches"""
        if not job_matches:
            return {}
        
        valid_matches = [match for match in job_matches if not match.filtered_out]
        
        if not valid_matches:
            return {"total_jobs": len(job_matches), "valid_jobs": 0}
        
        match_scores = [match.match_score for match in valid_matches]
        
        # Calculate score distribution
        score_ranges = {
            "excellent": len([s for s in match_scores if s >= 0.8]),
            "good": len([s for s in match_scores if 0.6 <= s < 0.8]),
            "fair": len([s for s in match_scores if 0.4 <= s < 0.6]),
            "poor": len([s for s in match_scores if s < 0.4])
        }
        
        # Company distribution
        companies = {}
        for match in valid_matches:
            company = match.job.company_name or "Unknown"
            companies[company] = companies.get(company, 0) + 1
        
        # Location distribution
        locations = {}
        for match in valid_matches:
            if match.job.location and match.job.location.display_location:
                location = match.job.location.display_location
            elif match.job.is_remote:
                location = "Remote"
            else:
                location = "Unknown"
            locations[location] = locations.get(location, 0) + 1
        
        return {
            "total_jobs": len(job_matches),
            "valid_jobs": len(valid_matches),
            "filtered_jobs": len(job_matches) - len(valid_matches),
            "average_match_score": sum(match_scores) / len(match_scores),
            "max_match_score": max(match_scores),
            "min_match_score": min(match_scores),
            "score_distribution": score_ranges,
            "top_companies": dict(sorted(companies.items(), key=lambda x: x[1], reverse=True)[:10]),
            "top_locations": dict(sorted(locations.items(), key=lambda x: x[1], reverse=True)[:10])
        }
    
    def filter_by_quality_threshold(
        self, 
        job_matches: List[JobMatchResult],
        min_match_score: float = 0.6,
        max_results: Optional[int] = None
    ) -> List[JobMatchResult]:
        """Filter job matches by quality threshold"""
        # Filter by match score
        quality_matches = [
            match for match in job_matches 
            if not match.filtered_out and match.match_score >= min_match_score
        ]
        
        # Sort by match score
        quality_matches.sort(key=lambda x: x.match_score, reverse=True)
        
        # Apply limit if specified
        if max_results and max_results > 0:
            quality_matches = quality_matches[:max_results]
        
        logger.info(f"Filtered to {len(quality_matches)} high-quality job matches (score >= {min_match_score})")
        return quality_matches


# Global job ranking service instance
job_ranking_service = JobRankingService()
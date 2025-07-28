"""
Job recommendation engine that combines matching, filtering, and ranking
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio

from app.models.job import JobPostData, JobMatchResult
from app.models.preferences import UserPreferencesData
from app.models.resume import ResumeData, ParsedResume
from app.services.job_matching_service import job_matching_service
from app.services.job_ranking_service import job_ranking_service, RankingCriteria
from app.services.job_filtering_service import job_filtering_service
from app.db.job_repository import JobRepository

logger = logging.getLogger(__name__)


class JobRecommendationEngine:
    """Comprehensive job recommendation engine"""
    
    def __init__(self, job_repository: JobRepository):
        self.job_repository = job_repository
        self.matching_service = job_matching_service
        self.ranking_service = job_ranking_service
        self.filtering_service = job_filtering_service
    
    async def get_job_recommendations(
        self,
        user_id: str,
        resume_data: ResumeData,
        parsed_resume: ParsedResume,
        user_preferences: UserPreferencesData,
        limit: int = 20,
        min_match_score: float = 0.6,
        ranking_criteria: RankingCriteria = RankingCriteria.COMBINED
    ) -> Dict[str, Any]:
        """Get comprehensive job recommendations for a user"""
        try:
            start_time = datetime.now()
            
            # Step 1: Get candidate jobs (from recent scrapes or search)
            candidate_jobs = await self._get_candidate_jobs(user_preferences, limit * 3)  # Get more candidates
            
            if not candidate_jobs:
                return {
                    "recommendations": [],
                    "statistics": {"total_candidates": 0, "processing_time": 0},
                    "message": "No candidate jobs found"
                }
            
            # Step 2: Get jobs user has already applied to
            applied_job_urls = await self.job_repository.get_applied_job_urls(user_id)
            applied_urls_set = set(applied_job_urls)
            
            # Step 3: Apply initial filtering
            filtered_results = self.filtering_service.apply_filters(
                candidate_jobs, user_preferences, applied_urls_set
            )
            
            # Step 4: Calculate match scores for non-filtered jobs
            match_results = []
            for result in filtered_results:
                if not result.filtered_out:
                    # Calculate comprehensive match score
                    match_result = await self.matching_service.calculate_job_resume_match(
                        result.job, resume_data, parsed_resume, user_preferences
                    )
                    match_results.append(match_result)
                else:
                    # Keep filtered results for statistics
                    match_results.append(result)
            
            # Step 5: Apply quality threshold filtering
            quality_matches = self.ranking_service.filter_by_quality_threshold(
                match_results, min_match_score, limit * 2
            )
            
            # Step 6: Rank the results
            ranked_matches = self.ranking_service.rank_job_matches(
                quality_matches, user_preferences, ranking_criteria, limit
            )
            
            # Step 7: Generate statistics and insights
            processing_time = (datetime.now() - start_time).total_seconds()
            statistics = self._generate_recommendation_statistics(
                candidate_jobs, filtered_results, match_results, ranked_matches, processing_time
            )
            
            # Step 8: Enhance recommendations with additional insights
            enhanced_recommendations = self._enhance_recommendations(ranked_matches, user_preferences)
            
            logger.info(f"Generated {len(enhanced_recommendations)} job recommendations for user {user_id}")
            
            return {
                "recommendations": enhanced_recommendations,
                "statistics": statistics,
                "message": f"Found {len(enhanced_recommendations)} high-quality job matches"
            }
            
        except Exception as e:
            logger.error(f"Error generating job recommendations: {e}")
            return {
                "recommendations": [],
                "statistics": {"error": str(e)},
                "message": "Error generating recommendations"
            }
    
    async def _get_candidate_jobs(
        self, 
        user_preferences: UserPreferencesData, 
        limit: int
    ) -> List[JobPostData]:
        """Get candidate jobs based on user preferences"""
        try:
            # For now, get recent jobs from database
            # In a full implementation, this might trigger a fresh job search
            recent_jobs = await self.job_repository.get_recent_jobs(limit)
            
            # Convert database jobs to JobPostData format
            candidate_jobs = []
            for db_job in recent_jobs:
                try:
                    job_data = self._convert_db_job_to_job_post_data(db_job)
                    candidate_jobs.append(job_data)
                except Exception as e:
                    logger.warning(f"Error converting job {db_job.id}: {e}")
                    continue
            
            return candidate_jobs
            
        except Exception as e:
            logger.error(f"Error getting candidate jobs: {e}")
            return []
    
    def _convert_db_job_to_job_post_data(self, db_job) -> JobPostData:
        """Convert database job to JobPostData model"""
        # This is a simplified conversion - in practice, you'd need to properly
        # deserialize the JSON fields and handle all the model mappings
        from app.models.job import JobLocation, JobCompensation, JobSite, JobTypeEnum, CompensationInterval
        
        # Parse location from JSON
        location = None
        if db_job.location:
            location_data = db_job.location if isinstance(db_job.location, dict) else {}
            location = JobLocation(
                display_location=location_data.get("display_location"),
                city=location_data.get("city"),
                state=location_data.get("state"),
                country=location_data.get("country"),
                is_remote=location_data.get("is_remote", False)
            )
        
        # Parse compensation from JSON
        compensation = None
        if db_job.salary_info:
            salary_data = db_job.salary_info if isinstance(db_job.salary_info, dict) else {}
            compensation = JobCompensation(
                min_amount=salary_data.get("min_amount"),
                max_amount=salary_data.get("max_amount"),
                currency=salary_data.get("currency", "USD"),
                interval=CompensationInterval(salary_data["interval"]) if salary_data.get("interval") else None
            )
        
        return JobPostData(
            title=db_job.title,
            company_name=db_job.company_name,
            job_url=db_job.job_url,
            location=location,
            description=db_job.description,
            compensation=compensation,
            date_posted=db_job.scraped_at.date() if db_job.scraped_at else None,
            is_remote=location.is_remote if location else False,
            site=JobSite.LINKEDIN  # Default site
        )
    
    def _generate_recommendation_statistics(
        self,
        candidate_jobs: List[JobPostData],
        filtered_results: List[JobMatchResult],
        match_results: List[JobMatchResult],
        final_recommendations: List[JobMatchResult],
        processing_time: float
    ) -> Dict[str, Any]:
        """Generate comprehensive statistics about the recommendation process"""
        
        # Basic counts
        total_candidates = len(candidate_jobs)
        filtered_out = len([r for r in filtered_results if r.filtered_out])
        matched_jobs = len([r for r in match_results if not r.filtered_out])
        final_count = len(final_recommendations)
        
        # Match score statistics
        match_scores = [r.match_score for r in match_results if not r.filtered_out and r.match_score > 0]
        
        score_stats = {}
        if match_scores:
            score_stats = {
                "average_score": sum(match_scores) / len(match_scores),
                "max_score": max(match_scores),
                "min_score": min(match_scores),
                "score_distribution": {
                    "excellent": len([s for s in match_scores if s >= 0.8]),
                    "good": len([s for s in match_scores if 0.6 <= s < 0.8]),
                    "fair": len([s for s in match_scores if 0.4 <= s < 0.6]),
                    "poor": len([s for s in match_scores if s < 0.4])
                }
            }
        
        # Filter statistics
        filter_stats = self.filtering_service.get_filter_statistics(filtered_results)
        
        # Ranking statistics
        ranking_stats = self.ranking_service.get_ranking_statistics(final_recommendations)
        
        return {
            "processing_time": processing_time,
            "pipeline_stats": {
                "total_candidates": total_candidates,
                "filtered_out": filtered_out,
                "matched_jobs": matched_jobs,
                "final_recommendations": final_count,
                "filter_rate": filtered_out / total_candidates if total_candidates > 0 else 0
            },
            "match_scores": score_stats,
            "filtering": filter_stats,
            "ranking": ranking_stats
        }
    
    def _enhance_recommendations(
        self, 
        recommendations: List[JobMatchResult], 
        user_preferences: UserPreferencesData
    ) -> List[Dict[str, Any]]:
        """Enhance recommendations with additional insights and metadata"""
        enhanced = []
        
        for i, match in enumerate(recommendations):
            job = match.job
            
            # Calculate additional insights
            insights = self._generate_job_insights(job, user_preferences)
            
            # Determine recommendation strength
            strength = self._get_recommendation_strength(match.match_score)
            
            # Generate action recommendations
            actions = self._generate_action_recommendations(match, user_preferences)
            
            enhanced_rec = {
                "rank": i + 1,
                "job": {
                    "id": getattr(job, 'id', None),
                    "title": job.title,
                    "company_name": job.company_name,
                    "job_url": job.job_url,
                    "location": {
                        "display_location": job.location.display_location if job.location else None,
                        "is_remote": job.is_remote
                    },
                    "description": job.description[:500] + "..." if job.description and len(job.description) > 500 else job.description,
                    "compensation": {
                        "min_amount": job.compensation.min_amount if job.compensation else None,
                        "max_amount": job.compensation.max_amount if job.compensation else None,
                        "currency": job.compensation.currency if job.compensation else None,
                        "interval": job.compensation.interval.value if job.compensation and job.compensation.interval else None
                    } if job.compensation else None,
                    "date_posted": job.date_posted.isoformat() if job.date_posted else None,
                    "company_rating": job.company_rating,
                    "site": job.site.value if hasattr(job.site, 'value') else str(job.site)
                },
                "match_analysis": {
                    "match_score": round(match.match_score, 3),
                    "strength": strength,
                    "match_reasons": match.match_reasons,
                    "insights": insights
                },
                "recommendations": {
                    "actions": actions,
                    "priority": self._get_application_priority(match, user_preferences),
                    "estimated_competition": self._estimate_competition_level(job),
                    "application_difficulty": self._estimate_application_difficulty(job)
                }
            }
            
            enhanced.append(enhanced_rec)
        
        return enhanced
    
    def _generate_job_insights(
        self, 
        job: JobPostData, 
        user_preferences: UserPreferencesData
    ) -> List[str]:
        """Generate insights about why this job is a good match"""
        insights = []
        
        # Location insights
        if job.is_remote and user_preferences.remote_work_preference:
            insights.append("Remote work opportunity matches your preference")
        
        # Company insights
        if job.company_name and user_preferences.preferred_companies:
            for preferred in user_preferences.preferred_companies:
                if preferred.lower() in job.company_name.lower():
                    insights.append(f"Preferred company: {job.company_name}")
                    break
        
        # Salary insights
        if job.compensation and user_preferences.salary_range:
            job_salary = job.compensation.max_amount or job.compensation.min_amount
            if job_salary and user_preferences.salary_range.min_salary:
                if job_salary >= user_preferences.salary_range.min_salary:
                    insights.append("Salary meets your minimum requirements")
        
        # Freshness insights
        if job.date_posted:
            days_old = (datetime.now().date() - job.date_posted).days
            if days_old <= 3:
                insights.append("Recently posted job (higher chance of success)")
        
        # Company rating insights
        if job.company_rating and job.company_rating >= 4.0:
            insights.append(f"Highly rated company ({job.company_rating}/5.0)")
        
        return insights
    
    def _get_recommendation_strength(self, match_score: float) -> str:
        """Get recommendation strength based on match score"""
        if match_score >= 0.85:
            return "Excellent Match"
        elif match_score >= 0.75:
            return "Very Good Match"
        elif match_score >= 0.65:
            return "Good Match"
        elif match_score >= 0.55:
            return "Fair Match"
        else:
            return "Potential Match"
    
    def _generate_action_recommendations(
        self, 
        match: JobMatchResult, 
        user_preferences: UserPreferencesData
    ) -> List[str]:
        """Generate action recommendations for the job"""
        actions = []
        
        if match.match_score >= 0.8:
            actions.append("Apply immediately - excellent match")
        elif match.match_score >= 0.7:
            actions.append("High priority application")
        else:
            actions.append("Consider applying after reviewing details")
        
        # Specific actions based on job characteristics
        if match.job.date_posted:
            days_old = (datetime.now().date() - match.job.date_posted).days
            if days_old <= 1:
                actions.append("Apply quickly - job posted recently")
        
        if match.job.company_rating and match.job.company_rating >= 4.5:
            actions.append("Research company culture - highly rated employer")
        
        # Resume customization suggestions
        if match.match_score < 0.8:
            actions.append("Consider customizing resume for better match")
        
        return actions
    
    def _get_application_priority(
        self, 
        match: JobMatchResult, 
        user_preferences: UserPreferencesData
    ) -> str:
        """Determine application priority"""
        score = match.match_score
        
        # Adjust priority based on automation settings
        threshold = user_preferences.automation_settings.min_match_score_threshold
        
        if score >= threshold + 0.2:
            return "High"
        elif score >= threshold + 0.1:
            return "Medium"
        elif score >= threshold:
            return "Low"
        else:
            return "Manual Review"
    
    def _estimate_competition_level(self, job: JobPostData) -> str:
        """Estimate competition level for the job"""
        # This is a simplified estimation - in practice, you might use
        # historical data, job site metrics, etc.
        
        competition_score = 0
        
        # Company rating affects competition
        if job.company_rating and job.company_rating >= 4.5:
            competition_score += 2
        elif job.company_rating and job.company_rating >= 4.0:
            competition_score += 1
        
        # Remote jobs tend to have more competition
        if job.is_remote:
            competition_score += 1
        
        # High salary jobs have more competition
        if job.compensation and job.compensation.max_amount:
            annual_salary = job.compensation.max_amount
            if job.compensation.interval and job.compensation.interval.value == "hourly":
                annual_salary *= 2080
            
            if annual_salary > 150000:
                competition_score += 2
            elif annual_salary > 100000:
                competition_score += 1
        
        # Job age affects competition
        if job.date_posted:
            days_old = (datetime.now().date() - job.date_posted).days
            if days_old <= 1:
                competition_score += 1  # New jobs get more applications
        
        if competition_score >= 4:
            return "High"
        elif competition_score >= 2:
            return "Medium"
        else:
            return "Low"
    
    def _estimate_application_difficulty(self, job: JobPostData) -> str:
        """Estimate how difficult the application process might be"""
        difficulty_score = 0
        
        # Site-specific difficulty
        site_difficulty = {
            "linkedin": 1,  # Usually easy apply
            "indeed": 1,
            "glassdoor": 2,
            "company_website": 3
        }
        
        site_name = job.site.value if hasattr(job.site, 'value') else str(job.site)
        difficulty_score += site_difficulty.get(site_name, 2)
        
        # Direct application URL makes it easier
        if job.job_url_direct:
            difficulty_score -= 1
        
        # Company size might affect process complexity
        if job.company_num_employees:
            try:
                if '-' in job.company_num_employees:
                    max_employees = int(job.company_num_employees.split('-')[1])
                else:
                    max_employees = int(job.company_num_employees.replace('+', '').replace(',', ''))
                
                if max_employees >= 10000:
                    difficulty_score += 1  # Large companies often have complex processes
            except (ValueError, AttributeError):
                pass
        
        if difficulty_score <= 1:
            return "Easy"
        elif difficulty_score <= 3:
            return "Medium"
        else:
            return "Hard"
    
    async def get_similar_jobs(
        self,
        job_id: str,
        user_preferences: UserPreferencesData,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get jobs similar to a specific job"""
        try:
            # Get the reference job
            reference_job = await self.job_repository.get_job_by_id(job_id)
            if not reference_job:
                return []
            
            # Find similar jobs using vector similarity
            # This would use the vector service to find jobs with similar embeddings
            similar_job_ids = await self._find_similar_job_ids(job_id, limit * 2)
            
            # Get the similar jobs
            similar_jobs = []
            for similar_id in similar_job_ids:
                job = await self.job_repository.get_job_by_id(similar_id)
                if job:
                    similar_jobs.append(self._convert_db_job_to_job_post_data(job))
            
            # Apply basic filtering
            filtered_results = self.filtering_service.apply_filters(
                similar_jobs, user_preferences
            )
            
            # Return non-filtered results
            valid_results = [r for r in filtered_results if not r.filtered_out][:limit]
            
            return [
                {
                    "job": result.job,
                    "similarity_reason": "Similar job content and requirements"
                }
                for result in valid_results
            ]
            
        except Exception as e:
            logger.error(f"Error finding similar jobs: {e}")
            return []
    
    async def _find_similar_job_ids(self, job_id: str, limit: int) -> List[str]:
        """Find similar job IDs using vector similarity"""
        try:
            # This would use the vector service to find similar jobs
            # For now, return empty list as placeholder
            return []
        except Exception as e:
            logger.error(f"Error finding similar job IDs: {e}")
            return []


# Global job recommendation engine instance
def create_job_recommendation_engine(job_repository: JobRepository) -> JobRecommendationEngine:
    """Factory function to create job recommendation engine"""
    return JobRecommendationEngine(job_repository)
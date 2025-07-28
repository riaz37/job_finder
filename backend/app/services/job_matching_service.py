"""
Job matching service for calculating job-resume compatibility using vector similarity
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio

from app.models.job import JobPostData, JobMatchResult
from app.models.preferences import UserPreferencesData
from app.models.resume import ResumeData, ParsedResume
from app.services.vector_service import vector_service
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)


class JobMatchingService:
    """Service for matching jobs to resumes using vector similarity and preference-based scoring"""
    
    def __init__(self):
        self.vector_service = vector_service
        self.embedding_service = embedding_service
    
    async def calculate_job_resume_match(
        self, 
        job: JobPostData, 
        resume_data: ResumeData,
        parsed_resume: ParsedResume,
        user_preferences: UserPreferencesData
    ) -> JobMatchResult:
        """Calculate comprehensive match score between job and resume"""
        try:
            # Calculate vector similarity score (40% weight)
            vector_score = await self._calculate_vector_similarity(job, resume_data)
            
            # Calculate preference-based score (35% weight)
            preference_score = self._calculate_preference_match(job, user_preferences)
            
            # Calculate resume-job content match (25% weight)
            content_score = self._calculate_content_match(job, parsed_resume)
            
            # Combine scores with weights
            final_score = (
                vector_score * 0.40 +
                preference_score * 0.35 +
                content_score * 0.25
            )
            
            # Generate match reasons
            match_reasons = self._generate_match_reasons(
                job, parsed_resume, user_preferences, 
                vector_score, preference_score, content_score
            )
            
            # Check if job should be filtered out
            filtered_out, filter_reasons = self._check_filters(job, user_preferences)
            
            return JobMatchResult(
                job=job,
                match_score=min(final_score, 1.0),  # Cap at 1.0
                match_reasons=match_reasons,
                filtered_out=filtered_out,
                filter_reasons=filter_reasons
            )
            
        except Exception as e:
            logger.error(f"Error calculating job-resume match: {e}")
            # Return low-score result on error
            return JobMatchResult(
                job=job,
                match_score=0.0,
                match_reasons=[],
                filtered_out=True,
                filter_reasons=[f"Error calculating match: {str(e)}"]
            )
    
    async def _calculate_vector_similarity(
        self, 
        job: JobPostData, 
        resume_data: ResumeData
    ) -> float:
        """Calculate vector similarity between job and resume embeddings"""
        try:
            # For now, we'll use a simplified approach since we need job embeddings
            # In a full implementation, jobs would be pre-embedded when scraped
            
            # Create a temporary job content for embedding
            job_content = self._prepare_job_content_for_embedding(job)
            
            # Generate job embedding
            job_embedding = await self.vector_service.generate_embedding(job_content)
            
            # Get resume embedding (assuming it exists)
            resume_vector_id = f"resume_{resume_data.id}"
            try:
                resume_response = await asyncio.get_event_loop().run_in_executor(
                    self.vector_service.executor,
                    lambda: self.vector_service.index.fetch(
                        ids=[resume_vector_id],
                        namespace="resumes"
                    )
                )
                
                if resume_response.vectors and resume_vector_id in resume_response.vectors:
                    # Calculate cosine similarity
                    resume_embedding = resume_response.vectors[resume_vector_id].values
                    similarity = self._cosine_similarity(job_embedding, resume_embedding)
                    return max(0.0, similarity)  # Ensure non-negative
                else:
                    logger.warning(f"Resume embedding not found for {resume_data.id}")
                    return 0.5  # Neutral score if no embedding
                    
            except Exception as e:
                logger.warning(f"Error fetching resume embedding: {e}")
                return 0.5  # Neutral score on error
                
        except Exception as e:
            logger.error(f"Error calculating vector similarity: {e}")
            return 0.0
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        import math
        
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _prepare_job_content_for_embedding(self, job: JobPostData) -> str:
        """Prepare job content for embedding generation"""
        content_parts = []
        
        content_parts.append(f"Job Title: {job.title}")
        
        if job.company_name:
            content_parts.append(f"Company: {job.company_name}")
        
        if job.location and job.location.display_location:
            content_parts.append(f"Location: {job.location.display_location}")
        
        if job.description:
            content_parts.append(f"Description: {job.description}")
        
        if job.skills:
            content_parts.append(f"Required Skills: {', '.join(job.skills)}")
        
        if job.job_type:
            job_types = [jt.value for jt in job.job_type]
            content_parts.append(f"Job Type: {', '.join(job_types)}")
        
        if job.compensation:
            comp_text = "Compensation: "
            if job.compensation.min_amount:
                comp_text += f"{job.compensation.min_amount}"
                if job.compensation.max_amount:
                    comp_text += f" - {job.compensation.max_amount}"
                comp_text += f" {job.compensation.currency}"
                if job.compensation.interval:
                    comp_text += f" {job.compensation.interval.value}"
            content_parts.append(comp_text)
        
        return "\n".join(content_parts)
    
    def _calculate_preference_match(
        self, 
        job: JobPostData, 
        user_preferences: UserPreferencesData
    ) -> float:
        """Calculate how well job matches user preferences"""
        score_components = []
        
        # Job title match (30% of preference score)
        title_score = self._calculate_title_match(job.title, user_preferences.job_titles)
        score_components.append(title_score * 0.30)
        
        # Location match (25% of preference score)
        location_score = self._calculate_location_match(job, user_preferences)
        score_components.append(location_score * 0.25)
        
        # Salary match (20% of preference score)
        salary_score = self._calculate_salary_match(job, user_preferences.salary_range)
        score_components.append(salary_score * 0.20)
        
        # Company preference (15% of preference score)
        company_score = self._calculate_company_match(job, user_preferences)
        score_components.append(company_score * 0.15)
        
        # Employment type match (10% of preference score)
        employment_score = self._calculate_employment_type_match(job, user_preferences)
        score_components.append(employment_score * 0.10)
        
        return sum(score_components)
    
    def _calculate_title_match(self, job_title: str, preferred_titles: List[str]) -> float:
        """Calculate job title match score"""
        if not preferred_titles:
            return 0.5  # Neutral if no preferences
        
        job_title_lower = job_title.lower()
        max_score = 0.0
        
        for preferred in preferred_titles:
            preferred_lower = preferred.lower()
            
            # Exact match
            if preferred_lower == job_title_lower:
                return 1.0
            
            # Substring match
            if preferred_lower in job_title_lower or job_title_lower in preferred_lower:
                max_score = max(max_score, 0.8)
            
            # Word-level match
            job_words = set(job_title_lower.split())
            pref_words = set(preferred_lower.split())
            
            if job_words & pref_words:  # Intersection
                overlap_ratio = len(job_words & pref_words) / len(job_words | pref_words)
                max_score = max(max_score, overlap_ratio * 0.7)
        
        return max_score
    
    def _calculate_location_match(
        self, 
        job: JobPostData, 
        user_preferences: UserPreferencesData
    ) -> float:
        """Calculate location match score"""
        # Remote work preference
        if user_preferences.remote_work_preference and job.is_remote:
            return 1.0
        
        if not user_preferences.locations:
            return 0.5  # Neutral if no location preference
        
        if not job.location or not job.location.display_location:
            return 0.3  # Low score for unknown location
        
        job_location_lower = job.location.display_location.lower()
        
        for preferred_location in user_preferences.locations:
            preferred_lower = preferred_location.lower()
            
            # Exact match
            if preferred_lower == job_location_lower:
                return 1.0
            
            # Substring match
            if preferred_lower in job_location_lower or job_location_lower in preferred_lower:
                return 0.8
            
            # City/state matching
            job_parts = job_location_lower.split(', ')
            pref_parts = preferred_lower.split(', ')
            
            if any(jp in pref_parts for jp in job_parts):
                return 0.6
        
        return 0.1  # Low score if no location match
    
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
        
        # Convert to annual if needed
        annual_multiplier = self._get_annual_multiplier(job.compensation.interval)
        if job_min:
            job_min *= annual_multiplier
        if job_max:
            job_max *= annual_multiplier
        
        # Check salary alignment
        if user_min and job_max and job_max < user_min * 0.8:
            return 0.1  # Job pays significantly less
        
        if user_max and job_min and job_min > user_max * 1.2:
            return 0.7  # Job pays more (not necessarily bad)
        
        # Good salary range overlap
        if user_min and user_max and job_min and job_max:
            # Calculate overlap
            overlap_start = max(user_min, job_min)
            overlap_end = min(user_max, job_max)
            
            if overlap_start <= overlap_end:
                return 0.9  # Good overlap
        
        return 0.8  # Reasonable salary match
    
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
    
    def _calculate_company_match(
        self, 
        job: JobPostData, 
        user_preferences: UserPreferencesData
    ) -> float:
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
    
    def _calculate_employment_type_match(
        self, 
        job: JobPostData, 
        user_preferences: UserPreferencesData
    ) -> float:
        """Calculate employment type match"""
        if not job.job_type or not user_preferences.employment_types:
            return 0.5  # Neutral if no type info
        
        # Convert job types to comparable format
        job_types_str = [jt.value for jt in job.job_type]
        pref_types_str = [pt.value for pt in user_preferences.employment_types]
        
        # Check for matches
        for job_type in job_types_str:
            if job_type in pref_types_str:
                return 1.0
        
        return 0.2  # Low score if no type match
    
    def _calculate_content_match(
        self, 
        job: JobPostData, 
        parsed_resume: ParsedResume
    ) -> float:
        """Calculate content-based match between job and resume"""
        score_components = []
        
        # Skills match (50% of content score)
        skills_score = self._calculate_skills_match(job, parsed_resume)
        score_components.append(skills_score * 0.50)
        
        # Experience match (30% of content score)
        experience_score = self._calculate_experience_match(job, parsed_resume)
        score_components.append(experience_score * 0.30)
        
        # Industry match (20% of content score)
        industry_score = self._calculate_industry_match(job, parsed_resume)
        score_components.append(industry_score * 0.20)
        
        return sum(score_components)
    
    def _calculate_skills_match(self, job: JobPostData, parsed_resume: ParsedResume) -> float:
        """Calculate skills match between job requirements and resume"""
        if not parsed_resume.skills:
            return 0.3  # Low score if no resume skills
        
        resume_skills = set(skill.lower() for skill in parsed_resume.skills)
        
        # Extract skills from job description and requirements
        job_skills = set()
        
        if job.skills:
            job_skills.update(skill.lower() for skill in job.skills)
        
        # Extract skills from job description using simple keyword matching
        if job.description:
            description_lower = job.description.lower()
            # Common technical skills to look for
            common_skills = [
                'python', 'java', 'javascript', 'react', 'node.js', 'sql', 'aws',
                'docker', 'kubernetes', 'git', 'agile', 'scrum', 'machine learning',
                'data analysis', 'project management', 'leadership', 'communication'
            ]
            
            for skill in common_skills:
                if skill in description_lower:
                    job_skills.add(skill)
        
        if not job_skills:
            return 0.5  # Neutral if no job skills identified
        
        # Calculate skill overlap
        matching_skills = resume_skills & job_skills
        if not matching_skills:
            return 0.2  # Low score if no skill overlap
        
        # Calculate match ratio
        match_ratio = len(matching_skills) / len(job_skills)
        return min(match_ratio * 1.2, 1.0)  # Boost score slightly, cap at 1.0
    
    def _calculate_experience_match(self, job: JobPostData, parsed_resume: ParsedResume) -> float:
        """Calculate experience level match"""
        if not parsed_resume.experience_years:
            return 0.5  # Neutral if no experience info
        
        # Extract experience requirements from job description
        required_years = self._extract_experience_requirement(job.description or "")
        
        if required_years is None:
            return 0.5  # Neutral if no requirement found
        
        resume_years = parsed_resume.experience_years
        
        # Calculate experience match
        if resume_years >= required_years:
            # Bonus for more experience, but diminishing returns
            excess_years = resume_years - required_years
            bonus = min(excess_years * 0.1, 0.3)  # Max 30% bonus
            return min(0.8 + bonus, 1.0)
        else:
            # Penalty for less experience
            shortage = required_years - resume_years
            penalty = shortage * 0.15
            return max(0.6 - penalty, 0.1)
    
    def _extract_experience_requirement(self, job_description: str) -> Optional[int]:
        """Extract experience requirement from job description"""
        import re
        
        if not job_description:
            return None
        
        # Look for patterns like "3+ years", "5-7 years", "minimum 2 years"
        patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'minimum\s*(\d+)\s*years?',
            r'at\s*least\s*(\d+)\s*years?',
            r'(\d+)-\d+\s*years?\s*(?:of\s*)?experience'
        ]
        
        description_lower = job_description.lower()
        
        for pattern in patterns:
            matches = re.findall(pattern, description_lower)
            if matches:
                try:
                    return int(matches[0])
                except ValueError:
                    continue
        
        return None
    
    def _calculate_industry_match(self, job: JobPostData, parsed_resume: ParsedResume) -> float:
        """Calculate industry match between job and resume"""
        if not parsed_resume.industries:
            return 0.5  # Neutral if no resume industry info
        
        resume_industries = set(industry.lower() for industry in parsed_resume.industries)
        
        # Get job industry
        job_industry = None
        if job.company_industry:
            job_industry = job.company_industry.lower()
        
        if not job_industry:
            return 0.5  # Neutral if no job industry info
        
        # Check for direct match
        if job_industry in resume_industries:
            return 1.0
        
        # Check for partial matches
        for resume_industry in resume_industries:
            if resume_industry in job_industry or job_industry in resume_industry:
                return 0.7
        
        return 0.3  # Low score for different industries
    
    def _check_filters(
        self, 
        job: JobPostData, 
        user_preferences: UserPreferencesData
    ) -> Tuple[bool, List[str]]:
        """Check if job should be filtered out based on user preferences"""
        filter_reasons = []
        
        # Check excluded companies
        if user_preferences.excluded_companies and job.company_name:
            company_lower = job.company_name.lower()
            for excluded in user_preferences.excluded_companies:
                if excluded.lower() in company_lower:
                    filter_reasons.append(f"Company '{job.company_name}' is in excluded list")
                    break
        
        # Check excluded keywords
        if user_preferences.excluded_keywords and job.description:
            description_lower = job.description.lower()
            for keyword in user_preferences.excluded_keywords:
                if keyword in description_lower:
                    filter_reasons.append(f"Contains excluded keyword '{keyword}'")
                    break
        
        # Check excluded industries
        if user_preferences.excluded_industries and job.company_industry:
            industry_lower = job.company_industry.lower()
            for excluded in user_preferences.excluded_industries:
                if excluded.lower() in industry_lower:
                    filter_reasons.append(f"Industry '{job.company_industry}' is in excluded list")
                    break
        
        return len(filter_reasons) > 0, filter_reasons
    
    def _generate_match_reasons(
        self, 
        job: JobPostData, 
        parsed_resume: ParsedResume,
        user_preferences: UserPreferencesData,
        vector_score: float,
        preference_score: float,
        content_score: float
    ) -> List[str]:
        """Generate human-readable reasons for the match score"""
        reasons = []
        
        # Overall score assessment
        total_score = (vector_score * 0.40 + preference_score * 0.35 + content_score * 0.25)
        
        if total_score >= 0.8:
            reasons.append("Excellent overall match")
        elif total_score >= 0.7:
            reasons.append("Very good match")
        elif total_score >= 0.6:
            reasons.append("Good match")
        elif total_score >= 0.5:
            reasons.append("Fair match")
        else:
            reasons.append("Poor match")
        
        # Specific component reasons
        if vector_score >= 0.7:
            reasons.append(f"Strong content similarity ({vector_score:.2f})")
        
        if preference_score >= 0.7:
            reasons.append(f"Matches user preferences well ({preference_score:.2f})")
        
        if content_score >= 0.7:
            reasons.append(f"Good skills and experience match ({content_score:.2f})")
        
        # Specific match details
        if job.title and user_preferences.job_titles:
            title_match = self._calculate_title_match(job.title, user_preferences.job_titles)
            if title_match >= 0.7:
                reasons.append(f"Job title matches preferences")
        
        if job.is_remote and user_preferences.remote_work_preference:
            reasons.append("Remote work opportunity")
        
        if job.company_name and user_preferences.preferred_companies:
            company_lower = job.company_name.lower()
            for preferred in user_preferences.preferred_companies:
                if preferred.lower() in company_lower:
                    reasons.append(f"Preferred company: {job.company_name}")
                    break
        
        return reasons


# Global job matching service instance
job_matching_service = JobMatchingService()
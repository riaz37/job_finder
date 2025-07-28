"""
Embedding service for processing and managing document embeddings
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.services.vector_service import vector_service
from app.models.resume import ResumeData, ParsedResume
from jobspy.model import JobPost

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for managing embeddings for resumes and job postings"""
    
    def __init__(self):
        self.vector_service = vector_service
    
    async def process_resume_embedding(
        self, 
        resume_data: ResumeData, 
        parsed_resume: ParsedResume
    ) -> str:
        """Process and store resume embedding with extracted content"""
        try:
            # Combine resume content for embedding
            resume_text = self._prepare_resume_text(parsed_resume)
            
            # Prepare metadata
            metadata = {
                "skills": parsed_resume.skills,
                "experience_years": parsed_resume.experience_years,
                "education_level": parsed_resume.education_level,
                "job_titles": parsed_resume.job_titles,
                "industries": parsed_resume.industries,
                "created_at": resume_data.created_at.isoformat() if resume_data.created_at else None,
                "filename": resume_data.original_filename
            }
            
            # Store embedding
            vector_id = await self.vector_service.store_resume_embedding(
                resume_id=resume_data.id,
                user_id=resume_data.user_id,
                resume_content=resume_text,
                metadata=metadata
            )
            
            logger.info(f"Processed resume embedding for resume {resume_data.id}")
            return vector_id
            
        except Exception as e:
            logger.error(f"Error processing resume embedding: {e}")
            raise
    
    def _prepare_resume_text(self, parsed_resume: ParsedResume) -> str:
        """Prepare resume text for embedding generation"""
        text_parts = []
        
        # Add personal information
        if parsed_resume.personal_info:
            if parsed_resume.personal_info.get("name"):
                text_parts.append(f"Name: {parsed_resume.personal_info['name']}")
            if parsed_resume.personal_info.get("email"):
                text_parts.append(f"Email: {parsed_resume.personal_info['email']}")
        
        # Add summary/objective
        if parsed_resume.summary:
            text_parts.append(f"Summary: {parsed_resume.summary}")
        
        # Add skills
        if parsed_resume.skills:
            skills_text = ", ".join(parsed_resume.skills)
            text_parts.append(f"Skills: {skills_text}")
        
        # Add work experience
        if parsed_resume.work_experience:
            text_parts.append("Work Experience:")
            for exp in parsed_resume.work_experience:
                exp_text = f"- {exp.get('title', '')} at {exp.get('company', '')} ({exp.get('duration', '')})"
                if exp.get('description'):
                    exp_text += f": {exp['description']}"
                text_parts.append(exp_text)
        
        # Add education
        if parsed_resume.education:
            text_parts.append("Education:")
            for edu in parsed_resume.education:
                edu_text = f"- {edu.get('degree', '')} from {edu.get('institution', '')} ({edu.get('year', '')})"
                text_parts.append(edu_text)
        
        # Add certifications
        if parsed_resume.certifications:
            cert_text = ", ".join(parsed_resume.certifications)
            text_parts.append(f"Certifications: {cert_text}")
        
        return "\n".join(text_parts)
    
    async def process_job_embedding(self, job_post: JobPost) -> str:
        """Process and store job posting embedding"""
        try:
            # Prepare job text for embedding
            job_text = self._prepare_job_text(job_post)
            
            # Prepare metadata
            metadata = {
                "company": job_post.company,
                "title": job_post.title,
                "location": job_post.location,
                "job_type": getattr(job_post, 'job_type', None),
                "salary_min": getattr(job_post, 'min_amount', None),
                "salary_max": getattr(job_post, 'max_amount', None),
                "currency": getattr(job_post, 'currency', None),
                "site": job_post.site.value if hasattr(job_post.site, 'value') else str(job_post.site),
                "scraped_at": datetime.now().isoformat(),
                "job_url": job_post.job_url
            }
            
            # Store embedding
            vector_id = await self.vector_service.store_job_embedding(
                job_id=job_post.id if hasattr(job_post, 'id') else str(hash(job_post.job_url)),
                job_content=job_text,
                metadata=metadata
            )
            
            logger.info(f"Processed job embedding for job {job_post.title} at {job_post.company}")
            return vector_id
            
        except Exception as e:
            logger.error(f"Error processing job embedding: {e}")
            raise
    
    def _prepare_job_text(self, job_post: JobPost) -> str:
        """Prepare job posting text for embedding generation"""
        text_parts = []
        
        # Add job title and company
        text_parts.append(f"Job Title: {job_post.title}")
        text_parts.append(f"Company: {job_post.company}")
        
        # Add location
        if job_post.location:
            text_parts.append(f"Location: {job_post.location}")
        
        # Add job type
        if hasattr(job_post, 'job_type') and job_post.job_type:
            text_parts.append(f"Job Type: {job_post.job_type}")
        
        # Add salary information
        if hasattr(job_post, 'min_amount') and job_post.min_amount:
            salary_text = f"Salary: {job_post.min_amount}"
            if hasattr(job_post, 'max_amount') and job_post.max_amount:
                salary_text += f" - {job_post.max_amount}"
            if hasattr(job_post, 'currency') and job_post.currency:
                salary_text += f" {job_post.currency}"
            text_parts.append(salary_text)
        
        # Add job description
        if job_post.description:
            text_parts.append(f"Description: {job_post.description}")
        
        return "\n".join(text_parts)
    
    async def find_matching_jobs(
        self, 
        resume_id: str, 
        limit: int = 20,
        min_score: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Find jobs that match a resume based on vector similarity"""
        try:
            similar_jobs = await self.vector_service.find_similar_jobs(
                resume_id=resume_id,
                top_k=limit,
                score_threshold=min_score
            )
            
            # Enhance results with additional processing
            enhanced_jobs = []
            for job in similar_jobs:
                enhanced_job = {
                    **job,
                    "match_reasons": self._generate_match_reasons(job["metadata"], job["score"])
                }
                enhanced_jobs.append(enhanced_job)
            
            return enhanced_jobs
            
        except Exception as e:
            logger.error(f"Error finding matching jobs: {e}")
            raise
    
    def _generate_match_reasons(self, job_metadata: Dict[str, Any], score: float) -> List[str]:
        """Generate human-readable reasons for job match"""
        reasons = []
        
        if score >= 0.9:
            reasons.append("Excellent overall match")
        elif score >= 0.8:
            reasons.append("Very good match")
        elif score >= 0.7:
            reasons.append("Good match")
        
        # Add specific reasons based on metadata
        if job_metadata.get("title"):
            reasons.append(f"Title: {job_metadata['title']}")
        
        if job_metadata.get("company"):
            reasons.append(f"Company: {job_metadata['company']}")
        
        return reasons
    
    async def calculate_job_resume_match(
        self, 
        resume_id: str, 
        job_id: str
    ) -> Dict[str, Any]:
        """Calculate detailed match score between resume and job"""
        try:
            score = await self.vector_service.calculate_similarity_score(
                resume_id=resume_id,
                job_id=job_id
            )
            
            # Categorize match quality
            if score >= 0.9:
                match_quality = "excellent"
            elif score >= 0.8:
                match_quality = "very_good"
            elif score >= 0.7:
                match_quality = "good"
            elif score >= 0.6:
                match_quality = "fair"
            else:
                match_quality = "poor"
            
            return {
                "score": score,
                "match_quality": match_quality,
                "recommendation": score >= 0.7
            }
            
        except Exception as e:
            logger.error(f"Error calculating job-resume match: {e}")
            raise


# Global embedding service instance
embedding_service = EmbeddingService()
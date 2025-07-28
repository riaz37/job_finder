"""
Resume customization service for tailoring resumes to specific job requirements
"""
import json
from typing import Dict, Any, List, Optional, Tuple
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

from app.models.resume import (
    ParsedResumeContent, 
    ResumeAnalysis, 
    JobRequirementsAnalysis,
    ResumeJobComparison,
    CustomizedResumeResult
)
from app.models.job import JobPostData
from app.core.config import settings
from app.services.ai_service import AIService


class ResumeCustomizationService:
    """Service for customizing resumes based on job requirements"""
    
    def __init__(self):
        self.ai_service = AIService()
        if settings.GEMINI_API_KEY:
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-pro",
                google_api_key=settings.GEMINI_API_KEY,
                temperature=0.2  # Slightly higher for creative optimization
            )
        else:
            self.llm = None
    
    async def analyze_job_requirements(self, job: JobPostData) -> Dict[str, Any]:
        """
        Analyze job requirements to extract key skills, qualifications, and keywords
        
        Args:
            job: Job posting data
            
        Returns:
            Dictionary with analyzed job requirements
        """
        if not self.llm:
            raise Exception("Gemini API key not configured")
        
        system_prompt = """
        You are an expert job requirements analyst. Analyze the job posting and extract key information as JSON:
        
        {
            "required_skills": ["list of required technical and soft skills"],
            "preferred_skills": ["list of preferred/nice-to-have skills"],
            "required_qualifications": ["education, certifications, experience requirements"],
            "key_responsibilities": ["main job responsibilities"],
            "keywords": ["important keywords for ATS optimization"],
            "experience_level": "entry-level, mid-level, senior, or executive",
            "industry": "primary industry",
            "company_culture_keywords": ["keywords indicating company culture/values"],
            "technical_requirements": ["specific technologies, tools, frameworks"],
            "soft_skills": ["communication, leadership, teamwork, etc."],
            "priority_skills": ["top 5 most important skills for this role"]
        }
        
        Focus on extracting information that would be relevant for resume optimization.
        """
        
        job_content = f"""
        Job Title: {job.title}
        Company: {job.company_name}
        Description: {job.description or 'No description available'}
        Skills: {', '.join(job.skills or [])}
        Experience Range: {job.experience_range or 'Not specified'}
        Job Function: {job.job_function or 'Not specified'}
        """
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Analyze this job posting:\n\n{job_content}")
            ]
            
            response = await self.llm.ainvoke(messages)
            return json.loads(response.content)
            
        except json.JSONDecodeError:
            # Fallback analysis
            return await self._fallback_job_analysis(job)
        except Exception as e:
            raise Exception(f"Failed to analyze job requirements: {str(e)}")
    
    async def compare_resume_to_job(
        self, 
        resume: ParsedResumeContent, 
        job_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare resume against job requirements to identify gaps and matches
        
        Args:
            resume: Parsed resume content
            job_requirements: Analyzed job requirements
            
        Returns:
            Dictionary with comparison results
        """
        if not self.llm:
            raise Exception("Gemini API key not configured")
        
        system_prompt = """
        You are an expert resume analyst. Compare the resume against job requirements and return analysis as JSON:
        
        {
            "skill_matches": ["skills from resume that match job requirements"],
            "skill_gaps": ["required skills missing from resume"],
            "experience_alignment": "how well experience aligns (high/medium/low)",
            "qualification_matches": ["qualifications that match requirements"],
            "qualification_gaps": ["missing qualifications"],
            "keyword_matches": ["keywords from resume that match job"],
            "missing_keywords": ["important job keywords missing from resume"],
            "strengths": ["resume strengths for this specific job"],
            "weaknesses": ["areas where resume is weak for this job"],
            "optimization_opportunities": ["specific ways to improve resume for this job"],
            "match_score": "overall match score from 0.0 to 1.0",
            "recommendations": ["specific recommendations for resume improvement"]
        }
        
        Be specific and actionable in your analysis.
        """
        
        comparison_content = f"""
        RESUME DATA:
        Skills: {', '.join(resume.skills)}
        Experience: {json.dumps(resume.experience, indent=2)}
        Education: {json.dumps(resume.education, indent=2)}
        Summary: {resume.summary or 'No summary'}
        
        JOB REQUIREMENTS:
        {json.dumps(job_requirements, indent=2)}
        """
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Compare this resume to job requirements:\n\n{comparison_content}")
            ]
            
            response = await self.llm.ainvoke(messages)
            return json.loads(response.content)
            
        except json.JSONDecodeError:
            # Fallback comparison
            return await self._fallback_resume_comparison(resume, job_requirements)
        except Exception as e:
            raise Exception(f"Failed to compare resume to job: {str(e)}")
    
    async def optimize_resume_content(
        self, 
        resume: ParsedResumeContent, 
        job_requirements: Dict[str, Any],
        comparison_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate optimized resume content based on job requirements and comparison
        
        Args:
            resume: Original parsed resume content
            job_requirements: Analyzed job requirements
            comparison_results: Resume-job comparison results
            
        Returns:
            Dictionary with optimized resume content
        """
        if not self.llm:
            raise Exception("Gemini API key not configured")
        
        system_prompt = """
        You are an expert resume optimizer. Create an optimized version of the resume for the specific job.
        Return the optimized content as JSON maintaining the same structure but with improvements:
        
        {
            "personal_info": "keep original personal info unchanged",
            "contact_info": "keep original contact info unchanged", 
            "summary": "optimized professional summary highlighting relevant skills for this job",
            "skills": ["optimized skills list emphasizing job-relevant skills"],
            "experience": [
                {
                    "title": "original title",
                    "company": "original company",
                    "location": "original location",
                    "start_date": "original start date",
                    "end_date": "original end date",
                    "description": "optimized description emphasizing relevant achievements",
                    "responsibilities": ["optimized responsibilities with job-relevant keywords"]
                }
            ],
            "education": "keep original education but optimize descriptions if relevant",
            "certifications": "keep original certifications but highlight relevant ones",
            "languages": "keep original languages",
            "optimization_notes": ["list of changes made and why"],
            "ats_keywords_added": ["keywords added for ATS optimization"],
            "factual_accuracy_maintained": true
        }
        
        CRITICAL RULES:
        1. NEVER change factual information (dates, company names, job titles, education)
        2. Only optimize descriptions, summaries, and emphasis
        3. Add relevant keywords naturally without keyword stuffing
        4. Maintain professional tone and readability
        5. Ensure all changes are truthful and based on original content
        """
        
        optimization_content = f"""
        ORIGINAL RESUME:
        {json.dumps(resume.dict(), indent=2)}
        
        JOB REQUIREMENTS:
        {json.dumps(job_requirements, indent=2)}
        
        COMPARISON RESULTS:
        {json.dumps(comparison_results, indent=2)}
        
        Optimize this resume for the job while maintaining complete factual accuracy.
        """
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=optimization_content)
            ]
            
            response = await self.llm.ainvoke(messages)
            return json.loads(response.content)
            
        except json.JSONDecodeError:
            # Fallback optimization
            return await self._fallback_resume_optimization(resume, job_requirements)
        except Exception as e:
            raise Exception(f"Failed to optimize resume content: {str(e)}")
    
    async def generate_ats_optimized_keywords(
        self, 
        job_requirements: Dict[str, Any],
        resume_skills: List[str]
    ) -> List[str]:
        """
        Generate ATS-optimized keywords for the resume
        
        Args:
            job_requirements: Analyzed job requirements
            resume_skills: Current resume skills
            
        Returns:
            List of ATS-optimized keywords
        """
        if not self.llm:
            return job_requirements.get('keywords', [])
        
        system_prompt = """
        You are an ATS (Applicant Tracking System) optimization expert. 
        Generate a list of keywords that should be naturally incorporated into the resume.
        Return as a simple JSON array of strings.
        
        Focus on:
        1. Keywords from job requirements not already in resume
        2. Industry-standard terminology
        3. Technical skills and tools
        4. Relevant certifications and qualifications
        5. Action verbs and achievement-oriented terms
        
        Return format: ["keyword1", "keyword2", "keyword3"]
        """
        
        content = f"""
        JOB REQUIREMENTS KEYWORDS: {job_requirements.get('keywords', [])}
        REQUIRED SKILLS: {job_requirements.get('required_skills', [])}
        TECHNICAL REQUIREMENTS: {job_requirements.get('technical_requirements', [])}
        CURRENT RESUME SKILLS: {resume_skills}
        
        Generate ATS-optimized keywords that are missing from the resume but relevant to the job.
        """
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=content)
            ]
            
            response = await self.llm.ainvoke(messages)
            return json.loads(response.content)
            
        except (json.JSONDecodeError, Exception):
            # Fallback keyword generation
            job_keywords = job_requirements.get('keywords', [])
            required_skills = job_requirements.get('required_skills', [])
            
            # Return keywords not already in resume skills
            resume_skills_lower = [skill.lower() for skill in resume_skills]
            missing_keywords = []
            
            for keyword in job_keywords + required_skills:
                if keyword.lower() not in resume_skills_lower:
                    missing_keywords.append(keyword)
            
            return missing_keywords[:10]  # Limit to top 10
    
    async def customize_resume_for_job(
        self, 
        resume: ParsedResumeContent, 
        job: JobPostData
    ) -> Dict[str, Any]:
        """
        Complete resume customization pipeline for a specific job
        
        Args:
            resume: Original parsed resume content
            job: Job posting data
            
        Returns:
            Dictionary with customized resume and analysis
        """
        try:
            # Step 1: Analyze job requirements (Requirement 4.1)
            job_requirements = await self.analyze_job_requirements(job)
            
            # Step 2: Compare resume to job and identify gaps (Requirement 4.2)
            comparison_results = await self.compare_resume_to_job(resume, job_requirements)
            
            # Step 3: Optimize resume content (Requirement 4.3)
            optimized_content = await self.optimize_resume_content(
                resume, job_requirements, comparison_results
            )
            
            # Step 4: Generate ATS keywords (Requirement 4.4)
            ats_keywords = await self.generate_ats_optimized_keywords(
                job_requirements, resume.skills
            )
            
            # Step 5: Create final customized resume (Requirement 4.5)
            customized_resume = ParsedResumeContent(
                personal_info=optimized_content.get('personal_info', resume.personal_info),
                contact_info=optimized_content.get('contact_info', resume.contact_info),
                summary=optimized_content.get('summary', resume.summary),
                skills=optimized_content.get('skills', resume.skills),
                experience=optimized_content.get('experience', resume.experience),
                education=optimized_content.get('education', resume.education),
                certifications=optimized_content.get('certifications', resume.certifications),
                languages=optimized_content.get('languages', resume.languages),
                raw_text=resume.raw_text  # Keep original raw text
            )
            
            return {
                'customized_resume': customized_resume,
                'job_requirements': job_requirements,
                'comparison_results': comparison_results,
                'optimization_notes': optimized_content.get('optimization_notes', []),
                'ats_keywords_added': ats_keywords,
                'match_score': comparison_results.get('match_score', 0.0),
                'factual_accuracy_maintained': optimized_content.get('factual_accuracy_maintained', True)
            }
            
        except Exception as e:
            raise Exception(f"Failed to customize resume for job: {str(e)}")
    
    async def _fallback_job_analysis(self, job: JobPostData) -> Dict[str, Any]:
        """Fallback job analysis when AI fails"""
        description = job.description or ""
        skills = job.skills or []
        
        # Basic keyword extraction from description
        common_tech_skills = [
            'python', 'java', 'javascript', 'react', 'node.js', 'sql', 'aws', 'docker',
            'kubernetes', 'git', 'html', 'css', 'mongodb', 'postgresql', 'redis'
        ]
        
        found_skills = []
        description_lower = description.lower()
        for skill in common_tech_skills:
            if skill in description_lower:
                found_skills.append(skill)
        
        return {
            'required_skills': skills + found_skills,
            'preferred_skills': [],
            'required_qualifications': [],
            'key_responsibilities': [],
            'keywords': skills,
            'experience_level': 'mid-level',
            'industry': 'Technology',
            'company_culture_keywords': [],
            'technical_requirements': found_skills,
            'soft_skills': [],
            'priority_skills': skills[:5]
        }
    
    async def _fallback_resume_comparison(
        self, 
        resume: ParsedResumeContent, 
        job_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback resume comparison when AI fails"""
        resume_skills = [skill.lower() for skill in resume.skills]
        required_skills = [skill.lower() for skill in job_requirements.get('required_skills', [])]
        
        skill_matches = [skill for skill in required_skills if skill in resume_skills]
        skill_gaps = [skill for skill in required_skills if skill not in resume_skills]
        
        match_score = len(skill_matches) / max(len(required_skills), 1)
        
        return {
            'skill_matches': skill_matches,
            'skill_gaps': skill_gaps,
            'experience_alignment': 'medium',
            'qualification_matches': [],
            'qualification_gaps': [],
            'keyword_matches': skill_matches,
            'missing_keywords': skill_gaps,
            'strengths': skill_matches[:3],
            'weaknesses': skill_gaps[:3],
            'optimization_opportunities': [
                'Add missing technical skills',
                'Emphasize relevant experience',
                'Include industry keywords'
            ],
            'match_score': match_score,
            'recommendations': [
                'Highlight relevant skills more prominently',
                'Add specific achievements with metrics',
                'Include missing keywords naturally'
            ]
        }
    
    async def _fallback_resume_optimization(
        self, 
        resume: ParsedResumeContent, 
        job_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback resume optimization when AI fails"""
        # Basic optimization - add missing skills if they exist in experience
        optimized_skills = resume.skills.copy()
        required_skills = job_requirements.get('required_skills', [])
        
        # Add required skills that might be mentioned in experience
        for exp in resume.experience:
            exp_text = str(exp).lower()
            for skill in required_skills:
                if skill.lower() in exp_text and skill not in optimized_skills:
                    optimized_skills.append(skill)
        
        return {
            'personal_info': resume.personal_info,
            'contact_info': resume.contact_info,
            'summary': resume.summary,
            'skills': optimized_skills,
            'experience': resume.experience,
            'education': resume.education,
            'certifications': resume.certifications,
            'languages': resume.languages,
            'optimization_notes': ['Added relevant skills found in experience'],
            'ats_keywords_added': [],
            'factual_accuracy_maintained': True
        }


# Global instance
resume_customization_service = ResumeCustomizationService()
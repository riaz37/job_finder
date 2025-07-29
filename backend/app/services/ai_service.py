"""
AI service for text generation using Gemini models
"""
import logging
from typing import Dict, Any, List, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI text generation using Gemini 2.5 Flash"""
    
    def __init__(self):
        self.llm = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        
    async def initialize(self):
        """Initialize Gemini 2.5 Flash model"""
        try:
            if not settings.GEMINI_API_KEY:
                logger.warning("GEMINI_API_KEY not provided, AI features will use fallback methods")
                self.llm = None
                return

            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=settings.GEMINI_API_KEY,
                temperature=0.7,
                max_tokens=1000
            )

            logger.info("AI service initialized with Gemini 2.5 Flash")

        except Exception as e:
            logger.error(f"Failed to initialize AI service: {e}")
            self.llm = None
    
    async def generate_job_match_explanation(
        self,
        resume_data: Dict[str, Any],
        job_data: Dict[str, Any],
        match_score: float
    ) -> str:
        """Generate detailed explanation for job-resume match"""
        # Check if LLM is initialized
        if self.llm is None:
            return f"Unable to generate detailed explanation (AI service not initialized). Match score: {match_score:.2f}"

        try:
            system_prompt = """You are an AI career advisor. Analyze the resume and job posting to provide a clear, helpful explanation of why they match or don't match. Focus on:
1. Skills alignment
2. Experience relevance
3. Education requirements
4. Career progression fit
5. Specific recommendations

Be concise but thorough. Use bullet points for clarity."""

            user_prompt = f"""
Resume Summary:
- Skills: {resume_data.get('skills', [])}
- Experience: {resume_data.get('experience_years', 'N/A')} years
- Education: {resume_data.get('education_level', 'N/A')}
- Job Titles: {resume_data.get('job_titles', [])}
- Industries: {resume_data.get('industries', [])}

Job Posting:
- Title: {job_data.get('title', 'N/A')}
- Company: {job_data.get('company', 'N/A')}
- Location: {job_data.get('location', 'N/A')}
- Description: {job_data.get('description', 'N/A')[:500]}...

Match Score: {match_score:.2f}

Provide a detailed analysis of this match:
"""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.llm.invoke(messages)
            )
            
            return response.content
            
        except Exception as e:
            logger.error(f"Error generating job match explanation: {e}")
            return f"Unable to generate detailed explanation. Match score: {match_score:.2f}"
    
    async def generate_resume_summary(self, resume_data: Dict[str, Any]) -> str:
        """Generate a professional summary of the resume"""
        # Check if LLM is initialized
        if self.llm is None:
            return "Unable to generate resume summary (AI service not initialized)."

        try:
            system_prompt = """You are a professional resume writer. Create a concise, compelling professional summary based on the resume data provided. The summary should:
1. Highlight key strengths and skills
2. Mention relevant experience
3. Be 2-3 sentences maximum
4. Sound professional and engaging"""

            user_prompt = f"""
Create a professional summary for this resume:

Skills: {resume_data.get('skills', [])}
Experience: {resume_data.get('experience_years', 'N/A')} years
Education: {resume_data.get('education_level', 'N/A')}
Job Titles: {resume_data.get('job_titles', [])}
Industries: {resume_data.get('industries', [])}
Summary: {resume_data.get('summary', 'N/A')}
"""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.llm.invoke(messages)
            )
            
            return response.content
            
        except Exception as e:
            logger.error(f"Error generating resume summary: {e}")
            return "Unable to generate resume summary at this time."
    
    async def parse_resume(self, text_content: str) -> Dict[str, Any]:
        """Parse resume text into structured data using AI"""
        # Check if LLM is initialized
        if self.llm is None:
            logger.warning("AI service not initialized, using fallback parsing")
            return await self._fallback_parsing(text_content)

        system_prompt = """You are an expert resume parser. Extract structured information from the resume text and return it as JSON:

        {
            "personal_info": {
                "name": "full name",
                "title": "professional title/role"
            },
            "contact_info": {
                "email": "email address",
                "phone": "phone number",
                "location": "city, state/country",
                "linkedin": "linkedin profile url",
                "website": "personal website url"
            },
            "summary": "professional summary or objective",
            "skills": ["list of technical and soft skills"],
            "experience": [
                {
                    "title": "job title",
                    "company": "company name",
                    "duration": "employment period",
                    "description": "job description and achievements"
                }
            ],
            "education": [
                {
                    "degree": "degree type",
                    "institution": "school name",
                    "year": "graduation year",
                    "gpa": "gpa if mentioned"
                }
            ],
            "certifications": ["list of certifications"],
            "languages": ["list of languages"]
        }

        Extract only information that is clearly present in the resume. Use empty strings or empty arrays for missing information.
        """

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Parse this resume:\n\n{text_content}")
            ]

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.llm.invoke(messages)
            )

            # Check if response has content
            if not response or not hasattr(response, 'content') or not response.content:
                logger.warning("AI service returned empty response, using fallback parsing")
                return await self._fallback_parsing(text_content)

            # Extract JSON from response content (handle markdown code blocks)
            content = response.content.strip()

            # Remove markdown code block markers if present
            if content.startswith('```json'):
                content = content[7:]  # Remove ```json
            elif content.startswith('```'):
                content = content[3:]   # Remove ```

            if content.endswith('```'):
                content = content[:-3]  # Remove closing ```

            content = content.strip()

            # Parse JSON response
            parsed_data = json.loads(content)
            return parsed_data

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI response as JSON: {e}. Response content: {getattr(response, 'content', 'No content') if 'response' in locals() else 'No response'}")
            return await self._fallback_parsing(text_content)
        except Exception as e:
            logger.error(f"Failed to parse resume with AI: {e}")
            return await self._fallback_parsing(text_content)
    
    async def analyze_resume(self, parsed_content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze resume data and provide insights"""
        # Check if LLM is initialized
        if self.llm is None:
            logger.warning("AI service not initialized, using fallback analysis")
            return await self._fallback_analysis(parsed_content)

        system_prompt = """You are an expert career advisor and resume analyst. Analyze the provided resume data and return insights as JSON:

        {
            "skills_extracted": ["comprehensive list of technical and soft skills"],
            "experience_years": "total years of professional experience (number)",
            "education_level": "highest education level (e.g., Bachelor's, Master's, PhD)",
            "key_strengths": ["top 5 professional strengths based on experience"],
            "suggested_improvements": ["specific suggestions to improve the resume"],
            "career_level": "entry-level, mid-level, senior, or executive",
            "industry_focus": ["primary industries based on experience"],
            "skill_gaps": ["skills that might be missing for career advancement"]
        }

        Provide actionable insights based on the resume content.
        """

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Analyze this resume data:\n\n{json.dumps(parsed_content, indent=2)}")
            ]

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                lambda: self.llm.invoke(messages)
            )

            # Parse JSON response
            analysis_data = json.loads(response.content)
            return analysis_data

        except json.JSONDecodeError as e:
            # Return basic analysis if JSON parsing fails
            return await self._fallback_analysis(parsed_content)
        except Exception as e:
            logger.error(f"Failed to analyze resume with AI: {e}")
            return await self._fallback_analysis(parsed_content)
    
    async def _fallback_parsing(self, text_content: str) -> Dict[str, Any]:
        """
        Fallback parsing method when AI parsing fails
        
        Args:
            text_content: Raw resume text
            
        Returns:
            Basic structured data
        """
        # Simple keyword-based extraction as fallback
        lines = text_content.split('\n')
        
        # Try to extract email
        email = None
        for line in lines:
            if '@' in line and '.' in line:
                words = line.split()
                for word in words:
                    if '@' in word and '.' in word:
                        email = word.strip('.,;:')
                        break
                if email:
                    break
        
        # Basic skills extraction (common technical terms)
        common_skills = [
            'python', 'java', 'javascript', 'react', 'node.js', 'sql', 'aws', 'docker',
            'kubernetes', 'git', 'html', 'css', 'mongodb', 'postgresql', 'redis',
            'machine learning', 'data analysis', 'project management', 'agile'
        ]
        
        text_lower = text_content.lower()
        found_skills = [skill for skill in common_skills if skill in text_lower]
        
        return {
            "personal_info": {"name": "", "title": ""},
            "contact_info": {"email": email or ""},
            "summary": "",
            "skills": found_skills,
            "experience": [],
            "education": [],
            "certifications": [],
            "languages": []
        }
    
    async def _fallback_analysis(self, parsed_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback analysis when AI analysis fails
        
        Args:
            parsed_content: Structured resume data
            
        Returns:
            Basic analysis data
        """
        skills = parsed_content.get('skills', [])
        experience = parsed_content.get('experience', [])
        
        # Estimate experience years
        experience_years = len(experience) * 2 if experience else 0
        
        return {
            "skills_extracted": skills,
            "experience_years": experience_years,
            "education_level": "",
            "key_strengths": skills[:5] if skills else [],
            "suggested_improvements": [
                "Add more specific achievements with quantifiable results",
                "Include relevant keywords for your target industry",
                "Ensure consistent formatting throughout the document"
            ],
            "career_level": "mid-level" if experience_years > 3 else "entry-level",
            "industry_focus": [],
            "skill_gaps": []
        }


# Global instance
ai_service = AIService()
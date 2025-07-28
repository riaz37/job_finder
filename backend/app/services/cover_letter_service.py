"""
Cover letter generation service with AI-powered personalization
"""
import json
import uuid
import re
from typing import Dict, List, Optional, Any
from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

from app.core.config import settings
from app.models.cover_letter import (
    CoverLetterTemplate, CoverLetterPersonalization, CoverLetterContent,
    CoverLetterValidation, CoverLetterGenerationRequest, CoverLetterResult,
    CoverLetterAnalysis, CoverLetterTone
)
from app.models.resume import ParsedResumeContent
from app.models.job import JobPostData


class CoverLetterTemplateManager:
    """Manages cover letter templates"""
    
    def __init__(self):
        self.templates = self._initialize_default_templates()
    
    def _initialize_default_templates(self) -> Dict[str, CoverLetterTemplate]:
        """Initialize default cover letter templates"""
        templates = {}
        
        # Professional template
        professional_template = CoverLetterTemplate(
            id="professional_standard",
            name="Professional Standard",
            description="A professional, formal cover letter template suitable for most industries",
            template_content="""Dear {hiring_manager_name},

I am writing to express my strong interest in the {job_title} position at {company_name}. With my background in {relevant_experience}, I am confident that I would be a valuable addition to your team.

{body_paragraph_1}

{body_paragraph_2}

{body_paragraph_3}

I am excited about the opportunity to contribute to {company_name}'s continued success and would welcome the chance to discuss how my skills and experience align with your needs. Thank you for your time and consideration.

Sincerely,
{candidate_name}""",
            tone=CoverLetterTone.PROFESSIONAL
        )
        templates[professional_template.id] = professional_template
        
        # Enthusiastic template
        enthusiastic_template = CoverLetterTemplate(
            id="enthusiastic_startup",
            name="Enthusiastic Startup",
            description="An energetic template perfect for startup environments and creative roles",
            template_content="""Dear {hiring_manager_name},

I'm thrilled to apply for the {job_title} role at {company_name}! Your company's mission to {company_mission} resonates deeply with my passion for {relevant_passion}.

{body_paragraph_1}

{body_paragraph_2}

I'm excited about the possibility of bringing my {key_skills} to {company_name} and contributing to your innovative team. I'd love to discuss how we can work together to achieve {company_goals}.

Best regards,
{candidate_name}""",
            tone=CoverLetterTone.ENTHUSIASTIC
        )
        templates[enthusiastic_template.id] = enthusiastic_template
        
        # Confident template
        confident_template = CoverLetterTemplate(
            id="confident_executive",
            name="Confident Executive",
            description="A confident template for senior-level positions and leadership roles",
            template_content="""Dear {hiring_manager_name},

As an experienced {professional_title} with {years_experience} years of proven success in {industry}, I am writing to express my interest in the {job_title} position at {company_name}.

{body_paragraph_1}

{body_paragraph_2}

I am confident that my track record of {key_achievements} makes me an ideal candidate for this role. I look forward to discussing how I can drive results for {company_name}.

Regards,
{candidate_name}""",
            tone=CoverLetterTone.CONFIDENT
        )
        templates[confident_template.id] = confident_template
        
        return templates
    
    def get_template(self, template_id: str) -> Optional[CoverLetterTemplate]:
        """Get template by ID"""
        return self.templates.get(template_id)
    
    def get_templates_by_tone(self, tone: CoverLetterTone) -> List[CoverLetterTemplate]:
        """Get templates by tone"""
        return [template for template in self.templates.values() if template.tone == tone]
    
    def get_all_templates(self) -> List[CoverLetterTemplate]:
        """Get all available templates"""
        return list(self.templates.values())


class CoverLetterService:
    """Service for generating personalized cover letters using AI"""
    
    def __init__(self):
        self.template_manager = CoverLetterTemplateManager()
        if settings.GEMINI_API_KEY:
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-pro",
                google_api_key=settings.GEMINI_API_KEY,
                temperature=0.3  # Slightly higher for more creative writing
            )
        else:
            self.llm = None
    
    async def generate_cover_letter(
        self,
        request: CoverLetterGenerationRequest,
        resume_data: ParsedResumeContent,
        user_id: str
    ) -> CoverLetterResult:
        """
        Generate a personalized cover letter based on job requirements and resume
        
        Args:
            request: Cover letter generation request
            resume_data: User's parsed resume data
            user_id: User identifier
            
        Returns:
            Complete cover letter result with content and validation
        """
        if not self.llm:
            raise Exception("Gemini API key not configured")
        
        # Extract personalization data
        personalization = self._extract_personalization_data(request, resume_data)
        
        # Generate cover letter content using AI
        content = await self._generate_ai_content(request, resume_data, personalization)
        
        # Validate the generated content
        validation = await self._validate_cover_letter(content, request)
        
        # Create result
        result = CoverLetterResult(
            id=str(uuid.uuid4()),
            user_id=user_id,
            content=content,
            personalization=personalization,
            validation=validation,
            template_used=request.template_id,
            generation_metadata={
                "tone_requested": request.tone.value,
                "max_word_count": request.max_word_count,
                "generation_timestamp": datetime.now().isoformat()
            }
        )
        
        return result
    
    def _extract_personalization_data(
        self,
        request: CoverLetterGenerationRequest,
        resume_data: ParsedResumeContent
    ) -> CoverLetterPersonalization:
        """Extract personalization data from request and resume"""
        
        # Use provided personalization data or create from request
        if request.personalization_data:
            return request.personalization_data
        
        return CoverLetterPersonalization(
            company_name=request.company_name,
            job_title=request.job_title,
            hiring_manager_name=request.hiring_manager_name,
            role_specific_requirements=request.job_requirements
        )
    
    async def _generate_ai_content(
        self,
        request: CoverLetterGenerationRequest,
        resume_data: ParsedResumeContent,
        personalization: CoverLetterPersonalization
    ) -> CoverLetterContent:
        """Generate cover letter content using AI"""
        
        system_prompt = f"""
        You are an expert career coach and professional writer specializing in cover letters.
        Generate a compelling, personalized cover letter that:
        
        1. Uses a {request.tone.value} tone throughout
        2. Is tailored specifically to the job and company
        3. Highlights the most relevant qualifications from the resume
        4. Stays within {request.max_word_count} words
        5. Follows professional formatting standards
        6. Includes specific examples and achievements
        7. Shows genuine interest in the company and role
        
        Return the response as a JSON object with this structure:
        {{
            "header": "Professional header with date and contact info",
            "opening_paragraph": "Engaging opening that mentions the specific role and company",
            "body_paragraphs": ["First body paragraph", "Second body paragraph", "Third body paragraph if needed"],
            "closing_paragraph": "Strong closing with call to action",
            "signature": "Professional signature line",
            "full_content": "Complete formatted cover letter text"
        }}
        
        Make sure the content is:
        - Specific to this job and company
        - Free of generic phrases
        - Professional yet engaging
        - Error-free in grammar and spelling
        - Appropriately formatted
        """
        
        # Prepare context information
        resume_summary = self._create_resume_summary(resume_data)
        job_context = self._create_job_context(request, personalization)
        
        user_prompt = f"""
        Generate a cover letter for this job application:
        
        JOB DETAILS:
        {job_context}
        
        CANDIDATE BACKGROUND:
        {resume_summary}
        
        REQUIREMENTS:
        - Tone: {request.tone.value}
        - Max words: {request.max_word_count}
        - Company: {personalization.company_name}
        - Role: {personalization.job_title}
        - Hiring Manager: {personalization.hiring_manager_name or "Hiring Manager"}
        
        Focus on the most relevant qualifications and create a compelling narrative that connects the candidate's experience to the job requirements.
        """
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # Parse JSON response
            content_data = json.loads(response.content)
            
            # Calculate word count
            full_text = content_data.get("full_content", "")
            word_count = len(full_text.split())
            
            return CoverLetterContent(
                header=content_data.get("header", ""),
                opening_paragraph=content_data.get("opening_paragraph", ""),
                body_paragraphs=content_data.get("body_paragraphs", []),
                closing_paragraph=content_data.get("closing_paragraph", ""),
                signature=content_data.get("signature", ""),
                full_content=full_text,
                word_count=word_count,
                tone_used=request.tone
            )
            
        except json.JSONDecodeError:
            # Fallback to template-based generation
            return await self._generate_template_content(request, resume_data, personalization)
        except Exception as e:
            raise Exception(f"Failed to generate cover letter content: {str(e)}")
    
    def _create_resume_summary(self, resume_data: ParsedResumeContent) -> str:
        """Create a concise summary of resume data for AI context"""
        summary_parts = []
        
        # Personal info
        if resume_data.personal_info:
            name = resume_data.personal_info.get("name", "")
            title = resume_data.personal_info.get("title", "")
            if name:
                summary_parts.append(f"Name: {name}")
            if title:
                summary_parts.append(f"Current Title: {title}")
        
        # Summary
        if resume_data.summary:
            summary_parts.append(f"Professional Summary: {resume_data.summary}")
        
        # Skills
        if resume_data.skills:
            skills_text = ", ".join(resume_data.skills[:10])  # Top 10 skills
            summary_parts.append(f"Key Skills: {skills_text}")
        
        # Experience
        if resume_data.experience:
            exp_summary = []
            for exp in resume_data.experience[:3]:  # Top 3 experiences
                title = exp.get("title", "")
                company = exp.get("company", "")
                if title and company:
                    exp_summary.append(f"{title} at {company}")
            if exp_summary:
                summary_parts.append(f"Recent Experience: {'; '.join(exp_summary)}")
        
        # Education
        if resume_data.education:
            edu = resume_data.education[0]  # Most recent education
            degree = edu.get("degree", "")
            field = edu.get("field", "")
            if degree and field:
                summary_parts.append(f"Education: {degree} in {field}")
        
        return "\n".join(summary_parts)
    
    def _create_job_context(
        self,
        request: CoverLetterGenerationRequest,
        personalization: CoverLetterPersonalization
    ) -> str:
        """Create job context for AI generation"""
        context_parts = [
            f"Job Title: {personalization.job_title}",
            f"Company: {personalization.company_name}"
        ]
        
        if request.job_description:
            context_parts.append(f"Job Description: {request.job_description}")
        
        if request.job_requirements:
            requirements_text = "; ".join(request.job_requirements)
            context_parts.append(f"Key Requirements: {requirements_text}")
        
        if request.company_info:
            context_parts.append(f"Company Info: {request.company_info}")
        
        if personalization.company_culture_keywords:
            culture_text = ", ".join(personalization.company_culture_keywords)
            context_parts.append(f"Company Culture: {culture_text}")
        
        return "\n".join(context_parts)
    
    async def _generate_template_content(
        self,
        request: CoverLetterGenerationRequest,
        resume_data: ParsedResumeContent,
        personalization: CoverLetterPersonalization
    ) -> CoverLetterContent:
        """Fallback template-based content generation"""
        
        # Get appropriate template
        template = None
        if request.template_id:
            template = self.template_manager.get_template(request.template_id)
        
        if not template:
            # Get default template by tone
            templates = self.template_manager.get_templates_by_tone(request.tone)
            template = templates[0] if templates else self.template_manager.get_all_templates()[0]
        
        # Extract data for template variables
        candidate_name = resume_data.personal_info.get("name", "[Your Name]")
        hiring_manager = personalization.hiring_manager_name or "Hiring Manager"
        
        # Create template variables
        template_vars = {
            "hiring_manager_name": hiring_manager,
            "job_title": personalization.job_title,
            "company_name": personalization.company_name,
            "candidate_name": candidate_name,
            "relevant_experience": ", ".join(resume_data.skills[:3]) if resume_data.skills else "relevant experience",
            "body_paragraph_1": "First paragraph content",
            "body_paragraph_2": "Second paragraph content",
            "body_paragraph_3": "Third paragraph content"
        }
        
        # Fill template
        full_content = template.template_content.format(**template_vars)
        
        # Split into components
        paragraphs = full_content.split("\n\n")
        
        return CoverLetterContent(
            header=f"Date: {datetime.now().strftime('%B %d, %Y')}",
            opening_paragraph=paragraphs[0] if paragraphs else "",
            body_paragraphs=paragraphs[1:-2] if len(paragraphs) > 2 else [],
            closing_paragraph=paragraphs[-2] if len(paragraphs) > 1 else "",
            signature=paragraphs[-1] if paragraphs else "",
            full_content=full_content,
            word_count=len(full_content.split()),
            tone_used=request.tone
        )
    
    async def _validate_cover_letter(
        self,
        content: CoverLetterContent,
        request: CoverLetterGenerationRequest
    ) -> CoverLetterValidation:
        """Validate cover letter content for quality and professionalism"""
        
        if not self.llm:
            return self._basic_validation(content, request)
        
        system_prompt = """
        You are a professional writing expert. Analyze the provided cover letter and return a detailed assessment as JSON:
        
        {
            "is_valid": true/false,
            "tone_score": 0.0-1.0,
            "grammar_score": 0.0-1.0,
            "personalization_score": 0.0-1.0,
            "relevance_score": 0.0-1.0,
            "overall_score": 0.0-1.0,
            "issues": ["list of specific issues found"],
            "suggestions": ["list of improvement suggestions"],
            "word_count": actual_word_count,
            "estimated_reading_time": reading_time_in_seconds
        }
        
        Evaluate:
        - Professional tone and language
        - Grammar, spelling, and punctuation
        - Level of personalization (company/role specific content)
        - Relevance to the job requirements
        - Overall quality and effectiveness
        """
        
        user_prompt = f"""
        Analyze this cover letter:
        
        COVER LETTER:
        {content.full_content}
        
        TARGET ROLE: {request.job_title}
        COMPANY: {request.company_name}
        REQUESTED TONE: {request.tone.value}
        MAX WORDS: {request.max_word_count}
        
        Provide detailed feedback on quality, professionalism, and effectiveness.
        """
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            validation_data = json.loads(response.content)
            
            return CoverLetterValidation(
                is_valid=validation_data.get("is_valid", True),
                tone_score=validation_data.get("tone_score", 0.8),
                grammar_score=validation_data.get("grammar_score", 0.8),
                personalization_score=validation_data.get("personalization_score", 0.7),
                relevance_score=validation_data.get("relevance_score", 0.7),
                overall_score=validation_data.get("overall_score", 0.75),
                issues=validation_data.get("issues", []),
                suggestions=validation_data.get("suggestions", []),
                word_count=validation_data.get("word_count", content.word_count),
                estimated_reading_time=validation_data.get("estimated_reading_time", content.word_count // 3)
            )
            
        except (json.JSONDecodeError, Exception):
            return self._basic_validation(content, request)
    
    def _basic_validation(
        self,
        content: CoverLetterContent,
        request: CoverLetterGenerationRequest
    ) -> CoverLetterValidation:
        """Basic validation without AI"""
        
        issues = []
        suggestions = []
        
        # Check word count
        if content.word_count > request.max_word_count:
            issues.append(f"Cover letter exceeds maximum word count ({content.word_count} > {request.max_word_count})")
            suggestions.append("Consider shortening the content to meet word count requirements")
        
        # Check for basic content
        if not content.opening_paragraph:
            issues.append("Missing opening paragraph")
        
        if not content.body_paragraphs:
            issues.append("Missing body paragraphs")
        
        if not content.closing_paragraph:
            issues.append("Missing closing paragraph")
        
        # Check for personalization
        company_mentioned = request.company_name.lower() in content.full_content.lower()
        job_mentioned = request.job_title.lower() in content.full_content.lower()
        
        personalization_score = 0.5
        if company_mentioned:
            personalization_score += 0.25
        if job_mentioned:
            personalization_score += 0.25
        
        if not company_mentioned:
            issues.append("Company name not mentioned in cover letter")
        if not job_mentioned:
            issues.append("Job title not mentioned in cover letter")
        
        overall_score = 0.8 if not issues else max(0.5, 0.8 - len(issues) * 0.1)
        
        return CoverLetterValidation(
            is_valid=len(issues) == 0,
            tone_score=0.8,
            grammar_score=0.8,
            personalization_score=personalization_score,
            relevance_score=0.7,
            overall_score=overall_score,
            issues=issues,
            suggestions=suggestions,
            word_count=content.word_count,
            estimated_reading_time=max(30, content.word_count // 3)
        )
    
    async def analyze_cover_letter(self, content: CoverLetterContent) -> CoverLetterAnalysis:
        """Perform detailed analysis of cover letter effectiveness"""
        
        if not self.llm:
            return self._basic_analysis(content)
        
        system_prompt = """
        You are a career expert analyzing cover letter effectiveness. Return detailed analysis as JSON:
        
        {
            "keyword_density": {"keyword1": 0.05, "keyword2": 0.03},
            "readability_score": 0.0-1.0,
            "sentiment_score": -1.0-1.0,
            "professional_language_score": 0.0-1.0,
            "company_alignment_score": 0.0-1.0,
            "job_relevance_score": 0.0-1.0,
            "uniqueness_score": 0.0-1.0,
            "call_to_action_strength": 0.0-1.0,
            "strengths": ["list of strengths"],
            "weaknesses": ["list of weaknesses"],
            "recommendations": ["specific recommendations"],
            "competitive_advantages_highlighted": ["advantages mentioned"],
            "missing_elements": ["elements that could be added"]
        }
        """
        
        user_prompt = f"""
        Analyze this cover letter for effectiveness:
        
        {content.full_content}
        
        Provide comprehensive analysis including keyword usage, readability, sentiment, and recommendations for improvement.
        """
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            analysis_data = json.loads(response.content)
            
            return CoverLetterAnalysis(**analysis_data)
            
        except (json.JSONDecodeError, Exception):
            return self._basic_analysis(content)
    
    def _basic_analysis(self, content: CoverLetterContent) -> CoverLetterAnalysis:
        """Basic analysis without AI"""
        
        text = content.full_content.lower()
        words = text.split()
        
        # Basic keyword density
        common_keywords = ["experience", "skills", "team", "company", "role", "position"]
        keyword_density = {}
        for keyword in common_keywords:
            count = text.count(keyword)
            keyword_density[keyword] = count / len(words) if words else 0
        
        return CoverLetterAnalysis(
            keyword_density=keyword_density,
            readability_score=0.7,
            sentiment_score=0.2,  # Slightly positive
            professional_language_score=0.8,
            company_alignment_score=0.6,
            job_relevance_score=0.7,
            uniqueness_score=0.6,
            call_to_action_strength=0.7,
            strengths=["Professional tone", "Clear structure"],
            weaknesses=["Could be more specific"],
            recommendations=["Add more quantifiable achievements", "Include company-specific details"],
            competitive_advantages_highlighted=[],
            missing_elements=["Specific metrics", "Company research insights"]
        )


# Global instance
cover_letter_service = CoverLetterService()
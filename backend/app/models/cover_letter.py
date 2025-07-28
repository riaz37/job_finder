"""
Cover letter related Pydantic models
"""
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum
from pydantic import BaseModel, Field, validator


class CoverLetterTone(str, Enum):
    """Available cover letter tones"""
    PROFESSIONAL = "professional"
    ENTHUSIASTIC = "enthusiastic"
    CONFIDENT = "confident"
    CONVERSATIONAL = "conversational"
    FORMAL = "formal"


class CoverLetterTemplate(BaseModel):
    """Cover letter template structure"""
    id: str
    name: str
    description: str
    template_content: str
    tone: CoverLetterTone
    industry_focus: Optional[str] = None
    job_level: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)


class CoverLetterPersonalization(BaseModel):
    """Personalization data for cover letter generation"""
    company_name: str
    job_title: str
    hiring_manager_name: Optional[str] = None
    company_culture_keywords: List[str] = Field(default_factory=list)
    role_specific_requirements: List[str] = Field(default_factory=list)
    company_values: List[str] = Field(default_factory=list)
    job_location: Optional[str] = None
    salary_range: Optional[str] = None
    company_size: Optional[str] = None
    industry: Optional[str] = None


class CoverLetterContent(BaseModel):
    """Generated cover letter content structure"""
    header: str
    opening_paragraph: str
    body_paragraphs: List[str]
    closing_paragraph: str
    signature: str
    full_content: str
    word_count: int
    tone_used: CoverLetterTone


class CoverLetterValidation(BaseModel):
    """Cover letter validation results"""
    is_valid: bool
    tone_score: float = Field(ge=0.0, le=1.0, description="Professional tone score")
    grammar_score: float = Field(ge=0.0, le=1.0, description="Grammar and language quality score")
    personalization_score: float = Field(ge=0.0, le=1.0, description="Level of personalization")
    relevance_score: float = Field(ge=0.0, le=1.0, description="Relevance to job requirements")
    overall_score: float = Field(ge=0.0, le=1.0, description="Overall quality score")
    issues: List[str] = Field(default_factory=list, description="List of identified issues")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")
    word_count: int
    estimated_reading_time: int = Field(description="Estimated reading time in seconds")


class CoverLetterGenerationRequest(BaseModel):
    """Request model for cover letter generation"""
    job_title: str
    company_name: str
    job_description: str
    job_requirements: List[str] = Field(default_factory=list)
    company_info: Optional[str] = None
    hiring_manager_name: Optional[str] = None
    template_id: Optional[str] = None
    tone: CoverLetterTone = CoverLetterTone.PROFESSIONAL
    personalization_data: Optional[CoverLetterPersonalization] = None
    max_word_count: int = Field(default=300, ge=150, le=500)
    include_salary_expectations: bool = False
    
    @validator('job_title', 'company_name')
    def validate_required_fields(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v.strip()


class CoverLetterResult(BaseModel):
    """Complete cover letter generation result"""
    id: str
    user_id: str
    job_id: Optional[str] = None
    content: CoverLetterContent
    personalization: CoverLetterPersonalization
    validation: CoverLetterValidation
    template_used: Optional[str] = None
    generation_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        from_attributes = True


class CoverLetterHistory(BaseModel):
    """Cover letter generation history"""
    id: str
    user_id: str
    job_title: str
    company_name: str
    generated_at: datetime
    quality_score: float
    was_used: bool = False
    feedback_rating: Optional[int] = Field(None, ge=1, le=5)
    
    class Config:
        from_attributes = True


class CoverLetterFeedback(BaseModel):
    """User feedback on generated cover letter"""
    cover_letter_id: str
    user_id: str
    rating: int = Field(ge=1, le=5)
    feedback_text: Optional[str] = None
    improvement_suggestions: List[str] = Field(default_factory=list)
    would_use_again: bool = True
    created_at: datetime = Field(default_factory=datetime.now)


class CoverLetterAnalysis(BaseModel):
    """Analysis of cover letter effectiveness"""
    keyword_density: Dict[str, float] = Field(default_factory=dict)
    readability_score: float = Field(ge=0.0, le=1.0)
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    professional_language_score: float = Field(ge=0.0, le=1.0)
    company_alignment_score: float = Field(ge=0.0, le=1.0)
    job_relevance_score: float = Field(ge=0.0, le=1.0)
    uniqueness_score: float = Field(ge=0.0, le=1.0)
    call_to_action_strength: float = Field(ge=0.0, le=1.0)
    
    # Detailed analysis
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    competitive_advantages_highlighted: List[str] = Field(default_factory=list)
    missing_elements: List[str] = Field(default_factory=list)
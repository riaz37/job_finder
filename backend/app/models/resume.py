"""
Resume-related Pydantic models
"""
from datetime import datetime
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field


class ResumeBase(BaseModel):
    original_filename: str
    file_url: str


class ResumeCreate(ResumeBase):
    pass


class ParsedResumeContent(BaseModel):
    """Structured representation of parsed resume content"""
    personal_info: Dict[str, Any] = Field(default_factory=dict)
    contact_info: Dict[str, Any] = Field(default_factory=dict)
    summary: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experience: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[Dict[str, Any]] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    raw_text: str = ""


class ParsedResume(BaseModel):
    """Parsed resume data for embedding processing"""
    personal_info: Dict[str, Any] = Field(default_factory=dict)
    summary: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    work_experience: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    experience_years: Optional[int] = None
    education_level: Optional[str] = None
    job_titles: List[str] = Field(default_factory=list)
    industries: List[str] = Field(default_factory=list)


class ResumeData(BaseModel):
    """Resume data model for embedding service"""
    id: str
    user_id: str
    original_filename: str
    created_at: Optional[datetime] = None


class ResumeInDB(ResumeBase):
    id: str
    user_id: str
    parsed_content: ParsedResumeContent
    embedding_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class Resume(ResumeBase):
    id: str
    user_id: str
    parsed_content: ParsedResumeContent
    embedding_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ResumeUploadResponse(BaseModel):
    """Response model for resume upload"""
    id: str
    filename: str
    status: str
    message: str
    parsed_content: Optional[ParsedResumeContent] = None


class ResumeAnalysis(BaseModel):
    """Resume analysis results"""
    skills_extracted: List[str]
    experience_years: Optional[int] = None
    education_level: Optional[str] = None
    key_strengths: List[str] = Field(default_factory=list)
    suggested_improvements: List[str] = Field(default_factory=list)


class JobRequirementsAnalysis(BaseModel):
    """Analysis of job requirements for resume customization"""
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    required_qualifications: List[str] = Field(default_factory=list)
    key_responsibilities: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    experience_level: Optional[str] = None
    industry: Optional[str] = None
    company_culture_keywords: List[str] = Field(default_factory=list)
    technical_requirements: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    priority_skills: List[str] = Field(default_factory=list)


class ResumeJobComparison(BaseModel):
    """Comparison results between resume and job requirements"""
    skill_matches: List[str] = Field(default_factory=list)
    skill_gaps: List[str] = Field(default_factory=list)
    experience_alignment: str = "medium"
    qualification_matches: List[str] = Field(default_factory=list)
    qualification_gaps: List[str] = Field(default_factory=list)
    keyword_matches: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    optimization_opportunities: List[str] = Field(default_factory=list)
    match_score: float = 0.0
    recommendations: List[str] = Field(default_factory=list)


class CustomizedResumeResult(BaseModel):
    """Result of resume customization process"""
    customized_resume: ParsedResumeContent
    job_requirements: JobRequirementsAnalysis
    comparison_results: ResumeJobComparison
    optimization_notes: List[str] = Field(default_factory=list)
    ats_keywords_added: List[str] = Field(default_factory=list)
    match_score: float = 0.0
    factual_accuracy_maintained: bool = True
    customization_timestamp: datetime = Field(default_factory=datetime.now)
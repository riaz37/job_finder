"""
User preferences Pydantic models for job search and automation settings
"""
from datetime import datetime
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field, validator


class JobType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    TEMPORARY = "temporary"
    INTERNSHIP = "internship"
    REMOTE = "remote"


class SalaryRange(BaseModel):
    min_salary: Optional[int] = Field(None, ge=0, description="Minimum salary in USD")
    max_salary: Optional[int] = Field(None, ge=0, description="Maximum salary in USD")
    currency: str = Field("USD", description="Currency code")
    
    @validator('max_salary')
    def validate_salary_range(cls, v, values):
        if v is not None and values.get('min_salary') is not None:
            if v < values['min_salary']:
                raise ValueError('max_salary must be greater than or equal to min_salary')
        return v


class AutomationSettings(BaseModel):
    enabled: bool = Field(True, description="Enable automated job applications")
    max_applications_per_day: int = Field(5, ge=1, le=50, description="Maximum applications per day")
    max_applications_per_week: int = Field(25, ge=1, le=200, description="Maximum applications per week")
    require_manual_approval: bool = Field(False, description="Require manual approval before applying")
    min_match_score_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum job match score to apply")
    application_delay_minutes: int = Field(30, ge=5, le=1440, description="Delay between applications in minutes")
    
    @validator('max_applications_per_week')
    def validate_weekly_limit(cls, v, values):
        daily_limit = values.get('max_applications_per_day', 5)
        if v < daily_limit:
            raise ValueError('max_applications_per_week must be at least equal to max_applications_per_day')
        return v


class UserPreferencesData(BaseModel):
    """Core preferences data structure"""
    job_titles: List[str] = Field(default_factory=list, description="Preferred job titles")
    locations: List[str] = Field(default_factory=list, description="Preferred job locations")
    remote_work_preference: bool = Field(True, description="Open to remote work")
    salary_range: Optional[SalaryRange] = Field(None, description="Desired salary range")
    employment_types: List[JobType] = Field(default_factory=lambda: [JobType.FULL_TIME], description="Preferred employment types")
    preferred_companies: List[str] = Field(default_factory=list, description="Preferred companies to work for")
    excluded_companies: List[str] = Field(default_factory=list, description="Companies to exclude from applications")
    preferred_industries: List[str] = Field(default_factory=list, description="Preferred industries")
    excluded_industries: List[str] = Field(default_factory=list, description="Industries to exclude")
    required_keywords: List[str] = Field(default_factory=list, description="Keywords that must be in job description")
    excluded_keywords: List[str] = Field(default_factory=list, description="Keywords to exclude from job description")
    automation_settings: AutomationSettings = Field(default_factory=AutomationSettings, description="Automation configuration")
    
    @validator('job_titles')
    def validate_job_titles(cls, v):
        if not v:
            raise ValueError('At least one job title must be specified')
        return [title.strip() for title in v if title.strip()]
    
    @validator('locations')
    def validate_locations(cls, v):
        return [location.strip() for location in v if location.strip()]
    
    @validator('preferred_companies', 'excluded_companies')
    def validate_companies(cls, v):
        return [company.strip() for company in v if company.strip()]
    
    @validator('preferred_industries', 'excluded_industries')
    def validate_industries(cls, v):
        return [industry.strip() for industry in v if industry.strip()]
    
    @validator('required_keywords', 'excluded_keywords')
    def validate_keywords(cls, v):
        return [keyword.strip().lower() for keyword in v if keyword.strip()]


class UserPreferencesCreate(BaseModel):
    """Model for creating user preferences"""
    preferences_data: UserPreferencesData


class UserPreferencesUpdate(BaseModel):
    """Model for updating user preferences"""
    preferences_data: UserPreferencesData


class UserPreferences(BaseModel):
    """Complete user preferences model with metadata"""
    id: str
    user_id: str
    preferences_data: UserPreferencesData
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserPreferencesResponse(BaseModel):
    """Response model for API endpoints"""
    id: str
    user_id: str
    preferences_data: UserPreferencesData
    created_at: datetime
    updated_at: datetime
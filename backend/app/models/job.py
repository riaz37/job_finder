"""
Job-related Pydantic models for JobSpy integration
"""
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator


class JobSite(str, Enum):
    """Supported job sites for scraping"""
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    ZIP_RECRUITER = "zip_recruiter"
    GLASSDOOR = "glassdoor"
    GOOGLE = "google"
    BAYT = "bayt"
    NAUKRI = "naukri"


class JobTypeEnum(str, Enum):
    """Job types from JobSpy"""
    FULL_TIME = "fulltime"
    PART_TIME = "parttime"
    CONTRACT = "contract"
    TEMPORARY = "temporary"
    INTERNSHIP = "internship"
    PER_DIEM = "perdiem"
    NIGHTS = "nights"
    OTHER = "other"
    SUMMER = "summer"
    VOLUNTEER = "volunteer"


class CompensationInterval(str, Enum):
    """Compensation intervals"""
    YEARLY = "yearly"
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    DAILY = "daily"
    HOURLY = "hourly"


class JobLocation(BaseModel):
    """Job location information"""
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    display_location: Optional[str] = None
    is_remote: bool = False


class JobCompensation(BaseModel):
    """Job compensation information"""
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    currency: str = "USD"
    interval: Optional[CompensationInterval] = None
    salary_source: Optional[str] = None


class JobSearchCriteria(BaseModel):
    """Criteria for job searching"""
    search_terms: List[str] = Field(..., description="Job titles or keywords to search for")
    locations: List[str] = Field(default_factory=list, description="Locations to search in")
    sites: List[JobSite] = Field(default_factory=lambda: [JobSite.LINKEDIN, JobSite.INDEED], description="Job sites to search")
    is_remote: bool = Field(False, description="Search for remote jobs")
    job_types: List[JobTypeEnum] = Field(default_factory=list, description="Job types to filter by")
    easy_apply: Optional[bool] = Field(None, description="Filter for easy apply jobs")
    results_per_site: int = Field(15, ge=1, le=100, description="Number of results per site")
    distance: int = Field(50, ge=1, le=200, description="Search radius in miles")
    hours_old: Optional[int] = Field(None, ge=1, description="Only jobs posted within this many hours")
    
    @validator('search_terms')
    def validate_search_terms(cls, v):
        if not v:
            raise ValueError('At least one search term must be provided')
        return [term.strip() for term in v if term.strip()]
    
    @validator('locations')
    def validate_locations(cls, v):
        return [location.strip() for location in v if location.strip()]


class JobPostData(BaseModel):
    """Raw job post data from JobSpy"""
    title: str
    company_name: Optional[str] = None
    job_url: str
    job_url_direct: Optional[str] = None
    location: Optional[JobLocation] = None
    description: Optional[str] = None
    company_url: Optional[str] = None
    company_url_direct: Optional[str] = None
    job_type: Optional[List[JobTypeEnum]] = None
    compensation: Optional[JobCompensation] = None
    date_posted: Optional[date] = None
    emails: Optional[List[str]] = None
    is_remote: Optional[bool] = None
    listing_type: Optional[str] = None
    site: JobSite
    
    # Site-specific fields
    job_level: Optional[str] = None
    company_industry: Optional[str] = None
    company_addresses: Optional[str] = None
    company_num_employees: Optional[str] = None
    company_revenue: Optional[str] = None
    company_description: Optional[str] = None
    company_logo: Optional[str] = None
    banner_photo_url: Optional[str] = None
    job_function: Optional[str] = None
    skills: Optional[List[str]] = None
    experience_range: Optional[str] = None
    company_rating: Optional[float] = None
    company_reviews_count: Optional[int] = None
    vacancy_count: Optional[int] = None
    work_from_home_type: Optional[str] = None


class JobPost(BaseModel):
    """Processed job post for database storage"""
    id: Optional[str] = None
    title: str
    company_name: str
    job_url: str
    location: Dict[str, Any]  # JSON field in database
    description: str
    requirements: Dict[str, Any]  # JSON field in database
    salary_info: Dict[str, Any]  # JSON field in database
    embedding_id: str
    scraped_at: datetime
    
    # Additional fields for matching and filtering
    site: JobSite
    job_types: List[JobTypeEnum]
    is_remote: bool
    match_score: Optional[float] = None
    
    class Config:
        from_attributes = True


class JobSearchResult(BaseModel):
    """Result of a job search operation"""
    jobs: List[JobPostData]
    total_found: int
    search_criteria: JobSearchCriteria
    search_timestamp: datetime
    sites_searched: List[JobSite]
    errors: List[str] = Field(default_factory=list)


class JobMatchResult(BaseModel):
    """Result of job matching against user preferences"""
    job: JobPostData
    match_score: float
    match_reasons: List[str]
    filtered_out: bool = False
    filter_reasons: List[str] = Field(default_factory=list)


class JobSearchFilters(BaseModel):
    """Filters to apply to job search results"""
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    required_keywords: List[str] = Field(default_factory=list)
    excluded_keywords: List[str] = Field(default_factory=list)
    preferred_companies: List[str] = Field(default_factory=list)
    excluded_companies: List[str] = Field(default_factory=list)
    preferred_industries: List[str] = Field(default_factory=list)
    excluded_industries: List[str] = Field(default_factory=list)
    min_match_score: float = Field(0.0, ge=0.0, le=1.0)
    exclude_applied_jobs: bool = True
    
    @validator('required_keywords', 'excluded_keywords')
    def validate_keywords(cls, v):
        return [keyword.strip().lower() for keyword in v if keyword.strip()]
    
    @validator('preferred_companies', 'excluded_companies')
    def validate_companies(cls, v):
        return [company.strip().lower() for company in v if company.strip()]
    
    @validator('preferred_industries', 'excluded_industries')
    def validate_industries(cls, v):
        return [industry.strip().lower() for industry in v if industry.strip()]
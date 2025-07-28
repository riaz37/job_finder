"""
Additional validation utilities for user preferences
"""
import re
from typing import List, Set
from fastapi import HTTPException, status


class PreferencesValidator:
    """Utility class for advanced preferences validation"""
    
    # Common job titles for validation
    COMMON_JOB_TITLES = {
        "software engineer", "data scientist", "product manager", "designer",
        "marketing manager", "sales representative", "business analyst",
        "project manager", "devops engineer", "qa engineer", "frontend developer",
        "backend developer", "full stack developer", "mobile developer"
    }
    
    # Common industries
    COMMON_INDUSTRIES = {
        "technology", "healthcare", "finance", "education", "retail",
        "manufacturing", "consulting", "media", "telecommunications",
        "automotive", "aerospace", "energy", "real estate", "hospitality"
    }
    
    @staticmethod
    def validate_job_titles(job_titles: List[str]) -> List[str]:
        """Validate and normalize job titles"""
        if not job_titles:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one job title must be provided"
            )
        
        normalized_titles = []
        for title in job_titles:
            title = title.strip()
            if not title:
                continue
            
            # Check for minimum length
            if len(title) < 2:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Job title '{title}' is too short"
                )
            
            # Check for maximum length
            if len(title) > 100:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Job title '{title}' is too long (max 100 characters)"
                )
            
            # Check for valid characters (letters, numbers, spaces, hyphens, parentheses)
            if not re.match(r'^[a-zA-Z0-9\s\-\(\)\.\/]+$', title):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Job title '{title}' contains invalid characters"
                )
            
            normalized_titles.append(title.lower())
        
        if not normalized_titles:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one valid job title must be provided"
            )
        
        return normalized_titles
    
    @staticmethod
    def validate_locations(locations: List[str]) -> List[str]:
        """Validate and normalize location strings"""
        normalized_locations = []
        for location in locations:
            location = location.strip()
            if not location:
                continue
            
            # Check for minimum length
            if len(location) < 2:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Location '{location}' is too short"
                )
            
            # Check for maximum length
            if len(location) > 100:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Location '{location}' is too long (max 100 characters)"
                )
            
            # Check for valid characters
            if not re.match(r'^[a-zA-Z0-9\s\-\,\.]+$', location):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Location '{location}' contains invalid characters"
                )
            
            normalized_locations.append(location.title())
        
        return normalized_locations
    
    @staticmethod
    def validate_company_names(companies: List[str]) -> List[str]:
        """Validate and normalize company names"""
        normalized_companies = []
        for company in companies:
            company = company.strip()
            if not company:
                continue
            
            # Check for minimum length
            if len(company) < 2:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Company name '{company}' is too short"
                )
            
            # Check for maximum length
            if len(company) > 100:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Company name '{company}' is too long (max 100 characters)"
                )
            
            normalized_companies.append(company.strip())
        
        return normalized_companies
    
    @staticmethod
    def validate_keywords(keywords: List[str]) -> List[str]:
        """Validate and normalize keywords"""
        normalized_keywords = []
        for keyword in keywords:
            keyword = keyword.strip().lower()
            if not keyword:
                continue
            
            # Check for minimum length
            if len(keyword) < 2:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Keyword '{keyword}' is too short"
                )
            
            # Check for maximum length
            if len(keyword) > 50:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Keyword '{keyword}' is too long (max 50 characters)"
                )
            
            # Check for valid characters
            if not re.match(r'^[a-zA-Z0-9\s\-\+\#\.]+$', keyword):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Keyword '{keyword}' contains invalid characters"
                )
            
            normalized_keywords.append(keyword)
        
        return normalized_keywords
    
    @staticmethod
    def validate_no_conflicts(preferred: List[str], excluded: List[str], item_type: str) -> None:
        """Validate that there are no conflicts between preferred and excluded lists"""
        preferred_set = set(item.lower().strip() for item in preferred)
        excluded_set = set(item.lower().strip() for item in excluded)
        
        conflicts = preferred_set.intersection(excluded_set)
        if conflicts:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{item_type.title()} cannot be both preferred and excluded: {', '.join(conflicts)}"
            )
    
    @staticmethod
    def validate_automation_settings(settings) -> None:
        """Validate automation settings for logical consistency"""
        # Check daily vs weekly limits
        if settings.max_applications_per_week < settings.max_applications_per_day:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Weekly application limit must be at least equal to daily limit"
            )
        
        # Check reasonable limits
        if settings.max_applications_per_day > 50:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Daily application limit cannot exceed 50"
            )
        
        if settings.max_applications_per_week > 200:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Weekly application limit cannot exceed 200"
            )
        
        # Check match score threshold
        if not 0.0 <= settings.min_match_score_threshold <= 1.0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Match score threshold must be between 0.0 and 1.0"
            )
        
        # Check application delay
        if settings.application_delay_minutes < 5:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Application delay must be at least 5 minutes"
            )
        
        if settings.application_delay_minutes > 1440:  # 24 hours
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Application delay cannot exceed 24 hours (1440 minutes)"
            )
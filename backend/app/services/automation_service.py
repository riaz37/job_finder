"""
Service for managing automation settings and rules
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from app.models.preferences import AutomationSettings, UserPreferencesData


class AutomationService:
    """Service for handling automation logic and rules"""
    
    @staticmethod
    def get_default_automation_settings() -> AutomationSettings:
        """Get default automation settings for new users"""
        return AutomationSettings(
            enabled=True,
            max_applications_per_day=5,
            max_applications_per_week=25,
            require_manual_approval=False,
            min_match_score_threshold=0.7,
            application_delay_minutes=30
        )
    
    @staticmethod
    def validate_automation_rules(settings: AutomationSettings) -> Dict[str, Any]:
        """Validate automation settings and return validation results"""
        validation_results = {
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "recommendations": []
        }
        
        # Check for potential issues
        if settings.max_applications_per_day > 20:
            validation_results["warnings"].append(
                "High daily application limit may appear spammy to employers"
            )
        
        if settings.min_match_score_threshold < 0.5:
            validation_results["warnings"].append(
                "Low match score threshold may result in poor job matches"
            )
        
        if settings.application_delay_minutes < 15:
            validation_results["warnings"].append(
                "Short application delay may trigger rate limiting"
            )
        
        if not settings.require_manual_approval and settings.max_applications_per_day > 10:
            validation_results["recommendations"].append(
                "Consider enabling manual approval for high-volume automated applications"
            )
        
        # Check for configuration conflicts
        if settings.enabled and settings.max_applications_per_day == 0:
            validation_results["errors"].append(
                "Automation is enabled but daily limit is set to 0"
            )
            validation_results["is_valid"] = False
        
        return validation_results
    
    @staticmethod
    def calculate_application_schedule(settings: AutomationSettings, start_time: datetime) -> Dict[str, Any]:
        """Calculate when applications should be submitted based on settings"""
        if not settings.enabled:
            return {"enabled": False, "next_application_time": None}
        
        # Calculate next application time based on delay
        next_application_time = start_time + timedelta(minutes=settings.application_delay_minutes)
        
        # Calculate daily and weekly limits
        daily_limit_reached_time = start_time + timedelta(
            minutes=settings.application_delay_minutes * settings.max_applications_per_day
        )
        
        weekly_limit_reached_time = start_time + timedelta(
            minutes=settings.application_delay_minutes * settings.max_applications_per_week
        )
        
        return {
            "enabled": True,
            "next_application_time": next_application_time,
            "daily_limit_reached_time": daily_limit_reached_time,
            "weekly_limit_reached_time": weekly_limit_reached_time,
            "applications_per_hour": 60 / settings.application_delay_minutes,
            "estimated_daily_applications": min(
                settings.max_applications_per_day,
                int(24 * 60 / settings.application_delay_minutes)
            )
        }
    
    @staticmethod
    def should_apply_to_job(
        job_match_score: float, 
        settings: AutomationSettings,
        daily_applications_count: int,
        weekly_applications_count: int
    ) -> Dict[str, Any]:
        """Determine if automation should apply to a specific job"""
        decision = {
            "should_apply": False,
            "reason": "",
            "requires_approval": settings.require_manual_approval
        }
        
        # Check if automation is enabled
        if not settings.enabled:
            decision["reason"] = "Automation is disabled"
            return decision
        
        # Check daily limit
        if daily_applications_count >= settings.max_applications_per_day:
            decision["reason"] = "Daily application limit reached"
            return decision
        
        # Check weekly limit
        if weekly_applications_count >= settings.max_applications_per_week:
            decision["reason"] = "Weekly application limit reached"
            return decision
        
        # Check match score threshold
        if job_match_score < settings.min_match_score_threshold:
            decision["reason"] = f"Job match score ({job_match_score:.2f}) below threshold ({settings.min_match_score_threshold:.2f})"
            return decision
        
        # All checks passed
        decision["should_apply"] = True
        decision["reason"] = "All automation criteria met"
        
        return decision
    
    @staticmethod
    def get_automation_summary(preferences: UserPreferencesData) -> Dict[str, Any]:
        """Get a summary of automation configuration"""
        settings = preferences.automation_settings
        
        return {
            "automation_enabled": settings.enabled,
            "daily_limit": settings.max_applications_per_day,
            "weekly_limit": settings.max_applications_per_week,
            "manual_approval_required": settings.require_manual_approval,
            "match_score_threshold": settings.min_match_score_threshold,
            "delay_between_applications": f"{settings.application_delay_minutes} minutes",
            "estimated_applications_per_hour": 60 / settings.application_delay_minutes if settings.application_delay_minutes > 0 else 0,
            "job_criteria": {
                "job_titles": len(preferences.job_titles),
                "locations": len(preferences.locations),
                "preferred_companies": len(preferences.preferred_companies),
                "excluded_companies": len(preferences.excluded_companies),
                "salary_range_set": preferences.salary_range is not None
            }
        }
    
    @staticmethod
    def generate_automation_recommendations(preferences: UserPreferencesData) -> List[str]:
        """Generate recommendations for improving automation settings"""
        recommendations = []
        settings = preferences.automation_settings
        
        # Check for overly aggressive settings
        if settings.max_applications_per_day > 15:
            recommendations.append(
                "Consider reducing daily application limit to avoid appearing spammy"
            )
        
        # Check for overly restrictive settings
        if settings.min_match_score_threshold > 0.9:
            recommendations.append(
                "Very high match score threshold may result in missing good opportunities"
            )
        
        # Check for insufficient job criteria
        if len(preferences.job_titles) < 3:
            recommendations.append(
                "Add more job titles to increase the pool of potential matches"
            )
        
        if not preferences.locations and not preferences.remote_work_preference:
            recommendations.append(
                "Specify preferred locations or enable remote work preference"
            )
        
        # Check for automation without approval
        if settings.enabled and not settings.require_manual_approval and settings.max_applications_per_day > 5:
            recommendations.append(
                "Consider enabling manual approval for quality control with high-volume automation"
            )
        
        # Check delay settings
        if settings.application_delay_minutes < 30:
            recommendations.append(
                "Increase application delay to reduce risk of rate limiting"
            )
        
        return recommendations
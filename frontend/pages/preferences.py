"""
Job preferences configuration page
"""
import streamlit as st
from typing import Optional, Dict, Any, List
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from utils.api_client import api_client

def get_user_preferences() -> Optional[Dict[str, Any]]:
    """Get current user preferences"""
    return api_client.get("preferences/")

def save_preferences(preferences_data: Dict[str, Any]) -> bool:
    """Save user preferences"""
    payload = {"preferences_data": preferences_data}
    result = api_client.post("preferences/upsert", payload)
    return bool(result)

def show():
    """Display the preferences page"""
    st.title("⚙️ Job Preferences")
    st.markdown("### Configure your job search criteria")
    
    # Load existing preferences
    existing_prefs = get_user_preferences()
    prefs_data = existing_prefs.get("preferences_data", {}) if existing_prefs else {}
    
    # Job Search Criteria
    st.subheader("🎯 Job Search Criteria")
    
    with st.form("preferences_form"):
        # Job titles
        job_titles_text = st.text_area(
            "Job Titles (one per line)",
            value="\n".join(prefs_data.get("job_titles", [])),
            help="Enter job titles you're interested in, one per line",
            height=100
        )
        
        # Locations
        locations_text = st.text_area(
            "Preferred Locations (one per line)",
            value="\n".join(prefs_data.get("locations", [])),
            help="Enter cities, states, or 'Remote' for remote work",
            height=80
        )
        
        # Remote work preference
        remote_work = st.checkbox(
            "Open to Remote Work",
            value=prefs_data.get("remote_work_preference", True)
        )
        
        # Employment types
        st.write("**Employment Types:**")
        employment_types = []
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.checkbox("Full-time", value="full_time" in prefs_data.get("employment_types", ["full_time"])):
                employment_types.append("full_time")
            if st.checkbox("Part-time", value="part_time" in prefs_data.get("employment_types", [])):
                employment_types.append("part_time")
        
        with col2:
            if st.checkbox("Contract", value="contract" in prefs_data.get("employment_types", [])):
                employment_types.append("contract")
            if st.checkbox("Temporary", value="temporary" in prefs_data.get("employment_types", [])):
                employment_types.append("temporary")
        
        with col3:
            if st.checkbox("Internship", value="internship" in prefs_data.get("employment_types", [])):
                employment_types.append("internship")
            if st.checkbox("Remote", value="remote" in prefs_data.get("employment_types", [])):
                employment_types.append("remote")
        
        # Salary range
        st.write("**Salary Range (USD):**")
        col1, col2 = st.columns(2)
        
        salary_range = prefs_data.get("salary_range", {})
        
        with col1:
            min_salary = st.number_input(
                "Minimum Salary",
                min_value=0,
                max_value=1000000,
                value=salary_range.get("min_salary", 50000),
                step=5000
            )
        
        with col2:
            max_salary = st.number_input(
                "Maximum Salary",
                min_value=0,
                max_value=1000000,
                value=salary_range.get("max_salary", 150000),
                step=5000
            )
        
        st.markdown("---")
        
        # Company preferences
        st.subheader("🏢 Company Preferences")
        
        preferred_companies = st.text_area(
            "Preferred Companies (one per line)",
            value="\n".join(prefs_data.get("preferred_companies", [])),
            help="Companies you'd like to work for",
            height=80
        )
        
        excluded_companies = st.text_area(
            "Companies to Exclude (one per line)",
            value="\n".join(prefs_data.get("excluded_companies", [])),
            help="Companies you want to avoid",
            height=80
        )
        
        # Industry preferences
        preferred_industries = st.text_area(
            "Preferred Industries (one per line)",
            value="\n".join(prefs_data.get("preferred_industries", [])),
            help="Industries you're interested in",
            height=80
        )
        
        excluded_industries = st.text_area(
            "Industries to Exclude (one per line)",
            value="\n".join(prefs_data.get("excluded_industries", [])),
            help="Industries you want to avoid",
            height=80
        )
        
        st.markdown("---")
        
        # Keywords
        st.subheader("🔍 Keywords")
        
        required_keywords = st.text_area(
            "Required Keywords (one per line)",
            value="\n".join(prefs_data.get("required_keywords", [])),
            help="Keywords that must appear in job descriptions",
            height=80
        )
        
        excluded_keywords = st.text_area(
            "Keywords to Exclude (one per line)",
            value="\n".join(prefs_data.get("excluded_keywords", [])),
            help="Keywords that should not appear in job descriptions",
            height=80
        )
        
        st.markdown("---")
        
        # Automation settings
        st.subheader("🤖 Automation Settings")
        
        automation_settings = prefs_data.get("automation_settings", {})
        
        automation_enabled = st.checkbox(
            "Enable Automated Job Applications",
            value=automation_settings.get("enabled", True),
            help="Allow the AI to automatically apply to jobs matching your criteria"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            max_daily_apps = st.slider(
                "Max Applications per Day",
                min_value=1,
                max_value=20,
                value=automation_settings.get("max_applications_per_day", 5),
                help="Maximum number of applications to submit per day"
            )
            
            min_match_score = st.slider(
                "Minimum Match Score",
                min_value=0.0,
                max_value=1.0,
                value=automation_settings.get("min_match_score_threshold", 0.7),
                step=0.1,
                help="Minimum job match score required for automatic application"
            )
        
        with col2:
            max_weekly_apps = st.slider(
                "Max Applications per Week",
                min_value=1,
                max_value=100,
                value=automation_settings.get("max_applications_per_week", 25),
                help="Maximum number of applications to submit per week"
            )
            
            require_approval = st.checkbox(
                "Require Manual Approval",
                value=automation_settings.get("require_manual_approval", False),
                help="Require your approval before submitting applications"
            )
        
        application_delay = st.slider(
            "Delay Between Applications (minutes)",
            min_value=5,
            max_value=240,
            value=automation_settings.get("application_delay_minutes", 30),
            help="Time to wait between submitting applications"
        )
        
        # Submit button
        submitted = st.form_submit_button("💾 Save Preferences", use_container_width=True)
        
        if submitted:
            # Validate required fields
            job_titles_list = [title.strip() for title in job_titles_text.split('\n') if title.strip()]
            
            if not job_titles_list:
                st.error("Please enter at least one job title")
                return
            
            if not employment_types:
                st.error("Please select at least one employment type")
                return
            
            if min_salary >= max_salary:
                st.error("Maximum salary must be greater than minimum salary")
                return
            
            # Prepare preferences data
            preferences_data = {
                "job_titles": job_titles_list,
                "locations": [loc.strip() for loc in locations_text.split('\n') if loc.strip()],
                "remote_work_preference": remote_work,
                "salary_range": {
                    "min_salary": min_salary,
                    "max_salary": max_salary,
                    "currency": "USD"
                },
                "employment_types": employment_types,
                "preferred_companies": [comp.strip() for comp in preferred_companies.split('\n') if comp.strip()],
                "excluded_companies": [comp.strip() for comp in excluded_companies.split('\n') if comp.strip()],
                "preferred_industries": [ind.strip() for ind in preferred_industries.split('\n') if ind.strip()],
                "excluded_industries": [ind.strip() for ind in excluded_industries.split('\n') if ind.strip()],
                "required_keywords": [kw.strip().lower() for kw in required_keywords.split('\n') if kw.strip()],
                "excluded_keywords": [kw.strip().lower() for kw in excluded_keywords.split('\n') if kw.strip()],
                "automation_settings": {
                    "enabled": automation_enabled,
                    "max_applications_per_day": max_daily_apps,
                    "max_applications_per_week": max_weekly_apps,
                    "require_manual_approval": require_approval,
                    "min_match_score_threshold": min_match_score,
                    "application_delay_minutes": application_delay
                }
            }
            
            # Save preferences
            with st.spinner("Saving preferences..."):
                if save_preferences(preferences_data):
                    st.success("✅ Preferences saved successfully!")
                    st.rerun()
    
    # Tips section
    st.markdown("---")
    st.subheader("💡 Tips for Better Job Matching")
    
    with st.expander("🎯 Optimizing Your Job Search"):
        st.markdown("""
        **Job Titles:**
        - Use specific titles (e.g., "Senior Python Developer" vs "Developer")
        - Include variations and synonyms
        - Consider both formal and informal titles
        
        **Keywords:**
        - Include technical skills and tools you know
        - Add industry-specific terms
        - Use both acronyms and full names (e.g., "AI" and "Artificial Intelligence")
        
        **Automation Settings:**
        - Start with manual approval enabled to review matches
        - Adjust match score threshold based on results
        - Monitor daily limits to avoid overwhelming employers
        """)
    
    with st.expander("🤖 How Automation Works"):
        st.markdown("""
        When automation is enabled, the AI will:
        1. Search for jobs matching your criteria
        2. Score each job based on your preferences
        3. Filter jobs by your minimum match score
        4. Apply rate limiting based on your settings
        5. Submit applications (with approval if required)
        6. Track all applications and responses
        
        You can pause automation anytime from the dashboard.
        """)
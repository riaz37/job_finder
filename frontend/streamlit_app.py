"""
AI Job Agent - Streamlit Frontend
Main application entry point with navigation
"""
import streamlit as st
import sys
import os

# Add app directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.utils.streamlit_auth import auth
from app.utils.api_client import api_client

# Configure page
st.set_page_config(
    page_title="AI Job Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

def show_home_page():
    """Display home page"""
    st.title("🤖 Welcome to AI Job Agent")
    st.write("Navigate using the sidebar to access different features.")

def show_sidebar() -> str:
    """Display sidebar navigation"""
    with st.sidebar:
        st.title("AI Job Agent")
        
        # Navigation
        pages = [
            "Dashboard",
            "Resume Upload",
            "Job Preferences",
            "Job Review",
            "Application Tracking",
            "Activity Log",
            "Settings"
        ]
        
        selected_page = st.radio("Navigation", pages, index=0)
        
        return selected_page

def main():
    """Main application logic"""
    # Check authentication
    if not auth.is_authenticated():
        auth.show_login_page()
        return
    
    # Show user info in sidebar
    auth.show_user_info()
    
    # Show sidebar and get selected page
    selected_page = show_sidebar()
    
    # Import and display selected page
    if selected_page == "Dashboard":
        from pages import dashboard
        dashboard.show()
    elif selected_page == "Resume Upload":
        from pages import resume_upload
        resume_upload.show()
    elif selected_page == "Job Preferences":
        from pages import preferences
        preferences.show()
    elif selected_page == "Job Review":
        from pages import job_review
        job_review.show()
    elif selected_page == "Application Tracking":
        from pages import application_tracking
        application_tracking.show()
    elif selected_page == "Activity Log":
        from pages import activity_log
        activity_log.show()
    elif selected_page == "Settings":
        from pages import settings
        settings.show()
    else:
        show_home_page()

if __name__ == "__main__":
    main()
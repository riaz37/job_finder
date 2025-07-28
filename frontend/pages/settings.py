"""
Settings and configuration page
"""
import streamlit as st
from typing import Optional, Dict, Any
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from utils.api_client import api_client

def show():
    """Display the settings page"""
    st.title("🛠️ Settings")
    st.markdown("### Configure your AI Job Agent")
    
    # User Profile Settings
    st.subheader("👤 Profile Settings")
    
    if st.session_state.user_info:
        user_email = st.session_state.user_info.get("email", "")
        
        with st.form("profile_form"):
            new_email = st.text_input("Email Address", value=user_email)
            
            st.write("**Change Password:**")
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            if st.form_submit_button("💾 Update Profile"):
                if new_password and new_password != confirm_password:
                    st.error("New passwords do not match")
                elif new_password and len(new_password) < 6:
                    st.error("Password must be at least 6 characters long")
                else:
                    # Update profile logic would go here
                    st.success("Profile updated successfully!")
    
    st.markdown("---")
    
    # Notification Settings
    st.subheader("🔔 Notification Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Email Notifications:**")
        email_new_jobs = st.checkbox("New job matches found", value=True)
        email_applications = st.checkbox("Application status updates", value=True)
        email_interviews = st.checkbox("Interview reminders", value=True)
        email_weekly = st.checkbox("Weekly summary report", value=True)
    
    with col2:
        st.write("**In-App Notifications:**")
        app_new_jobs = st.checkbox("New job matches", value=True)
        app_applications = st.checkbox("Application updates", value=True)
        app_errors = st.checkbox("System errors", value=True)
        app_limits = st.checkbox("Rate limit warnings", value=True)
    
    notification_frequency = st.selectbox(
        "Email notification frequency",
        ["Immediate", "Hourly digest", "Daily digest", "Weekly digest"]
    )
    
    st.markdown("---")
    
    # API and Integration Settings
    st.subheader("🔗 API & Integrations")
    
    with st.expander("🤖 AI Model Settings"):
        ai_model = st.selectbox(
            "Primary AI Model",
            ["GPT-4", "GPT-3.5-turbo", "Gemini Pro", "Claude-3"]
        )
        
        ai_temperature = st.slider(
            "AI Creativity Level",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.1,
            help="Higher values make AI responses more creative but less predictable"
        )
        
        custom_prompt = st.text_area(
            "Custom AI Instructions",
            placeholder="Add any specific instructions for the AI agent...",
            height=100
        )
    
    with st.expander("📧 Email Integration"):
        email_provider = st.selectbox(
            "Email Provider",
            ["Gmail", "Outlook", "Yahoo", "Custom SMTP"]
        )
        
        if email_provider == "Custom SMTP":
            smtp_server = st.text_input("SMTP Server")
            smtp_port = st.number_input("SMTP Port", value=587)
            smtp_username = st.text_input("Username")
            smtp_password = st.text_input("Password", type="password")
        
        email_signature = st.text_area(
            "Email Signature",
            placeholder="Your professional email signature...",
            height=80
        )
    
    with st.expander("📅 Calendar Integration"):
        calendar_provider = st.selectbox(
            "Calendar Provider",
            ["None", "Google Calendar", "Outlook Calendar", "Apple Calendar"]
        )
        
        if calendar_provider != "None":
            auto_schedule = st.checkbox("Automatically schedule interviews")
            interview_buffer = st.slider(
                "Interview buffer time (minutes)",
                min_value=15,
                max_value=120,
                value=30
            )
    
    st.markdown("---")
    
    # Privacy and Security
    st.subheader("🔒 Privacy & Security")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Data Privacy:**")
        data_retention = st.selectbox(
            "Data retention period",
            ["30 days", "90 days", "1 year", "Indefinite"]
        )
        
        share_analytics = st.checkbox(
            "Share anonymous usage analytics",
            value=True,
            help="Helps improve the service"
        )
        
        export_data = st.button("📤 Export My Data")
        if export_data:
            st.info("Data export request submitted. You'll receive an email with your data within 24 hours.")
    
    with col2:
        st.write("**Security:**")
        two_factor = st.checkbox("Enable two-factor authentication")
        
        session_timeout = st.selectbox(
            "Session timeout",
            ["1 hour", "8 hours", "24 hours", "1 week"]
        )
        
        login_notifications = st.checkbox(
            "Email notifications for new logins",
            value=True
        )
    
    st.markdown("---")
    
    # Advanced Settings
    st.subheader("⚙️ Advanced Settings")
    
    with st.expander("🔧 System Configuration"):
        debug_mode = st.checkbox("Enable debug mode")
        
        api_timeout = st.slider(
            "API timeout (seconds)",
            min_value=10,
            max_value=120,
            value=30
        )
        
        max_concurrent = st.slider(
            "Max concurrent applications",
            min_value=1,
            max_value=10,
            value=3
        )
        
        retry_attempts = st.slider(
            "Retry attempts for failed operations",
            min_value=1,
            max_value=5,
            value=3
        )
    
    with st.expander("📊 Analytics & Reporting"):
        detailed_logging = st.checkbox("Enable detailed logging", value=True)
        
        report_frequency = st.selectbox(
            "Automated report frequency",
            ["Daily", "Weekly", "Monthly", "Disabled"]
        )
        
        include_metrics = st.multiselect(
            "Include in reports",
            ["Application statistics", "Response rates", "Interview metrics", "Salary analysis"],
            default=["Application statistics", "Response rates"]
        )
    
    st.markdown("---")
    
    # Danger Zone
    st.subheader("⚠️ Danger Zone")
    
    with st.expander("🚨 Account Management", expanded=False):
        st.warning("These actions cannot be undone!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Delete All Applications", type="secondary"):
                if st.session_state.get("confirm_delete_apps", False):
                    st.error("All application data deleted!")
                    st.session_state.confirm_delete_apps = False
                else:
                    st.session_state.confirm_delete_apps = True
                    st.warning("Click again to confirm deletion of all applications")
        
        with col2:
            if st.button("❌ Delete Account", type="secondary"):
                if st.session_state.get("confirm_delete_account", False):
                    st.error("Account deletion initiated. You will be logged out.")
                    # Account deletion logic would go here
                    st.session_state.confirm_delete_account = False
                else:
                    st.session_state.confirm_delete_account = True
                    st.warning("Click again to confirm account deletion")
    
    # Save Settings
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Save All Settings", type="primary", use_container_width=True):
            st.success("✅ All settings saved successfully!")
    
    with col2:
        if st.button("🔄 Reset to Defaults", use_container_width=True):
            st.info("Settings reset to default values")
    
    with col3:
        if st.button("📋 Export Settings", use_container_width=True):
            st.info("Settings configuration exported")
    
    # System Information
    st.markdown("---")
    st.subheader("ℹ️ System Information")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**Application Version:** 1.0.0")
        st.write("**API Version:** v1")
        st.write("**Last Updated:** 2024-01-16")
    
    with col2:
        st.write("**Database Status:** ✅ Connected")
        st.write("**AI Service:** ✅ Online")
        st.write("**Email Service:** ✅ Active")
    
    with col3:
        st.write("**Storage Used:** 45.2 MB")
        st.write("**API Calls Today:** 1,247")
        st.write("**Uptime:** 99.9%")
    
    # Support and Help
    st.markdown("---")
    st.subheader("❓ Support & Help")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📚 Documentation", use_container_width=True):
            st.info("Opening documentation in new tab...")
    
    with col2:
        if st.button("💬 Contact Support", use_container_width=True):
            st.info("Opening support chat...")
    
    with col3:
        if st.button("🐛 Report Bug", use_container_width=True):
            st.info("Opening bug report form...")
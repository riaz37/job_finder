"""
Dashboard page - Overview of job search activity and key metrics
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

def show():
    """Display the dashboard page"""
    st.title("📊 Dashboard")
    st.markdown("### Your Job Search Overview")
    
    # Mock data for demonstration - replace with actual API calls
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Applications",
            value="24",
            delta="3 this week"
        )
    
    with col2:
        st.metric(
            label="Response Rate",
            value="12.5%",
            delta="2.1%"
        )
    
    with col3:
        st.metric(
            label="Interviews Scheduled",
            value="3",
            delta="1 this week"
        )
    
    with col4:
        st.metric(
            label="Active Applications",
            value="18",
            delta="-2"
        )
    
    st.markdown("---")
    
    # Charts section
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Application Activity")
        
        # Sample data for application timeline
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='D')
        applications = [0, 1, 0, 2, 1, 0, 0, 3, 1, 2, 0, 1, 0, 0, 2, 1, 3, 0, 1, 0, 2, 1, 0, 0, 1, 2, 0, 3, 1, 0, 2]
        
        df = pd.DataFrame({
            'Date': dates,
            'Applications': applications[:len(dates)]
        })
        
        fig = px.line(df, x='Date', y='Applications', title="Daily Applications")
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📊 Application Status")
        
        # Sample data for status distribution
        status_data = {
            'Status': ['Applied', 'Under Review', 'Interview', 'Rejected', 'Offer'],
            'Count': [12, 6, 3, 2, 1]
        }
        
        fig = px.pie(
            values=status_data['Count'],
            names=status_data['Status'],
            title="Application Status Distribution"
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Recent activity section
    st.subheader("🕒 Recent Activity")
    
    # Sample recent activity data
    recent_activities = [
        {"time": "2 hours ago", "action": "Applied to Software Engineer at TechCorp", "status": "success"},
        {"time": "1 day ago", "action": "Interview scheduled with DataCorp", "status": "info"},
        {"time": "2 days ago", "action": "Application rejected by StartupXYZ", "status": "error"},
        {"time": "3 days ago", "action": "Resume updated and optimized", "status": "success"},
        {"time": "4 days ago", "action": "Job preferences updated", "status": "info"}
    ]
    
    for activity in recent_activities:
        if activity["status"] == "success":
            st.success(f"✅ {activity['time']}: {activity['action']}")
        elif activity["status"] == "info":
            st.info(f"ℹ️ {activity['time']}: {activity['action']}")
        elif activity["status"] == "error":
            st.error(f"❌ {activity['time']}: {activity['action']}")
    
    st.markdown("---")
    
    # Quick actions
    st.subheader("⚡ Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔍 Find New Jobs", use_container_width=True):
            st.info("Job search functionality coming soon!")
    
    with col2:
        if st.button("📄 Upload Resume", use_container_width=True):
            st.switch_page("pages/resume_upload.py")
    
    with col3:
        if st.button("⚙️ Update Preferences", use_container_width=True):
            st.switch_page("pages/preferences.py")
    
    with col4:
        if st.button("📈 View Applications", use_container_width=True):
            st.switch_page("pages/application_tracking.py")
    
    # Automation status
    st.markdown("---")
    st.subheader("🤖 Automation Status")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.info("🟢 Automation is active - Searching for jobs matching your preferences")
        st.write("Next scheduled search: In 2 hours")
        st.write("Applications today: 2 / 5 (daily limit)")
    
    with col2:
        if st.button("⏸️ Pause Automation", use_container_width=True):
            st.warning("Automation paused")
        
        if st.button("🔧 Configure Automation", use_container_width=True):
            st.info("Redirecting to settings...")
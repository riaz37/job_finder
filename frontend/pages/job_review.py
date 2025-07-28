"""
Job review and approval page
"""
import streamlit as st
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List

def show():
    """Display the job review page"""
    st.title("🔍 Job Review")
    st.markdown("### Review and approve job recommendations")
    
    # Mock data for demonstration - replace with actual API calls
    st.info("🤖 AI has found 8 new job matches for you!")
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        match_score_filter = st.slider(
            "Minimum Match Score",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.1
        )
    
    with col2:
        location_filter = st.selectbox(
            "Location",
            ["All Locations", "Remote", "San Francisco", "New York", "Austin"]
        )
    
    with col3:
        sort_by = st.selectbox(
            "Sort by",
            ["Match Score", "Date Posted", "Salary", "Company"]
        )
    
    st.markdown("---")
    
    # Mock job recommendations
    jobs = [
        {
            "id": "1",
            "title": "Senior Python Developer",
            "company": "TechCorp Inc.",
            "location": "San Francisco, CA (Remote)",
            "salary": "$120,000 - $160,000",
            "match_score": 0.92,
            "posted_date": "2024-01-15",
            "description": "We're looking for a Senior Python Developer to join our AI team...",
            "requirements": ["5+ years Python", "Machine Learning", "FastAPI", "PostgreSQL"],
            "benefits": ["Health Insurance", "401k", "Remote Work", "Stock Options"]
        },
        {
            "id": "2",
            "title": "Full Stack Engineer",
            "company": "StartupXYZ",
            "location": "Austin, TX",
            "salary": "$100,000 - $140,000",
            "match_score": 0.87,
            "posted_date": "2024-01-14",
            "description": "Join our fast-growing startup as a Full Stack Engineer...",
            "requirements": ["React", "Node.js", "Python", "AWS"],
            "benefits": ["Equity", "Flexible Hours", "Health Insurance"]
        },
        {
            "id": "3",
            "title": "AI/ML Engineer",
            "company": "DataCorp",
            "location": "Remote",
            "salary": "$130,000 - $180,000",
            "match_score": 0.85,
            "posted_date": "2024-01-13",
            "description": "We're seeking an AI/ML Engineer to develop cutting-edge solutions...",
            "requirements": ["TensorFlow", "PyTorch", "Python", "MLOps"],
            "benefits": ["Remote First", "Learning Budget", "Health Insurance"]
        }
    ]
    
    # Display jobs
    for job in jobs:
        if job["match_score"] >= match_score_filter:
            with st.container():
                # Job header
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.subheader(f"{job['title']} at {job['company']}")
                    st.write(f"📍 {job['location']} | 💰 {job['salary']}")
                
                with col2:
                    # Match score with color coding
                    score = job['match_score']
                    if score >= 0.9:
                        st.success(f"🎯 {score:.0%} Match")
                    elif score >= 0.8:
                        st.info(f"🎯 {score:.0%} Match")
                    else:
                        st.warning(f"🎯 {score:.0%} Match")
                
                with col3:
                    st.write(f"📅 Posted: {job['posted_date']}")
                
                # Job details in expandable section
                with st.expander("View Details", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Job Description:**")
                        st.write(job['description'])
                        
                        st.write("**Requirements:**")
                        for req in job['requirements']:
                            st.write(f"• {req}")
                    
                    with col2:
                        st.write("**Benefits:**")
                        for benefit in job['benefits']:
                            st.write(f"• {benefit}")
                        
                        # Show customized resume preview
                        st.write("**Customized Resume Preview:**")
                        st.info("Resume optimized for this role with relevant keywords highlighted")
                        
                        # Show cover letter preview
                        st.write("**Generated Cover Letter:**")
                        st.info("Personalized cover letter generated based on job requirements")
                
                # Action buttons
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if st.button(f"✅ Apply Now", key=f"apply_{job['id']}", type="primary"):
                        st.success(f"Application submitted for {job['title']} at {job['company']}!")
                        st.balloons()
                
                with col2:
                    if st.button(f"📝 Customize", key=f"customize_{job['id']}"):
                        st.info("Opening customization options...")
                
                with col3:
                    if st.button(f"💾 Save for Later", key=f"save_{job['id']}"):
                        st.info(f"Job saved to your watchlist")
                
                with col4:
                    if st.button(f"❌ Not Interested", key=f"reject_{job['id']}"):
                        st.warning("Job marked as not interested. This will help improve future recommendations.")
                
                st.markdown("---")
    
    # Bulk actions
    st.subheader("⚡ Bulk Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("✅ Apply to All High Matches (90%+)", use_container_width=True):
            high_match_jobs = [job for job in jobs if job['match_score'] >= 0.9]
            st.success(f"Applied to {len(high_match_jobs)} high-match jobs!")
    
    with col2:
        if st.button("💾 Save All for Review", use_container_width=True):
            st.info(f"Saved {len(jobs)} jobs for later review")
    
    with col3:
        if st.button("🔄 Refresh Recommendations", use_container_width=True):
            st.info("Searching for new job matches...")
            st.rerun()
    
    # Application queue
    st.markdown("---")
    st.subheader("📋 Application Queue")
    
    queue_jobs = [
        {"title": "Senior Python Developer", "company": "TechCorp", "status": "Pending Approval"},
        {"title": "Data Scientist", "company": "AI Corp", "status": "Scheduled for 2:30 PM"},
        {"title": "Backend Engineer", "company": "WebCorp", "status": "Applied - Awaiting Response"}
    ]
    
    for i, job in enumerate(queue_jobs):
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            st.write(f"**{job['title']}** at {job['company']}")
        
        with col2:
            if job['status'] == "Pending Approval":
                st.warning(f"⏳ {job['status']}")
            elif "Scheduled" in job['status']:
                st.info(f"⏰ {job['status']}")
            else:
                st.success(f"✅ {job['status']}")
        
        with col3:
            if job['status'] == "Pending Approval":
                if st.button("Approve", key=f"approve_queue_{i}"):
                    st.success("Application approved!")
    
    # Settings
    st.markdown("---")
    st.subheader("⚙️ Review Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        auto_apply_threshold = st.slider(
            "Auto-apply threshold",
            min_value=0.8,
            max_value=1.0,
            value=0.95,
            step=0.05,
            help="Jobs with match scores above this will be auto-applied"
        )
    
    with col2:
        review_frequency = st.selectbox(
            "Review frequency",
            ["Real-time", "Hourly", "Daily", "Weekly"],
            help="How often to show new job recommendations"
        )
    
    if st.button("💾 Save Review Settings", use_container_width=True):
        st.success("Review settings saved!")
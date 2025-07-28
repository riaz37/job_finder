"""
Application tracking and management page
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from typing import List, Dict, Any

def show():
    """Display the application tracking page"""
    st.title("📈 Application Tracking")
    st.markdown("### Monitor your job application progress")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Applications", "47", "5 this week")
    
    with col2:
        st.metric("Response Rate", "23.4%", "3.2%")
    
    with col3:
        st.metric("Interviews", "8", "2 scheduled")
    
    with col4:
        st.metric("Offers", "2", "1 pending")
    
    st.markdown("---")
    
    # Filter and search
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Applied", "Under Review", "Interview", "Offer", "Rejected"]
        )
    
    with col2:
        date_range = st.selectbox(
            "Date Range",
            ["All Time", "Last 7 days", "Last 30 days", "Last 90 days"]
        )
    
    with col3:
        company_search = st.text_input("Search Company", placeholder="Enter company name...")
    
    with col4:
        position_search = st.text_input("Search Position", placeholder="Enter job title...")
    
    # Mock application data
    applications = [
        {
            "id": "1",
            "position": "Senior Python Developer",
            "company": "TechCorp Inc.",
            "status": "Interview",
            "applied_date": "2024-01-10",
            "last_update": "2024-01-15",
            "salary": "$120,000 - $160,000",
            "location": "San Francisco, CA",
            "match_score": 0.92,
            "notes": "Technical interview scheduled for Jan 18"
        },
        {
            "id": "2",
            "position": "Full Stack Engineer",
            "company": "StartupXYZ",
            "status": "Under Review",
            "applied_date": "2024-01-12",
            "last_update": "2024-01-14",
            "salary": "$100,000 - $140,000",
            "location": "Austin, TX",
            "match_score": 0.87,
            "notes": "Application submitted via company website"
        },
        {
            "id": "3",
            "position": "AI/ML Engineer",
            "company": "DataCorp",
            "status": "Offer",
            "applied_date": "2024-01-05",
            "last_update": "2024-01-16",
            "salary": "$130,000 - $180,000",
            "location": "Remote",
            "match_score": 0.85,
            "notes": "Offer received! Deadline: Jan 20"
        },
        {
            "id": "4",
            "position": "Backend Developer",
            "company": "WebCorp",
            "status": "Rejected",
            "applied_date": "2024-01-08",
            "last_update": "2024-01-12",
            "salary": "$90,000 - $120,000",
            "location": "New York, NY",
            "match_score": 0.78,
            "notes": "Position filled internally"
        },
        {
            "id": "5",
            "position": "Software Engineer",
            "company": "InnovateTech",
            "status": "Applied",
            "applied_date": "2024-01-14",
            "last_update": "2024-01-14",
            "salary": "$110,000 - $150,000",
            "location": "Seattle, WA",
            "match_score": 0.81,
            "notes": "Application auto-submitted by AI agent"
        }
    ]
    
    # Filter applications based on search criteria
    filtered_apps = applications
    if status_filter != "All":
        filtered_apps = [app for app in filtered_apps if app["status"] == status_filter]
    if company_search:
        filtered_apps = [app for app in filtered_apps if company_search.lower() in app["company"].lower()]
    if position_search:
        filtered_apps = [app for app in filtered_apps if position_search.lower() in app["position"].lower()]
    
    st.markdown("---")
    
    # Applications table
    st.subheader(f"📋 Applications ({len(filtered_apps)} found)")
    
    for app in filtered_apps:
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.write(f"**{app['position']}** at **{app['company']}**")
                st.write(f"📍 {app['location']} | 💰 {app['salary']}")
            
            with col2:
                # Status with color coding
                status = app['status']
                if status == "Offer":
                    st.success(f"🎉 {status}")
                elif status == "Interview":
                    st.info(f"🗣️ {status}")
                elif status == "Under Review":
                    st.warning(f"👀 {status}")
                elif status == "Applied":
                    st.info(f"📤 {status}")
                else:  # Rejected
                    st.error(f"❌ {status}")
            
            with col3:
                st.write(f"Applied: {app['applied_date']}")
                st.write(f"Updated: {app['last_update']}")
            
            # Expandable details
            with st.expander("View Details"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Match Score:** {app['match_score']:.0%}")
                    st.write(f"**Application ID:** {app['id']}")
                    st.write(f"**Notes:** {app['notes']}")
                
                with col2:
                    # Action buttons based on status
                    if app['status'] == "Offer":
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button(f"✅ Accept Offer", key=f"accept_{app['id']}", type="primary"):
                                st.success("Offer accepted! 🎉")
                        with col_b:
                            if st.button(f"❌ Decline Offer", key=f"decline_{app['id']}"):
                                st.info("Offer declined")
                    
                    elif app['status'] == "Interview":
                        if st.button(f"📅 Schedule Interview", key=f"schedule_{app['id']}"):
                            st.info("Opening calendar integration...")
                    
                    elif app['status'] == "Applied":
                        if st.button(f"📞 Follow Up", key=f"followup_{app['id']}"):
                            st.info("Follow-up email template opened")
                    
                    # Universal actions
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button(f"📝 Add Note", key=f"note_{app['id']}"):
                            st.text_area("Add a note:", key=f"note_text_{app['id']}")
                    
                    with col_b:
                        if st.button(f"🗑️ Archive", key=f"archive_{app['id']}"):
                            st.warning("Application archived")
            
            st.markdown("---")
    
    # Analytics section
    st.subheader("📊 Application Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Application timeline
        st.write("**Application Timeline**")
        
        # Create sample timeline data
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='D')
        daily_apps = [0, 1, 0, 2, 1, 0, 0, 3, 1, 2, 0, 1, 0, 0, 2, 1, 3, 0, 1, 0, 2, 1, 0, 0, 1, 2, 0, 3, 1, 0, 2]
        
        df = pd.DataFrame({
            'Date': dates,
            'Applications': daily_apps[:len(dates)]
        })
        
        fig = px.line(df, x='Date', y='Applications', title="Daily Applications")
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Status distribution
        st.write("**Status Distribution**")
        
        status_counts = {}
        for app in applications:
            status = app['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        fig = px.pie(
            values=list(status_counts.values()),
            names=list(status_counts.keys()),
            title="Application Status"
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    # Response rate analysis
    st.subheader("📈 Response Rate Analysis")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # By company size
        company_data = {
            'Company Size': ['Startup', 'Mid-size', 'Enterprise'],
            'Response Rate': [0.35, 0.28, 0.15]
        }
        fig = px.bar(company_data, x='Company Size', y='Response Rate', 
                     title="Response Rate by Company Size")
        fig.update_layout(height=250)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # By application method
        method_data = {
            'Method': ['AI Auto-Apply', 'Manual Apply', 'Referral'],
            'Response Rate': [0.18, 0.32, 0.65]
        }
        fig = px.bar(method_data, x='Method', y='Response Rate',
                     title="Response Rate by Application Method")
        fig.update_layout(height=250)
        st.plotly_chart(fig, use_container_width=True)
    
    with col3:
        # By match score
        score_data = {
            'Match Score': ['80-85%', '85-90%', '90-95%', '95%+'],
            'Response Rate': [0.12, 0.25, 0.38, 0.52]
        }
        fig = px.bar(score_data, x='Match Score', y='Response Rate',
                     title="Response Rate by Match Score")
        fig.update_layout(height=250)
        st.plotly_chart(fig, use_container_width=True)
    
    # Export options
    st.markdown("---")
    st.subheader("📤 Export Data")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Export to CSV", use_container_width=True):
            # Convert applications to DataFrame
            df = pd.DataFrame(applications)
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"job_applications_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("📈 Generate Report", use_container_width=True):
            st.info("Generating comprehensive application report...")
    
    with col3:
        if st.button("📧 Email Summary", use_container_width=True):
            st.info("Weekly application summary sent to your email!")
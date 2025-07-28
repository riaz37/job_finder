"""
Activity log and system monitoring page
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any

def show():
    """Display the activity log page"""
    st.title("📋 Activity Log")
    st.markdown("### Monitor AI agent activities and system events")
    
    # Filter options
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        log_level = st.selectbox(
            "Log Level",
            ["All", "Info", "Warning", "Error", "Success"]
        )
    
    with col2:
        activity_type = st.selectbox(
            "Activity Type",
            ["All", "Job Search", "Application", "Resume", "System", "User Action"]
        )
    
    with col3:
        date_filter = st.selectbox(
            "Time Period",
            ["Last 24 hours", "Last 7 days", "Last 30 days", "All time"]
        )
    
    with col4:
        search_query = st.text_input("Search logs", placeholder="Enter keywords...")
    
    # Mock activity log data
    activities = [
        {
            "timestamp": datetime.now() - timedelta(minutes=15),
            "level": "Success",
            "type": "Application",
            "message": "Successfully applied to Senior Python Developer at TechCorp",
            "details": {
                "job_id": "job_123",
                "company": "TechCorp",
                "position": "Senior Python Developer",
                "match_score": 0.92
            }
        },
        {
            "timestamp": datetime.now() - timedelta(hours=2),
            "level": "Info",
            "type": "Job Search",
            "message": "Found 12 new job matches based on updated preferences",
            "details": {
                "search_query": "Python Developer",
                "results_count": 12,
                "high_matches": 3
            }
        },
        {
            "timestamp": datetime.now() - timedelta(hours=4),
            "level": "Warning",
            "type": "System",
            "message": "Daily application limit reached (5/5)",
            "details": {
                "limit_type": "daily_applications",
                "current_count": 5,
                "limit": 5
            }
        },
        {
            "timestamp": datetime.now() - timedelta(hours=6),
            "level": "Success",
            "type": "Resume",
            "message": "Resume customized for AI/ML Engineer position",
            "details": {
                "job_id": "job_456",
                "customization_score": 0.88,
                "keywords_added": ["TensorFlow", "PyTorch", "MLOps"]
            }
        },
        {
            "timestamp": datetime.now() - timedelta(hours=8),
            "level": "Error",
            "type": "Application",
            "message": "Failed to submit application to DataCorp - website timeout",
            "details": {
                "job_id": "job_789",
                "error_code": "TIMEOUT",
                "retry_scheduled": True
            }
        },
        {
            "timestamp": datetime.now() - timedelta(hours=12),
            "level": "Info",
            "type": "User Action",
            "message": "User updated job preferences - added 'Remote' to locations",
            "details": {
                "action": "preferences_update",
                "field": "locations",
                "old_value": ["San Francisco", "New York"],
                "new_value": ["San Francisco", "New York", "Remote"]
            }
        },
        {
            "timestamp": datetime.now() - timedelta(days=1),
            "level": "Success",
            "type": "Job Search",
            "message": "Automated job search completed - 47 jobs analyzed",
            "details": {
                "total_jobs": 47,
                "matches_found": 8,
                "applications_queued": 3
            }
        },
        {
            "timestamp": datetime.now() - timedelta(days=1, hours=6),
            "level": "Info",
            "type": "System",
            "message": "Weekly application report generated and sent",
            "details": {
                "report_type": "weekly_summary",
                "applications_count": 12,
                "response_rate": 0.25
            }
        }
    ]
    
    # Filter activities
    filtered_activities = activities
    
    if log_level != "All":
        filtered_activities = [a for a in filtered_activities if a["level"] == log_level]
    
    if activity_type != "All":
        filtered_activities = [a for a in filtered_activities if a["type"] == activity_type]
    
    if search_query:
        filtered_activities = [a for a in filtered_activities 
                             if search_query.lower() in a["message"].lower()]
    
    # Summary stats
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Events", len(activities), "8 today")
    
    with col2:
        error_count = len([a for a in activities if a["level"] == "Error"])
        st.metric("Errors", error_count, "-2 from yesterday")
    
    with col3:
        success_count = len([a for a in activities if a["level"] == "Success"])
        st.metric("Successful Actions", success_count, "+3 from yesterday")
    
    with col4:
        app_count = len([a for a in activities if a["type"] == "Application"])
        st.metric("Applications", app_count, "+2 today")
    
    st.markdown("---")
    
    # Activity log display
    st.subheader(f"📝 Activity Log ({len(filtered_activities)} entries)")
    
    for activity in filtered_activities:
        with st.container():
            col1, col2, col3 = st.columns([1, 2, 4])
            
            with col1:
                # Timestamp
                time_str = activity["timestamp"].strftime("%H:%M")
                date_str = activity["timestamp"].strftime("%m/%d")
                st.write(f"**{time_str}**")
                st.write(f"{date_str}")
            
            with col2:
                # Level and type with color coding
                level = activity["level"]
                if level == "Success":
                    st.success(f"✅ {level}")
                elif level == "Error":
                    st.error(f"❌ {level}")
                elif level == "Warning":
                    st.warning(f"⚠️ {level}")
                else:
                    st.info(f"ℹ️ {level}")
                
                st.write(f"**{activity['type']}**")
            
            with col3:
                # Message and details
                st.write(activity["message"])
                
                # Show details in expandable section
                if activity.get("details"):
                    with st.expander("View Details"):
                        details = activity["details"]
                        for key, value in details.items():
                            if isinstance(value, list):
                                st.write(f"**{key.replace('_', ' ').title()}:** {', '.join(map(str, value))}")
                            else:
                                st.write(f"**{key.replace('_', ' ').title()}:** {value}")
            
            st.markdown("---")
    
    # System health monitoring
    st.subheader("🔧 System Health")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("API Response Time", "245ms", "-12ms")
        st.metric("Database Connections", "8/20", "Normal")
    
    with col2:
        st.metric("Job Search Success Rate", "94.2%", "+2.1%")
        st.metric("Application Success Rate", "87.5%", "-1.2%")
    
    with col3:
        st.metric("AI Model Latency", "1.2s", "+0.1s")
        st.metric("Queue Processing", "Real-time", "Healthy")
    
    # Error analysis
    st.markdown("---")
    st.subheader("🚨 Error Analysis")
    
    error_activities = [a for a in activities if a["level"] == "Error"]
    
    if error_activities:
        st.write(f"**Recent Errors ({len(error_activities)}):**")
        
        for error in error_activities[-5:]:  # Show last 5 errors
            with st.expander(f"❌ {error['message'][:50]}..."):
                st.write(f"**Time:** {error['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                st.write(f"**Type:** {error['type']}")
                st.write(f"**Message:** {error['message']}")
                
                if error.get("details"):
                    st.write("**Details:**")
                    for key, value in error["details"].items():
                        st.write(f"- {key}: {value}")
                
                # Suggested actions
                st.write("**Suggested Actions:**")
                if "timeout" in error["message"].lower():
                    st.write("- Check network connectivity")
                    st.write("- Verify target website availability")
                    st.write("- Consider increasing timeout limits")
                elif "limit" in error["message"].lower():
                    st.write("- Review rate limiting settings")
                    st.write("- Adjust application frequency")
                else:
                    st.write("- Check system logs for more details")
                    st.write("- Contact support if issue persists")
    else:
        st.success("🎉 No recent errors found!")
    
    # Export and management
    st.markdown("---")
    st.subheader("📤 Log Management")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📊 Export Logs", use_container_width=True):
            # Convert to DataFrame for export
            log_data = []
            for activity in activities:
                log_data.append({
                    "Timestamp": activity["timestamp"],
                    "Level": activity["level"],
                    "Type": activity["type"],
                    "Message": activity["message"]
                })
            
            df = pd.DataFrame(log_data)
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"activity_log_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("🧹 Clear Old Logs", use_container_width=True):
            st.warning("This will remove logs older than 90 days. Confirm?")
            if st.button("Confirm Clear"):
                st.success("Old logs cleared successfully!")
    
    with col3:
        if st.button("📧 Email Report", use_container_width=True):
            st.info("Activity report sent to your email!")
    
    with col4:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    # Real-time monitoring toggle
    st.markdown("---")
    st.subheader("⚡ Real-time Monitoring")
    
    col1, col2 = st.columns(2)
    
    with col1:
        auto_refresh = st.checkbox("Enable auto-refresh (30s)", value=False)
        if auto_refresh:
            st.info("🔄 Auto-refresh enabled - page will update every 30 seconds")
    
    with col2:
        notification_level = st.selectbox(
            "Notification threshold",
            ["Errors only", "Warnings and Errors", "All events"]
        )
        st.info(f"📱 Notifications set to: {notification_level}")
"""
Resume upload and management page
"""
import streamlit as st
import requests
from datetime import datetime
from typing import Optional, Dict, Any

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from utils.api_client import api_client

def upload_resume_file(file) -> Optional[Dict[str, Any]]:
    """Upload resume file to backend"""
    files = {"file": (file.name, file.getvalue(), file.type)}
    return api_client.post("resume/upload", files=files)

def get_user_resumes() -> Optional[list]:
    """Get user's uploaded resumes"""
    result = api_client.get("resume/")
    return result if isinstance(result, list) else []

def analyze_resume(resume_id: str) -> Optional[Dict[str, Any]]:
    """Get resume analysis"""
    return api_client.get(f"resume/{resume_id}/analyze")

def delete_resume(resume_id: str) -> bool:
    """Delete a resume"""
    result = api_client.delete(f"resume/{resume_id}")
    return bool(result)

def show():
    """Display the resume upload page"""
    st.title("📄 Resume Management")
    st.markdown("### Upload and manage your resumes")
    
    # Upload section
    st.subheader("📤 Upload New Resume")
    
    uploaded_file = st.file_uploader(
        "Choose a resume file",
        type=['pdf', 'doc', 'docx'],
        help="Supported formats: PDF, DOC, DOCX (Max size: 10MB)"
    )
    
    if uploaded_file is not None:
        # Show file details
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**Filename:** {uploaded_file.name}")
        with col2:
            st.write(f"**Size:** {uploaded_file.size / 1024:.1f} KB")
        with col3:
            st.write(f"**Type:** {uploaded_file.type}")
        
        if st.button("🚀 Upload and Process", use_container_width=True):
            with st.spinner("Uploading and processing resume..."):
                result = upload_resume_file(uploaded_file)
                
                if result:
                    st.success("✅ Resume uploaded and processed successfully!")
                    
                    # Show parsed content preview
                    if result.get("parsed_content"):
                        st.subheader("📋 Extracted Information")
                        
                        parsed = result["parsed_content"]
                        
                        # Personal info
                        if parsed.get("personal_info"):
                            st.write("**Personal Information:**")
                            for key, value in parsed["personal_info"].items():
                                if value:
                                    st.write(f"- {key.replace('_', ' ').title()}: {value}")
                        
                        # Skills
                        if parsed.get("skills"):
                            st.write("**Skills:**")
                            st.write(", ".join(parsed["skills"]))
                        
                        # Experience
                        if parsed.get("experience"):
                            st.write("**Experience:**")
                            for exp in parsed["experience"][:3]:  # Show first 3
                                if isinstance(exp, dict):
                                    title = exp.get("title", "Unknown Position")
                                    company = exp.get("company", "Unknown Company")
                                    st.write(f"- {title} at {company}")
                        
                        # Education
                        if parsed.get("education"):
                            st.write("**Education:**")
                            for edu in parsed["education"]:
                                if isinstance(edu, dict):
                                    degree = edu.get("degree", "Unknown Degree")
                                    school = edu.get("school", "Unknown School")
                                    st.write(f"- {degree} from {school}")
                    
                    st.rerun()
    
    st.markdown("---")
    
    # Existing resumes section
    st.subheader("📚 Your Resumes")
    
    resumes = get_user_resumes()
    
    if not resumes:
        st.info("No resumes uploaded yet. Upload your first resume above!")
    else:
        for resume in resumes:
            with st.expander(f"📄 {resume['original_filename']} (Uploaded: {resume['created_at'][:10]})"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button(f"🔍 Analyze", key=f"analyze_{resume['id']}"):
                        with st.spinner("Analyzing resume..."):
                            analysis = analyze_resume(resume['id'])
                            
                            if analysis:
                                st.subheader("📊 Resume Analysis")
                                
                                # Skills
                                if analysis.get("skills_extracted"):
                                    st.write("**Extracted Skills:**")
                                    st.write(", ".join(analysis["skills_extracted"]))
                                
                                # Experience years
                                if analysis.get("experience_years"):
                                    st.write(f"**Experience:** {analysis['experience_years']} years")
                                
                                # Education level
                                if analysis.get("education_level"):
                                    st.write(f"**Education Level:** {analysis['education_level']}")
                                
                                # Strengths
                                if analysis.get("key_strengths"):
                                    st.write("**Key Strengths:**")
                                    for strength in analysis["key_strengths"]:
                                        st.write(f"- {strength}")
                                
                                # Improvements
                                if analysis.get("suggested_improvements"):
                                    st.write("**Suggested Improvements:**")
                                    for improvement in analysis["suggested_improvements"]:
                                        st.write(f"- {improvement}")
                
                with col2:
                    if st.button(f"📝 View Details", key=f"view_{resume['id']}"):
                        st.subheader("📋 Resume Details")
                        
                        parsed = resume.get("parsed_content", {})
                        
                        # Show summary if available
                        if parsed.get("summary"):
                            st.write("**Summary:**")
                            st.write(parsed["summary"])
                        
                        # Show contact info
                        if parsed.get("contact_info"):
                            st.write("**Contact Information:**")
                            for key, value in parsed["contact_info"].items():
                                if value:
                                    st.write(f"- {key.replace('_', ' ').title()}: {value}")
                        
                        # Show skills
                        if parsed.get("skills"):
                            st.write("**Skills:**")
                            skills_text = ", ".join(parsed["skills"])
                            st.write(skills_text)
                
                with col3:
                    if st.button(f"🗑️ Delete", key=f"delete_{resume['id']}", type="secondary"):
                        if st.session_state.get(f"confirm_delete_{resume['id']}", False):
                            if delete_resume(resume['id']):
                                st.success("Resume deleted successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to delete resume")
                        else:
                            st.session_state[f"confirm_delete_{resume['id']}"] = True
                            st.warning("Click again to confirm deletion")
    
    # Tips section
    st.markdown("---")
    st.subheader("💡 Resume Tips")
    
    with st.expander("📝 Best Practices for Resume Upload"):
        st.markdown("""
        **For best results:**
        - Use a clear, well-formatted resume
        - Include relevant keywords for your target roles
        - Keep formatting simple (avoid complex layouts)
        - Ensure all text is selectable (not just images)
        - Include quantifiable achievements
        - Use standard section headers (Experience, Education, Skills, etc.)
        
        **Supported formats:**
        - PDF (recommended)
        - Microsoft Word (.doc, .docx)
        - Maximum file size: 10MB
        """)
    
    with st.expander("🤖 How AI Analysis Works"):
        st.markdown("""
        Our AI analyzes your resume to:
        - Extract key skills and technologies
        - Identify your experience level
        - Determine your education background
        - Highlight your strengths
        - Suggest improvements for better job matching
        - Optimize for Applicant Tracking Systems (ATS)
        
        This analysis helps match you with relevant job opportunities and customize your applications.
        """)
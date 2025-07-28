"""
Simple authentication test script
Run this to test the auth implementation
"""
import streamlit as st
import sys
import os

# Add app directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.utils.streamlit_auth import auth
from app.utils.api_client import api_client

st.set_page_config(page_title="Auth Test", page_icon="🔐")

st.title("🔐 Authentication Test")

if not auth.is_authenticated():
    st.info("Not authenticated - showing login page")
    auth.show_login_page()
else:
    st.success("✅ Authentication successful!")
    
    user_info = auth.get_current_user()
    if user_info:
        st.write("**User Info:**")
        st.json(user_info)
    
    st.write("**Auth Headers:**")
    st.json(auth.get_auth_headers())
    
    # Test API call
    if st.button("Test API Call"):
        with st.spinner("Testing API..."):
            result = api_client.get("auth/me")
            if result:
                st.success("API call successful!")
                st.json(result)
            else:
                st.error("API call failed")
    
    if st.button("Logout"):
        auth.logout()
        st.rerun()
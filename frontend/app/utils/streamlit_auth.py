"""
Streamlit Authentication Module
Handles user authentication, session management, and auth UI components
"""
import streamlit as st
import requests
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import jwt

class StreamlitAuth:
    def __init__(self, api_base_url: str = "http://localhost:8000/api/v1"):
        self.api_base_url = api_base_url
        self.auth_endpoint = f"{api_base_url}/auth"
        
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated"""
        token = st.session_state.get('access_token')
        if not token:
            return False
            
        # Check if token is expired
        try:
            # Decode without verification to check expiration
            decoded = jwt.decode(token, options={"verify_signature": False})
            exp_timestamp = decoded.get('exp')
            if exp_timestamp:
                exp_datetime = datetime.fromtimestamp(exp_timestamp)
                if datetime.now() >= exp_datetime:
                    self.logout()
                    return False
        except:
            self.logout()
            return False
            
        return True
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current user information"""
        return st.session_state.get('user_info')
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests"""
        token = st.session_state.get('access_token')
        if token:
            return {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
        return {'Content-Type': 'application/json'}
    
    def login(self, username: str, password: str) -> bool:
        """Authenticate user with username and password"""
        try:
            # Prepare form data for OAuth2PasswordRequestForm
            form_data = {
                'username': username,
                'password': password,
                'grant_type': 'password'
            }
            
            response = requests.post(
                f"{self.auth_endpoint}/login",
                data=form_data,  # Use form data, not JSON
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if response.status_code == 200:
                token_data = response.json()
                st.session_state['access_token'] = token_data['access_token']
                st.session_state['token_type'] = token_data['token_type']
                
                # Get user info
                user_info = self._get_user_info()
                if user_info:
                    st.session_state['user_info'] = user_info
                    return True
            else:
                error_detail = response.json().get('detail', 'Login failed')
                st.error(f"Login failed: {error_detail}")
                
        except requests.exceptions.RequestException as e:
            st.error(f"Connection error: {str(e)}")
        except Exception as e:
            st.error(f"Login error: {str(e)}")
            
        return False
    
    def register(self, email: str, password: str, full_name: str) -> bool:
        """Register a new user"""
        try:
            user_data = {
                'email': email,
                'password': password,
                'full_name': full_name
            }
            
            response = requests.post(
                f"{self.auth_endpoint}/register",
                json=user_data,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 201:
                st.success("Registration successful! Please login.")
                return True
            else:
                error_detail = response.json().get('detail', 'Registration failed')
                st.error(f"Registration failed: {error_detail}")
                
        except requests.exceptions.RequestException as e:
            st.error(f"Connection error: {str(e)}")
        except Exception as e:
            st.error(f"Registration error: {str(e)}")
            
        return False
    
    def logout(self):
        """Logout user and clear session"""
        try:
            # Call logout endpoint if authenticated
            if st.session_state.get('access_token'):
                headers = self.get_auth_headers()
                requests.post(f"{self.auth_endpoint}/logout", headers=headers)
        except:
            pass  # Ignore errors during logout API call
        
        # Clear session state
        for key in ['access_token', 'token_type', 'user_info']:
            if key in st.session_state:
                del st.session_state[key]
    
    def _get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get current user information from API"""
        try:
            headers = self.get_auth_headers()
            response = requests.get(f"{self.auth_endpoint}/me", headers=headers)
            
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None
    
    def show_login_page(self):
        """Display login/register page"""
        st.title("🤖 AI Job Agent")
        st.subheader("Please login to continue")
        
        # Create tabs for login and register
        login_tab, register_tab = st.tabs(["Login", "Register"])
        
        with login_tab:
            self._show_login_form()
            
        with register_tab:
            self._show_register_form()
    
    def _show_login_form(self):
        """Display login form"""
        with st.form("login_form"):
            st.subheader("Login")
            username = st.text_input("Email", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            
            col1, col2 = st.columns([1, 3])
            with col1:
                login_button = st.form_submit_button("Login", use_container_width=True)
            
            if login_button:
                if not username or not password:
                    st.error("Please enter both email and password")
                else:
                    with st.spinner("Logging in..."):
                        if self.login(username, password):
                            st.success("Login successful!")
                            st.rerun()
    
    def _show_register_form(self):
        """Display registration form"""
        with st.form("register_form"):
            st.subheader("Create Account")
            full_name = st.text_input("Full Name", key="register_name")
            email = st.text_input("Email", key="register_email")
            password = st.text_input("Password", type="password", key="register_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="register_confirm")
            
            col1, col2 = st.columns([1, 3])
            with col1:
                register_button = st.form_submit_button("Register", use_container_width=True)
            
            if register_button:
                if not all([full_name, email, password, confirm_password]):
                    st.error("Please fill in all fields")
                elif password != confirm_password:
                    st.error("Passwords do not match")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters long")
                else:
                    with st.spinner("Creating account..."):
                        if self.register(email, password, full_name):
                            st.balloons()
    
    def show_user_info(self):
        """Display user info in sidebar"""
        user_info = self.get_current_user()
        if user_info:
            with st.sidebar:
                st.divider()
                st.write(f"👤 **{user_info.get('full_name', 'User')}**")
                st.write(f"📧 {user_info.get('email', '')}")
                
                if st.button("Logout", use_container_width=True):
                    self.logout()
                    st.rerun()

# Global auth instance
auth = StreamlitAuth()
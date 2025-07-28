"""
API Client utility for making authenticated requests
"""
import streamlit as st
import requests
from typing import Dict, Any, Optional, Union
import json

class APIClient:
    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication token"""
        headers = {'Content-Type': 'application/json'}
        
        token = st.session_state.get('access_token')
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        return headers
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response with error checking"""
        if response.status_code == 401:
            # Token expired or invalid
            st.error("Session expired. Please login again.")
            from .streamlit_auth import auth
            auth.logout()
            st.rerun()
            return {}
        
        try:
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.HTTPError as e:
            error_msg = "API request failed"
            try:
                error_detail = response.json().get('detail', str(e))
                error_msg = f"API Error: {error_detail}"
            except:
                error_msg = f"HTTP Error: {response.status_code}"
            
            st.error(error_msg)
            return {}
        except requests.exceptions.RequestException as e:
            st.error(f"Connection error: {str(e)}")
            return {}
        except json.JSONDecodeError:
            st.error("Invalid response from server")
            return {}
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make GET request"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        try:
            response = requests.get(url, params=params, headers=headers)
            return self._handle_response(response)
        except Exception as e:
            st.error(f"Request failed: {str(e)}")
            return {}
    
    def post(self, endpoint: str, data: Optional[Dict] = None, files: Optional[Dict] = None) -> Dict[str, Any]:
        """Make POST request"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        try:
            if files:
                # Remove Content-Type for file uploads
                headers.pop('Content-Type', None)
                response = requests.post(url, data=data, files=files, headers=headers)
            else:
                response = requests.post(url, json=data, headers=headers)
            
            return self._handle_response(response)
        except Exception as e:
            st.error(f"Request failed: {str(e)}")
            return {}
    
    def put(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make PUT request"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        try:
            response = requests.put(url, json=data, headers=headers)
            return self._handle_response(response)
        except Exception as e:
            st.error(f"Request failed: {str(e)}")
            return {}
    
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make DELETE request"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        try:
            response = requests.delete(url, headers=headers)
            return self._handle_response(response)
        except Exception as e:
            st.error(f"Request failed: {str(e)}")
            return {}

# Global API client instance
api_client = APIClient()
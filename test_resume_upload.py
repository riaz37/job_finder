#!/usr/bin/env python3
"""
Test script for resume upload functionality
"""
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('backend/.env')

def test_resume_upload():
    """Test the resume upload endpoint"""
    
    # First, let's get an auth token by logging in
    login_data = {
        "username": "riaz@gmail.com",  # OAuth2 uses username field for email
        "password": "Shuvo302001"  # Replace with actual password
    }
    
    # Login to get token (using form data, not JSON)
    login_response = requests.post("http://localhost:8000/api/v1/auth/login", data=login_data)
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        print(f"Response: {login_response.text}")
        return
    
    token_data = login_response.json()
    access_token = token_data.get("access_token")
    
    if not access_token:
        print("❌ No access token received")
        return
    
    print(f"✅ Login successful, token: {access_token[:50]}...")
    
    # Now test resume upload
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    # Use the existing PDF file
    pdf_file_path = "Riazul Islam.pdf"
    
    if not os.path.exists(pdf_file_path):
        print(f"❌ PDF file not found: {pdf_file_path}")
        return
    
    with open(pdf_file_path, 'rb') as f:
        files = {
            'file': ('Riazul Islam.pdf', f, 'application/pdf')
        }
        
        print("📤 Uploading resume...")
        upload_response = requests.post(
            "http://localhost:8000/api/v1/resume/upload",
            headers=headers,
            files=files
        )
    
    print(f"📊 Upload response status: {upload_response.status_code}")
    print(f"📄 Upload response: {upload_response.text}")
    
    if upload_response.status_code == 200:
        print("✅ Resume upload successful!")
    else:
        print("❌ Resume upload failed!")

if __name__ == "__main__":
    test_resume_upload()
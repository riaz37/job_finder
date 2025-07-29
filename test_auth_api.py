#!/usr/bin/env python3
"""
Test authentication in API context
"""
import requests
import json

# Test login first
def test_login():
    print("=== Testing Login ===")
    
    login_data = {
        'username': 'riaz37.ipe@gmail.com',  # Use the email from debug
        'password': 'your_password_here'  # You'll need to provide the actual password
    }
    
    response = requests.post(
        'http://localhost:8000/api/v1/auth/login',
        data=login_data,
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        token_data = response.json()
        token = token_data['access_token']
        print(f"✅ Login successful, token: {token[:50]}...")
        return token
    else:
        print("❌ Login failed")
        return None

def test_auth_endpoint(token):
    print("\n=== Testing Auth Endpoint ===")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(
        'http://localhost:8000/api/v1/auth/me',
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    return response.status_code == 200

def test_resume_upload(token):
    print("\n=== Testing Resume Upload ===")
    
    # Create a simple test file
    test_content = "Test Resume\nJohn Doe\nSoftware Engineer\nSkills: Python, JavaScript"
    
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    files = {
        'file': ('test_resume.txt', test_content, 'text/plain')
    }
    
    response = requests.post(
        'http://localhost:8000/api/v1/resume/upload',
        files=files,
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

if __name__ == "__main__":
    print("🧪 Testing API Authentication and Resume Upload")
    print("Note: Make sure the backend server is running on localhost:8000")
    print("You may need to update the password in the script")
    
    # Uncomment and update password to test
    # token = test_login()
    # if token:
    #     if test_auth_endpoint(token):
    #         test_resume_upload(token)
    
    print("\n💡 To run this test:")
    print("1. Update the password in test_login()")
    print("2. Uncomment the test calls at the bottom")
    print("3. Make sure the backend server is running")
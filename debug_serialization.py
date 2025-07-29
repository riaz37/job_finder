#!/usr/bin/env python3
"""
Debug script to test serialization issues
"""
import json
import sys
import os
import asyncio

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.models.resume import ParsedResumeContent, ResumeUploadResponse

def test_serialization():
    """Test if ParsedResumeContent can be serialized"""
    
    # Create a test ParsedResumeContent with various data types
    test_data = {
        "personal_info": {
            "name": "Test User",
            "email": "test@example.com",
            "phone": "123-456-7890"
        },
        "contact_info": {
            "address": "123 Test St",
            "city": "Test City"
        },
        "summary": "Test summary",
        "skills": ["Python", "JavaScript", "SQL"],
        "experience": [
            {
                "company": "Test Company",
                "position": "Developer",
                "duration": "2020-2023"
            }
        ],
        "education": [
            {
                "school": "Test University",
                "degree": "Computer Science",
                "year": "2020"
            }
        ],
        "certifications": [],
        "languages": ["English", "Spanish"],
        "raw_text": "This is the raw text content"
    }
    
    print("Testing ParsedResumeContent serialization...")
    
    try:
        # Create ParsedResumeContent object
        parsed_content = ParsedResumeContent(**test_data)
        print("✅ ParsedResumeContent object created successfully")
        
        # Test model_dump
        content_dict = parsed_content.model_dump()
        print("✅ model_dump() successful")
        
        # Test JSON serialization
        json_str = json.dumps(content_dict)
        print("✅ JSON serialization successful")
        
        # Test ResumeUploadResponse
        response = ResumeUploadResponse(
            id="test-id",
            filename="test.pdf",
            status="success",
            message="Test message",
            parsed_content=parsed_content
        )
        print("✅ ResumeUploadResponse object created successfully")
        
        # Test response serialization
        response_dict = response.model_dump()
        print("✅ ResumeUploadResponse model_dump() successful")
        
        response_json = json.dumps(response_dict)
        print("✅ ResumeUploadResponse JSON serialization successful")
        
        print("\n🎉 All serialization tests passed!")
        
    except Exception as e:
        print(f"❌ Serialization test failed: {e}")
        import traceback
        traceback.print_exc()

def test_with_bytes():
    """Test what happens when bytes data is included"""
    
    print("\nTesting with bytes data...")
    
    test_data_with_bytes = {
        "personal_info": {
            "name": "Test User",
            "photo": b"fake_image_bytes"  # This should cause issues
        },
        "contact_info": {},
        "summary": "Test summary",
        "skills": [],
        "experience": [],
        "education": [],
        "certifications": [],
        "languages": [],
        "raw_text": "Test"
    }
    
    try:
        parsed_content = ParsedResumeContent(**test_data_with_bytes)
        print("✅ ParsedResumeContent with bytes created")
        
        content_dict = parsed_content.model_dump()
        print("✅ model_dump() with bytes successful")
        
        json_str = json.dumps(content_dict)
        print("✅ JSON serialization with bytes successful (unexpected!)")
        
    except Exception as e:
        print(f"❌ Expected failure with bytes: {e}")

if __name__ == "__main__":
    test_serialization()
    test_with_bytes()

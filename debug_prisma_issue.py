#!/usr/bin/env python3
"""
Debug script to test Prisma database operations
"""
import asyncio
import json
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('backend/.env')

# Add backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.models.resume import ParsedResumeContent
from app.db.database import get_database

async def test_prisma_operations():
    """Test basic Prisma operations to debug the issue"""
    
    try:
        # Get database connection
        db = await get_database()
        print("✅ Database connection successful")
        
        # Test user query first
        users = await db.user.find_many()
        print(f"✅ Found {len(users)} users in database")
        
        if not users:
            print("❌ No users found. Need to create a user first.")
            return
        
        user_id = users[0].id
        print(f"✅ Using user ID: {user_id}")
        
        # Create test parsed content
        test_parsed_content = ParsedResumeContent(
            personal_info={"name": "Test User"},
            contact_info={"email": "test@example.com"},
            summary="Test summary",
            skills=["Python", "FastAPI"],
            experience=[{"company": "Test Corp", "role": "Developer"}],
            education=[{"degree": "BS", "school": "Test University"}],
            certifications=[],
            languages=["English"],
            raw_text="Test raw text content"
        )
        
        print("✅ Created test parsed content")
        
        # Test serialization
        content_dict = test_parsed_content.model_dump()
        print(f"✅ Serialized content: {json.dumps(content_dict, indent=2)}")
        
        # Test database creation with minimal data first
        # Try with a very simple JSON object for parsedContent
        simple_content = {
            'personal_info': {'name': 'Test User'},
            'skills': ['Python'],
            'raw_text': 'Test content'
        }

        test_data = {
            'userId': user_id,
            'originalFilename': 'test.pdf',
            'fileUrl': 'https://example.com/test.pdf',
            'parsedContent': simple_content,
            'embeddingId': 'test_embedding_123'
        }
        
        print("📤 Attempting to create resume record...")
        print(f"Data being sent: {json.dumps(test_data, indent=2, default=str)}")
        
        resume_data = await db.resume.create(data=test_data)
        print(f"✅ Resume created successfully: {resume_data.id}")
        
        # Clean up - delete the test record
        await db.resume.delete(where={'id': resume_data.id})
        print("✅ Test record cleaned up")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print(f"❌ Error type: {type(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_prisma_operations())

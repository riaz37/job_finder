#!/usr/bin/env python3
"""
Debug script to test resume upload functionality
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('backend/.env')

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.db.database import get_database
from app.services.auth_service import AuthService
from app.api.v1.auth import get_current_user
from app.core.security import create_access_token

async def debug_auth():
    """Debug authentication flow"""
    print("=== Debugging Authentication ===")
    
    # Test database connection
    try:
        db = await get_database()
        print("✅ Database connection successful")
        
        # Check if we have any users
        users = await db.user.find_many()
        print(f"📊 Found {len(users)} users in database")
        
        if users:
            user = users[0]
            print(f"👤 First user: {user.email} (ID: {user.id})")
            
            # Test token creation
            token = create_access_token(data={"sub": user.id})
            print(f"🔑 Generated token: {token[:50]}...")
            
            # Test auth service
            auth_service = AuthService(db)
            retrieved_user = await auth_service.get_user_by_id(user.id)
            if retrieved_user:
                print(f"✅ User retrieval successful: {retrieved_user.email}")
            else:
                print("❌ Failed to retrieve user")
                
        else:
            print("⚠️ No users found in database")
            
    except Exception as e:
        print(f"❌ Database error: {e}")

async def debug_resume_creation():
    """Debug resume creation process"""
    print("\n=== Debugging Resume Creation ===")
    
    try:
        from app.models.resume import ParsedResumeContent
        from app.db.resume_repository import resume_repository
        
        # Create test parsed content
        test_content = ParsedResumeContent(
            personal_info={"name": "Test User", "title": "Software Engineer"},
            contact_info={"email": "test@example.com", "phone": "123-456-7890"},
            summary="Test summary",
            skills=["Python", "JavaScript", "React"],
            experience=[{"title": "Developer", "company": "Test Corp", "duration": "2 years"}],
            education=[{"degree": "BS Computer Science", "school": "Test University"}],
            raw_text="Test resume content"
        )
        
        print("✅ ParsedResumeContent created successfully")
        print(f"📄 Content: {test_content.model_dump()}")
        
        # Test serialization
        from app.db.resume_repository import ResumeRepository
        repo = ResumeRepository()
        serialized = repo._serialize_parsed_content(test_content)
        print("✅ Content serialization successful")
        
        # Test actual database creation
        db = await get_database()
        users = await db.user.find_many()
        if users:
            user_id = users[0].id
            print(f"🧪 Testing resume creation for user: {user_id}")
            
            try:
                resume = await resume_repository.create_resume(
                    user_id=user_id,
                    original_filename="test_resume.pdf",
                    file_url="https://test.com/resume.pdf",
                    parsed_content=test_content,
                    embedding_id="test_embedding_123"
                )
                print(f"✅ Resume created successfully: {resume.id}")
                
                # Clean up - delete the test resume
                await resume_repository.delete_resume(resume.id)
                print("🧹 Test resume cleaned up")
                
            except Exception as e:
                print(f"❌ Database creation error: {e}")
                import traceback
                traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Resume creation error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_auth())
    asyncio.run(debug_resume_creation())
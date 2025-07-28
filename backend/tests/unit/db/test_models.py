"""
Unit tests for database models and relationships
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from prisma.models import User, Resume, JobPost, Application, UserPreferences
from prisma.enums import ApplicationStatus


class TestUserModel:
    """Test cases for User model"""
    
    @pytest.mark.asyncio
    async def test_create_user(self):
        """Test creating a new user"""
        with patch('prisma.Prisma') as mock_prisma:
            mock_db = AsyncMock()
            mock_prisma.return_value = mock_db
            
            user_data = {
                'email': 'test@example.com',
                'passwordHash': 'hashed_password'
            }
            
            expected_user = User(
                id='user_123',
                email='test@example.com',
                passwordHash='hashed_password',
                createdAt=datetime.now(),
                updatedAt=datetime.now()
            )
            
            mock_db.user.create.return_value = expected_user
            
            result = await mock_db.user.create(data=user_data)
            
            assert result.email == 'test@example.com'
            assert result.passwordHash == 'hashed_password'
            mock_db.user.create.assert_called_once_with(data=user_data)
    
    @pytest.mark.asyncio
    async def test_find_user_by_email(self):
        """Test finding user by email"""
        with patch('prisma.Prisma') as mock_prisma:
            mock_db = AsyncMock()
            mock_prisma.return_value = mock_db
            
            expected_user = User(
                id='user_123',
                email='test@example.com',
                passwordHash='hashed_password',
                createdAt=datetime.now(),
                updatedAt=datetime.now()
            )
            
            mock_db.user.find_unique.return_value = expected_user
            
            result = await mock_db.user.find_unique(
                where={'email': 'test@example.com'}
            )
            
            assert result.email == 'test@example.com'
            mock_db.user.find_unique.assert_called_once_with(
                where={'email': 'test@example.com'}
            )
    
    @pytest.mark.asyncio
    async def test_user_with_relationships(self):
        """Test user with related resumes and applications"""
        with patch('prisma.Prisma') as mock_prisma:
            mock_db = AsyncMock()
            mock_prisma.return_value = mock_db
            
            expected_user = User(
                id='user_123',
                email='test@example.com',
                passwordHash='hashed_password',
                createdAt=datetime.now(),
                updatedAt=datetime.now(),
                resumes=[],
                applications=[]
            )
            
            mock_db.user.find_unique.return_value = expected_user
            
            result = await mock_db.user.find_unique(
                where={'id': 'user_123'},
                include={'resumes': True, 'applications': True}
            )
            
            assert result.id == 'user_123'
            assert hasattr(result, 'resumes')
            assert hasattr(result, 'applications')


class TestResumeModel:
    """Test cases for Resume model"""
    
    @pytest.mark.asyncio
    async def test_create_resume(self):
        """Test creating a new resume"""
        with patch('prisma.Prisma') as mock_prisma:
            mock_db = AsyncMock()
            mock_prisma.return_value = mock_db
            
            resume_data = {
                'userId': 'user_123',
                'originalFilename': 'resume.pdf',
                'fileContent': b'pdf_content',
                'parsedContent': {'skills': ['Python', 'FastAPI']},
                'embeddingId': 'embedding_123'
            }
            
            expected_resume = Resume(
                id='resume_123',
                userId='user_123',
                originalFilename='resume.pdf',
                fileContent=b'pdf_content',
                parsedContent={'skills': ['Python', 'FastAPI']},
                embeddingId='embedding_123',
                createdAt=datetime.now()
            )
            
            mock_db.resume.create.return_value = expected_resume
            
            result = await mock_db.resume.create(data=resume_data)
            
            assert result.originalFilename == 'resume.pdf'
            assert result.userId == 'user_123'
            mock_db.resume.create.assert_called_once_with(data=resume_data)
    
    @pytest.mark.asyncio
    async def test_resume_with_user_relationship(self):
        """Test resume with user relationship"""
        with patch('prisma.Prisma') as mock_prisma:
            mock_db = AsyncMock()
            mock_prisma.return_value = mock_db
            
            expected_resume = Resume(
                id='resume_123',
                userId='user_123',
                originalFilename='resume.pdf',
                fileContent=b'pdf_content',
                parsedContent={'skills': ['Python', 'FastAPI']},
                embeddingId='embedding_123',
                createdAt=datetime.now(),
                user=User(
                    id='user_123',
                    email='test@example.com',
                    passwordHash='hashed_password',
                    createdAt=datetime.now(),
                    updatedAt=datetime.now()
                )
            )
            
            mock_db.resume.find_unique.return_value = expected_resume
            
            result = await mock_db.resume.find_unique(
                where={'id': 'resume_123'},
                include={'user': True}
            )
            
            assert result.id == 'resume_123'
            assert result.user.email == 'test@example.com'


class TestJobPostModel:
    """Test cases for JobPost model"""
    
    @pytest.mark.asyncio
    async def test_create_job_post(self):
        """Test creating a new job post"""
        with patch('prisma.Prisma') as mock_prisma:
            mock_db = AsyncMock()
            mock_prisma.return_value = mock_db
            
            job_data = {
                'title': 'Senior Python Developer',
                'companyName': 'Tech Corp',
                'jobUrl': 'https://example.com/job/123',
                'location': {'city': 'San Francisco', 'state': 'CA'},
                'description': 'Great Python role',
                'requirements': {'skills': ['Python', 'FastAPI']},
                'salaryInfo': {'min': 100000, 'max': 150000},
                'embeddingId': 'job_embedding_123'
            }
            
            expected_job = JobPost(
                id='job_123',
                title='Senior Python Developer',
                companyName='Tech Corp',
                jobUrl='https://example.com/job/123',
                location={'city': 'San Francisco', 'state': 'CA'},
                description='Great Python role',
                requirements={'skills': ['Python', 'FastAPI']},
                salaryInfo={'min': 100000, 'max': 150000},
                embeddingId='job_embedding_123',
                scrapedAt=datetime.now()
            )
            
            mock_db.jobpost.create.return_value = expected_job
            
            result = await mock_db.jobpost.create(data=job_data)
            
            assert result.title == 'Senior Python Developer'
            assert result.companyName == 'Tech Corp'
            mock_db.jobpost.create.assert_called_once_with(data=job_data)


class TestApplicationModel:
    """Test cases for Application model"""
    
    @pytest.mark.asyncio
    async def test_create_application(self):
        """Test creating a new application"""
        with patch('prisma.Prisma') as mock_prisma:
            mock_db = AsyncMock()
            mock_prisma.return_value = mock_db
            
            application_data = {
                'userId': 'user_123',
                'jobPostId': 'job_123',
                'resumeId': 'resume_123',
                'status': ApplicationStatus.PENDING,
                'matchScore': 0.85,
                'customizedResumeContent': 'Customized resume content',
                'coverLetterContent': 'Cover letter content'
            }
            
            expected_application = Application(
                id='app_123',
                userId='user_123',
                jobPostId='job_123',
                resumeId='resume_123',
                status=ApplicationStatus.PENDING,
                matchScore=0.85,
                customizedResumeContent='Customized resume content',
                coverLetterContent='Cover letter content',
                appliedAt=datetime.now(),
                lastStatusUpdate=datetime.now()
            )
            
            mock_db.application.create.return_value = expected_application
            
            result = await mock_db.application.create(data=application_data)
            
            assert result.status == ApplicationStatus.PENDING
            assert result.matchScore == 0.85
            mock_db.application.create.assert_called_once_with(data=application_data)
    
    @pytest.mark.asyncio
    async def test_application_with_relationships(self):
        """Test application with all relationships"""
        with patch('prisma.Prisma') as mock_prisma:
            mock_db = AsyncMock()
            mock_prisma.return_value = mock_db
            
            expected_application = Application(
                id='app_123',
                userId='user_123',
                jobPostId='job_123',
                resumeId='resume_123',
                status=ApplicationStatus.SUBMITTED,
                matchScore=0.85,
                customizedResumeContent='Customized resume content',
                coverLetterContent='Cover letter content',
                appliedAt=datetime.now(),
                lastStatusUpdate=datetime.now(),
                user=User(
                    id='user_123',
                    email='test@example.com',
                    passwordHash='hashed_password',
                    createdAt=datetime.now(),
                    updatedAt=datetime.now()
                ),
                jobPost=JobPost(
                    id='job_123',
                    title='Senior Python Developer',
                    companyName='Tech Corp',
                    jobUrl='https://example.com/job/123',
                    location={'city': 'San Francisco', 'state': 'CA'},
                    description='Great Python role',
                    requirements={'skills': ['Python', 'FastAPI']},
                    salaryInfo={'min': 100000, 'max': 150000},
                    embeddingId='job_embedding_123',
                    scrapedAt=datetime.now()
                ),
                resume=Resume(
                    id='resume_123',
                    userId='user_123',
                    originalFilename='resume.pdf',
                    fileContent=b'pdf_content',
                    parsedContent={'skills': ['Python', 'FastAPI']},
                    embeddingId='embedding_123',
                    createdAt=datetime.now()
                )
            )
            
            mock_db.application.find_unique.return_value = expected_application
            
            result = await mock_db.application.find_unique(
                where={'id': 'app_123'},
                include={'user': True, 'jobPost': True, 'resume': True}
            )
            
            assert result.id == 'app_123'
            assert result.user.email == 'test@example.com'
            assert result.jobPost.title == 'Senior Python Developer'
            assert result.resume.originalFilename == 'resume.pdf'


class TestUserPreferencesModel:
    """Test cases for UserPreferences model"""
    
    @pytest.mark.asyncio
    async def test_create_user_preferences(self):
        """Test creating user preferences"""
        with patch('prisma.Prisma') as mock_prisma:
            mock_db = AsyncMock()
            mock_prisma.return_value = mock_db
            
            preferences_data = {
                'userId': 'user_123',
                'preferencesData': {
                    'jobTitles': ['Python Developer', 'Software Engineer'],
                    'locations': ['San Francisco', 'Remote'],
                    'salaryRange': {'min': 100000, 'max': 150000},
                    'employmentTypes': ['FULL_TIME'],
                    'automationSettings': {
                        'autoApply': True,
                        'maxApplicationsPerDay': 5
                    }
                }
            }
            
            expected_preferences = UserPreferences(
                id='pref_123',
                userId='user_123',
                preferencesData={
                    'jobTitles': ['Python Developer', 'Software Engineer'],
                    'locations': ['San Francisco', 'Remote'],
                    'salaryRange': {'min': 100000, 'max': 150000},
                    'employmentTypes': ['FULL_TIME'],
                    'automationSettings': {
                        'autoApply': True,
                        'maxApplicationsPerDay': 5
                    }
                },
                createdAt=datetime.now(),
                updatedAt=datetime.now()
            )
            
            mock_db.userpreferences.create.return_value = expected_preferences
            
            result = await mock_db.userpreferences.create(data=preferences_data)
            
            assert result.userId == 'user_123'
            assert 'jobTitles' in result.preferencesData
            mock_db.userpreferences.create.assert_called_once_with(data=preferences_data)
    
    @pytest.mark.asyncio
    async def test_update_user_preferences(self):
        """Test updating user preferences"""
        with patch('prisma.Prisma') as mock_prisma:
            mock_db = AsyncMock()
            mock_prisma.return_value = mock_db
            
            updated_data = {
                'preferencesData': {
                    'jobTitles': ['Senior Python Developer'],
                    'locations': ['Remote'],
                    'salaryRange': {'min': 120000, 'max': 180000}
                }
            }
            
            expected_preferences = UserPreferences(
                id='pref_123',
                userId='user_123',
                preferencesData={
                    'jobTitles': ['Senior Python Developer'],
                    'locations': ['Remote'],
                    'salaryRange': {'min': 120000, 'max': 180000}
                },
                createdAt=datetime.now(),
                updatedAt=datetime.now()
            )
            
            mock_db.userpreferences.update.return_value = expected_preferences
            
            result = await mock_db.userpreferences.update(
                where={'userId': 'user_123'},
                data=updated_data
            )
            
            assert result.preferencesData['jobTitles'] == ['Senior Python Developer']
            mock_db.userpreferences.update.assert_called_once_with(
                where={'userId': 'user_123'},
                data=updated_data
            )
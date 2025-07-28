"""
Unit tests for vector service
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any

from app.services.vector_service import VectorService, vector_service


class TestVectorService:
    """Test cases for VectorService"""
    
    @pytest.fixture
    def mock_pinecone(self):
        """Mock Pinecone client"""
        with patch('app.services.vector_service.Pinecone') as mock_pc:
            mock_instance = Mock()
            mock_pc.return_value = mock_instance
            
            # Mock index operations
            mock_index = Mock()
            mock_instance.Index.return_value = mock_index
            mock_instance.list_indexes.return_value = Mock(indexes=[])
            mock_instance.create_index = Mock()
            mock_instance.describe_index.return_value = Mock(status={'ready': True})
            
            yield mock_instance, mock_index
    
    @pytest.fixture
    def mock_embeddings(self):
        """Mock Google embeddings"""
        with patch('app.services.vector_service.GoogleGenerativeAIEmbeddings') as mock_emb:
            mock_instance = Mock()
            mock_emb.return_value = mock_instance
            mock_instance.embed_query.return_value = [0.1] * 768
            mock_instance.embed_documents.return_value = [[0.1] * 768, [0.2] * 768]
            yield mock_instance
    
    @pytest.fixture
    async def vector_service_instance(self, mock_pinecone, mock_embeddings):
        """Create vector service instance with mocked dependencies"""
        service = VectorService()
        await service.initialize()
        return service
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, mock_pinecone, mock_embeddings):
        """Test successful initialization"""
        service = VectorService()
        await service.initialize()
        
        assert service.pc is not None
        assert service.embeddings_model is not None
        assert service.index is not None
    
    @pytest.mark.asyncio
    async def test_initialize_creates_index_if_not_exists(self, mock_pinecone, mock_embeddings):
        """Test index creation when it doesn't exist"""
        mock_pc, mock_index = mock_pinecone
        mock_pc.list_indexes.return_value = Mock(indexes=[])
        
        service = VectorService()
        await service.initialize()
        
        mock_pc.create_index.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_embedding(self, vector_service_instance):
        """Test embedding generation"""
        text = "Test resume content"
        embedding = await vector_service_instance.generate_embedding(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 768
        assert all(isinstance(x, float) for x in embedding)
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_batch(self, vector_service_instance):
        """Test batch embedding generation"""
        texts = ["Resume 1", "Resume 2"]
        embeddings = await vector_service_instance.generate_embeddings_batch(texts)
        
        assert isinstance(embeddings, list)
        assert len(embeddings) == 2
        assert all(len(emb) == 768 for emb in embeddings)
    
    @pytest.mark.asyncio
    async def test_store_resume_embedding(self, vector_service_instance, mock_pinecone):
        """Test storing resume embedding"""
        mock_pc, mock_index = mock_pinecone
        mock_index.upsert = Mock()
        
        resume_id = "resume_123"
        user_id = "user_456"
        content = "Software engineer with Python experience"
        metadata = {"skills": ["Python", "FastAPI"], "experience_years": 5}
        
        vector_id = await vector_service_instance.store_resume_embedding(
            resume_id, user_id, content, metadata
        )
        
        assert vector_id == f"resume_{resume_id}"
        mock_index.upsert.assert_called_once()
        
        # Check upsert call arguments
        call_args = mock_index.upsert.call_args[1]
        assert "vectors" in call_args
        assert call_args["namespace"] == "resumes"
    
    @pytest.mark.asyncio
    async def test_store_job_embedding(self, vector_service_instance, mock_pinecone):
        """Test storing job embedding"""
        mock_pc, mock_index = mock_pinecone
        mock_index.upsert = Mock()
        
        job_id = "job_789"
        content = "Senior Python Developer position"
        metadata = {"company": "TechCorp", "title": "Senior Developer"}
        
        vector_id = await vector_service_instance.store_job_embedding(
            job_id, content, metadata
        )
        
        assert vector_id == f"job_{job_id}"
        mock_index.upsert.assert_called_once()
        
        # Check upsert call arguments
        call_args = mock_index.upsert.call_args[1]
        assert "vectors" in call_args
        assert call_args["namespace"] == "jobs"
    
    @pytest.mark.asyncio
    async def test_find_similar_jobs(self, vector_service_instance, mock_pinecone):
        """Test finding similar jobs"""
        mock_pc, mock_index = mock_pinecone
        
        # Mock fetch response for resume
        mock_fetch_response = Mock()
        mock_fetch_response.vectors = {
            "resume_123": Mock(values=[0.1] * 768)
        }
        mock_index.fetch.return_value = mock_fetch_response
        
        # Mock query response for similar jobs
        mock_match = Mock()
        mock_match.score = 0.85
        mock_match.metadata = {"job_id": "job_456", "title": "Python Developer"}
        
        mock_query_response = Mock()
        mock_query_response.matches = [mock_match]
        mock_index.query.return_value = mock_query_response
        
        similar_jobs = await vector_service_instance.find_similar_jobs("123", top_k=5)
        
        assert len(similar_jobs) == 1
        assert similar_jobs[0]["job_id"] == "job_456"
        assert similar_jobs[0]["score"] == 0.85
        assert "metadata" in similar_jobs[0]
    
    @pytest.mark.asyncio
    async def test_find_similar_jobs_with_threshold(self, vector_service_instance, mock_pinecone):
        """Test finding similar jobs with score threshold"""
        mock_pc, mock_index = mock_pinecone
        
        # Mock fetch response
        mock_fetch_response = Mock()
        mock_fetch_response.vectors = {
            "resume_123": Mock(values=[0.1] * 768)
        }
        mock_index.fetch.return_value = mock_fetch_response
        
        # Mock query response with low score
        mock_match = Mock()
        mock_match.score = 0.6  # Below threshold
        mock_match.metadata = {"job_id": "job_456"}
        
        mock_query_response = Mock()
        mock_query_response.matches = [mock_match]
        mock_index.query.return_value = mock_query_response
        
        similar_jobs = await vector_service_instance.find_similar_jobs(
            "123", top_k=5, score_threshold=0.7
        )
        
        assert len(similar_jobs) == 0  # Filtered out by threshold
    
    @pytest.mark.asyncio
    async def test_find_similar_resumes(self, vector_service_instance, mock_pinecone):
        """Test finding similar resumes"""
        mock_pc, mock_index = mock_pinecone
        
        # Mock fetch response for job
        mock_fetch_response = Mock()
        mock_fetch_response.vectors = {
            "job_456": Mock(values=[0.2] * 768)
        }
        mock_index.fetch.return_value = mock_fetch_response
        
        # Mock query response for similar resumes
        mock_match = Mock()
        mock_match.score = 0.8
        mock_match.metadata = {"resume_id": "resume_123", "user_id": "user_789"}
        
        mock_query_response = Mock()
        mock_query_response.matches = [mock_match]
        mock_index.query.return_value = mock_query_response
        
        similar_resumes = await vector_service_instance.find_similar_resumes("456", top_k=5)
        
        assert len(similar_resumes) == 1
        assert similar_resumes[0]["resume_id"] == "resume_123"
        assert similar_resumes[0]["user_id"] == "user_789"
        assert similar_resumes[0]["score"] == 0.8
    
    @pytest.mark.asyncio
    async def test_calculate_similarity_score(self, vector_service_instance, mock_pinecone):
        """Test calculating similarity score between resume and job"""
        mock_pc, mock_index = mock_pinecone
        
        # Mock fetch responses
        mock_resume_response = Mock()
        mock_resume_response.vectors = {
            "resume_123": Mock(values=[0.1] * 768)
        }
        
        mock_job_response = Mock()
        mock_job_response.vectors = {
            "job_456": Mock(values=[0.2] * 768)
        }
        
        mock_index.fetch.side_effect = [mock_resume_response, mock_job_response]
        
        # Mock query response
        mock_match = Mock()
        mock_match.score = 0.75
        
        mock_query_response = Mock()
        mock_query_response.matches = [mock_match]
        mock_index.query.return_value = mock_query_response
        
        score = await vector_service_instance.calculate_similarity_score("123", "456")
        
        assert score == 0.75
    
    @pytest.mark.asyncio
    async def test_calculate_similarity_score_no_match(self, vector_service_instance, mock_pinecone):
        """Test calculating similarity score when no match found"""
        mock_pc, mock_index = mock_pinecone
        
        # Mock fetch responses
        mock_resume_response = Mock()
        mock_resume_response.vectors = {
            "resume_123": Mock(values=[0.1] * 768)
        }
        
        mock_job_response = Mock()
        mock_job_response.vectors = {
            "job_456": Mock(values=[0.2] * 768)
        }
        
        mock_index.fetch.side_effect = [mock_resume_response, mock_job_response]
        
        # Mock empty query response
        mock_query_response = Mock()
        mock_query_response.matches = []
        mock_index.query.return_value = mock_query_response
        
        score = await vector_service_instance.calculate_similarity_score("123", "456")
        
        assert score == 0.0
    
    @pytest.mark.asyncio
    async def test_delete_resume_embedding(self, vector_service_instance, mock_pinecone):
        """Test deleting resume embedding"""
        mock_pc, mock_index = mock_pinecone
        mock_index.delete = Mock()
        
        result = await vector_service_instance.delete_resume_embedding("123")
        
        assert result is True
        mock_index.delete.assert_called_once_with(
            ids=["resume_123"],
            namespace="resumes"
        )
    
    @pytest.mark.asyncio
    async def test_delete_job_embedding(self, vector_service_instance, mock_pinecone):
        """Test deleting job embedding"""
        mock_pc, mock_index = mock_pinecone
        mock_index.delete = Mock()
        
        result = await vector_service_instance.delete_job_embedding("456")
        
        assert result is True
        mock_index.delete.assert_called_once_with(
            ids=["job_456"],
            namespace="jobs"
        )
    
    @pytest.mark.asyncio
    async def test_get_index_stats(self, vector_service_instance, mock_pinecone):
        """Test getting index statistics"""
        mock_pc, mock_index = mock_pinecone
        
        mock_stats = Mock()
        mock_stats.total_vector_count = 100
        mock_stats.namespaces = {"resumes": 60, "jobs": 40}
        mock_stats.dimension = 768
        
        mock_index.describe_index_stats.return_value = mock_stats
        
        stats = await vector_service_instance.get_index_stats()
        
        assert stats["total_vectors"] == 100
        assert stats["namespaces"] == {"resumes": 60, "jobs": 40}
        assert stats["dimension"] == 768
    
    @pytest.mark.asyncio
    async def test_resume_not_found_error(self, vector_service_instance, mock_pinecone):
        """Test error when resume embedding not found"""
        mock_pc, mock_index = mock_pinecone
        
        # Mock empty fetch response
        mock_fetch_response = Mock()
        mock_fetch_response.vectors = {}
        mock_index.fetch.return_value = mock_fetch_response
        
        with pytest.raises(ValueError, match="Resume embedding not found"):
            await vector_service_instance.find_similar_jobs("nonexistent")
    
    @pytest.mark.asyncio
    async def test_job_not_found_error(self, vector_service_instance, mock_pinecone):
        """Test error when job embedding not found"""
        mock_pc, mock_index = mock_pinecone
        
        # Mock empty fetch response
        mock_fetch_response = Mock()
        mock_fetch_response.vectors = {}
        mock_index.fetch.return_value = mock_fetch_response
        
        with pytest.raises(ValueError, match="Job embedding not found"):
            await vector_service_instance.find_similar_resumes("nonexistent")
    
    @pytest.mark.asyncio
    async def test_cleanup(self, vector_service_instance):
        """Test cleanup method"""
        # Mock executor
        mock_executor = Mock()
        vector_service_instance.executor = mock_executor
        
        await vector_service_instance.cleanup()
        
        mock_executor.shutdown.assert_called_once_with(wait=True)
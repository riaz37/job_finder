"""
Vector database service for managing embeddings and similarity search
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
import asyncio
from concurrent.futures import ThreadPoolExecutor

import pinecone
from pinecone import Pinecone, ServerlessSpec
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import settings

logger = logging.getLogger(__name__)


class VectorService:
    """Service for managing vector embeddings and similarity search using Pinecone"""
    
    def __init__(self):
        self.pc = None
        self.index = None
        self.embeddings_model = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    async def initialize(self):
        """Initialize Pinecone connection and embedding model"""
        try:
            # Initialize Pinecone
            self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
            
            # Initialize embedding model with gemini-embedding-001
            self.embeddings_model = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",  # Gemini embedding model as requested
                google_api_key=settings.GEMINI_API_KEY
            )
            
            # Connect to or create index
            await self._ensure_index_exists()
            self.index = self.pc.Index(settings.PINECONE_INDEX_NAME)
            
            logger.info("Vector service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector service: {e}")
            raise
    
    async def _ensure_index_exists(self):
        """Ensure the Pinecone index exists, create if it doesn't"""
        try:
            # Check if index exists
            existing_indexes = self.pc.list_indexes()
            index_names = [idx.name for idx in existing_indexes.indexes]
            
            if settings.PINECONE_INDEX_NAME not in index_names:
                logger.info(f"Creating Pinecone index: {settings.PINECONE_INDEX_NAME}")
                
                # Create index with appropriate dimensions for Gemini embeddings
                self.pc.create_index(
                    name=settings.PINECONE_INDEX_NAME,
                    dimension=768,  # Gemini embedding dimension
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
                
                # Wait for index to be ready
                while not self.pc.describe_index(settings.PINECONE_INDEX_NAME).status['ready']:
                    await asyncio.sleep(1)
                    
                logger.info("Index created successfully")
            else:
                logger.info(f"Index {settings.PINECONE_INDEX_NAME} already exists")
                
        except Exception as e:
            logger.error(f"Error ensuring index exists: {e}")
            raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for given text using Gemini"""
        try:
            # Run embedding generation in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                self.executor,
                self.embeddings_model.embed_query,
                text
            )
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        try:
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                self.executor,
                self.embeddings_model.embed_documents,
                texts
            )
            return embeddings
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise

    async def store_resume_embedding(
        self, 
        resume_id: str, 
        user_id: str, 
        resume_content: str, 
        metadata: Dict[str, Any]
        ) -> str:
        """Store resume embedding in Pinecone with metadata"""
        try:
            # Generate embedding for resume content
            embedding = await self.generate_embedding(resume_content)
            
            # Prepare metadata
            vector_metadata = {
                "type": "resume",
                "resume_id": resume_id,
                "user_id": user_id,
                "created_at": metadata.get("created_at"),
                **metadata
            }
            
            # Store in Pinecone
            vector_id = f"resume_{resume_id}"
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.index.upsert(
                    vectors=[(vector_id, embedding, vector_metadata)],
                    namespace="resumes"
                )
            )
            
            logger.info(f"Stored resume embedding: {vector_id}")
            return vector_id
            
        except Exception as e:
            logger.error(f"Error storing resume embedding: {e}")
            raise
    
    async def store_job_embedding(
        self, 
        job_id: str, 
        job_content: str, 
        metadata: Dict[str, Any]
    ) -> str:
        """Store job posting embedding in Pinecone with metadata"""
        try:
            # Generate embedding for job content
            embedding = await self.generate_embedding(job_content)
            
            # Prepare metadata
            vector_metadata = {
                "type": "job",
                "job_id": job_id,
                "company": metadata.get("company"),
                "title": metadata.get("title"),
                "location": metadata.get("location"),
                "scraped_at": metadata.get("scraped_at"),
                **metadata
            }
            
            # Store in Pinecone
            vector_id = f"job_{job_id}"
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.index.upsert(
                    vectors=[(vector_id, embedding, vector_metadata)],
                    namespace="jobs"
                )
            )
            
            logger.info(f"Stored job embedding: {vector_id}")
            return vector_id
            
        except Exception as e:
            logger.error(f"Error storing job embedding: {e}")
            raise
    
    async def find_similar_jobs(
        self, 
        resume_id: str, 
        top_k: int = 10,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Find jobs similar to a resume using vector similarity search"""
        try:
            # Get resume vector
            resume_vector_id = f"resume_{resume_id}"
            resume_response = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.index.fetch(
                    ids=[resume_vector_id],
                    namespace="resumes"
                )
            )
            
            if not resume_response.vectors or resume_vector_id not in resume_response.vectors:
                raise ValueError(f"Resume embedding not found: {resume_id}")
            
            resume_embedding = resume_response.vectors[resume_vector_id].values
            
            # Search for similar jobs
            search_response = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.index.query(
                    vector=resume_embedding,
                    top_k=top_k,
                    namespace="jobs",
                    include_metadata=True
                )
            )
            
            # Filter by score threshold and format results
            similar_jobs = []
            for match in search_response.matches:
                if match.score >= score_threshold:
                    similar_jobs.append({
                        "job_id": match.metadata.get("job_id"),
                        "score": match.score,
                        "metadata": match.metadata
                    })
            
            logger.info(f"Found {len(similar_jobs)} similar jobs for resume {resume_id}")
            return similar_jobs
            
        except Exception as e:
            logger.error(f"Error finding similar jobs: {e}")
            raise
    
    async def find_similar_resumes(
        self, 
        job_id: str, 
        top_k: int = 10,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Find resumes similar to a job posting using vector similarity search"""
        try:
            # Get job vector
            job_vector_id = f"job_{job_id}"
            job_response = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.index.fetch(
                    ids=[job_vector_id],
                    namespace="jobs"
                )
            )
            
            if not job_response.vectors or job_vector_id not in job_response.vectors:
                raise ValueError(f"Job embedding not found: {job_id}")
            
            job_embedding = job_response.vectors[job_vector_id].values
            
            # Search for similar resumes
            search_response = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.index.query(
                    vector=job_embedding,
                    top_k=top_k,
                    namespace="resumes",
                    include_metadata=True
                )
            )
            
            # Filter by score threshold and format results
            similar_resumes = []
            for match in search_response.matches:
                if match.score >= score_threshold:
                    similar_resumes.append({
                        "resume_id": match.metadata.get("resume_id"),
                        "user_id": match.metadata.get("user_id"),
                        "score": match.score,
                        "metadata": match.metadata
                    })
            
            logger.info(f"Found {len(similar_resumes)} similar resumes for job {job_id}")
            return similar_resumes
            
        except Exception as e:
            logger.error(f"Error finding similar resumes: {e}")
            raise
    
    async def calculate_similarity_score(
        self, 
        resume_id: str, 
        job_id: str
    ) -> float:
        """Calculate similarity score between a specific resume and job"""
        try:
            # Get both vectors
            resume_vector_id = f"resume_{resume_id}"
            job_vector_id = f"job_{job_id}"
            
            # Fetch both vectors
            resume_response, job_response = await asyncio.gather(
                asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    lambda: self.index.fetch(
                        ids=[resume_vector_id],
                        namespace="resumes"
                    )
                ),
                asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    lambda: self.index.fetch(
                        ids=[job_vector_id],
                        namespace="jobs"
                    )
                )
            )
            
            if (not resume_response.vectors or resume_vector_id not in resume_response.vectors or
                not job_response.vectors or job_vector_id not in job_response.vectors):
                raise ValueError("One or both embeddings not found")
            
            resume_embedding = resume_response.vectors[resume_vector_id].values
            
            # Query job embedding against resume
            search_response = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.index.query(
                    vector=resume_embedding,
                    top_k=1,
                    namespace="jobs",
                    filter={"job_id": job_id},
                    include_metadata=False
                )
            )
            
            if search_response.matches:
                return search_response.matches[0].score
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Error calculating similarity score: {e}")
            raise
    
    async def delete_resume_embedding(self, resume_id: str) -> bool:
        """Delete resume embedding from Pinecone"""
        try:
            vector_id = f"resume_{resume_id}"
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.index.delete(
                    ids=[vector_id],
                    namespace="resumes"
                )
            )
            
            logger.info(f"Deleted resume embedding: {vector_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting resume embedding: {e}")
            return False
    
    async def delete_job_embedding(self, job_id: str) -> bool:
        """Delete job embedding from Pinecone"""
        try:
            vector_id = f"job_{job_id}"
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.index.delete(
                    ids=[vector_id],
                    namespace="jobs"
                )
            )
            
            logger.info(f"Deleted job embedding: {vector_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting job embedding: {e}")
            return False
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the Pinecone index"""
        try:
            stats = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.index.describe_index_stats()
            )
            
            return {
                "total_vectors": stats.total_vector_count,
                "namespaces": stats.namespaces,
                "dimension": stats.dimension
            }
            
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.executor:
            self.executor.shutdown(wait=True)


# Global vector service instance
vector_service = VectorService()
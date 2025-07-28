"""
LangGraph workflows for job application process.
Implements multi-step workflows with state management.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, TypedDict, Annotated
from datetime import datetime
from enum import Enum

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from pydantic import BaseModel

from app.services.workflow_orchestrator import WorkflowOrchestrator, WorkflowContext


logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobApplicationState(TypedDict):
    """State for job application workflow."""
    user_id: str
    job_id: str
    resume_id: str
    messages: List[BaseMessage]
    current_step: str
    status: WorkflowStatus
    resume_data: Optional[Dict[str, Any]]
    job_data: Optional[Dict[str, Any]]
    customized_resume: Optional[str]
    cover_letter: Optional[str]
    match_score: Optional[float]
    application_result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    retry_count: int
    max_retries: int
    created_at: datetime
    updated_at: datetime


class ResumeCustomizationState(TypedDict):
    """State for resume customization workflow."""
    user_id: str
    resume_id: str
    job_id: str
    messages: List[BaseMessage]
    current_step: str
    status: WorkflowStatus
    original_resume: Optional[Dict[str, Any]]
    job_requirements: Optional[Dict[str, Any]]
    analysis_result: Optional[Dict[str, Any]]
    customization_suggestions: Optional[List[str]]
    customized_content: Optional[str]
    error_message: Optional[str]
    retry_count: int
    max_retries: int
    created_at: datetime
    updated_at: datetime


class CoverLetterGenerationState(TypedDict):
    """State for cover letter generation workflow."""
    user_id: str
    resume_id: str
    job_id: str
    messages: List[BaseMessage]
    current_step: str
    status: WorkflowStatus
    resume_data: Optional[Dict[str, Any]]
    job_data: Optional[Dict[str, Any]]
    company_info: Optional[Dict[str, Any]]
    personalization_data: Optional[Dict[str, Any]]
    generated_content: Optional[str]
    error_message: Optional[str]
    retry_count: int
    max_retries: int
    created_at: datetime
    updated_at: datetime


class LangGraphWorkflowManager:
    """
    Manager for LangGraph workflows in the job application process.
    """
    
    def __init__(self, orchestrator: WorkflowOrchestrator):
        self.orchestrator = orchestrator
        self.active_workflows: Dict[str, Any] = {}
        
        # Initialize workflow graphs
        self.job_application_graph = self._create_job_application_workflow()
        self.resume_customization_graph = self._create_resume_customization_workflow()
        self.cover_letter_graph = self._create_cover_letter_workflow()
    
    def _create_job_application_workflow(self) -> StateGraph:
        """Create the complete job application workflow graph."""
        
        def analyze_job_match(state: JobApplicationState) -> JobApplicationState:
            """Analyze job-resume match and calculate score."""
            logger.info(f"Analyzing job match for user {state['user_id']}")
            
            state["current_step"] = "analyze_job_match"
            state["updated_at"] = datetime.utcnow()
            
            try:
                # Placeholder for actual job matching logic
                # This would integrate with the job matching service
                state["match_score"] = 0.85  # Mock score
                state["status"] = WorkflowStatus.RUNNING
                
                logger.info(f"Job match analysis completed with score: {state['match_score']}")
                
            except Exception as e:
                logger.error(f"Job match analysis failed: {e}")
                state["error_message"] = str(e)
                state["status"] = WorkflowStatus.FAILED
            
            return state
        
        def customize_resume(state: JobApplicationState) -> JobApplicationState:
            """Customize resume for the specific job."""
            logger.info(f"Customizing resume for user {state['user_id']}")
            
            state["current_step"] = "customize_resume"
            state["updated_at"] = datetime.utcnow()
            
            try:
                # This would integrate with the resume customization workflow
                state["customized_resume"] = "Customized resume content..."  # Mock content
                state["status"] = WorkflowStatus.RUNNING
                
                logger.info("Resume customization completed")
                
            except Exception as e:
                logger.error(f"Resume customization failed: {e}")
                state["error_message"] = str(e)
                state["status"] = WorkflowStatus.FAILED
            
            return state
        
        def generate_cover_letter(state: JobApplicationState) -> JobApplicationState:
            """Generate personalized cover letter."""
            logger.info(f"Generating cover letter for user {state['user_id']}")
            
            state["current_step"] = "generate_cover_letter"
            state["updated_at"] = datetime.utcnow()
            
            try:
                # This would integrate with the cover letter generation workflow
                state["cover_letter"] = "Generated cover letter content..."  # Mock content
                state["status"] = WorkflowStatus.RUNNING
                
                logger.info("Cover letter generation completed")
                
            except Exception as e:
                logger.error(f"Cover letter generation failed: {e}")
                state["error_message"] = str(e)
                state["status"] = WorkflowStatus.FAILED
            
            return state
        
        def submit_application(state: JobApplicationState) -> JobApplicationState:
            """Submit the job application."""
            logger.info(f"Submitting application for user {state['user_id']}")
            
            state["current_step"] = "submit_application"
            state["updated_at"] = datetime.utcnow()
            
            try:
                # This would integrate with the application submission service
                state["application_result"] = {
                    "status": "submitted",
                    "application_id": "app_123",
                    "submitted_at": datetime.utcnow()
                }
                state["status"] = WorkflowStatus.COMPLETED
                
                logger.info("Application submission completed")
                
            except Exception as e:
                logger.error(f"Application submission failed: {e}")
                state["error_message"] = str(e)
                state["status"] = WorkflowStatus.FAILED
            
            return state
        
        def should_continue(state: JobApplicationState) -> str:
            """Determine next step based on current state."""
            if state["status"] == WorkflowStatus.FAILED:
                if state["retry_count"] < state["max_retries"]:
                    state["retry_count"] += 1
                    return "retry"
                else:
                    return END
            elif state["status"] == WorkflowStatus.COMPLETED:
                return END
            else:
                current_step = state["current_step"]
                if current_step == "analyze_job_match":
                    return "customize_resume"
                elif current_step == "customize_resume":
                    return "generate_cover_letter"
                elif current_step == "generate_cover_letter":
                    return "submit_application"
                else:
                    return END
        
        def retry_step(state: JobApplicationState) -> JobApplicationState:
            """Retry the current step after failure."""
            logger.info(f"Retrying step {state['current_step']} for user {state['user_id']}")
            
            state["status"] = WorkflowStatus.RUNNING
            state["error_message"] = None
            state["updated_at"] = datetime.utcnow()
            
            return state
        
        # Build the workflow graph
        workflow = StateGraph(JobApplicationState)
        
        # Add nodes
        workflow.add_node("analyze_job_match", analyze_job_match)
        workflow.add_node("customize_resume", customize_resume)
        workflow.add_node("generate_cover_letter", generate_cover_letter)
        workflow.add_node("submit_application", submit_application)
        workflow.add_node("retry", retry_step)
        
        # Set entry point
        workflow.set_entry_point("analyze_job_match")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "analyze_job_match",
            should_continue,
            {
                "customize_resume": "customize_resume",
                "retry": "retry",
                END: END
            }
        )
        
        workflow.add_conditional_edges(
            "customize_resume",
            should_continue,
            {
                "generate_cover_letter": "generate_cover_letter",
                "retry": "retry",
                END: END
            }
        )
        
        workflow.add_conditional_edges(
            "generate_cover_letter",
            should_continue,
            {
                "submit_application": "submit_application",
                "retry": "retry",
                END: END
            }
        )
        
        workflow.add_conditional_edges(
            "submit_application",
            should_continue,
            {
                "retry": "retry",
                END: END
            }
        )
        
        workflow.add_conditional_edges(
            "retry",
            should_continue,
            {
                "customize_resume": "customize_resume",
                "generate_cover_letter": "generate_cover_letter",
                "submit_application": "submit_application",
                END: END
            }
        )
        
        return workflow.compile()
    
    def _create_resume_customization_workflow(self) -> StateGraph:
        """Create the resume customization workflow graph."""
        
        def analyze_job_requirements(state: ResumeCustomizationState) -> ResumeCustomizationState:
            """Analyze job requirements and compare with resume."""
            logger.info(f"Analyzing job requirements for user {state['user_id']}")
            
            state["current_step"] = "analyze_job_requirements"
            state["updated_at"] = datetime.utcnow()
            
            try:
                # Mock analysis result
                state["analysis_result"] = {
                    "missing_skills": ["Python", "AWS"],
                    "matching_skills": ["JavaScript", "React"],
                    "experience_gaps": ["Senior level experience"],
                    "keyword_suggestions": ["cloud computing", "microservices"]
                }
                state["status"] = WorkflowStatus.RUNNING
                
                logger.info("Job requirements analysis completed")
                
            except Exception as e:
                logger.error(f"Job requirements analysis failed: {e}")
                state["error_message"] = str(e)
                state["status"] = WorkflowStatus.FAILED
            
            return state
        
        def generate_customization_suggestions(state: ResumeCustomizationState) -> ResumeCustomizationState:
            """Generate suggestions for resume customization."""
            logger.info(f"Generating customization suggestions for user {state['user_id']}")
            
            state["current_step"] = "generate_customization_suggestions"
            state["updated_at"] = datetime.utcnow()
            
            try:
                # Mock suggestions
                state["customization_suggestions"] = [
                    "Emphasize Python experience in technical skills section",
                    "Add AWS certification mention",
                    "Highlight relevant project experience",
                    "Optimize keywords for ATS scanning"
                ]
                state["status"] = WorkflowStatus.RUNNING
                
                logger.info("Customization suggestions generated")
                
            except Exception as e:
                logger.error(f"Customization suggestions generation failed: {e}")
                state["error_message"] = str(e)
                state["status"] = WorkflowStatus.FAILED
            
            return state
        
        def apply_customizations(state: ResumeCustomizationState) -> ResumeCustomizationState:
            """Apply customizations to the resume."""
            logger.info(f"Applying customizations for user {state['user_id']}")
            
            state["current_step"] = "apply_customizations"
            state["updated_at"] = datetime.utcnow()
            
            try:
                # Mock customized content
                state["customized_content"] = "Customized resume with job-specific optimizations..."
                state["status"] = WorkflowStatus.COMPLETED
                
                logger.info("Resume customizations applied")
                
            except Exception as e:
                logger.error(f"Resume customization application failed: {e}")
                state["error_message"] = str(e)
                state["status"] = WorkflowStatus.FAILED
            
            return state
        
        def should_continue_customization(state: ResumeCustomizationState) -> str:
            """Determine next step for resume customization."""
            if state["status"] == WorkflowStatus.FAILED:
                if state["retry_count"] < state["max_retries"]:
                    state["retry_count"] += 1
                    return "retry"
                else:
                    return END
            elif state["status"] == WorkflowStatus.COMPLETED:
                return END
            else:
                current_step = state["current_step"]
                if current_step == "analyze_job_requirements":
                    return "generate_customization_suggestions"
                elif current_step == "generate_customization_suggestions":
                    return "apply_customizations"
                else:
                    return END
        
        def retry_customization_step(state: ResumeCustomizationState) -> ResumeCustomizationState:
            """Retry the current customization step."""
            logger.info(f"Retrying customization step {state['current_step']} for user {state['user_id']}")
            
            state["status"] = WorkflowStatus.RUNNING
            state["error_message"] = None
            state["updated_at"] = datetime.utcnow()
            
            return state
        
        # Build the workflow graph
        workflow = StateGraph(ResumeCustomizationState)
        
        # Add nodes
        workflow.add_node("analyze_job_requirements", analyze_job_requirements)
        workflow.add_node("generate_customization_suggestions", generate_customization_suggestions)
        workflow.add_node("apply_customizations", apply_customizations)
        workflow.add_node("retry", retry_customization_step)
        
        # Set entry point
        workflow.set_entry_point("analyze_job_requirements")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "analyze_job_requirements",
            should_continue_customization,
            {
                "generate_customization_suggestions": "generate_customization_suggestions",
                "retry": "retry",
                END: END
            }
        )
        
        workflow.add_conditional_edges(
            "generate_customization_suggestions",
            should_continue_customization,
            {
                "apply_customizations": "apply_customizations",
                "retry": "retry",
                END: END
            }
        )
        
        workflow.add_conditional_edges(
            "apply_customizations",
            should_continue_customization,
            {
                "retry": "retry",
                END: END
            }
        )
        
        workflow.add_conditional_edges(
            "retry",
            should_continue_customization,
            {
                "generate_customization_suggestions": "generate_customization_suggestions",
                "apply_customizations": "apply_customizations",
                END: END
            }
        )
        
        return workflow.compile()
    
    def _create_cover_letter_workflow(self) -> StateGraph:
        """Create the cover letter generation workflow graph."""
        
        def gather_personalization_data(state: CoverLetterGenerationState) -> CoverLetterGenerationState:
            """Gather data for personalizing the cover letter."""
            logger.info(f"Gathering personalization data for user {state['user_id']}")
            
            state["current_step"] = "gather_personalization_data"
            state["updated_at"] = datetime.utcnow()
            
            try:
                # Mock personalization data
                state["personalization_data"] = {
                    "company_name": "Tech Corp",
                    "hiring_manager": "John Smith",
                    "role_title": "Senior Developer",
                    "key_requirements": ["Python", "AWS", "Team Leadership"],
                    "company_values": ["Innovation", "Collaboration", "Excellence"]
                }
                state["status"] = WorkflowStatus.RUNNING
                
                logger.info("Personalization data gathered")
                
            except Exception as e:
                logger.error(f"Personalization data gathering failed: {e}")
                state["error_message"] = str(e)
                state["status"] = WorkflowStatus.FAILED
            
            return state
        
        def generate_cover_letter_content(state: CoverLetterGenerationState) -> CoverLetterGenerationState:
            """Generate the cover letter content."""
            logger.info(f"Generating cover letter content for user {state['user_id']}")
            
            state["current_step"] = "generate_cover_letter_content"
            state["updated_at"] = datetime.utcnow()
            
            try:
                # Mock generated content
                state["generated_content"] = """
Dear John Smith,

I am writing to express my strong interest in the Senior Developer position at Tech Corp...

[Generated personalized cover letter content]

Sincerely,
[User Name]
                """.strip()
                state["status"] = WorkflowStatus.COMPLETED
                
                logger.info("Cover letter content generated")
                
            except Exception as e:
                logger.error(f"Cover letter content generation failed: {e}")
                state["error_message"] = str(e)
                state["status"] = WorkflowStatus.FAILED
            
            return state
        
        def should_continue_cover_letter(state: CoverLetterGenerationState) -> str:
            """Determine next step for cover letter generation."""
            if state["status"] == WorkflowStatus.FAILED:
                if state["retry_count"] < state["max_retries"]:
                    state["retry_count"] += 1
                    return "retry"
                else:
                    return END
            elif state["status"] == WorkflowStatus.COMPLETED:
                return END
            else:
                current_step = state["current_step"]
                if current_step == "gather_personalization_data":
                    return "generate_cover_letter_content"
                else:
                    return END
        
        def retry_cover_letter_step(state: CoverLetterGenerationState) -> CoverLetterGenerationState:
            """Retry the current cover letter step."""
            logger.info(f"Retrying cover letter step {state['current_step']} for user {state['user_id']}")
            
            state["status"] = WorkflowStatus.RUNNING
            state["error_message"] = None
            state["updated_at"] = datetime.utcnow()
            
            return state
        
        # Build the workflow graph
        workflow = StateGraph(CoverLetterGenerationState)
        
        # Add nodes
        workflow.add_node("gather_personalization_data", gather_personalization_data)
        workflow.add_node("generate_cover_letter_content", generate_cover_letter_content)
        workflow.add_node("retry", retry_cover_letter_step)
        
        # Set entry point
        workflow.set_entry_point("gather_personalization_data")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "gather_personalization_data",
            should_continue_cover_letter,
            {
                "generate_cover_letter_content": "generate_cover_letter_content",
                "retry": "retry",
                END: END
            }
        )
        
        workflow.add_conditional_edges(
            "generate_cover_letter_content",
            should_continue_cover_letter,
            {
                "retry": "retry",
                END: END
            }
        )
        
        workflow.add_conditional_edges(
            "retry",
            should_continue_cover_letter,
            {
                "gather_personalization_data": "gather_personalization_data",
                "generate_cover_letter_content": "generate_cover_letter_content",
                END: END
            }
        )
        
        return workflow.compile()
    
    async def execute_job_application_workflow(
        self,
        user_id: str,
        job_id: str,
        resume_id: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Execute the complete job application workflow."""
        
        workflow_id = f"job_app_{user_id}_{job_id}_{datetime.utcnow().timestamp()}"
        
        initial_state: JobApplicationState = {
            "user_id": user_id,
            "job_id": job_id,
            "resume_id": resume_id,
            "messages": [],
            "current_step": "initialize",
            "status": WorkflowStatus.PENDING,
            "resume_data": None,
            "job_data": None,
            "customized_resume": None,
            "cover_letter": None,
            "match_score": None,
            "application_result": None,
            "error_message": None,
            "retry_count": 0,
            "max_retries": max_retries,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        try:
            logger.info(f"Starting job application workflow {workflow_id}")
            
            # Store workflow state
            self.active_workflows[workflow_id] = initial_state
            
            # Execute the workflow
            final_state = await self.job_application_graph.ainvoke(initial_state)
            
            # Update stored state
            self.active_workflows[workflow_id] = final_state
            
            logger.info(f"Job application workflow {workflow_id} completed with status: {final_state['status']}")
            
            return {
                "workflow_id": workflow_id,
                "status": final_state["status"],
                "result": final_state.get("application_result"),
                "error": final_state.get("error_message"),
                "final_state": final_state
            }
            
        except Exception as e:
            logger.error(f"Job application workflow {workflow_id} failed: {e}")
            
            if workflow_id in self.active_workflows:
                self.active_workflows[workflow_id]["status"] = WorkflowStatus.FAILED
                self.active_workflows[workflow_id]["error_message"] = str(e)
            
            return {
                "workflow_id": workflow_id,
                "status": WorkflowStatus.FAILED,
                "error": str(e),
                "final_state": self.active_workflows.get(workflow_id)
            }
    
    async def execute_resume_customization_workflow(
        self,
        user_id: str,
        resume_id: str,
        job_id: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Execute the resume customization workflow."""
        
        workflow_id = f"resume_custom_{user_id}_{job_id}_{datetime.utcnow().timestamp()}"
        
        initial_state: ResumeCustomizationState = {
            "user_id": user_id,
            "resume_id": resume_id,
            "job_id": job_id,
            "messages": [],
            "current_step": "initialize",
            "status": WorkflowStatus.PENDING,
            "original_resume": None,
            "job_requirements": None,
            "analysis_result": None,
            "customization_suggestions": None,
            "customized_content": None,
            "error_message": None,
            "retry_count": 0,
            "max_retries": max_retries,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        try:
            logger.info(f"Starting resume customization workflow {workflow_id}")
            
            # Store workflow state
            self.active_workflows[workflow_id] = initial_state
            
            # Execute the workflow
            final_state = await self.resume_customization_graph.ainvoke(initial_state)
            
            # Update stored state
            self.active_workflows[workflow_id] = final_state
            
            logger.info(f"Resume customization workflow {workflow_id} completed with status: {final_state['status']}")
            
            return {
                "workflow_id": workflow_id,
                "status": final_state["status"],
                "result": final_state.get("customized_content"),
                "suggestions": final_state.get("customization_suggestions"),
                "error": final_state.get("error_message"),
                "final_state": final_state
            }
            
        except Exception as e:
            logger.error(f"Resume customization workflow {workflow_id} failed: {e}")
            
            if workflow_id in self.active_workflows:
                self.active_workflows[workflow_id]["status"] = WorkflowStatus.FAILED
                self.active_workflows[workflow_id]["error_message"] = str(e)
            
            return {
                "workflow_id": workflow_id,
                "status": WorkflowStatus.FAILED,
                "error": str(e),
                "final_state": self.active_workflows.get(workflow_id)
            }
    
    async def execute_cover_letter_workflow(
        self,
        user_id: str,
        resume_id: str,
        job_id: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Execute the cover letter generation workflow."""
        
        workflow_id = f"cover_letter_{user_id}_{job_id}_{datetime.utcnow().timestamp()}"
        
        initial_state: CoverLetterGenerationState = {
            "user_id": user_id,
            "resume_id": resume_id,
            "job_id": job_id,
            "messages": [],
            "current_step": "initialize",
            "status": WorkflowStatus.PENDING,
            "resume_data": None,
            "job_data": None,
            "company_info": None,
            "personalization_data": None,
            "generated_content": None,
            "error_message": None,
            "retry_count": 0,
            "max_retries": max_retries,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        try:
            logger.info(f"Starting cover letter workflow {workflow_id}")
            
            # Store workflow state
            self.active_workflows[workflow_id] = initial_state
            
            # Execute the workflow
            final_state = await self.cover_letter_graph.ainvoke(initial_state)
            
            # Update stored state
            self.active_workflows[workflow_id] = final_state
            
            logger.info(f"Cover letter workflow {workflow_id} completed with status: {final_state['status']}")
            
            return {
                "workflow_id": workflow_id,
                "status": final_state["status"],
                "result": final_state.get("generated_content"),
                "error": final_state.get("error_message"),
                "final_state": final_state
            }
            
        except Exception as e:
            logger.error(f"Cover letter workflow {workflow_id} failed: {e}")
            
            if workflow_id in self.active_workflows:
                self.active_workflows[workflow_id]["status"] = WorkflowStatus.FAILED
                self.active_workflows[workflow_id]["error_message"] = str(e)
            
            return {
                "workflow_id": workflow_id,
                "status": WorkflowStatus.FAILED,
                "error": str(e),
                "final_state": self.active_workflows.get(workflow_id)
            }
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a workflow."""
        workflow_state = self.active_workflows.get(workflow_id)
        if not workflow_state:
            return None
        
        return {
            "workflow_id": workflow_id,
            "status": workflow_state.get("status"),
            "current_step": workflow_state.get("current_step"),
            "created_at": workflow_state.get("created_at"),
            "updated_at": workflow_state.get("updated_at"),
            "error_message": workflow_state.get("error_message"),
            "retry_count": workflow_state.get("retry_count", 0)
        }
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        if workflow_id in self.active_workflows:
            self.active_workflows[workflow_id]["status"] = WorkflowStatus.CANCELLED
            self.active_workflows[workflow_id]["updated_at"] = datetime.utcnow()
            logger.info(f"Workflow {workflow_id} cancelled")
            return True
        return False
    
    async def cleanup_workflow(self, workflow_id: str) -> bool:
        """Clean up a completed workflow."""
        if workflow_id in self.active_workflows:
            del self.active_workflows[workflow_id]
            logger.info(f"Workflow {workflow_id} cleaned up")
            return True
        return False


# Global workflow manager instance
workflow_manager = None


def get_workflow_manager() -> LangGraphWorkflowManager:
    """Get or create the global workflow manager instance."""
    global workflow_manager
    if workflow_manager is None:
        from app.services.workflow_orchestrator import orchestrator
        workflow_manager = LangGraphWorkflowManager(orchestrator)
    return workflow_manager
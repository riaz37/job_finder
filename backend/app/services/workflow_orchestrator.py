"""
LangChain orchestrator for AI workflow management.
Handles coordination of AI operations and tool usage.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Type
from datetime import datetime

from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferMemory
from langchain.callbacks.base import BaseCallbackHandler
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from app.core.config import settings


logger = logging.getLogger(__name__)


class WorkflowContext(BaseModel):
    """Context object for workflow execution."""
    user_id: str
    session_id: str
    workflow_type: str
    current_step: str
    data: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()


class WorkflowCallbackHandler(BaseCallbackHandler):
    """Custom callback handler for workflow logging and monitoring."""
    
    def __init__(self, context: WorkflowContext):
        self.context = context
        self.step_logs: List[Dict[str, Any]] = []
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        """Called when LLM starts running."""
        logger.info(f"LLM started for workflow {self.context.workflow_type}, step {self.context.current_step}")
        self.step_logs.append({
            "event": "llm_start",
            "timestamp": datetime.utcnow(),
            "step": self.context.current_step,
            "prompts_count": len(prompts)
        })
    
    def on_llm_end(self, response, **kwargs) -> None:
        """Called when LLM ends running."""
        logger.info(f"LLM completed for workflow {self.context.workflow_type}, step {self.context.current_step}")
        self.step_logs.append({
            "event": "llm_end",
            "timestamp": datetime.utcnow(),
            "step": self.context.current_step,
            "response_length": len(str(response)) if response else 0
        })
    
    def on_llm_error(self, error: Exception, **kwargs) -> None:
        """Called when LLM encounters an error."""
        logger.error(f"LLM error in workflow {self.context.workflow_type}, step {self.context.current_step}: {error}")
        self.step_logs.append({
            "event": "llm_error",
            "timestamp": datetime.utcnow(),
            "step": self.context.current_step,
            "error": str(error)
        })
    
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs) -> None:
        """Called when a tool starts running."""
        tool_name = serialized.get("name", "unknown")
        logger.info(f"Tool {tool_name} started in workflow {self.context.workflow_type}")
        self.step_logs.append({
            "event": "tool_start",
            "timestamp": datetime.utcnow(),
            "step": self.context.current_step,
            "tool_name": tool_name,
            "input": input_str
        })
    
    def on_tool_end(self, output: str, **kwargs) -> None:
        """Called when a tool ends running."""
        logger.info(f"Tool completed in workflow {self.context.workflow_type}")
        self.step_logs.append({
            "event": "tool_end",
            "timestamp": datetime.utcnow(),
            "step": self.context.current_step,
            "output_length": len(output)
        })
    
    def on_tool_error(self, error: Exception, **kwargs) -> None:
        """Called when a tool encounters an error."""
        logger.error(f"Tool error in workflow {self.context.workflow_type}: {error}")
        self.step_logs.append({
            "event": "tool_error",
            "timestamp": datetime.utcnow(),
            "step": self.context.current_step,
            "error": str(error)
        })


class WorkflowOrchestrator:
    """
    LangChain orchestrator for managing AI workflows.
    Coordinates AI operations, tool usage, and context management.
    """
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.1,
            max_tokens=2048
        )
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        self.active_contexts: Dict[str, WorkflowContext] = {}
    
    async def create_context(
        self,
        user_id: str,
        workflow_type: str,
        initial_data: Optional[Dict[str, Any]] = None
    ) -> WorkflowContext:
        """Create a new workflow context."""
        session_id = f"{user_id}_{workflow_type}_{datetime.utcnow().timestamp()}"
        
        context = WorkflowContext(
            user_id=user_id,
            session_id=session_id,
            workflow_type=workflow_type,
            current_step="initialization",
            data=initial_data or {},
            metadata={"created_by": "workflow_orchestrator"}
        )
        
        self.active_contexts[session_id] = context
        logger.info(f"Created workflow context {session_id} for user {user_id}")
        
        return context
    
    async def get_context(self, session_id: str) -> Optional[WorkflowContext]:
        """Retrieve an existing workflow context."""
        return self.active_contexts.get(session_id)
    
    async def update_context(
        self,
        session_id: str,
        step: Optional[str] = None,
        data_updates: Optional[Dict[str, Any]] = None,
        metadata_updates: Optional[Dict[str, Any]] = None
    ) -> Optional[WorkflowContext]:
        """Update an existing workflow context."""
        context = self.active_contexts.get(session_id)
        if not context:
            logger.warning(f"Context {session_id} not found for update")
            return None
        
        if step:
            context.current_step = step
        
        if data_updates:
            context.data.update(data_updates)
        
        if metadata_updates:
            context.metadata.update(metadata_updates)
        
        context.updated_at = datetime.utcnow()
        
        logger.info(f"Updated context {session_id}, current step: {context.current_step}")
        return context
    
    async def execute_ai_operation(
        self,
        context: WorkflowContext,
        prompt: str,
        system_message: Optional[str] = None,
        max_retries: int = 3
    ) -> str:
        """
        Execute an AI operation with retry logic and error handling.
        """
        callback_handler = WorkflowCallbackHandler(context)
        
        messages = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        
        # Add conversation history from memory
        memory_messages = self.memory.chat_memory.messages
        messages.extend(memory_messages)
        
        # Add current prompt
        messages.append(HumanMessage(content=prompt))
        
        for attempt in range(max_retries):
            try:
                logger.info(f"AI operation attempt {attempt + 1} for context {context.session_id}")
                
                response = await self.llm.ainvoke(
                    messages,
                    callbacks=[callback_handler]
                )
                
                # Store in memory
                self.memory.chat_memory.add_user_message(prompt)
                self.memory.chat_memory.add_ai_message(response.content)
                
                # Update context with operation logs
                context.metadata["last_ai_operation"] = {
                    "timestamp": datetime.utcnow(),
                    "prompt_length": len(prompt),
                    "response_length": len(response.content),
                    "attempt": attempt + 1,
                    "logs": callback_handler.step_logs
                }
                
                logger.info(f"AI operation successful for context {context.session_id}")
                return response.content
                
            except Exception as e:
                logger.error(f"AI operation attempt {attempt + 1} failed: {e}")
                
                if attempt == max_retries - 1:
                    # Final attempt failed
                    context.metadata["last_error"] = {
                        "timestamp": datetime.utcnow(),
                        "error": str(e),
                        "operation": "ai_operation",
                        "attempts": max_retries
                    }
                    raise e
                
                # Wait before retry with exponential backoff
                await asyncio.sleep(2 ** attempt)
        
        raise Exception(f"AI operation failed after {max_retries} attempts")
    
    async def execute_tool_operation(
        self,
        context: WorkflowContext,
        tool_name: str,
        tool_input: Dict[str, Any],
        max_retries: int = 3
    ) -> Any:
        """
        Execute a tool operation with retry logic and error handling.
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"Tool operation {tool_name} attempt {attempt + 1} for context {context.session_id}")
                
                # This is a placeholder for actual tool execution
                # In a real implementation, you would have a tool registry
                # and execute the appropriate tool based on tool_name
                
                # Update context with tool operation logs
                context.metadata["last_tool_operation"] = {
                    "timestamp": datetime.utcnow(),
                    "tool_name": tool_name,
                    "input": tool_input,
                    "attempt": attempt + 1
                }
                
                logger.info(f"Tool operation {tool_name} successful for context {context.session_id}")
                return {"status": "success", "tool": tool_name, "input": tool_input}
                
            except Exception as e:
                logger.error(f"Tool operation {tool_name} attempt {attempt + 1} failed: {e}")
                
                if attempt == max_retries - 1:
                    # Final attempt failed
                    context.metadata["last_error"] = {
                        "timestamp": datetime.utcnow(),
                        "error": str(e),
                        "operation": f"tool_{tool_name}",
                        "attempts": max_retries
                    }
                    raise e
                
                # Wait before retry with exponential backoff
                await asyncio.sleep(2 ** attempt)
        
        raise Exception(f"Tool operation {tool_name} failed after {max_retries} attempts")
    
    async def cleanup_context(self, session_id: str) -> bool:
        """Clean up a workflow context."""
        if session_id in self.active_contexts:
            del self.active_contexts[session_id]
            logger.info(f"Cleaned up context {session_id}")
            return True
        return False
    
    async def get_context_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of the workflow context."""
        context = self.active_contexts.get(session_id)
        if not context:
            return None
        
        return {
            "session_id": context.session_id,
            "user_id": context.user_id,
            "workflow_type": context.workflow_type,
            "current_step": context.current_step,
            "created_at": context.created_at,
            "updated_at": context.updated_at,
            "data_keys": list(context.data.keys()),
            "metadata_keys": list(context.metadata.keys())
        }


# Global orchestrator instance
orchestrator = WorkflowOrchestrator()
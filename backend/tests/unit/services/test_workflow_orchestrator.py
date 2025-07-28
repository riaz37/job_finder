"""
Unit tests for workflow orchestrator.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from app.services.workflow_orchestrator import (
    WorkflowOrchestrator,
    WorkflowContext,
    WorkflowCallbackHandler
)


@pytest.fixture
def orchestrator():
    """Create a workflow orchestrator instance for testing."""
    with patch('app.services.workflow_orchestrator.ChatGoogleGenerativeAI') as mock_llm:
        mock_llm.return_value = Mock()
        return WorkflowOrchestrator()


@pytest.fixture
def sample_context():
    """Create a sample workflow context for testing."""
    return WorkflowContext(
        user_id="test_user_123",
        session_id="test_session_456",
        workflow_type="test_workflow",
        current_step="initialization",
        data={"key": "value"},
        metadata={"test": True}
    )


class TestWorkflowContext:
    """Test WorkflowContext model."""
    
    def test_context_creation(self):
        """Test creating a workflow context."""
        context = WorkflowContext(
            user_id="user123",
            session_id="session456",
            workflow_type="job_application",
            current_step="start"
        )
        
        assert context.user_id == "user123"
        assert context.session_id == "session456"
        assert context.workflow_type == "job_application"
        assert context.current_step == "start"
        assert context.data == {}
        assert context.metadata == {}
        assert isinstance(context.created_at, datetime)
        assert isinstance(context.updated_at, datetime)
    
    def test_context_with_data(self):
        """Test creating a context with initial data."""
        data = {"resume_id": "resume123", "job_id": "job456"}
        metadata = {"priority": "high"}
        
        context = WorkflowContext(
            user_id="user123",
            session_id="session456",
            workflow_type="job_application",
            current_step="start",
            data=data,
            metadata=metadata
        )
        
        assert context.data == data
        assert context.metadata == metadata


class TestWorkflowCallbackHandler:
    """Test WorkflowCallbackHandler."""
    
    def test_callback_handler_creation(self, sample_context):
        """Test creating a callback handler."""
        handler = WorkflowCallbackHandler(sample_context)
        
        assert handler.context == sample_context
        assert handler.step_logs == []
    
    def test_on_llm_start(self, sample_context):
        """Test LLM start callback."""
        handler = WorkflowCallbackHandler(sample_context)
        
        handler.on_llm_start({"name": "test_llm"}, ["test prompt"])
        
        assert len(handler.step_logs) == 1
        log = handler.step_logs[0]
        assert log["event"] == "llm_start"
        assert log["step"] == sample_context.current_step
        assert log["prompts_count"] == 1
        assert isinstance(log["timestamp"], datetime)
    
    def test_on_llm_end(self, sample_context):
        """Test LLM end callback."""
        handler = WorkflowCallbackHandler(sample_context)
        
        mock_response = Mock()
        mock_response.content = "test response"
        handler.on_llm_end(mock_response)
        
        assert len(handler.step_logs) == 1
        log = handler.step_logs[0]
        assert log["event"] == "llm_end"
        assert log["step"] == sample_context.current_step
        assert log["response_length"] == len("test response")
    
    def test_on_llm_error(self, sample_context):
        """Test LLM error callback."""
        handler = WorkflowCallbackHandler(sample_context)
        
        test_error = Exception("Test error")
        handler.on_llm_error(test_error)
        
        assert len(handler.step_logs) == 1
        log = handler.step_logs[0]
        assert log["event"] == "llm_error"
        assert log["step"] == sample_context.current_step
        assert log["error"] == "Test error"
    
    def test_on_tool_start(self, sample_context):
        """Test tool start callback."""
        handler = WorkflowCallbackHandler(sample_context)
        
        handler.on_tool_start({"name": "test_tool"}, "test input")
        
        assert len(handler.step_logs) == 1
        log = handler.step_logs[0]
        assert log["event"] == "tool_start"
        assert log["tool_name"] == "test_tool"
        assert log["input"] == "test input"
    
    def test_on_tool_end(self, sample_context):
        """Test tool end callback."""
        handler = WorkflowCallbackHandler(sample_context)
        
        handler.on_tool_end("test output")
        
        assert len(handler.step_logs) == 1
        log = handler.step_logs[0]
        assert log["event"] == "tool_end"
        assert log["output_length"] == len("test output")
    
    def test_on_tool_error(self, sample_context):
        """Test tool error callback."""
        handler = WorkflowCallbackHandler(sample_context)
        
        test_error = Exception("Tool error")
        handler.on_tool_error(test_error)
        
        assert len(handler.step_logs) == 1
        log = handler.step_logs[0]
        assert log["event"] == "tool_error"
        assert log["error"] == "Tool error"


class TestWorkflowOrchestrator:
    """Test WorkflowOrchestrator."""
    
    @pytest.mark.asyncio
    async def test_create_context(self, orchestrator):
        """Test creating a workflow context."""
        initial_data = {"test": "data"}
        
        context = await orchestrator.create_context(
            user_id="user123",
            workflow_type="test_workflow",
            initial_data=initial_data
        )
        
        assert context.user_id == "user123"
        assert context.workflow_type == "test_workflow"
        assert context.current_step == "initialization"
        assert context.data == initial_data
        assert context.session_id in orchestrator.active_contexts
    
    @pytest.mark.asyncio
    async def test_get_context(self, orchestrator):
        """Test retrieving a workflow context."""
        context = await orchestrator.create_context(
            user_id="user123",
            workflow_type="test_workflow"
        )
        
        retrieved_context = await orchestrator.get_context(context.session_id)
        
        assert retrieved_context == context
        assert retrieved_context.user_id == "user123"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_context(self, orchestrator):
        """Test retrieving a non-existent context."""
        result = await orchestrator.get_context("nonexistent_session")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_context(self, orchestrator):
        """Test updating a workflow context."""
        context = await orchestrator.create_context(
            user_id="user123",
            workflow_type="test_workflow"
        )
        
        updated_context = await orchestrator.update_context(
            session_id=context.session_id,
            step="new_step",
            data_updates={"new_key": "new_value"},
            metadata_updates={"updated": True}
        )
        
        assert updated_context.current_step == "new_step"
        assert updated_context.data["new_key"] == "new_value"
        assert updated_context.metadata["updated"] is True
        assert updated_context.updated_at > context.created_at
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_context(self, orchestrator):
        """Test updating a non-existent context."""
        result = await orchestrator.update_context(
            session_id="nonexistent_session",
            step="new_step"
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_execute_ai_operation_success(self, orchestrator):
        """Test successful AI operation execution."""
        context = await orchestrator.create_context(
            user_id="user123",
            workflow_type="test_workflow"
        )
        
        # Mock the LLM response
        mock_response = Mock()
        mock_response.content = "AI response"
        orchestrator.llm.ainvoke = AsyncMock(return_value=mock_response)
        
        result = await orchestrator.execute_ai_operation(
            context=context,
            prompt="Test prompt",
            system_message="System message"
        )
        
        assert result == "AI response"
        assert "last_ai_operation" in context.metadata
        assert context.metadata["last_ai_operation"]["attempt"] == 1
    
    @pytest.mark.asyncio
    async def test_execute_ai_operation_with_retry(self, orchestrator):
        """Test AI operation execution with retry logic."""
        context = await orchestrator.create_context(
            user_id="user123",
            workflow_type="test_workflow"
        )
        
        # Mock the LLM to fail twice then succeed
        mock_response = Mock()
        mock_response.content = "AI response"
        orchestrator.llm.ainvoke = AsyncMock(
            side_effect=[Exception("First failure"), Exception("Second failure"), mock_response]
        )
        
        result = await orchestrator.execute_ai_operation(
            context=context,
            prompt="Test prompt",
            max_retries=3
        )
        
        assert result == "AI response"
        assert context.metadata["last_ai_operation"]["attempt"] == 3
    
    @pytest.mark.asyncio
    async def test_execute_ai_operation_max_retries_exceeded(self, orchestrator):
        """Test AI operation failure after max retries."""
        context = await orchestrator.create_context(
            user_id="user123",
            workflow_type="test_workflow"
        )
        
        # Mock the LLM to always fail
        orchestrator.llm.ainvoke = AsyncMock(side_effect=Exception("Persistent failure"))
        
        with pytest.raises(Exception, match="Persistent failure"):
            await orchestrator.execute_ai_operation(
                context=context,
                prompt="Test prompt",
                max_retries=2
            )
        
        assert "last_error" in context.metadata
        assert context.metadata["last_error"]["attempts"] == 2
    
    @pytest.mark.asyncio
    async def test_execute_tool_operation_success(self, orchestrator):
        """Test successful tool operation execution."""
        context = await orchestrator.create_context(
            user_id="user123",
            workflow_type="test_workflow"
        )
        
        result = await orchestrator.execute_tool_operation(
            context=context,
            tool_name="test_tool",
            tool_input={"param": "value"}
        )
        
        assert result["status"] == "success"
        assert result["tool"] == "test_tool"
        assert result["input"] == {"param": "value"}
        assert "last_tool_operation" in context.metadata
    
    @pytest.mark.asyncio
    async def test_cleanup_context(self, orchestrator):
        """Test cleaning up a workflow context."""
        context = await orchestrator.create_context(
            user_id="user123",
            workflow_type="test_workflow"
        )
        
        session_id = context.session_id
        assert session_id in orchestrator.active_contexts
        
        result = await orchestrator.cleanup_context(session_id)
        
        assert result is True
        assert session_id not in orchestrator.active_contexts
    
    @pytest.mark.asyncio
    async def test_cleanup_nonexistent_context(self, orchestrator):
        """Test cleaning up a non-existent context."""
        result = await orchestrator.cleanup_context("nonexistent_session")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_context_summary(self, orchestrator):
        """Test getting a context summary."""
        context = await orchestrator.create_context(
            user_id="user123",
            workflow_type="test_workflow",
            initial_data={"key1": "value1", "key2": "value2"}
        )
        
        summary = await orchestrator.get_context_summary(context.session_id)
        
        assert summary["session_id"] == context.session_id
        assert summary["user_id"] == "user123"
        assert summary["workflow_type"] == "test_workflow"
        assert summary["current_step"] == "initialization"
        assert "key1" in summary["data_keys"]
        assert "key2" in summary["data_keys"]
        assert isinstance(summary["created_at"], datetime)
        assert isinstance(summary["updated_at"], datetime)
    
    @pytest.mark.asyncio
    async def test_get_summary_nonexistent_context(self, orchestrator):
        """Test getting summary for non-existent context."""
        result = await orchestrator.get_context_summary("nonexistent_session")
        
        assert result is None


@pytest.mark.asyncio
async def test_orchestrator_memory_management(orchestrator):
    """Test that orchestrator properly manages conversation memory."""
    context = await orchestrator.create_context(
        user_id="user123",
        workflow_type="test_workflow"
    )
    
    # Mock the LLM response
    mock_response = Mock()
    mock_response.content = "AI response"
    orchestrator.llm.ainvoke = AsyncMock(return_value=mock_response)
    
    # Execute multiple operations
    await orchestrator.execute_ai_operation(context, "First prompt")
    await orchestrator.execute_ai_operation(context, "Second prompt")
    
    # Check that memory contains the conversation
    messages = orchestrator.memory.chat_memory.messages
    assert len(messages) == 4  # 2 user messages + 2 AI messages
    assert messages[0].content == "First prompt"
    assert messages[1].content == "AI response"
    assert messages[2].content == "Second prompt"
    assert messages[3].content == "AI response"


@pytest.mark.asyncio
async def test_concurrent_context_management(orchestrator):
    """Test managing multiple contexts concurrently."""
    # Create multiple contexts concurrently
    contexts = await asyncio.gather(
        orchestrator.create_context("user1", "workflow1"),
        orchestrator.create_context("user2", "workflow2"),
        orchestrator.create_context("user3", "workflow3")
    )
    
    assert len(contexts) == 3
    assert len(orchestrator.active_contexts) == 3
    
    # Verify each context is unique and properly stored
    for context in contexts:
        retrieved = await orchestrator.get_context(context.session_id)
        assert retrieved == context
    
    # Clean up all contexts
    cleanup_results = await asyncio.gather(
        orchestrator.cleanup_context(contexts[0].session_id),
        orchestrator.cleanup_context(contexts[1].session_id),
        orchestrator.cleanup_context(contexts[2].session_id)
    )
    
    assert all(cleanup_results)
    assert len(orchestrator.active_contexts) == 0
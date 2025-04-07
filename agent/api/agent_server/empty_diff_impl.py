import asyncio
import logging
from typing import Dict, Any, Optional, List

from interface import FSMInterface
from models import (
    AgentSseEvent,
    AgentMessage,
    ConversationMessage,
    AgentStatus,
    MessageKind
)

logger = logging.getLogger(__name__)

class EmptyDiffFSMImplementation(FSMInterface):
    """
    Minimal implementation of FSMInterface that returns empty dummy results.
    Used for testing the SSE stream functionality.
    """
    
    def __init__(self, chatbot_id: str = None, trace_id: str = None, settings: Optional[Dict[str, Any]] = None):
        """
        Initialize with session information
        
        Args:
            chatbot_id: ID of the chatbot
            trace_id: Trace ID for tracking
            settings: Optional settings
        """
        self.chatbot_id = chatbot_id or "default-bot"
        self.trace_id = trace_id or "default-trace"
        self.settings = settings or {}
        self.event_queue = asyncio.Queue()
        self.has_initialized = False
        
    async def process_event(self, 
                           messages: Optional[List[ConversationMessage]] = None, 
                           agent_state: Optional[Dict[str, Any]] = None) -> None:
        """
        Process an event and add response events to the queue
        
        Args:
            messages: Optional list of messages for initialization
            agent_state: Optional agent state for initialization
        """
        logger.info(f"Processing event for {self.chatbot_id}:{self.trace_id}")
        
        # Update the test to match the API spec
        # Create agent message with EXPLICIT unifiedDiff='' instead of unified_diff=''
        agent_message = AgentMessage(
            role="agent",
            kind=MessageKind.STAGE_RESULT,
            content="FSM initialized with EmptyDiffFSMImplementation",
            agent_state=agent_state or {},
            unifiedDiff=""  # Use the alias name directly
        )
        
        # Create initialization event with the message
        event = AgentSseEvent(
            status=AgentStatus.IDLE,
            traceId=self.trace_id,  # Use the trace_id from initialization
            message=agent_message
        )
        await self.event_queue.put(event)
    
    async def get_next_event(self) -> Optional[AgentSseEvent]:
        """
        Get the next event from the queue
        
        Returns:
            Next event or None if queue is empty
        """
        try:
            return self.event_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

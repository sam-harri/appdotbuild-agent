from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from models import (
    AgentSseEvent,
    ConversationMessage
)

class FSMInterface(ABC):
    """
    Simple interface for FSM event processing with minimal methods.
    Acts as an abstraction layer between server and FSM implementation.
    """

    @abstractmethod
    async def process_event(self, 
                           messages: Optional[list[ConversationMessage]] = None, 
                           agent_state: Optional[Dict[str, Any]] = None) -> None:
        """
        Process an incoming event asynchronously
        
        Args:
            messages: Optional list of conversation messages for initialization
            agent_state: Optional agent state for initialization
        """
        pass
    
    @abstractmethod
    async def get_next_event(self) -> Optional[AgentSseEvent]:
        """
        Get the next event to send back if available
        
        Returns:
            SSE event or None if no event is available
        """
        pass
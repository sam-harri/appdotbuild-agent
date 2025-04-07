import asyncio
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from models import (
    AgentRequest,
    AgentSseEvent,
    AgentMessage,
    AgentStatus,
    MessageKind,
    ErrorResponse
)
from interface import FSMInterface
from empty_diff_impl import EmptyDiffFSMImplementation

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Async Agent Server API")
    yield
    logger.info("Shutting down Async Agent Server API")

app = FastAPI(
    title="Async Agent Server API",
    description="Async API for communication between the Platform (Backend) and the Agent Server",
    version="1.0.0",
    lifespan=lifespan
)

async def get_fsm_session(chatbot_id: str, trace_id: str, settings: Optional[Dict[str, Any]] = None) -> FSMInterface:
    """
    Get or create an FSM session
    
    Args:
        chatbot_id: ID of the chatbot
        trace_id: Trace ID
        settings: Optional settings
        
    Returns:
        FSM interface implementation
    """
    # Create a new FSM implementation with the provided parameters
    logger.info(f"Creating new FSM session for {chatbot_id}:{trace_id}")
    return EmptyDiffFSMImplementation(chatbot_id, trace_id, settings)

async def sse_event_generator(fsm: FSMInterface, request: AgentRequest) -> AsyncGenerator[str, None]:
    """
    Generate SSE events from the FSM implementation according to the API spec
    
    Args:
        fsm: FSM interface to use
        request: The agent request containing all messages, chatbot ID, trace ID, agent state and settings
        
    Yields:
        SSE event strings in the format specified by the API
    """
    try:
        # Process the request with the FSM by providing messages and agent state
        await fsm.process_event(
            messages=request.all_messages, 
            agent_state=request.agent_state
        )
        
        # Loop to get and yield events
        while True:
            # Check for a new event
            event = await fsm.get_next_event()
            
            if event:
                # If we got an event, yield it as an SSE event with proper formatting
                # Format: data: {json_payload}\n\n
                yield f"data: {event.to_json()}\n\n"
                
                # If the status is idle, we're done processing
                # This happens when the FSM has completed its work or is waiting for more input
                if event.status == AgentStatus.IDLE:
                    break
            else:
                # No event available, poll the FSM by processing with empty parameters
                # This allows the FSM to continue processing without new input
                await fsm.process_event()
                
                # Small delay to avoid CPU spinning while polling
                await asyncio.sleep(0.1)
                
    except Exception as e:
        logger.error(f"Error in SSE generator: {str(e)}")
        
        # Create and yield an error event following the API spec format
        error_event = AgentSseEvent(
            status=AgentStatus.IDLE,  # Set to idle since we're ending the stream after error
            traceId=request.trace_id,  # Use traceId (the alias) not trace_id for instantiation
            message=AgentMessage(
                role="agent",
                kind=MessageKind.RUNTIME_ERROR,
                content=f"Error processing request: {str(e)}",
                agent_state=None,
                unified_diff=""  # Empty string instead of None for valid diff
            )
        )
        yield f"data: {error_event.to_json()}\n\n"

@app.post("/message", response_model=None)
async def message(request: AgentRequest) -> StreamingResponse:
    """
    Send a message to the agent and stream responses via SSE.
    
    Platform (Backend) -> Agent Server API Spec:
    POST Request:
    - allMessages: [str] - history of all user messages
    - chatbotId: str - required for Agent Server for tracing
    - traceId: str - required - a string used in SSE events
    - agentState: {..} or null - the full state of the Agent to restore from
    - settings: {...} - json with settings with number of iterations etc
    
    SSE Response:
    - status: "running" | "idle" - defines if the Agent stopped or continues running
    - traceId: corresponding traceId of the input
    - message: {kind, content, agentState, unifiedDiff} - response from the Agent Server
    
    Args:
        request: The agent request containing all necessary fields
        
    Returns:
        Streaming response with SSE events according to the API spec
    """
    try:
        logger.info(f"Received message request for chatbot {request.chatbot_id}, trace {request.trace_id}")
        
        
        # Get or create the FSM session for this request
        fsm = await get_fsm_session(
            request.chatbot_id, 
            request.trace_id, 
            request.settings
        )
        
        # Start the SSE stream
        logger.info(f"Starting SSE stream for chatbot {request.chatbot_id}, trace {request.trace_id}")
        return StreamingResponse(
            sse_event_generator(fsm, request),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        logger.error(f"Error processing message request: {str(e)}")
        # Return an HTTP error response for non-SSE errors
        error_response = ErrorResponse(
            error="Internal Server Error",
            details=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=error_response.to_json()
        )

@app.get("/healthcheck")
async def healthcheck():
    """Health check endpoint"""
    logger.debug("Health check requested")
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    import argparse
    import sys
    import os
    
    # Add parent directory to path to enable imports
    parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.append(parent_dir)
    
    # Configure argument parser
    parser = argparse.ArgumentParser(description="Run the Async Agent Server API")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8001, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--log-level", default="info", 
                      choices=["debug", "info", "warning", "error", "critical"],
                      help="Logging level")
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = getattr(logging, args.log_level.upper())
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the server
    uvicorn.run(
        "api.agent_server.async_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level
    )
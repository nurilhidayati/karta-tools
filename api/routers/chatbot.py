import json
import os

from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.encoders import jsonable_encoder
from declarai.memory import FileMessageHistory

import declarai
from config import settings

# Global variables for caching
_gpt_35 = None
_api_key_checked = False

def get_gpt35_client():
    """Get or create the GPT-3.5 client with proper API key validation"""
    global _gpt_35, _api_key_checked
    
    if _gpt_35 is not None:
        return _gpt_35
    
    # Check for API key
    openai_api_key = settings.OPENAI_API_KEY
    
    if not openai_api_key:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key is not configured. Please set either OPENAI_API_KEY or DECLARAI_OPENAI_API_KEY environment variable."
        )
    
    try:
        # Set the API key in the environment for declarai to use
        os.environ["OPENAI_API_KEY"] = openai_api_key
        
        # Initialize declarai - it will automatically use the OPENAI_API_KEY from environment
        _gpt_35 = declarai.openai(model="gpt-3.5-turbo")
        return _gpt_35
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize OpenAI client: {str(e)}"
        )

# Create router instance
router = APIRouter()

system_msg = """
    You are a sql assistant. You are helping a user to write a sql query.
    You should first know what sql syntax the user wants to use. It can be mysql, postgresql, sqllite, etc.
    If the user says something that is completely not related to SQL, you should say "I don't understand. I'm here to help you write a SQL query."
    After you provide the user with a query, you should ask the user if they need anything else.
    """

greeting = "Hey dear SQL User. Hope you are doing well today. I am here to help you write a SQL query. Let's get started!. What SQL syntax would you like to use? It can be mysql, postgresql, sqllite, etc."


def create_sql_chat(chat_history):
    """Create SQLChat instance with lazy-loaded GPT client"""
    gpt_client = get_gpt35_client()
    
    @gpt_client.experimental.chat(system=system_msg, greeting=greeting)
    class SQLChat:
        ...
    
    return SQLChat(chat_history=chat_history)


def create_streaming_sql_chat(chat_history):
    """Create StreamingSQLChat instance with lazy-loaded GPT client"""
    gpt_client = get_gpt35_client()
    
    @gpt_client.experimental.chat(system=system_msg, greeting=greeting, streaming=True)
    class StreamingSQLChat:
        ...
    
    return StreamingSQLChat(chat_history=chat_history)
    
@router.post("/chat/submit/{chat_id}")
def submit_chat(chat_id: str, request: str):
    try:
        chat = create_sql_chat(FileMessageHistory(file_path=chat_id))
        response = chat.send(request)
        return response
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        if "api key" in str(e).lower():
            raise HTTPException(
                status_code=500, 
                detail="OpenAI API key is not configured. Please contact the administrator."
            )
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@router.post("/chat/submit/{chat_id}/streaming")
def submit_chat_streaming(chat_id: str, request: str):
    try:
        chat = create_streaming_sql_chat(FileMessageHistory(file_path=chat_id))
        response = chat.send(request)

        def stream():
            try:
                for llm_response in response:
                    # Convert the LLMResponse to a JSON string
                    data = json.dumps(jsonable_encoder(llm_response))
                    yield data + "\n"  # Yielding as newline-separated JSON strings
            except Exception as e:
                error_response = {"error": f"Streaming error: {str(e)}"}
                yield json.dumps(error_response) + "\n"

        return StreamingResponse(stream(), media_type="text/event-stream")
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        if "api key" in str(e).lower():
            raise HTTPException(
                status_code=500, 
                detail="OpenAI API key is not configured. Please contact the administrator."
            )
        raise HTTPException(status_code=500, detail=f"Chat streaming error: {str(e)}")


@router.get("/chat/history/{chat_id}")
def get_chat_history(chat_id: str):
    try:
        chat = create_sql_chat(FileMessageHistory(file_path=chat_id))
        response = chat.conversation
        return response
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        if "api key" in str(e).lower():
            raise HTTPException(
                status_code=500, 
                detail="OpenAI API key is not configured. Please contact the administrator."
            )
        raise HTTPException(status_code=500, detail=f"Chat history error: {str(e)}")


@router.get("/chat/health")
def chatbot_health_check():
    """Health check endpoint for chatbot functionality"""
    try:
        # Try to get the GPT client to validate configuration
        get_gpt35_client()
        return {
            "status": "healthy",
            "chatbot": "available",
            "openai_configured": True,
            "message": "Chatbot is ready to use"
        }
    except HTTPException as e:
        return {
            "status": "unhealthy", 
            "chatbot": "unavailable",
            "openai_configured": False,
            "error": e.detail,
            "message": "Please configure OpenAI API key to use chatbot functionality"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "chatbot": "error", 
            "openai_configured": False,
            "error": str(e),
            "message": "Unexpected error in chatbot configuration"
        }



from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ChatMessagePart(BaseModel):
    text: str

class ChatMessageHistory(BaseModel):
    role: str
    parts: List[ChatMessagePart]

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessageHistory] = Field(default_factory=list)
    session_id: Optional[str] = None

class ChatError(BaseModel):
    code: str
    message: str

class ChatResponse(BaseModel):
    success: bool
    text: Optional[str] = None
    session_id: Optional[str] = None
    suggestions: Optional[List[str]] = None  # Clickable follow-up questions
    error: Optional[ChatError] = None

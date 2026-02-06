import re
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# Security configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "a_very_secret_key_for_jwt_tokens_change_it_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def sanitize_openai_response(response_dict: dict) -> dict:
    """
    Filters the response dictionary to only include standard OpenAI fields.
    Also removes <think>...</think> tags from the message content.
    """
    standard_keys = {"id", "object", "created", "model", "choices", "usage", "system_fingerprint"}
    message_standard_keys = {"role", "content", "tool_calls", "function_call", "name"}
    
    # 1. Filter top-level keys
    sanitized = {k: v for k, v in response_dict.items() if k in standard_keys}
    
    # 2. Process choices and filter <think> tags
    if "choices" in sanitized and isinstance(sanitized["choices"], list):
        for choice in sanitized["choices"]:
            if "message" in choice:
                # Filter message keys
                choice["message"] = {k: v for k, v in choice["message"].items() if k in message_standard_keys}
                
                content = choice["message"].get("content")
                if isinstance(content, str) and content:
                    # Remove <think>...</think> blocks
                    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                    choice["message"]["content"] = content
            
            # OpenAI standard for delta in streaming
            if "delta" in choice and "content" in choice["delta"]:
                # For streaming, we might not want to filter <think> tags here because it's partial
                # But if a whole tag is present in one chunk (rare), we could.
                # Usually filtering <think> in streaming requires a state machine.
                pass

    return sanitized

def filter_think_tag_from_chunk(chunk_text: str) -> str:
    """
    A simple attempt to filter <think> tags from streaming chunks.
    This is limited as tags might be split across chunks.
    """
    # If the chunk contains the whole tag, remove it.
    # For more robust filtering, a state machine in the stream generator is needed.
    return re.sub(r'<think>.*?</think>', '', chunk_text, flags=re.DOTALL)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
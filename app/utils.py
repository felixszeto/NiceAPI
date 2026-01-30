import re
import json
import logging

logger = logging.getLogger(__name__)

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
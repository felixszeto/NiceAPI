from pydantic import BaseModel
from typing import Optional, List, Any, Union
from datetime import datetime

# Base schema for ApiProvider
class ApiProviderBase(BaseModel):
    name: str
    api_endpoint: str
    model: Optional[str] = None
    price_per_million_tokens: Optional[float] = None
    type: Optional[str] = "per_token"
    is_active: Optional[bool] = True

# Schema for creating a new ApiProvider
class ApiProviderCreate(ApiProviderBase):
    api_key: str

# Schema for reading/returning ApiProvider data
class ProviderGroupLink(BaseModel):
    provider_id: int
    priority: int

class Group(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

class ApiProvider(ApiProviderBase):
    id: int
    groups: List["Group"] = []

    class Config:
        from_attributes = True

# Schemas for Group
class GroupBase(BaseModel):
    name: str

class GroupCreate(GroupBase):
    pass

class Group(GroupBase):
    id: int
    providers: List[ApiProvider] = []

    class Config:
        from_attributes = True



# Schema for importing models from a base URL
class ModelImportRequest(BaseModel):
    base_url: str
    api_key: str
    alias: Optional[str] = None
    default_type: str = "per_token"
    filter_mode: Optional[str] = None
    filter_keyword: Optional[str] = None

# Schema for the main chat request
class ChatMessage(BaseModel):
    role: str
    content: Optional[Union[str, List[Any]]] = None
    tool_calls: Optional[List[Any]] = None
    function_call: Optional[Any] = None
    name: Optional[str] = None
    tool_call_id: Optional[str] = None

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    type: Optional[str] = None
    stream: Optional[bool] = False

    class Config:
        extra = "allow"

# Schema for legacy Completions API
class CompletionRequest(BaseModel):
    model: str
    prompt: Union[str, List[str]]
    suffix: Optional[str] = None
    max_tokens: Optional[int] = 16
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    logprobs: Optional[int] = None
    stop: Optional[Union[str, List[str]]] = None

# Schema for Embeddings API
class EmbeddingRequest(BaseModel):
    model: str
    input: Union[str, List[str], List[int], List[List[int]]]
    user: Optional[str] = None

# Schema for Image Generation API
class ImageGenerationRequest(BaseModel):
    prompt: str
    model: Optional[str] = "dall-e-2"
    n: Optional[int] = 1
    quality: Optional[str] = "standard"
    size: Optional[str] = "1024x1024"
    style: Optional[str] = "vivid"
    response_format: Optional[str] = "url"
    user: Optional[str] = None

# Schema for ErrorMaintenance
class ErrorKeywordBase(BaseModel):
    keyword: str
    description: Optional[str] = None
    is_active: bool = True

class ErrorKeywordCreate(ErrorKeywordBase):
    pass

class ErrorKeyword(ErrorKeywordBase):
    id: int
    last_triggered: Optional[datetime] = None

    class Config:
        from_attributes = True
# Schemas for APIKey
class APIKeyBase(BaseModel):
    is_active: bool = True

class APIKeyCreate(APIKeyBase):
    group_ids: List[int]

class APIKeyUpdate(APIKeyBase):
    group_ids: Optional[List[int]] = None

class APIKey(APIKeyBase):
    id: int
    key: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    groups: List[Group] = []
    call_count: Optional[int] = None

    class Config:
        from_attributes = True

# Schemas for CallLog
class CallLogBase(BaseModel):
    provider_id: int
    api_key_id: Optional[int] = None
    request_timestamp: Optional[datetime] = None
    response_timestamp: Optional[datetime] = None
    is_success: bool
    status_code: int
    response_time_ms: int
    error_message: Optional[str] = None
    request_body: Optional[str] = None
    response_body: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost: Optional[float] = None

class CallLogCreate(CallLogBase):
    pass

class CallLog(CallLogBase):
    id: int
    request_timestamp: Optional[datetime] = None
    response_timestamp: Optional[datetime] = None

    class Config:
        from_attributes = True

# Schemas for OpenAI-compatible model list
class ModelResponse(BaseModel):
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = ""

class ModelListResponse(BaseModel):
    object: str = "list"
    data: List[ModelResponse]

# Schemas for Settings
class SettingBase(BaseModel):
    key: str
    value: str

class SettingCreate(SettingBase):
    pass

class Setting(SettingBase):
    class Config:
        from_attributes = True

# --- Anthropic Compatible Schemas ---

class AnthropicContent(BaseModel):
    type: str = "text"
    text: Optional[str] = None
    
    class Config:
        extra = "allow"

class AnthropicMessage(BaseModel):
    role: str
    content: Union[str, List[AnthropicContent]]

class AnthropicChatRequest(BaseModel):
    model: str
    messages: List[AnthropicMessage]
    system: Optional[Union[str, List[AnthropicContent]]] = None
    max_tokens: Optional[int] = 4096
    stop_sequences: Optional[List[str]] = None
    stream: Optional[bool] = False
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None

    class Config:
        extra = "allow"

class AnthropicUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0

class AnthropicChatResponse(BaseModel):
    id: str
    type: str = "message"
    role: str = "assistant"
    content: List[AnthropicContent]
    model: str
    stop_reason: Optional[str] = "end_turn"
    stop_sequence: Optional[str] = None
    usage: AnthropicUsage
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
    content: Union[str, List[Any]]

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    type: Optional[str] = None
    stream: Optional[bool] = False

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

    class Config:
        from_attributes = True

# Schemas for CallLog
class CallLogBase(BaseModel):
    provider_id: int
    request_timestamp: Optional[datetime] = None
    response_timestamp: Optional[datetime] = None
    is_success: bool
    status_code: int
    response_time_ms: int
    error_message: Optional[str] = None
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
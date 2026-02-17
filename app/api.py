from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import func, case, cast, Integer
from sqlalchemy.orm import Session
from typing import List, Optional
import asyncio
import json
from . import crud, models, schemas, router as smart_router, utils
from .database import get_db, SessionLocal
from fastapi.responses import StreamingResponse
import time
import logging
import httpx
from datetime import datetime
import pytz

TAIPEI_TZ = pytz.timezone('Asia/Taipei')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter() # Management APIs
proxy_router = APIRouter() # OpenAI/Anthropic Compatibility APIs

# Authentication dependency for internal management APIs
from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

async def get_current_admin(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = utils.jwt.decode(token, utils.SECRET_KEY, algorithms=[utils.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except utils.JWTError:
        raise credentials_exception
    
    import os
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    if token_data.username != ADMIN_USERNAME:
        raise credentials_exception
    return token_data.username

@router.post("/auth/login", response_model=schemas.Token)
async def login_for_access_token(login_data: schemas.LoginRequest):
    import os
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "password")
    
    if login_data.username != ADMIN_USERNAME or login_data.password != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = utils.timedelta(minutes=utils.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = utils.create_access_token(
        data={"sub": login_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/status", response_model=schemas.SystemStatusResponse)
def get_system_status(db: Session = Depends(get_db)):
    """
    Integrated public endpoint for Groups, Models, and Associations.
    """
    return {
        "Groups": [schemas.GroupSimple(id=g.id, name=g.name) for g in crud.get_groups(db)],
        "Models": crud.get_providers_simple(db),
        "Association": crud.get_concurrency_status(db)
    }

@router.get("/dashboard/stats", response_model=dict)
def get_dashboard_stats(db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    from datetime import datetime, timedelta
    
    # 我們將統計範圍限制在最近 10,000 條記錄（或最近 30 天，這裡維持原邏輯的「最近」概念，但改用 ID 範圍或全表聚合）
    # 為了性能，我們直接對數據庫進行聚合查詢
    
    # 1. 基礎統計 (Summary)
    summary_query = db.query(
        func.count(models.CallLog.id).label('total_calls'),
        func.sum(case((models.CallLog.is_success == True, 1), else_=0)).label('success_calls'),
        func.sum(models.CallLog.total_tokens).label('total_tokens'),
        func.sum(models.CallLog.cost).label('total_cost')
    ).filter(models.CallLog.provider_id.isnot(None)).first()
    
    total_calls = summary_query.total_calls or 0
    success_rate = (summary_query.success_calls / total_calls * 100) if total_calls > 0 else 0
    api_keys_count = db.query(func.count(models.APIKey.id)).scalar()

    # 2. 模型使用分佈 & 平均響應時間 & 成本 (按模型分組)
    # 這裡使用 JOIN 以獲取模型名稱
    model_stats_query = db.query(
        models.ApiProvider.model,
        func.count(models.CallLog.id).label('count'),
        func.avg(models.CallLog.response_time_ms).label('avg_time'),
        func.sum(models.CallLog.cost).label('total_cost')
    ).join(models.ApiProvider, models.CallLog.provider_id == models.ApiProvider.id)\
     .group_by(models.ApiProvider.model).all()

    model_distribution = [{"name": r.model, "value": r.count} for r in model_stats_query if r.model]
    
    model_names = sorted([r.model for r in model_stats_query if r.model])
    model_avg_times = {r.model: round(r.avg_time or 0) for r in model_stats_query}
    model_costs_map = {r.model: round(r.total_cost or 0, 4) for r in model_stats_query}

    # 3. 每日調用次數 (最近 7 天)
    now = datetime.now(TAIPEI_TZ)
    start_date = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # SQLite 的日期處理比較特殊，這裡使用 func.date
    daily_query = db.query(
        func.date(models.CallLog.request_timestamp).label('date'),
        func.count(models.CallLog.id).label('count')
    ).filter(models.CallLog.request_timestamp >= start_date)\
     .group_by(func.date(models.CallLog.request_timestamp))\
     .order_by('date').all()

    daily_counts_map = {r.date: r.count for r in daily_query}
    sorted_dates = []
    daily_data = []
    for i in range(7):
        d_str = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
        sorted_dates.append(d_str)
        daily_data.append(daily_counts_map.get(d_str, 0))

    # 4. 端點統計 (Endpoint Stats)
    endpoint_query = db.query(
        models.ApiProvider.api_endpoint,
        func.count(models.CallLog.id).label('total'),
        func.sum(case((models.CallLog.is_success == True, 1), else_=0)).label('success'),
        func.avg(models.CallLog.response_time_ms).label('avg_time')
    ).join(models.ApiProvider, models.CallLog.provider_id == models.ApiProvider.id)\
     .group_by(models.ApiProvider.api_endpoint).all()

    from urllib.parse import urlparse
    endpoint_names = []
    endpoint_success_rates = []
    endpoint_avg_times = []
    endpoint_total_calls = []

    for r in sorted(endpoint_query, key=lambda x: x.api_endpoint):
        try:
            name = urlparse(r.api_endpoint).netloc or r.api_endpoint
        except:
            name = r.api_endpoint
        endpoint_names.append(name)
        endpoint_total_calls.append(r.total)
        endpoint_success_rates.append(round((r.success / r.total * 100)) if r.total > 0 else 0)
        endpoint_avg_times.append(round(r.avg_time or 0))

    return {
        "summary": {
            "total_calls": total_calls,
            "success_rate": round(success_rate, 1),
            "total_tokens": int(summary_query.total_tokens or 0),
            "api_keys": api_keys_count,
            "total_cost": round(summary_query.total_cost or 0, 4)
        },
        "model_distribution": model_distribution,
        "daily_calls": {"dates": sorted_dates, "values": daily_data},
        "endpoint_stats": {
            "names": endpoint_names,
            "success_rates": endpoint_success_rates,
            "avg_times": endpoint_avg_times,
            "total_calls": endpoint_total_calls
        },
        "model_stats": {
            "names": model_names,
            "avg_times": [model_avg_times.get(m, 0) for m in model_names]
        },
        "cost_stats": {
            "names": model_names,
            "values": [model_costs_map.get(m, 0) for m in model_names]
        }
    }

@router.get("/public/groups", response_model=List[schemas.GroupSimple])
def get_public_groups(db: Session = Depends(get_db)):
    """
    Public endpoint to get all groups (ID and Name only).
    """
    return [schemas.GroupSimple(id=g.id, name=g.name) for g in crud.get_groups(db)]

@router.get("/public/providers", response_model=List[schemas.ApiProviderSimple])
def get_public_providers(db: Session = Depends(get_db)):
    """
    Public endpoint to get basic info of all providers.
    """
    return crud.get_providers_simple(db)

# Security scheme
auth_scheme = HTTPBearer()

# Dependency to get and validate API key
async def get_api_key_from_bearer(
    request: Request,
    db: Session = Depends(get_db),
    authorization: HTTPAuthorizationCredentials = Depends(auth_scheme)
) -> models.APIKey:
    """
    Validates the API key from the 'Authorization: Bearer <key>' header.
    """
    api_key_str = authorization.credentials
    error_detail = None
    
    if not api_key_str:
        error_detail = "No API key provided."
    else:
        db_api_key = crud.get_api_key_by_key(db, key=api_key_str)
        if not db_api_key or not db_api_key.is_active:
            error_detail = f"Incorrect API key provided or key has been revoked: {api_key_str[:10]}..."
        else:
            # Success
            crud.update_api_key_last_used(db, db_api_key.id)
            return db_api_key

    # Log Authentication Failure
    if error_detail:
        try:
            body = await request.body()
            body_str = body.decode('utf-8', errors='ignore')
        except:
            body_str = "Could not read request body"

        crud.create_call_log(db, schemas.CallLogCreate(
            provider_id=None,
            api_key_id=None,
            response_timestamp=datetime.now(TAIPEI_TZ),
            is_success=False,
            status_code=401,
            response_time_ms=0,
            error_message=f"Auth Error: {error_detail}",
            request_body=body_str,
            response_body=error_detail
        ))
        
        raise HTTPException(
            status_code=401,
            detail={"error": {"message": "Incorrect API key provided or key has been revoked.", "type": "invalid_request_error"}},
            headers={"WWW-Authenticate": "Bearer"},
        )

# Dependency to get API key from Anthropic's custom header
async def get_api_key_from_anthropic_header(
    request: Request,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(None, alias="x-api-key"),
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> models.APIKey:
    """
    Validates the API key from 'x-api-key' header OR 'Authorization: Bearer' header.
    """
    api_key_str = x_api_key
    if not api_key_str and authorization:
        api_key_str = authorization.credentials

    error_detail = None
    if not api_key_str:
        error_detail = "No API key provided."
    else:
        db_api_key = crud.get_api_key_by_key(db, key=api_key_str)
        if not db_api_key or not db_api_key.is_active:
            error_detail = f"Invalid API key: {api_key_str[:10]}..."
        else:
            # Success
            crud.update_api_key_last_used(db, db_api_key.id)
            return db_api_key

    # Log Authentication Failure
    if error_detail:
        try:
            body = await request.body()
            body_str = body.decode('utf-8', errors='ignore')
        except:
            body_str = "Could not read request body"

        crud.create_call_log(db, schemas.CallLogCreate(
            provider_id=None,
            api_key_id=None,
            response_timestamp=datetime.now(TAIPEI_TZ),
            is_success=False,
            status_code=401,
            response_time_ms=0,
            error_message=f"Auth Error: {error_detail}",
            request_body=body_str,
            response_body=error_detail
        ))
        
        raise HTTPException(
            status_code=401,
            detail={"error": {"message": error_detail, "type": "authentication_error"}},
        )


@router.post("/providers/", response_model=schemas.ApiProvider)
def create_provider(provider: schemas.ApiProviderCreate, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    return crud.create_provider(db=db, provider=provider)

@router.get("/providers/", response_model=schemas.ProviderListResponse)
def read_providers(skip: Optional[int] = None, limit: Optional[int] = None, name_filter: Optional[str] = None, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    providers = crud.get_providers(db, skip=skip, limit=limit, name_filter=name_filter)
    total = crud.count_providers(db, name_filter=name_filter)
    return {"items": providers, "total": total}

@router.get("/providers/{provider_id}", response_model=schemas.ApiProvider)
def read_provider(provider_id: int, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    db_provider = crud.get_provider(db, provider_id=provider_id)
    if db_provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    return db_provider

@router.patch("/providers/{provider_id}", response_model=schemas.ApiProvider)
def update_provider(provider_id: int, provider_data: dict, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    db_provider = crud.update_provider(db, provider_id, provider_data)
    if not db_provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return db_provider

@router.delete("/providers/{provider_id}")
def delete_provider(provider_id: int, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    db_provider = crud.delete_provider(db, provider_id)
    if not db_provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"detail": "Provider deleted"}

@router.delete("/providers/quick-remove/{api_key}")
def quick_remove_providers(api_key: str, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    count = crud.delete_providers_by_key(db, api_key)
    return {"detail": f"Removed {count} providers", "count": count}

@router.post("/providers/sync")
async def sync_providers(request: schemas.ModelImportRequest, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    """
    Synchronous version of model import (for simple UI calls)
    """
    # ... logic handled by background or simple loop ...
    # Re-using the logic from import_models but without streaming
    clean_base = request.base_url.strip().rstrip('/')
    if clean_base.endswith('/v1'):
        clean_base = clean_base[:-3].rstrip('/')
    v1_base_url = f"{clean_base}/v1"
    
    models_url = f"{v1_base_url}/models"
    headers = {"Authorization": f"Bearer {request.api_key}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(models_url, headers=headers, timeout=30)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch models from provider")
        models_data = response.json()

    models_list = models_data.get('data', [])
    if request.filter_keyword and request.filter_mode != 'None':
        keyword = request.filter_keyword.lower()
        if request.filter_mode == 'Include':
            models_list = [m for m in models_list if m.get('id') and keyword in m.get('id').lower()]
        elif request.filter_mode == 'Exclude':
            models_list = [m for m in models_list if m.get('id') and keyword not in m.get('id').lower()]

    imported = 0
    for model_info in models_list:
        model_id = model_info.get('id')
        if not model_id: continue
        
        target_endpoint = f"{v1_base_url}/chat/completions"
        existing = db.query(models.ApiProvider).filter(
            models.ApiProvider.api_endpoint == target_endpoint,
            models.ApiProvider.api_key == request.api_key,
            models.ApiProvider.model == model_id
        ).first()
        
        if existing: continue
        
        formatted_name = request.alias if request.alias else model_id.replace('/', '.')
        # For NVIDIA and other model-specific providers, ensure the endpoint includes the model if necessary,
        # but the primary fix requested is ensuring 'model' field (model_id) is used correctly.
        provider_data = schemas.ApiProviderCreate(
            name=formatted_name,
            api_endpoint=target_endpoint,
            api_key=request.api_key,
            model=model_id, # Ensure this is the raw model_id from the provider
            price_per_million_tokens=0,
            input_price_per_million_tokens=0,
            output_price_per_million_tokens=0,
            type=request.default_type,
            is_active=True
        )
        crud.create_provider(db, provider_data)
        imported += 1
        
    return {"detail": f"Synced {imported} models", "count": imported}

# Endpoints for Groups
@router.post("/groups/", response_model=schemas.Group)
def create_group(group: schemas.GroupCreate, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    db_group = crud.get_group_by_name(db, name=group.name)
    if db_group:
        raise HTTPException(status_code=400, detail="Group with this name already exists")
    return crud.create_group(db=db, group=group)

@router.get("/groups/", response_model=schemas.GroupListResponse)
def read_groups(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    groups = crud.get_groups(db, skip=skip, limit=limit)
    total = crud.count_groups(db)
    return {"items": groups, "total": total}

@router.delete("/groups/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    db_group = crud.delete_group(db, group_id)
    if not db_group:
        raise HTTPException(status_code=404, detail="Group not found")
    return {"detail": "Group deleted"}

@router.post("/groups/{group_id}/providers/{provider_id}", response_model=schemas.ApiProvider)
def add_provider_to_group(group_id: int, provider_id: int, priority_data: dict = None, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    priority = 1
    if priority_data and "priority" in priority_data:
        priority = priority_data["priority"]
    
    provider = crud.add_provider_to_group(db, provider_id=provider_id, group_id=group_id, priority=priority)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider or Group not found")
    return provider

@router.delete("/groups/{group_id}/providers/{provider_id}")
def remove_provider_from_group(group_id: int, provider_id: int, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    success = crud.remove_provider_from_group(db, provider_id=provider_id, group_id=group_id)
    if not success:
        raise HTTPException(status_code=404, detail="Provider or Group not found, or provider not in group")
    return {"detail": "Provider removed from group"}

@router.put("/groups/{group_id}/providers")
def update_group_providers(group_id: int, providers_data: List[dict], db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    """
    Batch update providers in a group.
    Expected format: [{"id": 1, "priority": 1, "selected": true}, ...]
    """
    # Remove all existing associations for this group
    db.query(models.ProviderGroupAssociation).filter(
        models.ProviderGroupAssociation.group_id == group_id
    ).delete(synchronize_session=False)
    
    # Add new associations
    for p in providers_data:
        if p.get('selected'):
            crud.add_provider_to_group(db, provider_id=p['id'], group_id=group_id, priority=p.get('priority', 99), commit=False)
    
    db.commit()
    return {"detail": "Group providers updated"}

@proxy_router.post("/v1/chat/completions")
async def chat(request: schemas.ChatRequest, db: Session = Depends(get_db), api_key: models.APIKey = Depends(get_api_key_from_bearer)):
    
    # --- Permission Check ---
    # The user now sends a group name as the "model".
    # Check if the requested group name is in the list of groups associated with the API key.
    authorized_group_names = {group.name for group in api_key.groups}
    
    # Matching logic: allow exact match or match after removing prefix (e.g., 'gemini' matches 'google/gemini')
    matched_group_name = None
    if request.model in authorized_group_names:
        matched_group_name = request.model
    else:
        # Try to find a group that ends with /requested_model or matches common variations
        for name in authorized_group_names:
            if (name.endswith(f"/{request.model}") or
                request.model.endswith(f"/{name}") or
                name == request.model.replace("claude-", "anthropic/") or
                name == request.model.replace("gpt-", "openai/")):
                matched_group_name = name
                logger.info(f"Mapping requested model '{request.model}' to authorized group '{matched_group_name}'")
                break
    
    if not matched_group_name:
        group_names = ", ".join(list(authorized_group_names))
        error_msg = f"API key not authorized for the requested model (group): {request.model}. Authorized groups: [{group_names}]"
        logger.warning(f"API Key {api_key.key[:5]}... {error_msg}")
        
        # Log Permission Error
        crud.create_call_log(db, schemas.CallLogCreate(
            provider_id=None,
            api_key_id=api_key.id,
            response_timestamp=datetime.now(TAIPEI_TZ),
            is_success=False,
            status_code=403,
            response_time_ms=0,
            error_message=f"Permission Error: {error_msg}",
            request_body=json.dumps(request.dict()),
            response_body=error_msg
        ))

        raise HTTPException(
            status_code=403,
            detail={"error": {"message": f"API key not authorized for the requested model (group): {request.model}", "type": "permission_denied_error"}}
        )

    # Update the request model to the matched group name so select_provider finds the right providers
    original_requested_model = request.model
    request.model = matched_group_name

    # --- Streaming Response Logic ---
    if request.stream:
        async def stream_generator():
            excluded_provider_ids = []
            in_think_block = False
            while True:
                provider = None
                failure_keywords = []
                
                # Use a temporary session to select a provider and get keywords, then close it.
                db_session = SessionLocal()
                try:
                    provider, group_id = smart_router.select_provider(db_session, request, excluded_provider_ids=excluded_provider_ids)
                    if provider:
                        failure_keywords = [kw.keyword.lower() for kw in crud.get_all_active_error_keywords(db_session)]
                finally:
                    db_session.close()

                if not provider:
                    logger.error("All providers failed for streaming request.")
                    error_info = "All suitable providers failed or are unavailable."
                    
                    # Log 503 Error
                    log_db = SessionLocal()
                    try:
                        crud.create_call_log(log_db, schemas.CallLogCreate(
                            provider_id=None,
                            api_key_id=api_key.id,
                            response_timestamp=datetime.now(TAIPEI_TZ),
                            is_success=False,
                            status_code=503,
                            response_time_ms=0,
                            error_message=f"Service Error: {error_info}",
                            request_body=json.dumps(request.dict()),
                            response_body=error_info
                        ))
                    finally:
                        log_db.close()

                    error_message = {"error": {"message": error_info}}
                    yield f"data: {json.dumps(error_message)}\n\n"
                    return

                logger.info(f"Streaming attempt with provider: {provider.name} (ID: {provider.id})")
                start_time = time.time()
                full_response_text = ""
                stream_usage = {}  # To capture usage from the final chunk
                
                # Increment active calls
                log_db_init = SessionLocal()
                try:
                    if group_id:
                        crud.increment_active_calls(log_db_init, provider.id, group_id)
                finally:
                    log_db_init.close()

                try:
                    api_url = provider.api_endpoint
                    provider_api_key = provider.api_key
                    headers = {"Authorization": f"Bearer {provider_api_key}", "Content-Type": "application/json"}
                    payload = request.dict(exclude_unset=True)
                    # Ensure we use the provider's actual model ID, not the group name or alias
                    payload['model'] = provider.model
                    payload['stream'] = True

                    async with httpx.AsyncClient(timeout=300) as client:
                        async with client.stream("POST", api_url, headers=headers, json=payload) as response:
                            if response.status_code >= 400:
                                error_body = await response.aread()
                                error_message = error_body.decode('utf-8', 'ignore')
                                end_time = time.time()
                                status_code = response.status_code

                                if status_code == 429:
                                    logger.warning(f"Provider {provider.name} (ID: {provider.id}) failed with 429 Too Many Requests. Marking as failed and retrying.")
                                else:
                                    logger.warning(f"Provider {provider.name} (ID: {provider.id}) failed with status code {status_code}: {error_message}")
                                
                                # Use a temporary session to log the error
                                log_db = SessionLocal()
                                try:
                                    crud.create_call_log(log_db, schemas.CallLogCreate(
                                        provider_id=provider.id, api_key_id=api_key.id, response_timestamp=datetime.now(TAIPEI_TZ), is_success=False,
                                        status_code=status_code, response_time_ms=int((end_time - start_time) * 1000), error_message=error_message,
                                        request_body=json.dumps(request.dict()), response_body=error_message
                                    ))
                                finally:
                                    log_db.close()
                                
                                excluded_provider_ids.append(provider.id)
                                logger.info(f"Adding provider ID {provider.id} to exclusion list. Retrying stream.")
                                continue

                            async for chunk in response.aiter_bytes():
                                chunk_raw = chunk.decode('utf-8', errors='ignore')
                                chunk_text_lower = chunk_raw.lower()
                                full_response_text += chunk_text_lower
                                for keyword in failure_keywords:
                                    if keyword in full_response_text:
                                        raise ValueError(f"Failure keyword found: '{keyword}'")
                                
                                # Try to extract usage from SSE data chunks
                                for sse_line in chunk_raw.split('\n'):
                                    if sse_line.startswith('data: ') and sse_line.strip() != 'data: [DONE]':
                                        try:
                                            sse_data = json.loads(sse_line[6:])
                                            if 'usage' in sse_data and sse_data['usage']:
                                                stream_usage = sse_data['usage']
                                        except (json.JSONDecodeError, KeyError):
                                            pass

                                # Basic <think> tag filtering for streaming
                                if "<think>" in chunk_raw:
                                    in_think_block = True
                                    parts = chunk_raw.split("<think>")
                                    if parts[0]: yield parts[0].encode('utf-8')
                                    continue
                                
                                if "</think>" in chunk_raw:
                                    in_think_block = False
                                    parts = chunk_raw.split("</think>")
                                    if len(parts) > 1 and parts[1]: yield parts[1].encode('utf-8')
                                    continue

                                if not in_think_block:
                                    yield chunk
                            
                            end_time = time.time()
                            # Calculate cost from stream usage if available
                            stream_prompt_tokens = stream_usage.get('prompt_tokens')
                            stream_completion_tokens = stream_usage.get('completion_tokens')
                            stream_total_tokens = stream_usage.get('total_tokens')
                            stream_cost = None
                            
                            # Need to re-fetch provider from DB since the original object may be detached
                            log_db = SessionLocal()
                            try:
                                if stream_prompt_tokens is not None or stream_total_tokens is not None:
                                    db_provider = crud.get_provider(log_db, provider.id)
                                    if db_provider:
                                        stream_cost = crud.calculate_cost(db_provider, stream_prompt_tokens, stream_completion_tokens, stream_total_tokens)
                                
                                crud.create_call_log(log_db, schemas.CallLogCreate(
                                    provider_id=provider.id, api_key_id=api_key.id, response_timestamp=datetime.now(TAIPEI_TZ), is_success=True,
                                    status_code=response.status_code, response_time_ms=int((end_time - start_time) * 1000),
                                    error_message=None,
                                    prompt_tokens=stream_prompt_tokens, completion_tokens=stream_completion_tokens,
                                    total_tokens=stream_total_tokens, cost=stream_cost,
                                    request_body=json.dumps(request.dict()), response_body=full_response_text
                                ))
                            finally:
                                log_db.close()
                            logger.info(f"--- Streaming Response Finished (Provider ID: {provider.id}) ---")
                            logger.info(f"Full response text: {full_response_text[:500]}..." if len(full_response_text) > 500 else f"Full response text: {full_response_text}")
                            break

                except (httpx.RequestError, ValueError) as e:
                    end_time = time.time()
                    status_code = 503
                    logger.warning(f"Provider {provider.name} (ID: {provider.id}) failed during stream: {e}")
                    
                    # Use a temporary session to log the exception
                    log_db = SessionLocal()
                    try:
                        crud.create_call_log(log_db, schemas.CallLogCreate(
                            provider_id=provider.id, api_key_id=api_key.id, response_timestamp=datetime.now(TAIPEI_TZ), is_success=False,
                            status_code=status_code, response_time_ms=int((end_time - start_time) * 1000), error_message=str(e),
                            request_body=json.dumps(request.dict()), response_body=full_response_text
                        ))
                    finally:
                        log_db.close()
                    
                    excluded_provider_ids.append(provider.id)
                    logger.info(f"Adding provider ID {provider.id} to exclusion list. Retrying stream.")
                    continue
                finally:
                    # Decrement active calls
                    log_db_end = SessionLocal()
                    try:
                        if group_id:
                            crud.decrement_active_calls(log_db_end, provider.id, group_id)
                    finally:
                        log_db_end.close()

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    # --- Non-Streaming Response Logic (remains the same) ---
    else:
        excluded_provider_ids = []
        while True:
            # The select_provider function now looks up providers by the group name in request.model
            provider, group_id = smart_router.select_provider(db, request, excluded_provider_ids=excluded_provider_ids)
            if not provider:
                error_info = "All suitable providers failed or are unavailable."
                # Log 503 Error
                crud.create_call_log(db, schemas.CallLogCreate(
                    provider_id=None,
                    api_key_id=api_key.id,
                    response_timestamp=datetime.now(TAIPEI_TZ),
                    is_success=False,
                    status_code=503,
                    response_time_ms=0,
                    error_message=f"Service Error: {error_info}",
                    request_body=json.dumps(request.dict()),
                    response_body=error_info
                ))
                raise HTTPException(status_code=503, detail=error_info)

            logger.info(f"Non-streaming attempt with provider: {provider.model} (ID: {provider.id})")
            start_time = time.time()
            
            # Increment active calls
            if group_id:
                crud.increment_active_calls(db, provider.id, group_id)

            try:
                api_url = provider.api_endpoint
                provider_api_key = provider.api_key
                headers = {"Authorization": f"Bearer {provider_api_key}", "Content-Type": "application/json"}
                payload = request.dict(exclude_unset=True)
                # Ensure we use the provider's actual model ID, not the group name or alias
                payload['model'] = provider.model
                payload['stream'] = False
                failure_keywords = [kw.keyword.lower() for kw in crud.get_all_active_error_keywords(db)]

                async with httpx.AsyncClient(timeout=300) as client:
                    response = await client.post(api_url, headers=headers, json=payload)
                    response.raise_for_status()
                
                response_json = response.json()
                if not response_json or not response_json.get("choices"):
                    raise ValueError("Empty or null response from provider")

                response_text = str(response_json).lower()
                for keyword in failure_keywords:
                    if keyword in response_text:
                        raise ValueError(f"Failure keyword found: '{keyword}'")

                # Success case
                end_time = time.time()
                usage = response_json.get("usage", {})
                cost = crud.calculate_cost(provider, usage.get("prompt_tokens"), usage.get("completion_tokens"), usage.get("total_tokens"))
                try:
                    crud.create_call_log(db, schemas.CallLogCreate(
                        provider_id=provider.id, api_key_id=api_key.id, response_timestamp=datetime.now(TAIPEI_TZ), is_success=True,
                        status_code=response.status_code, response_time_ms=int((end_time - start_time) * 1000),
                        prompt_tokens=usage.get("prompt_tokens"), completion_tokens=usage.get("completion_tokens"),
                        total_tokens=usage.get("total_tokens"), cost=cost,
                        request_body=json.dumps(request.dict()), response_body=json.dumps(response_json)
                    ))
                except Exception as log_err:
                    logger.error(f"Failed to create success call log: {log_err}")
                    db.rollback()
                logger.info(f"--- Non-streaming Response Success (Provider ID: {provider.id}) ---")
                logger.info(f"Response JSON: {json.dumps(response_json)}")
                # Sanitize response to remove non-standard fields and <think> tags
                return utils.sanitize_openai_response(response_json)

            except (httpx.RequestError, ValueError) as e:
                end_time = time.time()
                status_code = e.response.status_code if hasattr(e, 'response') and e.response is not None else 503
                response_body = e.response.text if hasattr(e, 'response') and e.response is not None else None
                
                if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 429:
                    logger.warning(f"Provider {provider.name} (ID: {provider.id}) failed with 429 Too Many Requests. Marking as failed for this request and retrying with another provider.")
                else:
                    logger.warning(f"Provider {provider.name} (ID: {provider.id}) failed: {e}")
                
                try:
                    crud.create_call_log(db, schemas.CallLogCreate(
                        provider_id=provider.id, api_key_id=api_key.id, response_timestamp=datetime.now(TAIPEI_TZ), is_success=False,
                        status_code=status_code, response_time_ms=int((end_time - start_time) * 1000), error_message=str(e),
                        request_body=json.dumps(request.dict()), response_body=response_body
                    ))
                except Exception as log_err:
                    logger.error(f"Failed to create failure call log: {log_err}")
                    db.rollback()

                error_str = str(e).lower()
                if "insufficient" in error_str and "quota" in error_str:
                    logger.warning(f"Provider {provider.name} (ID: {provider.id}) disabled due to insufficient quota.")
                    provider.is_active = False
                    db.commit()
                    crud.create_maintenance_error(db=db, provider_id=provider.id, error_type="INSUFFICIENT_QUOTA", details=str(e))

                excluded_provider_ids.append(provider.id)
                logger.info(f"Adding provider ID {provider.id} to exclusion list. Retrying.")
                continue
            finally:
                # Decrement active calls
                if group_id:
                    crud.decrement_active_calls(db, provider.id, group_id)

@router.post("/import-models/")
async def import_models(request: schemas.ModelImportRequest, admin: str = Depends(get_current_admin)):
    async def progress_stream():
        db = SessionLocal()
        try:
            logger.info(f"Starting model import from raw base URL: {request.base_url}")
            
            # Normalize the base URL to ensure it points to the v1 endpoint
            clean_base = request.base_url.strip().rstrip('/')
            if clean_base.endswith('/v1'):
                clean_base = clean_base[:-3].rstrip('/')
            v1_base_url = f"{clean_base}/v1"
            
            models_url = f"{v1_base_url}/models"
            headers = {"Authorization": f"Bearer {request.api_key}"}
            
            async with httpx.AsyncClient() as client:
                logger.info(f"Fetching models from normalized URL: {models_url}")
                response = await client.get(models_url, headers=headers, timeout=30)
                response.raise_for_status()
                models_data = response.json()
            logger.info("Successfully fetched models data.")

            if 'data' not in models_data or not isinstance(models_data['data'], list):
                logger.error("Invalid response format from model provider.")
                yield f"data: ERROR=Invalid response format from model provider.\n\n"
                return

            models_list = models_data['data']

            # Filter models based on request parameters
            if request.filter_keyword and request.filter_mode != 'None':
                keyword = request.filter_keyword.lower()
                mode = request.filter_mode
                
                if mode == 'Include':
                    models_list = [m for m in models_list if m.get('id') and keyword in m.get('id').lower()]
                elif mode == 'Exclude':
                    models_list = [m for m in models_list if m.get('id') and keyword not in m.get('id').lower()]

            total_models = len(models_list)
            logger.info(f"Found {total_models} models in the response.")
            yield f"data: TOTAL={total_models}\n\n"
            await asyncio.sleep(0.1)

            # Keep track of models returned by the provider
            fetched_model_ids = {m.get('id') for m in models_list if m.get('id')}
            target_endpoint = f"{v1_base_url}/chat/completions"

            # Requirement: If a model exists in DB for this endpoint but NOT in the fetched list, mark as inactive
            db_existing_models = db.query(models.ApiProvider).filter(
                models.ApiProvider.api_endpoint == target_endpoint,
                models.ApiProvider.api_key == request.api_key
            ).all()

            deactivated_count = 0
            for db_p in db_existing_models:
                if db_p.model not in fetched_model_ids and db_p.is_active:
                    db_p.is_active = False
                    deactivated_count += 1
            
            if deactivated_count > 0:
                db.commit()
                logger.info(f"Deactivated {deactivated_count} models that are no longer available at {target_endpoint}")

            imported_count = 0
            for i, model_info in enumerate(models_list):
                model_id = model_info.get('id')
                if not model_id:
                    logger.warning(f"Skipping model at index {i} due to missing 'id'.")
                    continue

                # Check for duplicates in a sync way
                # Requirement: Alias is used directly as name, no model name combination
                formatted_name = request.alias if request.alias else model_id.replace('/', '.')

                # Requirement: Use api_endpoint + api_key + model together as uniqueness check
                # Some providers might need the model in the path, but standard OpenAI is /chat/completions
                target_endpoint = f"{v1_base_url}/chat/completions"
                
                existing_provider = db.query(models.ApiProvider).filter(
                    models.ApiProvider.api_endpoint == target_endpoint,
                    models.ApiProvider.api_key == request.api_key,
                    models.ApiProvider.model == model_id
                ).first()
                
                if existing_provider:
                    logger.info(f"Provider with endpoint={target_endpoint}, key={request.api_key[:5]}..., model={model_id} already exists. Skipping.")
                    imported_count += 1
                    yield f"data: PROGRESS={imported_count}\n\n"
                    continue

                provider_data = schemas.ApiProviderCreate(
                    name=formatted_name,
                    api_endpoint=target_endpoint,
                    api_key=request.api_key,
                    model=model_id,
                    price_per_million_tokens=0,
                    input_price_per_million_tokens=0,
                    output_price_per_million_tokens=0,
                    type=request.default_type,
                    usage_level=3,
                    is_active=True
                )
                
                new_provider = crud.create_provider(db, provider_data)
                imported_count += 1
                logger.info(f"Successfully imported and created provider (ID: {new_provider.id}) for model '{model_id}'.")
                yield f"data: PROGRESS={imported_count}\n\n"
                await asyncio.sleep(0.05) # Small delay to allow UI to update

            final_message = f"Successfully imported {imported_count} new models."
            logger.info(f"Import process finished. {final_message}")
            yield f"data: DONE={final_message}\n\n"

        except httpx.ConnectError as e:
            logger.error(f"Connection failed for {e.request.url}: {e}")
            yield f"data: ERROR=Connection Failed: Could not connect to the Base URL. Please check the URL and your network connection.\n\n"
        except httpx.RequestError as e:
            logger.error(f"Could not fetch models from provider: {e}")
            yield f"data: ERROR=Could not fetch models from provider: {e}\n\n"
        except Exception as e:
            logger.error(f"An unexpected error occurred during model import: {e}")
            yield f"data: ERROR=An unexpected error occurred: {e}\n\n"
        finally:
            db.close()

    return StreamingResponse(progress_stream(), media_type="text/event-stream")

@proxy_router.get("/v1/models", response_model=schemas.ModelListResponse)
def get_models_list(db: Session = Depends(get_db), api_key: models.APIKey = Depends(get_api_key_from_bearer)):
    """
    Returns a list of models available to the authenticated API key,
    formatted to be compatible with the OpenAI API.
    """
    # Per user request, this endpoint should return the names of the groups the key has access to.
    authorized_groups = {group.name for group in api_key.groups}

    data = [schemas.ModelResponse(id=group_name) for group_name in sorted(list(authorized_groups))]
    
    return schemas.ModelListResponse(data=data)

@proxy_router.post("/v1/responses")
async def responses_proxy(request: schemas.ChatRequest, db: Session = Depends(get_db), api_key: models.APIKey = Depends(get_api_key_from_bearer)):
    """
    OpenAI compatible endpoint /v1/responses.
    Internally redirects to /v1/chat/completions logic.
    """
    return await chat(request, db, api_key)

@proxy_router.post("/v1/messages")
async def messages_proxy(request: schemas.AnthropicChatRequest, db: Session = Depends(get_db), api_key: models.APIKey = Depends(get_api_key_from_anthropic_header)):
    """
    Anthropic compatible endpoint /v1/messages.
    Converts Anthropic request to OpenAI format, calls internal chat logic,
    and converts back to Anthropic response.
    """
    # 1. Convert Anthropic request to OpenAI-style ChatRequest
    openai_messages = []
    
    # Handle optional system prompt (can be string or list of blocks)
    if request.system:
        system_content = ""
        if isinstance(request.system, str):
            system_content = request.system
        else:
            system_content = " ".join([block.text for block in request.system if block.type == "text" and block.text])
        
        if system_content:
            openai_messages.append(schemas.ChatMessage(role="system", content=system_content))
    
    for msg in request.messages:
        content_str = ""
        if isinstance(msg.content, str):
            content_str = msg.content
        else:
            # Concatenate text blocks
            content_str = " ".join([block.text for block in msg.content if block.type == "text"])
        
        openai_messages.append(schemas.ChatMessage(role=msg.role, content=content_str))

    chat_request = schemas.ChatRequest(
        messages=openai_messages,
        model=request.model,
        stream=request.stream
    )

    # 2. Call internal chat logic
    if request.stream:
        # Basic OpenAI to Anthropic stream transformer
        async def anthropic_stream_generator():
            openai_response = await chat(chat_request, db, api_key)
            if not isinstance(openai_response, StreamingResponse):
                yield f"data: {json.dumps({'type': 'error', 'error': {'type': 'api_error', 'message': 'Expected streaming response'}})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'message_start', 'message': {'id': 'msg_start', 'type': 'message', 'role': 'assistant', 'content': [], 'model': request.model, 'usage': {'input_tokens': 0, 'output_tokens': 0}}})}\n\n"
            yield f"data: {json.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}})}\n\n"

            async for line in openai_response.body_iterator:
                if isinstance(line, bytes):
                    line = line.decode('utf-8')
                
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        if "content" in delta:
                            content = delta["content"]
                            # Basic filtering of <think> tags in stream
                            content = utils.filter_think_tag_from_chunk(content)
                            if content:
                                yield f"data: {json.dumps({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': content}})}\n\n"
                    except:
                        continue

            yield f"data: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"
            yield f"data: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': 'end_turn', 'stop_sequence': None}, 'usage': {'output_tokens': 0}})}\n\n"
            yield f"data: {json.dumps({'type': 'message_stop'})}\n\n"

        return StreamingResponse(anthropic_stream_generator(), media_type="text/event-stream")

    response_json = await chat(chat_request, db, api_key)
    
    # 3. Convert OpenAI response back to Anthropic response
    # response_json is the dict returned by chat()
    
    choices = response_json.get("choices", [])
    assistant_message = ""
    if choices:
        assistant_message = choices[0].get("message", {}).get("content", "")

    usage = response_json.get("usage", {})
    
    anthropic_response = schemas.AnthropicChatResponse(
        id=response_json.get("id", "msg_" + response_json.get("id", "none")),
        role="assistant",
        content=[schemas.AnthropicContent(type="text", text=assistant_message)],
        model=response_json.get("model", request.model),
        usage=schemas.AnthropicUsage(
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0)
        )
    )

    return anthropic_response

@proxy_router.post("/v1/completions")
async def completions(request: schemas.CompletionRequest, db: Session = Depends(get_db), api_key: models.APIKey = Depends(get_api_key_from_bearer)):
    """
    OpenAI legacy completions API.
    """
    # Use chat logic but wrap/unwrap as needed or just forward if provider supports it.
    # For now, we reuse select_provider logic.
    excluded_provider_ids = []
    while True:
        # Create a dummy ChatRequest for provider selection
        dummy_request = schemas.ChatRequest(model=request.model, messages=[], stream=request.stream)
        provider, group_id = smart_router.select_provider(db, dummy_request, excluded_provider_ids=excluded_provider_ids)
        if not provider:
            raise HTTPException(status_code=503, detail="All suitable providers failed or are unavailable.")

        start_time = time.time()
        if group_id:
            crud.increment_active_calls(db, provider.id, group_id)
        try:
            api_url = provider.api_endpoint.replace("/chat/completions", "/completions") if "/chat/completions" in provider.api_endpoint else provider.api_endpoint
            headers = {"Authorization": f"Bearer {provider.api_key}", "Content-Type": "application/json"}
            payload = request.dict(exclude_unset=True)
            payload['model'] = provider.model
            
            async with httpx.AsyncClient(timeout=300) as client:
                response = await client.post(api_url, headers=headers, json=payload)
                response.raise_for_status()
            
            response_json = response.json()
            # Log success
            crud.create_call_log(db, schemas.CallLogCreate(
                provider_id=provider.id, api_key_id=api_key.id, response_timestamp=datetime.now(TAIPEI_TZ), is_success=True,
                status_code=response.status_code, response_time_ms=int((time.time() - start_time) * 1000),
                response_body=json.dumps(response_json)
            ))
            return response_json
        except Exception as e:
            excluded_provider_ids.append(provider.id)
            continue
        finally:
            if group_id:
                crud.decrement_active_calls(db, provider.id, group_id)

@proxy_router.post("/v1/embeddings")
async def embeddings(request: schemas.EmbeddingRequest, db: Session = Depends(get_db), api_key: models.APIKey = Depends(get_api_key_from_bearer)):
    """
    OpenAI Embeddings API.
    """
    excluded_provider_ids = []
    while True:
        dummy_request = schemas.ChatRequest(model=request.model, messages=[])
        provider, group_id = smart_router.select_provider(db, dummy_request, excluded_provider_ids=excluded_provider_ids)
        if not provider:
            raise HTTPException(status_code=503, detail="No provider found for embeddings.")

        start_time = time.time()
        if group_id:
            crud.increment_active_calls(db, provider.id, group_id)
        try:
            api_url = provider.api_endpoint.replace("/chat/completions", "/embeddings") if "/chat/completions" in provider.api_endpoint else provider.api_endpoint
            headers = {"Authorization": f"Bearer {provider.api_key}", "Content-Type": "application/json"}
            payload = request.dict(exclude_unset=True)
            payload['model'] = provider.model
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(api_url, headers=headers, json=payload)
                response.raise_for_status()
            
            return response.json()
        except Exception as e:
            excluded_provider_ids.append(provider.id)
            continue
        finally:
            if group_id:
                crud.decrement_active_calls(db, provider.id, group_id)

# --- Management APIs for Logs, Keys, Keywords, Settings ---

@router.get("/logs/", response_model=schemas.CallLogResponse)
def read_call_logs(skip: int = 0, limit: int = 100, filter_success: Optional[bool] = None, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    # 這裡返回的 logs 將會根據 schemas.CallLogSummary 進行序列化
    # 確保不包含任何 details 或 body 欄位，從而避免 SQLAlchemy 觸發延遲加載
    logs = crud.get_call_logs(db, skip=skip, limit=limit, filter_success=filter_success)
    total = crud.count_call_logs(db, filter_success=filter_success)
    return {"items": logs, "total": total}

@router.get("/logs/{log_id}", response_model=schemas.CallLog)
def read_call_log(log_id: int, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    db_log = crud.get_call_log(db, log_id=log_id)
    if db_log is None:
        raise HTTPException(status_code=404, detail="Log not found")
    
    # 為了兼容性，如果 details 存在，將 body 合併到主對象中
    # 如果 details 不存在，則自動使用 CallLog 表中可能存在的舊數據
    if db_log.details:
        db_log.request_body = db_log.details.request_body
        db_log.response_body = db_log.details.response_body
        
    # 避免在 response 中重複發送 details 對象 (因為 body 已經提到頂層了)
    # 這樣可以減少傳輸體積
    db_log.details = None
        
    return db_log

@router.get("/keys/", response_model=List[schemas.APIKey])
def read_api_keys(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    return crud.get_api_keys(db, skip=skip, limit=limit)

@router.post("/keys/", response_model=schemas.APIKey)
def create_api_key(api_key: schemas.APIKeyCreate, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    return crud.create_api_key(db, api_key)

@router.patch("/keys/{key_id}", response_model=schemas.APIKey)
def update_api_key(key_id: int, api_key: schemas.APIKeyUpdate, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    return crud.update_api_key(db, key_id, api_key)

@router.delete("/keys/{key_id}")
def delete_api_key(key_id: int, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    crud.delete_api_key(db, key_id)
    return {"detail": "API key deleted"}

@router.get("/keywords/", response_model=List[schemas.ErrorKeyword])
def read_error_keywords(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    return crud.get_error_keywords(db, skip=skip, limit=limit)

@router.post("/keywords/", response_model=schemas.ErrorKeyword)
def create_error_keyword(keyword: schemas.ErrorKeywordCreate, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    return crud.create_error_keyword(db, keyword)

@router.patch("/keywords/{keyword_id}", response_model=schemas.ErrorKeyword)
def update_error_keyword(keyword_id: int, keyword_data: dict, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    return crud.update_error_keyword(db, keyword_id, keyword_data)

@router.delete("/keywords/{keyword_id}")
def delete_error_keyword(keyword_id: int, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    crud.delete_error_keyword(db, keyword_id)
    return {"detail": "Keyword deleted"}

@router.get("/settings/{key}", response_model=schemas.Setting)
def get_setting(key: str, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    setting = crud.get_setting(db, key)
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting

@router.post("/settings/", response_model=schemas.Setting)
def update_setting(setting: schemas.SettingCreate, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    return crud.update_setting(db, setting.key, setting.value)

@proxy_router.post("/v1/images/generations")
async def image_generation(request: schemas.ImageGenerationRequest, db: Session = Depends(get_db), api_key: models.APIKey = Depends(get_api_key_from_bearer)):
    """
    OpenAI Image Generation API.
    """
    excluded_provider_ids = []
    while True:
        # Use 'dall-e-3' or similar if model not specified
        model_name = request.model or "dall-e-3"
        dummy_request = schemas.ChatRequest(model=model_name, messages=[])
        provider, group_id = smart_router.select_provider(db, dummy_request, excluded_provider_ids=excluded_provider_ids)
        if not provider:
            raise HTTPException(status_code=503, detail="No provider found for image generation.")

        try:
            api_url = provider.api_endpoint.replace("/chat/completions", "/images/generations") if "/chat/completions" in provider.api_endpoint else provider.api_endpoint
            headers = {"Authorization": f"Bearer {provider.api_key}", "Content-Type": "application/json"}
            payload = request.dict(exclude_unset=True)
            payload['model'] = provider.model
            
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(api_url, headers=headers, json=payload)
                response.raise_for_status()
            
            return response.json()
        except Exception as e:
            excluded_provider_ids.append(provider.id)
            continue
        finally:
            if group_id:
                crud.decrement_active_calls(db, provider.id, group_id)

# --- Remote Public Management APIs (Auth via API Key) ---

@router.get("/remote/status")
def get_remote_status(api_key: str, db: Session = Depends(get_db)):
    db_api_key = crud.get_api_key_by_key(db, api_key)
    if not db_api_key or not db_api_key.is_active:
        raise HTTPException(status_code=401, detail="Invalid or inactive API Key")
    
    results = []
    for group in db_api_key.groups:
        # Get associations for this group, sorted by priority
        associations = db.query(models.ProviderGroupAssociation).filter_by(group_id=group.id).order_by(models.ProviderGroupAssociation.priority.asc()).all()
        
        provider_list = []
        for assoc in associations:
            provider = crud.get_provider(db, assoc.provider_id)
            if provider:
                provider_list.append({
                    "id": provider.id,
                    "name": provider.name,
                    "model": provider.model,
                    "priority": assoc.priority
                })
        
        results.append({
            "id": group.id,
            "name": group.name,
            "providers": provider_list
        })
    return results

@router.post("/remote/move-to-top")
def remote_move_to_top(api_key: str, group_id: int, provider_id: int, db: Session = Depends(get_db)):
    db_api_key = crud.get_api_key_by_key(db, api_key)
    if not db_api_key or not db_api_key.is_active:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    # Check if this group belongs to the API key
    if group_id not in [g.id for g in db_api_key.groups]:
        raise HTTPException(status_code=403, detail="Group not authorized for this API Key")
    
    # Get all current associations for the group
    associations = db.query(models.ProviderGroupAssociation).filter_by(group_id=group_id).order_by(models.ProviderGroupAssociation.priority.asc()).all()
    pids = [a.provider_id for a in associations]
    
    if provider_id not in pids:
        raise HTTPException(status_code=404, detail="Provider not found in this group")
    
    # Re-order: move provider_id to index 0
    pids.remove(provider_id)
    pids.insert(0, provider_id)
    
    # Update priorities in DB
    for idx, pid in enumerate(pids):
        crud.add_provider_to_group(db, provider_id=pid, group_id=group_id, priority=idx+1)
    
    db.commit()
    return {"detail": "Priority updated successfully"}

@router.post("/remote/update-order")
def remote_update_order(api_key: str, group_id: int, provider_ids: List[int], db: Session = Depends(get_db)):
    db_api_key = crud.get_api_key_by_key(db, api_key)
    if not db_api_key or not db_api_key.is_active:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    if group_id not in [g.id for g in db_api_key.groups]:
        raise HTTPException(status_code=403, detail="Group not authorized")
    
    # Update all provided IDs with their new sequential priority
    for idx, pid in enumerate(provider_ids):
        crud.add_provider_to_group(db, provider_id=pid, group_id=group_id, priority=idx+1)
    
    db.commit()
    return {"detail": "Order updated successfully"}
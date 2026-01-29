from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List
import asyncio
import json
from . import crud, models, schemas, router as smart_router
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

router = APIRouter()

# Security scheme
auth_scheme = HTTPBearer()

# Dependency to get and validate API key
def get_api_key_from_bearer(
    db: Session = Depends(get_db),
    authorization: HTTPAuthorizationCredentials = Depends(auth_scheme)
) -> models.APIKey:
    """
    Validates the API key from the 'Authorization: Bearer <key>' header.
    """
    api_key_str = authorization.credentials
    if not api_key_str:
        raise HTTPException(
            status_code=401,
            detail={"error": {"message": "Incorrect API key provided or key has been revoked.", "type": "invalid_request_error"}},
            headers={"WWW-Authenticate": "Bearer"},
        )

    db_api_key = crud.get_api_key_by_key(db, key=api_key_str)

    if not db_api_key or not db_api_key.is_active:
        raise HTTPException(
            status_code=401,
            detail={"error": {"message": "Incorrect API key provided or key has been revoked.", "type": "invalid_request_error"}},
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last used timestamp
    crud.update_api_key_last_used(db, db_api_key.id)
    
    return db_api_key


@router.post("/api/providers/", response_model=schemas.ApiProvider)
def create_provider(provider: schemas.ApiProviderCreate, db: Session = Depends(get_db)):
    return crud.create_provider(db=db, provider=provider)

@router.get("/api/providers/", response_model=List[schemas.ApiProvider])
def read_providers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    providers = crud.get_providers(db, skip=skip, limit=limit)
    return providers

@router.get("/api/providers/{provider_id}", response_model=schemas.ApiProvider)
def read_provider(provider_id: int, db: Session = Depends(get_db)):
    db_provider = crud.get_provider(db, provider_id=provider_id)
    if db_provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    return db_provider

# Endpoints for Groups
@router.post("/api/groups/", response_model=schemas.Group)
def create_group(group: schemas.GroupCreate, db: Session = Depends(get_db)):
    db_group = crud.get_group_by_name(db, name=group.name)
    if db_group:
        raise HTTPException(status_code=400, detail="Group with this name already exists")
    return crud.create_group(db=db, group=group)

@router.get("/api/groups/", response_model=List[schemas.Group])
def read_groups(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    groups = crud.get_groups(db, skip=skip, limit=limit)
    return groups

@router.post("/api/groups/{group_id}/providers/{provider_id}", response_model=schemas.ApiProvider)
def add_provider_to_group(group_id: int, provider_id: int, db: Session = Depends(get_db)):
    provider = crud.add_provider_to_group(db, provider_id=provider_id, group_id=group_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider or Group not found")
    return provider

@router.delete("/api/groups/{group_id}/providers/{provider_id}", response_model=schemas.ApiProvider)
def remove_provider_from_group(group_id: int, provider_id: int, db: Session = Depends(get_db)):
    provider = crud.remove_provider_from_group(db, provider_id=provider_id, group_id=group_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider or Group not found, or provider not in group")
    return provider

@router.post("/v1/chat/completions")
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
        # Try to find a group that ends with /requested_model
        for name in authorized_group_names:
            if name.endswith(f"/{request.model}"):
                matched_group_name = name
                logger.info(f"Mapping requested model '{request.model}' to authorized group '{matched_group_name}'")
                break
    
    if not matched_group_name:
        group_names = ", ".join(list(authorized_group_names))
        logger.warning(f"API Key {api_key.key[:5]}... not authorized for group '{request.model}'. Authorized groups: [{group_names}]")
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
            while True:
                # The select_provider function now looks up providers by the group name in request.model
                provider = smart_router.select_provider(db, request, excluded_provider_ids=excluded_provider_ids)
                if not provider:
                    logger.error("All providers failed for streaming request.")
                    error_message = {"error": {"message": "All suitable providers failed or are unavailable."}}
                    yield f"data: {json.dumps(error_message)}\n\n"
                    return

                logger.info(f"Streaming attempt with provider: {provider.name} (ID: {provider.id})")
                start_time = time.time()
                full_response_text = ""
                
                try:
                    api_url = provider.api_endpoint
                    api_key = provider.api_key
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    payload = request.dict(exclude_unset=True)
                    payload['model'] = provider.model
                    payload['stream'] = True
                    failure_keywords = [kw.keyword.lower() for kw in crud.get_all_active_error_keywords(db)]

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
                                
                                crud.create_call_log(db, schemas.CallLogCreate(
                                    provider_id=provider.id, response_timestamp=datetime.now(TAIPEI_TZ), is_success=False,
                                    status_code=status_code, response_time_ms=int((end_time - start_time) * 1000), error_message=error_message,
                                    response_body=error_message
                                ))
                                
                                excluded_provider_ids.append(provider.id)
                                logger.info(f"Adding provider ID {provider.id} to exclusion list. Retrying stream.")
                                continue

                            async for chunk in response.aiter_bytes():
                                chunk_text = chunk.decode('utf-8', errors='ignore').lower()
                                full_response_text += chunk_text
                                for keyword in failure_keywords:
                                    if keyword in full_response_text:
                                        raise ValueError(f"Failure keyword found: '{keyword}'")
                                yield chunk
                            
                            end_time = time.time()
                            crud.create_call_log(db, schemas.CallLogCreate(
                                provider_id=provider.id, response_timestamp=datetime.now(TAIPEI_TZ), is_success=True,
                                status_code=response.status_code, response_time_ms=int((end_time - start_time) * 1000),
                                error_message="Usage data not available for streaming responses.",
                                response_body=full_response_text
                            ))
                            logger.info(f"--- Streaming Response Finished (Provider ID: {provider.id}) ---")
                            logger.info(f"Full response text: {full_response_text[:500]}..." if len(full_response_text) > 500 else f"Full response text: {full_response_text}")
                            break

                except (httpx.RequestError, ValueError) as e:
                    end_time = time.time()
                    status_code = 503
                    logger.warning(f"Provider {provider.name} (ID: {provider.id}) failed during stream: {e}")
                    
                    crud.create_call_log(db, schemas.CallLogCreate(
                        provider_id=provider.id, response_timestamp=datetime.now(TAIPEI_TZ), is_success=False,
                        status_code=status_code, response_time_ms=int((end_time - start_time) * 1000), error_message=str(e),
                        response_body=full_response_text
                    ))
                    
                    excluded_provider_ids.append(provider.id)
                    logger.info(f"Adding provider ID {provider.id} to exclusion list. Retrying stream.")
                    continue

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    # --- Non-Streaming Response Logic (remains the same) ---
    else:
        excluded_provider_ids = []
        while True:
            # The select_provider function now looks up providers by the group name in request.model
            provider = smart_router.select_provider(db, request, excluded_provider_ids=excluded_provider_ids)
            if not provider:
                raise HTTPException(status_code=503, detail="All suitable providers failed or are unavailable.")

            logger.info(f"Non-streaming attempt with provider: {provider.name} (ID: {provider.id})")
            start_time = time.time()
            
            try:
                api_url = provider.api_endpoint
                api_key = provider.api_key
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                payload = request.dict(exclude_unset=True)
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
                crud.create_call_log(db, schemas.CallLogCreate(
                    provider_id=provider.id, response_timestamp=datetime.now(TAIPEI_TZ), is_success=True,
                    status_code=response.status_code, response_time_ms=int((end_time - start_time) * 1000),
                    prompt_tokens=usage.get("prompt_tokens"), completion_tokens=usage.get("completion_tokens"),
                    total_tokens=usage.get("total_tokens"), cost=cost,
                    response_body=json.dumps(response_json)
                ))
                logger.info(f"--- Non-streaming Response Success (Provider ID: {provider.id}) ---")
                logger.info(f"Response JSON: {json.dumps(response_json)}")
                return response_json

            except (httpx.RequestError, ValueError) as e:
                end_time = time.time()
                status_code = e.response.status_code if hasattr(e, 'response') and e.response is not None else 503
                response_body = e.response.text if hasattr(e, 'response') and e.response is not None else None
                
                if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 429:
                    logger.warning(f"Provider {provider.name} (ID: {provider.id}) failed with 429 Too Many Requests. Marking as failed for this request and retrying with another provider.")
                else:
                    logger.warning(f"Provider {provider.name} (ID: {provider.id}) failed: {e}")
                
                crud.create_call_log(db, schemas.CallLogCreate(
                    provider_id=provider.id, response_timestamp=datetime.now(TAIPEI_TZ), is_success=False,
                    status_code=status_code, response_time_ms=int((end_time - start_time) * 1000), error_message=str(e),
                    response_body=response_body
                ))

                error_str = str(e).lower()
                if "insufficient" in error_str and "quota" in error_str:
                    logger.warning(f"Provider {provider.name} (ID: {provider.id}) disabled due to insufficient quota.")
                    provider.is_active = False
                    db.commit()
                    crud.create_maintenance_error(db=db, provider_id=provider.id, error_type="INSUFFICIENT_QUOTA", details=str(e))

                excluded_provider_ids.append(provider.id)
                logger.info(f"Adding provider ID {provider.id} to exclusion list. Retrying.")
                continue

@router.post("/api/import-models/")
async def import_models(request: schemas.ModelImportRequest):
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
                target_endpoint = f"{v1_base_url}/chat/completions"
                existing_provider = db.query(models.ApiProvider).filter(
                    models.ApiProvider.api_endpoint == target_endpoint,
                    models.ApiProvider.api_key == request.api_key,
                    models.ApiProvider.model == model_id
                ).first()
                
                if existing_provider:
                    logger.info(f"Provider with endpoint={target_endpoint}, key={request.api_key[:5]}..., model={model_id} already exists. Skipping.")
                    continue

                provider_data = schemas.ApiProviderCreate(
                    name=formatted_name,
                    api_endpoint=target_endpoint,
                    api_key=request.api_key,
                    model=model_id,
                    price_per_million_tokens=0,
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

@router.get("/v1/models", response_model=schemas.ModelListResponse)
def get_models_list(db: Session = Depends(get_db), api_key: models.APIKey = Depends(get_api_key_from_bearer)):
    """
    Returns a list of models available to the authenticated API key,
    formatted to be compatible with the OpenAI API.
    """
    # Per user request, this endpoint should return the names of the groups the key has access to.
    authorized_groups = {group.name for group in api_key.groups}

    data = [schemas.ModelResponse(id=group_name) for group_name in sorted(list(authorized_groups))]
    
    return schemas.ModelListResponse(data=data)
from sqlalchemy.orm import Session
from typing import List
from . import models, schemas
from sqlalchemy.dialects.sqlite import insert

def get_provider(db: Session, provider_id: int):
    return db.query(models.ApiProvider).filter(models.ApiProvider.id == provider_id).first()

def get_provider_by_name(db: Session, name: str):
    return db.query(models.ApiProvider).filter(models.ApiProvider.name == name).first()

def get_providers(db: Session, skip: int = None, limit: int = None, name_filter: str = None, endpoint_filter: str = None):
    from sqlalchemy import or_
    query = db.query(models.ApiProvider)
    if name_filter:
        query = query.filter(or_(
            models.ApiProvider.name.contains(name_filter),
            models.ApiProvider.model.contains(name_filter)
        ))
    if endpoint_filter:
        query = query.filter(models.ApiProvider.api_endpoint.contains(endpoint_filter))
    
    if skip is not None:
        query = query.offset(skip)
    if limit is not None:
        query = query.limit(limit)
        
    return query.all()

def count_providers(db: Session, name_filter: str = None, endpoint_filter: str = None):
    from sqlalchemy import or_
    query = db.query(models.ApiProvider)
    if name_filter:
        query = query.filter(or_(
            models.ApiProvider.name.contains(name_filter),
            models.ApiProvider.model.contains(name_filter)
        ))
    if endpoint_filter:
        query = query.filter(models.ApiProvider.api_endpoint.contains(endpoint_filter))
    return query.count()

def get_unique_endpoints(db: Session):
    return db.query(models.ApiProvider.api_endpoint).distinct().all()

def get_keys_for_endpoint(db: Session, endpoint: str):
    return db.query(models.ApiProvider.api_key).filter(models.ApiProvider.api_endpoint == endpoint).distinct().all()

def get_all_unique_keys(db: Session):
    return db.query(models.ApiProvider.api_key).distinct().all()

def create_provider(db: Session, provider: schemas.ApiProviderCreate):
    provider_data = provider.dict()
    if 'usage_level' in provider_data:
        del provider_data['usage_level']
    db_provider = models.ApiProvider(**provider_data)
    db.add(db_provider)
    db.commit()
    db.refresh(db_provider)
    return db_provider

def update_provider(db: Session, provider_id: int, provider_data: dict):
    # Only allow updating actual column fields, filter out relationships and non-column keys
    allowed_fields = {
        'name', 'api_endpoint', 'api_key', 'model',
        'price_per_million_tokens', 'input_price_per_million_tokens', 'output_price_per_million_tokens',
        'type', 'is_active'
    }
    filtered_data = {k: v for k, v in provider_data.items() if k in allowed_fields}
    if not filtered_data:
        return get_provider(db, provider_id)
    db.query(models.ApiProvider).filter(models.ApiProvider.id == provider_id).update(filtered_data)
    db.commit()
    return get_provider(db, provider_id)

def delete_provider(db: Session, provider_id: int):
    db_provider = get_provider(db, provider_id)
    if db_provider:
        db.delete(db_provider)
        db.commit()
    return db_provider

def delete_providers_by_key(db: Session, api_key: str):
    # Find all providers with the given API key
    providers_to_delete = db.query(models.ApiProvider).filter(
        models.ApiProvider.api_key == api_key
    ).all()

    if not providers_to_delete:
        return 0

    provider_ids = [p.id for p in providers_to_delete]

    # Delete associated call logs
    db.query(models.CallLog).filter(
        models.CallLog.provider_id.in_(provider_ids)
    ).delete(synchronize_session=False)

    # Delete associations from groups
    db.query(models.ProviderGroupAssociation).filter(
        models.ProviderGroupAssociation.provider_id.in_(provider_ids)
    ).delete(synchronize_session=False)

    # Delete the providers themselves
    deleted_count = len(provider_ids)
    for provider in providers_to_delete:
        db.delete(provider)

    db.commit()
    return deleted_count

def get_call_logs(db: Session, skip: int = 0, limit: int = 100, filter_success: bool | None = None):
    from sqlalchemy.orm import joinedload, load_only
    # 進一步優化查詢性能：
    # 1. 使用 load_only 只查詢列表顯示所需的欄位，徹底排除遺留的大文本 Body
    # 2. 同時使用 joinedload 預加載 Provider 和 API Key，並限制它們加載的欄位 (避免 N+1)
    query = db.query(models.CallLog).options(
        load_only(
            models.CallLog.id,
            models.CallLog.provider_id,
            models.CallLog.api_key_id,
            models.CallLog.request_timestamp,
            models.CallLog.is_success,
            models.CallLog.status_code,
            models.CallLog.response_time_ms,
            models.CallLog.prompt_tokens,
            models.CallLog.completion_tokens,
            models.CallLog.total_tokens,
            models.CallLog.cost,
            models.CallLog.error_message
        ),
        joinedload(models.CallLog.provider).load_only(
            models.ApiProvider.id,
            models.ApiProvider.name,
            models.ApiProvider.model,
            models.ApiProvider.api_endpoint
        ),
        joinedload(models.CallLog.api_key).load_only(
            models.APIKey.id,
            models.APIKey.key
        )
    ).order_by(models.CallLog.id.desc())
    if filter_success is not None:
        query = query.filter(models.CallLog.is_success == filter_success)
    return query.offset(skip).limit(limit).all()

def get_call_log(db: Session, log_id: int):
    from sqlalchemy.orm import joinedload
    return db.query(models.CallLog).options(
        joinedload(models.CallLog.details),
        joinedload(models.CallLog.provider),
        joinedload(models.CallLog.api_key)
    ).filter(models.CallLog.id == log_id).first()

def count_call_logs(db: Session, filter_success: bool | None = None):
    query = db.query(models.CallLog)
    if filter_success is not None:
        query = query.filter(models.CallLog.is_success == filter_success)
    return query.count()

def get_error_keywords(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.ErrorMaintenance).order_by(models.ErrorMaintenance.id.desc()).offset(skip).limit(limit).all()

def create_call_log(db: Session, log: schemas.CallLogCreate):
    try:
        if log.provider_id:
            provider = get_provider(db, log.provider_id)
            if provider:
                provider.total_calls += 1
            if log.is_success:
                provider.successful_calls += 1

        # Extract body data to save in separate table via relationship
        log_data = log.dict()
        req_body = log_data.pop('request_body', None)
        resp_body = log_data.pop('response_body', None)

        db_log = models.CallLog(**log_data)
        
        # Create detail record associated with the log
        # SQLAlchemy will automatically link the IDs
        db_log.details = models.CallLogDetail(
            request_body=req_body,
            response_body=resp_body
        )
        
        db.add(db_log)
        db.commit()
        db.refresh(db_log)
        return db_log
    except Exception as e:
        db.rollback()
        raise e

def get_error_keyword(db: Session, keyword_id: int):
    return db.query(models.ErrorMaintenance).filter(models.ErrorMaintenance.id == keyword_id).first()

def get_all_active_error_keywords(db: Session):
    return db.query(models.ErrorMaintenance).filter(models.ErrorMaintenance.is_active == True).all()

def create_error_keyword(db: Session, keyword: schemas.ErrorKeywordCreate):
    db_keyword = models.ErrorMaintenance(**keyword.dict())
    db.add(db_keyword)
    db.commit()
    db.refresh(db_keyword)
    return db_keyword

def update_error_keyword(db: Session, keyword_id: int, keyword_data: dict):
    db.query(models.ErrorMaintenance).filter(models.ErrorMaintenance.id == keyword_id).update(keyword_data)
    db.commit()
    return get_error_keyword(db, keyword_id)

def delete_error_keyword(db: Session, keyword_id: int):
    db_keyword = get_error_keyword(db, keyword_id)
    if db_keyword:
        db.delete(db_keyword)
        db.commit()
    return db_keyword

def update_keyword_trigger_time(db: Session, keyword_id: int):
    from datetime import datetime
    import pytz

    TAIPEI_TZ = pytz.timezone('Asia/Taipei')
    db.query(models.ErrorMaintenance).filter(models.ErrorMaintenance.id == keyword_id).update({"last_triggered": datetime.now(TAIPEI_TZ)})
    db.commit()


from datetime import datetime, timedelta
import pytz

TAIPEI_TZ = pytz.timezone('Asia/Taipei')

def count_recent_failures_for_provider(db: Session, provider_id: int, minutes: int = 5) -> int:
    """Counts the number of failed calls for a specific provider within the last N minutes."""
    time_threshold = datetime.now(TAIPEI_TZ) - timedelta(minutes=minutes)
    failure_count = db.query(models.CallLog).filter(
        models.CallLog.provider_id == provider_id,
        models.CallLog.is_success == False,
        models.CallLog.request_timestamp >= time_threshold
    ).count()
    return failure_count

# CRUD for Groups
def get_group(db: Session, group_id: int):
    return db.query(models.Group).filter(models.Group.id == group_id).first()

def get_group_by_name(db: Session, name: str):
    return db.query(models.Group).filter(models.Group.name == name).first()

def get_groups(db: Session, skip: int = 0, limit: int = 100):
    from sqlalchemy.orm import joinedload
    # 使用 joinedload 一次性加載關聯的 ProviderGroupAssociation 和 ApiProvider
    groups = db.query(models.Group).options(
        joinedload(models.Group.providers)
    ).offset(skip).limit(limit).all()

    # 由於 SQLAlchemy 的多對多 relationship 直接返回 ApiProvider，
    # 而我們需要從 association 表中獲取 'priority' 字段，
    # 這裡我們需要優化加載邏輯。
    
    # 重新查詢以包含關聯表數據
    for group in groups:
        associations = db.query(models.ProviderGroupAssociation).options(
            joinedload(models.ProviderGroupAssociation.provider)
        ).filter_by(group_id=group.id).all()
        
        provider_list = []
        for assoc in associations:
            if assoc.provider:
                # 為了避免 Identity Map 污染（多個組共享同一個 Provider 實例時 priority 被互相覆蓋），
                # 我們必須確保每個組擁有自己的 Provider 數據副本。
                # 這裡最簡單的方法是從 DB 對象創建一個新的臨時對象。
                p = models.ApiProvider(
                    id=assoc.provider.id,
                    name=assoc.provider.name,
                    api_endpoint=assoc.provider.api_endpoint,
                    api_key=assoc.provider.api_key,
                    model=assoc.provider.model,
                    price_per_million_tokens=assoc.provider.price_per_million_tokens,
                    input_price_per_million_tokens=assoc.provider.input_price_per_million_tokens,
                    output_price_per_million_tokens=assoc.provider.output_price_per_million_tokens,
                    type=assoc.provider.type,
                    is_active=assoc.provider.is_active,
                    total_calls=assoc.provider.total_calls,
                    successful_calls=assoc.provider.successful_calls
                )
                setattr(p, 'priority', assoc.priority)
                provider_list.append(p)
        group.providers = provider_list
    return groups

def count_groups(db: Session):
    return db.query(models.Group).count()

def create_group(db: Session, group: schemas.GroupCreate):
    db_group = models.Group(name=group.name)
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group

def delete_group(db: Session, group_id: int):
    db_group = get_group(db, group_id)
    if db_group:
        # Manually delete associations from the provider_group_association table
        db.query(models.ProviderGroupAssociation).filter(
            models.ProviderGroupAssociation.group_id == group_id
        ).delete(synchronize_session=False)

        # Manually delete associations from the api_key_group_association table
        stmt_apikey = models.api_key_group_association.delete().where(
            models.api_key_group_association.c.group_id == group_id
        )
        db.execute(stmt_apikey)

        db.delete(db_group)
        db.commit()
    return db_group

def add_provider_to_group(db: Session, provider_id: int, group_id: int, priority: int = 1, commit: bool = True):
    stmt = insert(models.ProviderGroupAssociation).values(
        provider_id=provider_id,
        group_id=group_id,
        priority=priority,
        active_calls=0
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=['provider_id', 'group_id'],
        set_=dict(priority=priority)
    )
    db.execute(stmt)
    if commit:
        db.commit()
    return get_provider(db, provider_id)

def remove_provider_from_group(db: Session, provider_id: int, group_id: int):
    result = db.query(models.ProviderGroupAssociation).filter(
        models.ProviderGroupAssociation.provider_id == provider_id,
        models.ProviderGroupAssociation.group_id == group_id
    ).delete(synchronize_session=False)
    db.commit()
    return result > 0

def calculate_cost(provider: models.ApiProvider, prompt_tokens: int, completion_tokens: int, total_tokens: int) -> float | None:
    """Calculates the cost of an API call based on token usage.
    Supports separate input/output pricing when available, falls back to unified price."""
    input_price = provider.input_price_per_million_tokens
    output_price = provider.output_price_per_million_tokens
    unified_price = provider.price_per_million_tokens

    # If separate input/output prices are set, use them
    if input_price is not None and output_price is not None:
        if prompt_tokens is not None and completion_tokens is not None:
            input_cost = (prompt_tokens / 1_000_000) * input_price
            output_cost = (completion_tokens / 1_000_000) * output_price
            return input_cost + output_cost
        # Fallback: if only total_tokens available, use average of input+output price
        if total_tokens is not None:
            avg_price = (input_price + output_price) / 2
            return (total_tokens / 1_000_000) * avg_price
        return None

    # Fallback to unified price
    if not unified_price:
        return None
    
    if prompt_tokens is not None and completion_tokens is not None:
        total_tokens_for_cost = prompt_tokens + completion_tokens
        return (total_tokens_for_cost / 1_000_000) * unified_price
    
    if total_tokens is not None:
        return (total_tokens / 1_000_000) * unified_price
        
    return None
import secrets
import string

# CRUD for API Keys
def get_api_key(db: Session, api_key_id: int):
    return db.query(models.APIKey).filter(models.APIKey.id == api_key_id).first()

def get_api_key_by_key(db: Session, key: str):
    return db.query(models.APIKey).filter(models.APIKey.key == key).first()

def get_api_keys(db: Session, skip: int = 0, limit: int = 100):
    from sqlalchemy import func

    # Subquery to count call logs for each API key
    call_count_subquery = db.query(
        models.CallLog.api_key_id,
        func.count(models.CallLog.id).label('call_count')
    ).group_by(models.CallLog.api_key_id).subquery()

    # Main query to get API keys and join with the call count subquery
    query = db.query(
        models.APIKey,
        call_count_subquery.c.call_count
    ).outerjoin(
        call_count_subquery, models.APIKey.id == call_count_subquery.c.api_key_id
    ).order_by(models.APIKey.id.desc())

    results = query.offset(skip).limit(limit).all()

    # Process results to add call_count to each APIKey object
    api_keys_with_counts = []
    for api_key, call_count in results:
        api_key.call_count = call_count if call_count is not None else 0
        api_keys_with_counts.append(api_key)

    return api_keys_with_counts

def generate_api_key():
    alphabet = string.ascii_letters + string.digits
    key = ''.join(secrets.choice(alphabet) for i in range(48))
    return f"sk-{key}"

def create_api_key(db: Session, api_key_data: schemas.APIKeyCreate):
    new_key = generate_api_key()
    db_api_key = models.APIKey(key=new_key, name=api_key_data.name or "", is_active=api_key_data.is_active)
    
    groups = db.query(models.Group).filter(models.Group.id.in_(api_key_data.group_ids)).all()
    if not groups:
        raise ValueError("One or more group IDs are invalid.")
        
    db_api_key.groups.extend(groups)
    
    db.add(db_api_key)
    db.commit()
    db.refresh(db_api_key)
    return db_api_key

def update_api_key(db: Session, api_key_id: int, api_key_update: schemas.APIKeyUpdate):
    db_api_key = get_api_key(db, api_key_id)
    if not db_api_key:
        return None

    update_data = api_key_update.dict(exclude_unset=True)
    
    # Explicitly handle group updates
    if 'group_ids' in update_data:
        group_ids = update_data.pop('group_ids')
        if group_ids is not None:
            groups = db.query(models.Group).filter(models.Group.id.in_(group_ids)).all()
            if len(groups) != len(group_ids):
                # This ensures that if a non-existent group_id is passed, we don't silently fail.
                raise ValueError("One or more group IDs are invalid.")
            db_api_key.groups = groups
        else:
            # If group_ids is explicitly set to None, we can interpret it as clearing all groups.
            db_api_key.groups = []

    for key, value in update_data.items():
        setattr(db_api_key, key, value)

    db.commit()
    db.refresh(db_api_key)
    return db_api_key

def delete_api_key(db: Session, api_key_id: int):
    db_api_key = get_api_key(db, api_key_id)
    if db_api_key:
        db.delete(db_api_key)
        db.commit()
    return db_api_key

def update_api_key_last_used(db: Session, api_key_id: int):
    from datetime import datetime
    import pytz

    TAIPEI_TZ = pytz.timezone('Asia/Taipei')
    db.query(models.APIKey).filter(models.APIKey.id == api_key_id).update({"last_used_at": datetime.now(TAIPEI_TZ)})
    db.commit()

# CRUD for Settings
def get_setting(db: Session, key: str) -> models.Setting | None:
    return db.query(models.Setting).filter(models.Setting.key == key).first()

def update_setting(db: Session, key: str, value: str):
    stmt = insert(models.Setting).values(key=key, value=value)
    stmt = stmt.on_conflict_do_update(
        index_elements=['key'],
        set_=dict(value=value)
    )
    db.execute(stmt)
    db.commit()
    return get_setting(db, key)

# Concurrency Management
def reset_all_active_calls(db: Session):
    """Sets all active_calls to 0. Called on server startup."""
    db.query(models.ProviderGroupAssociation).update({models.ProviderGroupAssociation.active_calls: 0})
    db.commit()

def increment_active_calls(db: Session, provider_id: int, group_id: int):
    """Increments active_calls for a specific provider-group association."""
    db.query(models.ProviderGroupAssociation).filter(
        models.ProviderGroupAssociation.provider_id == provider_id,
        models.ProviderGroupAssociation.group_id == group_id
    ).update({models.ProviderGroupAssociation.active_calls: models.ProviderGroupAssociation.active_calls + 1})
    db.commit()

def decrement_active_calls(db: Session, provider_id: int, group_id: int):
    """Decrements active_calls for a specific provider-group association."""
    db.query(models.ProviderGroupAssociation).filter(
        models.ProviderGroupAssociation.provider_id == provider_id,
        models.ProviderGroupAssociation.group_id == group_id,
        models.ProviderGroupAssociation.active_calls > 0
    ).update({models.ProviderGroupAssociation.active_calls: models.ProviderGroupAssociation.active_calls - 1})
    db.commit()

def get_concurrency_status(db: Session) -> List[schemas.ProviderConcurrencyStatus]:
    """Returns the current active_calls for all provider-group associations."""
    results = db.query(
        models.ProviderGroupAssociation.provider_id,
        models.ProviderGroupAssociation.group_id,
        models.ProviderGroupAssociation.active_calls
    ).all()
    
    return [
        schemas.ProviderConcurrencyStatus(
            provider_id=r.provider_id,
            group_id=r.group_id,
            active_calls=r.active_calls
        ) for r in results
    ]

def get_unique_providers(db: Session) -> List[schemas.ApiProviderSimple]:
    """Returns all providers (models) with renamed fields for status API."""
    results = db.query(
        models.ApiProvider.id,
        models.ApiProvider.name.label('provider'),
        models.ApiProvider.model,
        models.ApiProvider.api_endpoint
    ).all()
    
    return [
        schemas.ApiProviderSimple(
            id=r.id,
            provider=r.provider,
            model=r.model,
            api_endpoint=r.api_endpoint
        ) for r in results
    ]

def get_providers_simple(db: Session) -> List[schemas.ApiProviderSimple]:
    """Returns basic info of all providers for the status API."""
    return get_unique_providers(db)
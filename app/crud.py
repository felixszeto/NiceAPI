from sqlalchemy.orm import Session
from . import models, schemas
from sqlalchemy.dialects.sqlite import insert

def get_provider(db: Session, provider_id: int):
    return db.query(models.ApiProvider).filter(models.ApiProvider.id == provider_id).first()

def get_provider_by_name(db: Session, name: str):
    return db.query(models.ApiProvider).filter(models.ApiProvider.name == name).first()

def get_providers(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.ApiProvider).offset(skip).limit(limit).all()

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
    if 'usage_level' in provider_data:
        del provider_data['usage_level']
    db.query(models.ApiProvider).filter(models.ApiProvider.id == provider_id).update(provider_data)
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
    stmt = models.provider_group_association.delete().where(
        models.provider_group_association.c.provider_id.in_(provider_ids)
    )
    db.execute(stmt)

    # Delete the providers themselves
    deleted_count = len(provider_ids)
    for provider in providers_to_delete:
        db.delete(provider)

    db.commit()
    return deleted_count

def get_call_logs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.CallLog).join(models.ApiProvider).order_by(models.CallLog.id.desc()).offset(skip).limit(limit).all()

def get_error_keywords(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.ErrorMaintenance).order_by(models.ErrorMaintenance.id.desc()).offset(skip).limit(limit).all()

def create_call_log(db: Session, log: schemas.CallLogCreate):
    provider = get_provider(db, log.provider_id)
    if provider:
        provider.total_calls += 1
        if log.is_success:
            provider.successful_calls += 1

    db_log = models.CallLog(**log.dict())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

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
    return db.query(models.Group).offset(skip).limit(limit).all()

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
        stmt_provider = models.provider_group_association.delete().where(
            models.provider_group_association.c.group_id == group_id
        )
        db.execute(stmt_provider)

        # Manually delete associations from the api_key_group_association table
        stmt_apikey = models.api_key_group_association.delete().where(
            models.api_key_group_association.c.group_id == group_id
        )
        db.execute(stmt_apikey)

        db.delete(db_group)
        db.commit()
    return db_group

def add_provider_to_group(db: Session, provider_id: int, group_id: int, priority: int = 1):
    stmt = insert(models.provider_group_association).values(
        provider_id=provider_id,
        group_id=group_id,
        priority=priority
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=['provider_id', 'group_id'],
        set_=dict(priority=priority)
    )
    db.execute(stmt)
    db.commit()
    return get_provider(db, provider_id)

def remove_provider_from_group(db: Session, provider_id: int, group_id: int):
    stmt = models.provider_group_association.delete().where(
        models.provider_group_association.c.provider_id == provider_id,
        models.provider_group_association.c.group_id == group_id
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount > 0

def calculate_cost(provider: models.ApiProvider, prompt_tokens: int, completion_tokens: int, total_tokens: int) -> float | None:
    """Calculates the cost of an API call based on token usage."""
    if not provider.price_per_million_tokens:
        return None
    
    # Prioritize prompt and completion tokens for more accurate pricing
    if prompt_tokens is not None and completion_tokens is not None:
        total_tokens_for_cost = prompt_tokens + completion_tokens
        return (total_tokens_for_cost / 1_000_000) * provider.price_per_million_tokens
    
    # Fallback to total_tokens if prompt/completion are not available
    if total_tokens is not None:
        return (total_tokens / 1_000_000) * provider.price_per_million_tokens
        
    return None
import secrets
import string

# CRUD for API Keys
def get_api_key(db: Session, api_key_id: int):
    return db.query(models.APIKey).filter(models.APIKey.id == api_key_id).first()

def get_api_key_by_key(db: Session, key: str):
    return db.query(models.APIKey).filter(models.APIKey.key == key).first()

def get_api_keys(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.APIKey).offset(skip).limit(limit).all()

def generate_api_key():
    alphabet = string.ascii_letters + string.digits
    key = ''.join(secrets.choice(alphabet) for i in range(48))
    return f"sk-{key}"

def create_api_key(db: Session, api_key_data: schemas.APIKeyCreate):
    new_key = generate_api_key()
    db_api_key = models.APIKey(key=new_key, is_active=api_key_data.is_active)
    
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
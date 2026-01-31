from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List
from . import models, schemas, crud
import logging

logger = logging.getLogger(__name__)

def _find_available_provider(db: Session, providers_query, failure_threshold=5, failure_period_minutes=5):
    """
    Helper function to find an available provider from a list, checking for recent failures.
    Returns (provider, group_id)
    """
    potential_providers = providers_query.all()
    logger.info(f"Found {len(potential_providers)} potential providers based on query, sorted by selection criteria.")
    
    if not potential_providers:
        logger.warning("No providers found matching the query criteria.")
        return None

    logger.info("Iterating through sorted provider list to find one that meets failover criteria:")
    for i, row in enumerate(potential_providers):
        # Handle both direct model objects and Row objects from with_entities
        if hasattr(row, 'ApiProvider'):
            p = row.ApiProvider
            priority = row.priority
            group_id = getattr(row, 'group_id', None)
        else:
            p = row
            priority = None
            group_id = None
        
        success_rate = (p.successful_calls / p.total_calls * 100) if p.total_calls > 0 else 0
        priority_str = f", Priority={priority}" if priority is not None else ""
        logger.info(f"  - Candidate #{i+1}: ID={p.id}, Name='{p.name}', Model='{p.model}', Price=${p.price_per_million_tokens}/M tokens{priority_str}, Success Rate={success_rate:.2f}%")

    for row in potential_providers:
        provider = row.ApiProvider if hasattr(row, 'ApiProvider') else row
        failure_count = crud.count_recent_failures_for_provider(db, provider.id, minutes=failure_period_minutes)
        logger.info(f"  - Checking failure status for ID={provider.id}... Recent failures ({failure_period_minutes}min): {failure_count}")
        if failure_count < failure_threshold:
            logger.info(f"  -> [SUCCESS] Selected provider ID={provider.id}. Reason: This is the highest-priority provider with a failure count ({failure_count}) below the threshold ({failure_threshold}).")
            return provider, group_id # Return the provider object and group_id
        else:
            logger.warning(f"  -> [SKIPPED] Provider ID={provider.id} because its failure count ({failure_count}) is not less than the threshold ({failure_threshold}).")
    
    logger.error("No provider meeting the failover criteria was found among all candidates.")
    return None, None

def select_provider(db: Session, request: schemas.ChatRequest, excluded_provider_ids: List[int] = None):
    """
    Selects the best provider based on user-provided constraints.
    Can exclude a list of provider IDs.
    Returns (provider, group_id)
    """
    # Get failover settings from the database, with defaults
    count_setting = crud.get_setting(db, 'failover_threshold_count')
    period_setting = crud.get_setting(db, 'failover_threshold_period_minutes')
    
    FAILURE_THRESHOLD = int(count_setting.value) if count_setting else 2
    FAILURE_PERIOD_MINUTES = int(period_setting.value) if period_setting else 5
    logger.info("--- Starting Provider Selection ---")
    if excluded_provider_ids:
        logger.info(f"Excluding previously attempted provider IDs: {excluded_provider_ids}")
    
    model_or_group_name = request.model
    logger.info(f"Request parameter: model/group='{model_or_group_name}'")

    # Base query: all active providers
    query = db.query(models.ApiProvider).filter(models.ApiProvider.is_active == True)

    # Exclude already tried providers
    if excluded_provider_ids:
        query = query.filter(models.ApiProvider.id.notin_(excluded_provider_ids))
        
    logger.info(f"Step 1: Initial query, found {query.count()} active providers.")

    # 2. Filter by model or group
    is_group_request = False
    if model_or_group_name:
        group = crud.get_group_by_name(db, name=model_or_group_name)
        if group:
            logger.info(f"Step 2: Filtering by group '{model_or_group_name}'.")
            # We need to select from the association table to get priority
            query = query.join(models.ProviderGroupAssociation).filter(models.ProviderGroupAssociation.group_id == group.id)
            logger.info(f"  - {query.count()} providers remaining after filter.")
            is_group_request = True
        else:
            logger.info(f"Step 2: Filtering by model name '{model_or_group_name}'.")
            query = query.filter(models.ApiProvider.model == model_or_group_name)
            logger.info(f"  - {query.count()} providers remaining after filter.")

    # Pre-flight check for single model requests
    if not is_group_request and model_or_group_name:
        potential_providers = query.all()
        if not potential_providers:
            logger.error(f"No active providers found for model '{model_or_group_name}'.")
            return None, None
            
        total_providers = len(potential_providers)
        failed_providers_count = 0
        for p in potential_providers:
            if crud.count_recent_failures_for_provider(db, p.id, minutes=FAILURE_PERIOD_MINUTES) >= FAILURE_THRESHOLD:
                failed_providers_count += 1
        
        if total_providers > 0 and failed_providers_count == total_providers:
            logger.error(f"All providers for model '{model_or_group_name}' have failed more than {FAILURE_THRESHOLD} times in the last {FAILURE_PERIOD_MINUTES} minutes.")
            return None, None

    # Define ordering
    # 3. Define ordering
    logger.info("Step 3: Applying sorting rules.")
    if is_group_request:
        logger.info("  - Applying group sorting: 1. Priority (ASC), 2. Price (ASC)")
        # Select the model and the priority from the association table
        query = query.with_entities(
            models.ApiProvider,
            models.ProviderGroupAssociation.priority.label('priority'),
            models.ProviderGroupAssociation.group_id.label('group_id')
        )
        strict_query = query.order_by(
            models.ProviderGroupAssociation.priority.asc(),
            models.ApiProvider.price_per_million_tokens.asc()
        )
    else:
        logger.info("  - Applying single model sorting: 1. Price (ASC)")
        strict_query = query.order_by(
            models.ApiProvider.price_per_million_tokens.asc()
        )
        
    logger.info("Step 4: Finding the best available provider.")
    provider, group_id = _find_available_provider(db, strict_query, failure_threshold=FAILURE_THRESHOLD, failure_period_minutes=FAILURE_PERIOD_MINUTES)

    if provider:
        logger.info("--- Provider Selection End (Provider Found) ---")
        return provider, group_id

    logger.error("No suitable provider found matching the specified constraints and failure threshold.")
    logger.info("--- Provider Selection End (Provider Not Found) ---")
    return None, None
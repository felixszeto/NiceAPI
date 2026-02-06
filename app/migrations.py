import logging
from sqlalchemy import inspect, text
from .database import engine

logger = logging.getLogger(__name__)

def run_migrations():
    """運行資料庫遷移，確保現有資料表結構與模型同步。"""
    inspector = inspect(engine)
    
    if 'call_logs' in inspector.get_table_names():
        columns = [c['name'] for c in inspector.get_columns('call_logs')]
        
        with engine.begin() as conn:
            # 遷移 1: 添加 api_key_id 欄位
            if 'api_key_id' not in columns:
                try:
                    logger.info("正在遷移：為 call_logs 添加 api_key_id 欄位...")
                    conn.execute(text("ALTER TABLE call_logs ADD COLUMN api_key_id INTEGER REFERENCES api_keys(id)"))
                    logger.info("遷移成功：已添加 api_key_id 欄位。")
                except Exception as e:
                    logger.error(f"遷移失敗 (api_key_id): {e}")

            # 遷移 2: 添加 request_body 欄位
            if 'request_body' not in columns:
                try:
                    logger.info("正在遷移：為 call_logs 添加 request_body 欄位...")
                    conn.execute(text("ALTER TABLE call_logs ADD COLUMN request_body TEXT"))
                    logger.info("遷移成功：已添加 request_body 欄位。")
                except Exception as e:
                    logger.error(f"遷移失敗 (request_body): {e}")
    else:
        logger.info("call_logs 表不存在，將由 create_all 建立。")

    # 遷移 3: 添加索引
    if 'call_logs' in inspector.get_table_names():
        with engine.begin() as conn:
            try:
                # 獲取現有索引
                indexes = [i['name'] for i in inspector.get_indexes('call_logs')]
                
                # 添加 request_timestamp 索引 (用於排序)
                if 'ix_call_logs_request_timestamp' not in indexes:
                    logger.info("正在遷移：為 call_logs 添加 request_timestamp 索引...")
                    conn.execute(text("CREATE INDEX ix_call_logs_request_timestamp ON call_logs (request_timestamp)"))
                
                # 添加 is_success 索引 (用於過濾)
                if 'ix_call_logs_is_success' not in indexes:
                    logger.info("正在遷移：為 call_logs 添加 is_success 索引...")
                    conn.execute(text("CREATE INDEX ix_call_logs_is_success ON call_logs (is_success)"))

                # 添加 provider_id 索引 (用於關聯)
                if 'ix_call_logs_provider_id' not in indexes:
                    logger.info("正在遷移：為 call_logs 添加 provider_id 索引...")
                    conn.execute(text("CREATE INDEX ix_call_logs_provider_id ON call_logs (provider_id)"))

                # 添加 api_key_id 索引 (用於關聯)
                if 'ix_call_logs_api_key_id' not in indexes:
                    logger.info("正在遷移：為 call_logs 添加 api_key_id 索引...")
                    conn.execute(text("CREATE INDEX ix_call_logs_api_key_id ON call_logs (api_key_id)"))
                    
                logger.info("索引遷移檢查完成。")
            except Exception as e:
                logger.error(f"遷移失敗 (索引): {e}")

    # Migration for provider_group_association to add active_calls
    if 'provider_group_association' in inspector.get_table_names():
        pga_columns = [c['name'] for c in inspector.get_columns('provider_group_association')]
        if 'active_calls' not in pga_columns:
            with engine.begin() as conn:
                try:
                    logger.info("正在遷移：為 provider_group_association 添加 active_calls 欄位...")
                    conn.execute(text("ALTER TABLE provider_group_association ADD COLUMN active_calls INTEGER DEFAULT 0"))
                    logger.info("遷移成功：已添加 active_calls 欄位。")
                except Exception as e:
                    logger.error(f"遷移失敗 (active_calls): {e}")

    # Ensure CallLogDetail table exists (though create_all handles new tables, we log it)
    if 'call_log_details' not in inspector.get_table_names():
        logger.info("正在遷移：call_log_details 表不存在，將由 create_all 建立。")
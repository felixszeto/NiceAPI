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
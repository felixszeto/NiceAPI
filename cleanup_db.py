import sqlite3
import os

db_path = "api_server.db"

def cleanup():
    if not os.path.exists(db_path):
        print(f"錯誤: 找不到資料庫檔案 '{db_path}'。")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("--- 開始資料庫清理程序 ---")

        # 需要清空的資料表
        tables_to_clear = ['call_logs', 'provider_group_association', 'api_providers']

        for table in tables_to_clear:
            try:
                cursor.execute(f"DELETE FROM {table};")
                print(f"已清空資料表: {table} (刪除 {cursor.rowcount} 筆資料)")
            except sqlite3.OperationalError as e:
                print(f"跳過資料表 {table}: {e}")

        # 重置自增 ID 序列 (如果存在)
        try:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('api_providers', 'call_logs');")
            print("已重置自增 ID 序列。")
        except sqlite3.OperationalError:
            # 某些環境可能沒有 sqlite_sequence 表
            pass

        conn.commit()
        print("\n資料庫清理成功完成。")
        
        # 驗證保留的資料表
        remaining_tables = ['api_keys', 'groups', 'settings', 'error_maintenance']
        print("\n保留的資料表狀態:")
        for table in remaining_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                count = cursor.fetchone()[0]
                print(f"- {table}: 剩餘 {count} 筆資料")
            except sqlite3.OperationalError:
                print(f"- {table}: 資料表不存在")

        conn.close()

    except Exception as e:
        print(f"執行過程中發生錯誤: {e}")

if __name__ == "__main__":
    cleanup()
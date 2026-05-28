import requests
import hashlib
import mysql.connector
from datetime import datetime, timedelta
import time

# 1. 설정 정보
API_KEY = "bc6db4ee470f6a2cd80c09558bb8161c8bf01c6739567f75d0abcc73467467b2"
API_NAME = "Grid_20240625000000000654_1"

MARKET_MAP = {
    "110001": "서울가락", "210001": "인천구월", "230001": "대구북부",
    "240001": "광주각화", "250001": "대전노은", "350101": "전주도매", "350301": "익산도매"
}

# 2. AWS RDS 접속 정보
db_config = {
    'host': 'database-1.cdeygca48zyu.ap-northeast-2.rds.amazonaws.com',
    'user': 'team_member1',
    'password': '1234',
    'database': 'project1'
}

def collect_to_mysql():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        start_date = datetime(2026, 4, 1)
        end_date = datetime(2026, 4, 3)
        current_date = start_date
        total_inserted = 0

        while current_date <= end_date:
            target_str = current_date.strftime("%Y%m%d")
            batch_id = f"BATCH_{target_str}"
            
            for m_code, m_name in MARKET_MAP.items():
                URL = f"http://211.237.50.150:7080/openapi/{API_KEY}/json/{API_NAME}/1/20"
                params = {'SALEDATE': target_str, 'WHSALCD': m_code}
                
                res = requests.get(URL, params=params)
                data = res.json()
                root = data.get(API_NAME, {})
                rows = root.get('row', [])

                if not rows: continue

                insert_values = []
                for row in rows:
                    sbid_time = row['SBIDTIME']
                    item_name = f"{row['MIDNAME']}({row['SMALLNAME']})"
                    origin = row['SANNAME']
                    dest = row['WHSALNAME']
                    
                    # --- [추가된 부분] API에서 QTY(물량) 값을 가져옵니다 ---
                    qty_str = row.get('QTY', '0')
                    # 빈 문자열이 올 경우를 대비해 예외 처리 후 float 변환
                    qty = float(qty_str) if qty_str.strip() != '' else 0.0
                    
                    # 무결성 검증용 해시 생성 (기존과 동일)
                    raw_str = f"{sbid_time}{item_name}{origin}{dest}"
                    row_hash = hashlib.sha256(raw_str.encode()).hexdigest()

                    # 튜플 맨 끝에 qty 추가
                    insert_values.append((sbid_time, item_name, origin, dest, row_hash, batch_id, qty))

                # --- [추가된 부분] SQL 문에 qty 컬럼 추가 ---
                sql = """INSERT IGNORE INTO wholesale_transactions 
                         (sbid_time, item_name, origin_name, whsal_name, row_hash, batch_id, qty) 
                         VALUES (%s, %s, %s, %s, %s, %s, %s)"""
                
                cursor.executemany(sql, insert_values)
                conn.commit()
                total_inserted += cursor.rowcount
                print(f"[{target_str}] {m_name}: {cursor.rowcount}건 저장 완료")
            
            current_date += timedelta(days=1)
            time.sleep(0.1)

        print(f"\n 최종 완료: 총 {total_inserted}건이 DB에 저장되었습니다.")

    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    collect_to_mysql()
import requests
import json
import hashlib
import random
import pymysql
from datetime import datetime, timedelta

# 1. DB 접속 설정 
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '', # 본인 DB 비밀번호
    'db': 'retail', # db 이름 입력
    'charset': 'utf8mb4'
}

# 2. 확장된 20개 소매처 리스트 (전주/완주 지역 중심)
STORES = [
    "이마트 전주점", "롯데마트 덕진점", "홈플러스 전주효자점", "홈플러스 전주점",
    "농협하나로마트 전주점", "전주농협 로컬푸드 중화산점", "전주원예농협 로컬푸드",
    "완주공공급식지원센터", "전주푸드 직매장 효자점", "전주푸드 직매장 송천점",
    "CU 전북대본점", "CU 전주객사점", "GS25 금암점", "GS25 전주한옥마을점",
    "이마트24 전주혁신점", "세븐일레븐 서신점", "농협하나로마트 전주농협점",
    "롯데마트 전주점", "전주푸드 직매장 종합경기장점", "CU 전주서신점"
]

# 3. API 설정
API_KEY = "5e9b3c2ceeb74c25f419af7efbc3df9fb6453b5e4b387167447272bedaf46a9d"
API_NAME = "Grid_20240625000000000654_1"
URL = f"http://211.237.50.150:7080/openapi/{API_KEY}/json/{API_NAME}/1/20" # 20건 테스트

def generate_hash(data_str):
    """SHA-256 해시 생성 함수"""
    return hashlib.sha256(data_str.encode()).hexdigest()

def start_integration():
    conn = None
    try:
        # DB 연결
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        
        # API 데이터 호출 (2024-05-02 가락시장 데이터 기준)
        response = requests.get(URL, params={'SALEDATE': '20240502', 'WHSALCD': '110001'})
        rows = response.json().get(API_NAME, {}).get('row', [])
        
        print(f"[확장 모드] 총 {len(rows)}건의 유통 데이터 적재를 시작합니다...")

        for row in rows:
            # [Step 1] 도매 데이터 저장 및 해시 생성
            # 재료: 경락일시 + 산지 + 가격
            w_material = f"{row['SBIDTIME']}{row['SANNAME']}{row['COST']}"
            w_hash = generate_hash(w_material)
            
            w_sql = """INSERT INTO wholesale_log (sbid_time, san_name, whsal_name, item_name, cost, qty, curr_hash) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(w_sql, (row['SBIDTIME'], row['SANNAME'], row['WHSALNAME'], 
                                   f"{row['MIDNAME']}({row['SMALLNAME']})", row['COST'], row['QTY'], w_hash))
            
            # 생성된 도매 ID 가져오기
            wholesale_id = cursor.lastrowid
            
            # [Step 2] 소매 데이터 가상 생성 (20개 리스트 활용)
            store = random.choice(STORES)
            
            # 마진율 차등 적용 (편의점은 더 비싸게, 마트는 더 저렴하게 가상 시뮬레이션)
            if "CU" in store or "GS25" in store or "세븐일레븐" in store:
                margin = random.uniform(1.5, 1.7) # 편의점 마진 50~70%
            else:
                margin = random.uniform(1.3, 1.45) # 마트 마진 30~45%
                
            sale_price = int(int(row['COST']) * margin)
            clean_date = row['SBIDTIME'].replace('-', '')[:8] # 하이픈(-)을 제거하고 8자리만 추출
            auction_date = datetime.strptime(clean_date, "%Y%m%d")
            # 경매 후 1~2일 뒤 소비자 판매 시작
            sale_date = auction_date + timedelta(days=random.randint(1, 2))
            
            # [Step 3] 소매 해시 체이닝 (이전 도매 해시 연결)
            r_material = f"{w_hash}{store}{sale_price}{sale_date.strftime('%Y-%m-%d')}"
            r_hash = generate_hash(r_material)
            
            # 소매 데이터 저장
            r_sql = """INSERT INTO retail_log (wholesale_id, store_name, sale_price, sale_date, prev_hash, curr_hash) 
                       VALUES (%s, %s, %s, %s, %s, %s)"""
            cursor.execute(r_sql, (wholesale_id, store, sale_price, sale_date, w_hash, r_hash))

        conn.commit()
        print(f"✅ 완료: 20개 소매처를 포함한 {len(rows)}건의 무결성 체인이 구축되었습니다.")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    start_integration()

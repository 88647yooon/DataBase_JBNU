import pymysql
import hashlib
import random
from datetime import timedelta

# 1. DB 접속 정보
db_config = {
    'host': 'database-1.cdeygca48zyu.ap-northeast-2.rds.amazonaws.com',
    'user': 'team_member1',
    'password': '1234',
    'db': 'project1',
    'charset': 'utf8mb4'
}

# 2. 지역별 상세 지점 매핑 (DB의 whsal_name과 100% 일치하도록 수정)
REGION_DISTRICTS = {
    "서울가락": ["송파점", "강남점", "서초점", "잠실점", "문정점", "위례점", "강동점", "성수점"],
    "인천구월": ["구월본점", "송도점", "부평점", "연수점", "남동점", "주안점", "논현점"],
    "대구북부": ["칠성점", "수성점", "침산점", "대구본점", "범어점", "상인점", "동성로점"],
    "광주각화": ["수완점", "상무점", "광주본점", "봉선점", "첨단점", "일곡점", "화정점"],
    "대전노은": ["유성점", "둔산점", "노은점", "도안점", "탄방점", "관평점", "대전본점"],
    "전주": ["효자점", "송천점", "덕진점", "전주본점", "서신점", "혁신점", "평화점", "에코시티점"],
    "익산": ["영등점", "모현점", "부송점", "어양점", "신동점", "남중점", "익산본점"],
    "부산엄궁": ["해운대점", "사상점", "센텀시티점", "서면점", "광안리점", "남포점", "동래점", "명지점"]
}

# 3. 매장 브랜드 카테고리
LARGE_MARTS = ["이마트", "롯데마트", "홈플러스"]
LOCAL_MARTS = ["농협하나로마트", "로컬푸드 직매장"]
CONVENIENCE_STORES = ["CU", "GS25", "세븐일레븐", "이마트24"]

def generate_hash(data_str):
    return hashlib.sha256(data_str.encode()).hexdigest()

def seed_retail_data():
    conn = None
    try:
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        
        # 기존 잘못된 소매 데이터 초기화
        cursor.execute("TRUNCATE TABLE retail_transactions")
        
        # 도매 테이블에서 실제 데이터(qty, row_hash 포함) 조회
        cursor.execute("SELECT id, sbid_time, item_name, whsal_name, row_hash, qty FROM wholesale_transactions")
        wholesale_data = wholesale_data = cursor.fetchall()
        
        print(f"✅ 총 {len(wholesale_data)}건의 도매 데이터를 지리적/물량 논리에 맞춰 연결합니다.")

        insert_count = 0
        for w_row in wholesale_data:
            w_id, auction_date, item_name, whsal_name, w_hash, qty = w_row
            
            # --- [교정 1] 지리적 인접성 매칭 ---
            # DB에 저장된 whsal_name에 맞는 지역 리스트를 가져옴
            district_list = REGION_DISTRICTS.get(whsal_name, ["중앙점", "본점", "1호점"])
            
            # --- [교정 2] 물량(qty) 기반 가중치 선정 ---
            current_qty = qty if qty is not None else 50
            if current_qty >= 150: # 대량 -> 대형마트 위주
                brand_list = random.choices([LARGE_MARTS, LOCAL_MARTS], weights=[85, 15], k=1)[0]
            elif current_qty <= 15: # 소량 -> 로컬푸드/편의점 위주
                brand_list = random.choices([LOCAL_MARTS, CONVENIENCE_STORES], weights=[70, 30], k=1)[0]
            else: # 일반 물량 -> 균등 배분
                brand_list = random.choices([LARGE_MARTS, LOCAL_MARTS, CONVENIENCE_STORES], weights=[40, 40, 20], k=1)[0]
            
            brand = random.choice(brand_list)
            district = random.choice(district_list)
            store_full_name = f"{brand} {district}"

            # 가격 및 날짜 생성
            sale_price = random.randint(2000, 45000) 
            sale_date = auction_date + timedelta(days=random.randint(1, 2))
            
            # --- [교정 3] 해시 체이닝 (부모 row_hash 참조) ---
            # 부모의 row_hash(w_hash)를 prev_hash로 사용
            prev_hash = w_hash
            r_material = f"{prev_hash}{store_full_name}{sale_price}{sale_date.strftime('%Y-%m-%d %H:%M:%S')}"
            curr_hash = generate_hash(r_material)
            
            # DB 저장 (retail_transactions)
            r_sql = """INSERT INTO retail_transactions 
                       (wholesale_id, store_name, sale_price, sale_date, prev_hash, curr_hash) 
                       VALUES (%s, %s, %s, %s, %s, %s)"""
            cursor.execute(r_sql, (w_id, store_full_name, sale_price, sale_date, prev_hash, curr_hash))
            insert_count += 1

        conn.commit()
        print(f"🎉 성공: {insert_count}건의 소매 데이터가 무결성 체인으로 연결되었습니다.")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    seed_retail_data()
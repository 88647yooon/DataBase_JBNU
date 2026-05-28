import pymysql
import hashlib


#조인해시 업데이트 버전
# 1. DB 설정 (비밀번호 꼭 수정하세요!)
db_config = {
    'host': 'database-1.cdeygca48zyu.ap-northeast-2.rds.amazonaws.com',
    'user': 'admin',
    'password': 'leejinwook0210',  
    'db': 'project1',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# 배치로그에 없는 소매테이블에 있는 소매날짜에 대해 배치 해시를 만들고 배치로그에 삽입하는 코드
def make_batch_logs():
    conn = None
    try:
        conn = pymysql.connect(**db_config)
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            
            # 1. 소매 테이블 기준 마감 일자 추출
            cursor.execute("SELECT DISTINCT DATE(sale_date) as target_date FROM retail_transactions ORDER BY target_date")
            batch_list = [str(row['target_date']) for row in cursor.fetchall() if row['target_date']]
            
            if not batch_list:
                print("✨ 모든 데이터가 이미 batch_log에 마감되어 있습니다!")
                return
            
            # 💡 [복구] 시작 알림 및 총 마감 날짜 수 출력
            print(f"🔍 결산할 날짜를 {len(batch_list)}개 찾았습니다. 마감을 시작합니다...\n")
            
            processed_count = 0 # 실제 새로 마감한 건수 체크용

            for target_date in batch_list:
                # 이미 마감된 날짜인지 확인
                check_sql = "SELECT 1 FROM batch_log WHERE batch_id = %s"
                cursor.execute(check_sql, (target_date,))
                if cursor.fetchone():
                    continue # 이미 마감되었으면 조용히 패스

                # 2. 해당 일자의 소매 테이블 'curr_hash' 리스트 병합
                sql_get_hashes = "SELECT curr_hash FROM retail_transactions WHERE DATE(sale_date) = %s ORDER BY id"
                cursor.execute(sql_get_hashes, (target_date,))
                daily_retail_rows = cursor.fetchall()
                
                if not daily_retail_rows:
                    continue
                
                # 💡 [복구] 해당 날짜에 팔린 소매 데이터가 몇 건인지 추출
                retail_count = len(daily_retail_rows)
                
                combined_hashes_str = "".join([row['curr_hash'] for row in daily_retail_rows])
                today_pure_hash = hashlib.sha256(combined_hashes_str.encode()).hexdigest()
                
                # 3. 체이닝: 이전 배치 해시 로드
                sql_get_prev = "SELECT batch_hash FROM batch_log ORDER BY created_at DESC LIMIT 1"
                cursor.execute(sql_get_prev)
                prev_row = cursor.fetchone()
                
                previous_hash = prev_row['batch_hash'] if prev_row else "GENESIS_BATCH_HASH_000000000000000000000"
                final_batch_hash = hashlib.sha256((previous_hash + today_pure_hash).encode()).hexdigest()
                
                # 4. 최종 적재
                sql_insert_log = "INSERT INTO batch_log (batch_id, batch_hash, previous_hash) VALUES (%s, %s, %s)"
                cursor.execute(sql_insert_log, (target_date, final_batch_hash, previous_hash))
                
                conn.commit()
                processed_count += 1
                
                # 💡 [복구] 마감 완료 및 포함된 건수 출력
                print(f"✅ {target_date} 마감 완료! (포함된 소매 데이터: {retail_count}건)")

            print() # 줄바꿈
            
            # 💡 [복구] 결과 요약 출력
            if processed_count == 0:
                print("✨ 모든 데이터가 이미 batch_log에 마감되어 있습니다!")
            else:
                print("🎉 모든 마감 작업이 끝났습니다. batch_log 테이블을 확인해보세요!")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    make_batch_logs()
import pymysql
import hashlib

# DB 접속 정보 (기존과 동일하게 맞춰주세요)
db_config = {
    'host': 'database-1.cdeygca48zyu.ap-northeast-2.rds.amazonaws.com',
    'user': 'team_member1',
    'password': '1234',
    'db': 'project1',
    'charset': 'utf8mb4'
}


def verify_all_layers_deep():
    conn = None
    try:
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        print("🔍 시스템 전체 무결성 딥(Deep) 검증을 시작합니다...\n")

        # ==========================================
        # [1단계] 도매 데이터(Wholesale) 바닥부터 검증
        # ==========================================
        print("▶️ 1단계: 도매 원본 데이터 검증 중...")
        cursor.execute("SELECT * FROM wholesale_transactions")
        wholesale_rows = cursor.fetchall()
        
        for w in wholesale_rows:
            # DB에 적힌 원본 텍스트로 row_hash 다시 만들기
            # 주의: 데이터 타입(시간 등)을 문자열로 정확히 변환해서 결합
            raw_w_str = f"{w['sbid_time']}{w['item_name']}{w['origin_name']}{w['whsal_name']}"
            re_row_hash = hashlib.sha256(raw_w_str.encode()).hexdigest()
            
            if re_row_hash != w['row_hash']:
                print(f"🚨 [도매 조작 적발!] ID {w['id']}번 도매 데이터의 텍스트가 변조되었습니다!")
                return # 즉시 시스템 정지

        print("✅ 1단계 통과: 모든 도매 원본 데이터 안전 확인.\n")


        # ==========================================
        # [2단계] 소매 데이터(Retail) 바닥부터 검증
        # ==========================================
        print("▶️ 2단계: 소매 원본 데이터 검증 중...")
        cursor.execute("SELECT * FROM retail_transactions")
        retail_rows = cursor.fetchall()

        for r in retail_rows:
            # DB에 적힌 원본 텍스트로 curr_hash 다시 만들기 (시간은 형태소 변환 필요할 수 있음)
            sale_date_str = r['sale_date'].strftime('%Y-%m-%d %H:%M:%S')
            raw_r_str = f"{r['prev_hash']}{r['store_name']}{r['sale_price']}{sale_date_str}"
            re_curr_hash = hashlib.sha256(raw_r_str.encode()).hexdigest()
            
            if re_curr_hash != r['curr_hash']:
                print(f"🚨 [소매 조작 적발!] ID {r['id']}번 소매 데이터의 텍스트가 변조되었습니다!")
                return # 즉시 시스템 정지

        print("✅ 2단계 통과: 모든 소매 원본 데이터 안전 확인.\n")


        # ==========================================
        # [3단계] 배치 장부(Batch Log) 최종 도미노 검증
        # ==========================================
        print("▶️ 3단계: 일일 마감 배치 장부 검증 중...")
        cursor.execute("SELECT batch_id, batch_hash, previous_hash FROM batch_log ORDER BY batch_id ASC")
        batch_logs = cursor.fetchall()

        for log in batch_logs:
            target_date = log['batch_id']
            stored_batch_hash = log['batch_hash']
            stored_prev_hash = log['previous_hash']

            # 여기서 가져오는 curr_hash는 2단계에서 이미 '안전'하다고 보증된 진짜 해시들!
            sql_get_retail = "SELECT curr_hash FROM retail_transactions WHERE DATE(sale_date) = %s ORDER BY id"
            cursor.execute(sql_get_retail, (target_date,))
            daily_retail = cursor.fetchall()

            if not daily_retail:
                print(f"🚨 [삭제 변조 적발!] {target_date} 일자의 소매 데이터가 삭제되었습니다!")
                return

            combined_hashes_str = "".join([row['curr_hash'] for row in daily_retail])
            re_pure_hash = hashlib.sha256(combined_hashes_str.encode()).hexdigest()
            re_batch_hash = hashlib.sha256((stored_prev_hash + re_pure_hash).encode()).hexdigest()
            
            if re_batch_hash != stored_batch_hash:
                print(f"🚨 [배치 조작 적발!] {target_date} 일자의 마감 해시가 일치하지 않습니다!")
                return
            
            print(f"  ✔️ [{target_date}] 배치 검증 완료")

        print("\n🛡️ [최종 결과] 도매 원본 텍스트부터 최종 마감 장부까지 100% 안전하게 보호되고 있습니다.")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    verify_all_layers_deep()
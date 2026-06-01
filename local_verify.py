import json
from web3 import Web3
from db_manager import DBManager

def calculate_realtime_hash(data):
    """
    주어진 데이터를 기반으로 실시간 Keccak256 해시를 계산합니다.
    (기존 integrity_check.py와 동일한 방식 사용)
    """
    if not data:
        return ""
    
    def default_serializer(obj):
        return str(obj)
        
    json_string = json.dumps(data, sort_keys=True, separators=(',', ':'), default=default_serializer)
    return Web3.keccak(text=json_string).hex()

def verify_local_db(batch_id):
    """
    블록체인 없이 로컬 DB 데이터만으로 무결성을 검증합니다.
    """
    db = DBManager()
    
    # DB 연결 (출력 생략을 위해 내부적으로만 수행)
    if not db.connect():
        return {"status": "error", "message": "데이터베이스 연결에 실패했습니다."}
    
    try:
        with db.connection.cursor() as cursor:
            # 1. DB에 저장된 '기준 해시(batch_hash)' 조회
            sql_hash = "SELECT batch_hash FROM batch_log WHERE batch_id = %s"
            cursor.execute(sql_hash, (batch_id,))
            result = cursor.fetchone()
            
            if not result:
                return {"status": "error", "message": f"'{batch_id}'에 해당하는 배치를 찾을 수 없습니다."}
            
            stored_hash = result['batch_hash']

            # 2. 해시를 역연산할 '원본 데이터' 조회
            raw_tuples = db.get_raw_tuples_by_batch_id(batch_id)
            
            # 3. 실시간 해시 계산
            # 주의: 현재 get_raw_tuples_by_batch_id는 batch_log 테이블 전체(batch_hash 포함)를 반환합니다.
            realtime_hash = calculate_realtime_hash(raw_tuples)
            
            # 4. 검증 결과 도출
            is_valid = (stored_hash == realtime_hash)

            return {
                "status": "success",
                "batch_id": batch_id,
                "is_valid": is_valid,
                "stored_hash": stored_hash,
                "realtime_hash": realtime_hash
            }
    except Exception as e:
         return {"status": "error", "message": f"검증 중 오류 발생: {e}"}
    finally:
        db.close()

if __name__ == "__main__":
    # 테스트용 배치 ID
    test_batch_id = "2026-04-02"
    
    print("=" * 60)
    print(f"[웹 포털 백엔드용] 로컬 DB 무결성 검증 테스트 (Batch ID: {test_batch_id})")
    print("=" * 60)
    
    result = verify_local_db(test_batch_id)
    
    if result["status"] == "success":
        print(f"DB 저장 해시: {result['stored_hash']}")
        print(f"실시간 해시: {result['realtime_hash']}")
        print("-" * 60)
        if result["is_valid"]:
            print("[PASS] 결과: 무결성 검증 통과 (데이터가 조작되지 않았습니다.)")
        else:
            print("[FAIL] 결과: 무결성 위반! (저장된 해시와 실시간 계산 해시가 다릅니다.)")
    else:
        print(f"[ERROR] 오류: {result['message']}")
    
    print("=" * 60)

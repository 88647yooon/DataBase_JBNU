from db_manager import DBManager
from eth_manager import EthManager
import os

def get_contract_address():
    if not os.path.exists("contract_address.txt"):
        print("contract_address.txt 파일이 없습니다. 먼저 hello.py를 실행하여 컨트랙트를 배포하세요.")
        return None
    with open("contract_address.txt", "r") as f:
        return f.read().strip()

def sync_batch_logs_to_blockchain():
    CONTRACT_ADDRESS = get_contract_address()
    if not CONTRACT_ADDRESS:
        return

    print("=" * 60)
    print("[동기화 시스템 시작] DB batch_log -> 블록체인 업로드")
    print("=" * 60)

    # 1. DB에서 데이터 가져오기
    print("\n[1단계] MySQL 데이터베이스에서 batch_log 조회 중...")
    db_manager = DBManager()
    if not db_manager.connect():
        return

    batch_logs = db_manager.get_all_batch_logs()
    db_manager.close()

    if not batch_logs:
        print("DB에 업로드할 batch_log 데이터가 없습니다.")
        return
    
    print(f"총 {len(batch_logs)}개의 batch_log를 DB에서 성공적으로 가져왔습니다.")

    # 2. 블록체인 연결 및 컨트랙트 설정
    print("\n[2단계] 이더리움 블록체인 연결 및 컨트랙트 로드 중...")
    eth_manager = EthManager()
    if not eth_manager.connect() or not eth_manager.load_contract_data():
        return
    
    if not eth_manager.set_contract(CONTRACT_ADDRESS):
        return

    # 3. 데이터 블록체인에 저장
    print("\n[3단계] 블록체인에 데이터 업로드를 시작합니다...")
    success_count = 0
    for log in batch_logs:
        batch_id = log['batch_id']
        batch_hash = log['batch_hash']
        previous_hash = log['previous_hash']
        
        # datetime 객체를 문자열로 변환
        created_at = log['created_at'].strftime('%Y-%m-%d %H:%M:%S') if log['created_at'] else ""

        print(f" -> 전송 중: Batch ID {batch_id}")
        
        # eth_manager를 통해 블록체인에 저장
        result = eth_manager.store_batch_log(batch_id, batch_hash, previous_hash, created_at)
        if result:
            success_count += 1
        else:
            print(f"    [실패] Batch ID: {batch_id} 저장 실패")

    print("\n" + "=" * 60)
    print(f"최종 결과: 총 {len(batch_logs)}개 중 {success_count}개 성공적으로 블록체인에 업로드 완료!")
    print("=" * 60)

if __name__ == "__main__":
    sync_batch_logs_to_blockchain()

from db_manager import DBManager
from eth_manager import EthManager
import time
import os
import json
from web3 import Web3

def get_contract_address():
    if not os.path.exists("contract_address.txt"):
        print("contract_address.txt 파일이 없습니다. 먼저 hello.py를 실행하여 컨트랙트를 배포하세요.")
        return None
    with open("contract_address.txt", "r") as f:
        return f.read().strip()

def calculate_realtime_hash(tuples_list):
    
    if not tuples_list:
        return ""
    
   
    def default_serializer(obj):
        return str(obj)
        
    # 딕셔너리 키 정렬(sort_keys=True) 및 공백 제거로 항상 동일한 문자열이 생성되도록 보장
    json_string = json.dumps(tuples_list, sort_keys=True, separators=(',', ':'), default=default_serializer)
    return Web3.keccak(text=json_string).hex()

def check_integrity():
    CONTRACT_ADDRESS = get_contract_address()
    if not CONTRACT_ADDRESS:
        return

    print("=" * 60)
    print("[무결성 검사 시스템 시작] 블록체인 ↔ DB 관계형 검증")
    print("=" * 60)

    # 1. 블록체인(Geth) 연결 및 데이터 가져오기
    print("\n[1단계] 이더리움 블록체인에서 신뢰할 수 있는 데이터(원본) 조회 중...")
    eth_manager = EthManager()
    if not eth_manager.connect() or not eth_manager.load_contract_data():
        return
    eth_manager.set_contract(CONTRACT_ADDRESS)
    
    if not eth_manager.contract:
        return

    chain_logs = []
    try:
        count = eth_manager.contract.functions.getLogsCount().call()
        for i in range(count):
            log_data = eth_manager.contract.functions.getLog(i).call()
            # Solidity 반환: (batchId, batchHash, previousHash, createdAt)
            chain_logs.append({
                'batch_id': log_data[0],
                'batch_hash': log_data[1],
                'previous_hash': log_data[2],
                'created_at': log_data[3]
            })
        print(f"블록체인에서 총 {len(chain_logs)}개의 로그를 성공적으로 가져왔습니다.")
    except Exception as e:
        print(f"블록체인 조회 실패: {e}")
        return

    # 2. 데이터베이스(MySQL) 연결 및 데이터 가져오기
    print("\n[2단계] MySQL 데이터베이스 연결 중...")
    db_manager = DBManager()
    if not db_manager.connect():
        return

    # 3. 무결성 대조 검사 (핵심 로직)
    print("\n[3단계] 데이터 무결성 검증을 시작합니다...")
    time.sleep(1) # 시각적인 효과를 위해 1초 대기

    is_tampered = False
    
    # --- 3.0 블록체인 로그 개수와 DB 로그 개수 비교 ---
    db_logs = db_manager.get_all_batch_logs()
    if len(chain_logs) != len(db_logs):
        print(f"\n[무결성 위반 발견!] 블록체인 로그 개수({len(chain_logs)})와 DB 로그 개수({len(db_logs)})가 일치하지 않습니다.")
        is_tampered = True

    with db_manager.connection.cursor() as cursor:
        for i in range(len(chain_logs)):
            chain_log = chain_logs[i]
            batch_id = chain_log['batch_id']
            chain_batch_hash = chain_log['batch_hash']
            
            # --- 3.1 블록체인 ↔ batch_log 대조 ---
            cursor.execute("SELECT batch_hash FROM batch_log WHERE batch_id = %s", (batch_id,))
            db_batch_row = cursor.fetchone()
            
            if not db_batch_row:
                print(f"\n[무결성 위반 발견!] Batch ID: {batch_id} - DB의 batch_log에 데이터가 존재하지 않습니다.")
                is_tampered = True
                continue
                
            db_batch_hash = db_batch_row['batch_hash']
            if chain_batch_hash != db_batch_hash:
                print(f"\n[무결성 훼손 발견!] Batch ID: {batch_id} - 블록체인 해시와 batch_log 테이블 해시가 불일치합니다!")
                print(f"  블록체인 Hash: {chain_batch_hash}")
                print(f"  batch_log Hash: {db_batch_hash}")
                is_tampered = True
            
            # --- 3.2 블록체인 체인 검증 ---
            if i > 0:
                prev_chain_log = chain_logs[i-1]
                if chain_log['previous_hash'] != prev_chain_log['batch_hash']:
                    print(f"\n[블록체인 논리 오류!] 인덱스 {i}의 hash 조작 의심.")
                    is_tampered = True

    print("\n" + "=" * 60)
    if is_tampered:
        print("최종 결과: 무결성이 심각하게 훼손되었습니다! (블록체인과 DB 데이터 불일치)")
    else:
        print("최종 결과: 무결성 검증 통과! 블록체인과 DB의 batch_log 데이터가 일치합니다.")
            
    print("=" * 60)
    
    db_manager.close() # 작업이 끝난 후 안전하게 연결 종료

if __name__ == "__main__":
    check_integrity()

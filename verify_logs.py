import os
from eth_manager import EthManager

def verify():
    if not os.path.exists("contract_address.txt"):
        print("contract_address.txt 파일이 없습니다. 먼저 hello.py를 실행하여 컨트랙트를 배포하세요.")
        return
        
    with open("contract_address.txt", "r") as f:
        CONTRACT_ADDRESS = f.read().strip()


    print("--- Ethereum 네트워크에서 데이터 조회 ---")
    eth_manager = EthManager()
    if not eth_manager.connect():
        return
        
    if not eth_manager.load_contract_data():
        return
        
    # 이미 배포된 컨트랙트 주소로 연결
    eth_manager.set_contract(CONTRACT_ADDRESS)
    
    if not eth_manager.contract:
        return
        
    try:
        # 스마트 컨트랙트의 getLogsCount() 함수 호출 (view 함수이므로 가스비가 들지 않음)
        count = eth_manager.contract.functions.getLogsCount().call()
        print(f"\n블록체인에 저장된 총 로그 개수: {count}개")
        
        # 저장된 모든 로그를 인덱스로 순회하며 조회
        for i in range(count):
            # getLog(index) 호출
            log_data = eth_manager.contract.functions.getLog(i).call()
            # 반환값은 (batchId, batchHash, previousHash, createdAt) 튜플 형태입니다.
            print(f"\n[인덱스 {i}]")
            print(f"  Batch ID     : {log_data[0]}")
            print(f"  Batch Hash   : {log_data[1]}")
            print(f"  Previous Hash: {log_data[2]}")
            print(f"  Created At   : {log_data[3]}")
            
    except Exception as e:
        print(f"데이터 조회 중 오류 발생: {e}")

if __name__ == "__main__":
    verify()

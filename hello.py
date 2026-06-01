from eth_manager import EthManager

def main():
    print("--- Ethereum 연결 및 컨트랙트 배포 시도 ---")
    eth_manager = EthManager()
    if not eth_manager.connect():
        return
        
    if not eth_manager.load_contract_data():
        return
        
    contract_address = eth_manager.deploy_contract()
    
    if not contract_address:
        print("컨트랙트 배포에 실패하여 프로세스를 종료합니다.")
        return
        
    with open("contract_address.txt", "w") as f:
        f.write(contract_address)
    print(f"컨트랙트 주소를 contract_address.txt 에 저장했습니다.")
    print("\n컨트랙트 배포가 완료되었습니다. 이제 sync_to_blockchain.py를 실행하여 데이터를 업로드하세요.")

if __name__ == "__main__":
    main()

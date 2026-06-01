import json
import sys
from web3 import Web3

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

class EthManager:
    def __init__(self, rpc_url='http://127.0.0.1:8545'):
        self.rpc_url = rpc_url
        # Geth 노드에 연결합니다.
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.account = None
        self.contract = None
        self.abi = None
        self.bytecode = None

    def connect(self):
        if self.w3.is_connected():
            latest_block_number = self.w3.eth.block_number
            print(f"Geth 노드 연결 성공 (현재 블록 번호: {latest_block_number})")
            
            accounts = self.w3.eth.accounts
            if accounts:
                self.account = accounts[0]  # 기본적으로 첫 번째 계정 사용
                self.w3.eth.default_account = self.account
                print(f"사용할 계정: {self.account}")
            else:
                print("사용할 수 있는 계정이 없습니다. 노드에 계정을 생성하세요.")
            return True
        else:
            print("Geth 노드 연결 실패 (--http 옵션 확인 필)")
            return False

    def load_contract_data(self):
        """abi.json과 bytecode.json 파일을 읽어옵니다."""
        try:
            with open('abi.json', 'r', encoding='utf-8') as f:
                self.abi = json.load(f)
            
            with open('bytecode.json', 'r', encoding='utf-8') as f:
                bytecode_data = json.load(f)
                # Remix에서 복사한 경우 보통 'object' 키 안에 바이트코드가 있습니다.
                if isinstance(bytecode_data, dict) and 'object' in bytecode_data:
                    self.bytecode = bytecode_data['object']
                else:
                    self.bytecode = bytecode_data
            
            print("ABI 및 Bytecode 로드 성공")
            return True
        except Exception as e:
            print(f"ABI 또는 Bytecode 파일 로드 실패: {e}")
            return False

    def deploy_contract(self):
        """스마트 컨트랙트를 Geth 네트워크에 배포합니다."""
        if not self.account or not self.abi or not self.bytecode:
            print("배포 준비가 되지 않았습니다. 계정 연결 및 컨트랙트 데이터를 확인하세요.")
            return None
        
        print("\n--- 스마트 컨트랙트 배포 시작 ---")
        # 주의: 이 시점에서 self.account는 unlock 상태여야 합니다.
        
        contract = self.w3.eth.contract(abi=self.abi, bytecode=self.bytecode)
        
        try:
            # 컨트랙트 배포 트랜잭션 전송
            tx_hash = contract.constructor().transact()
            print(f"트랜잭션 해시: {tx_hash.hex()}")
            print("블록에 기록될 때까지 대기 중... (마이닝이 진행 중이어야 합니다)")
            
            # 트랜잭션 영수증을 기다림
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"컨트랙트 배포 완료! 주소: {tx_receipt.contractAddress}")
            
            # 배포된 컨트랙트 객체 생성
            self.contract = self.w3.eth.contract(
                address=tx_receipt.contractAddress,
                abi=self.abi
            )
            return tx_receipt.contractAddress
        except Exception as e:
            print(f"컨트랙트 배포 실패: {e}")
            return None
            
    def set_contract(self, contract_address):
        """이미 배포된 컨트랙트가 있을 경우 주소로 연결합니다."""
        if self.abi:
            code = self.w3.eth.get_code(contract_address)
            if code == b'' or code.hex() == '0x' or code == '0x':
                print(f"해당 주소({contract_address})에 배포된 컨트랙트가 없습니다.")
                print("Geth 노드가 초기화되었을 수 있습니다. hello.py를 다시 실행하여 컨트랙트를 새로 배포해주세요.")
                self.contract = None
                return False
                
            self.contract = self.w3.eth.contract(address=contract_address, abi=self.abi)
            print(f"기존 컨트랙트 연결 완료: {contract_address}")
            return True
        else:
            print("ABI 데이터가 로드되지 않았습니다.")
            return False

    def store_batch_log(self, batch_id, batch_hash, previous_hash, created_at):
        """Geth 네트워크의 스마트 컨트랙트에 데이터를 저장합니다."""
        if not self.contract:
            print("컨트랙트가 설정되지 않았습니다.")
            return False
            
        print(f"로그 저장 시도: ID={batch_id}, Hash={batch_hash[:10]}...")
        try:
            # 상태 변경을 발생시키는 트랜잭션 (가스비 소모)
            tx_hash = self.contract.functions.storeBatchLog(
                batch_id, batch_hash, previous_hash, created_at
            ).transact()
            
            # 영수증 대기
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"블록체인 저장 완료! (블록 번호: {receipt.blockNumber}, 트랜잭션 해시: {tx_hash.hex()})")
            return True
        except Exception as e:
            print(f"저장 실패: {e}")
            return False

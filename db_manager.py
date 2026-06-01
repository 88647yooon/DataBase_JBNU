import pymysql
import os
from dotenv import load_dotenv

class DBManager:
    def __init__(self):
        load_dotenv()
        self.host = os.getenv('DB_HOST')
        self.user = os.getenv('DB_USER')
        self.password = os.getenv('DB_PASSWORD')
        self.database = os.getenv('DB_NAME')
        self.connection = None

    def connect(self):
        try:
            self.connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                cursorclass=pymysql.cursors.DictCursor
            )
            print("AWS MySQL 데이터베이스에 성공적으로 연결되었습니다!")
            return True
        except pymysql.MySQLError as e:
            print(f"데이터베이스 연결 중 오류 발생: {e}")
            return False

    # --- 추가된 확인용 메서드 1: 테이블 목록 보기 ---
    def show_all_tables(self):
        if not self.connection:
            print("연결이 되어 있지 않습니다.")
            return

        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                print(f"\n'{self.database}' 데이터베이스의 테이블 목록:")
                if not tables:
                    print("   (생성된 테이블이 없습니다.)")
                for table in tables:
                    # DictCursor는 {'Tables_in_db명': '테이블명'} 형태이므로 값만 추출
                    print(f"   - {list(table.values())[0]}")
                
                # batch_log 테이블의 모든 데이터(투플) 출력
                cursor.execute("SELECT * FROM batch_log")
                rows = cursor.fetchall()
                print(f"\n'batch_log' 테이블의 모든 투플:")
                if not rows:
                    print("   (데이터가 없습니다.)")
                for row in rows:
                    print(f"   {row}")
        except Exception as e:
            print(f"테이블 목록 조회 실패: {e}")

    # --- 추가된 확인용 메서드 2: 특정 테이블 데이터 확인 ---
    def check_table_data(self, table_name, limit=5):
        if not self.connection:
            return

        try:
            with self.connection.cursor() as cursor:
                # SQL 인젝션 방지를 위해 f-string 대신 조심해서 사용 (테이블명은 동적 바인딩이 안 됨)
                sql = f"SELECT * FROM {table_name} LIMIT {limit}"
                cursor.execute(sql)
                rows = cursor.fetchall()
                
                print(f"\n'{table_name}' 테이블 상위 {limit}개 데이터:")
                if not rows:
                    print("   (데이터가 비어 있습니다.)")
                else:
                    for row in rows:
                        print(f"   {row}")
        except Exception as e:
            print(f"'{table_name}' 데이터 조회 실패: {e}")

    def get_all_batch_logs(self):
        """batch_log 테이블의 모든 데이터를 리스트 형태로 반환합니다."""
        if not self.connection:
            print("연결이 되어 있지 않습니다.")
            return []

        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT * FROM batch_log")
                rows = cursor.fetchall()
                return rows
        except Exception as e:
            print(f"데이터 조회 실패: {e}")
            return []

    def get_raw_tuples_by_batch_id(self, batch_id):
        """특정 배치 ID에 속한 원본 투플(물류 데이터)들을 DB에서 조회합니다."""
        if not self.connection:
            return []
        try:
            with self.connection.cursor() as cursor:
                # retail_transactions 테이블에서 해당 날짜(batch_id)의 데이터를 원본으로 가져옵니다.
                sql = "SELECT * FROM retail_transactions WHERE DATE(sale_date) = %s ORDER BY id"
                cursor.execute(sql, (batch_id,))
                return cursor.fetchall()
        except Exception as e:
            print(f"원본 투플 조회 실패 (batch_id={batch_id}): {e}")
            return []

    def close(self):
        if self.connection:
            self.connection.close()
            print("데이터베이스 연결이 안전하게 종료되었습니다.")

# --- 실행부 ---
if __name__ == "__main__":
    db = DBManager()
    if db.connect():
      db.show_all_tables()
        
    db.close()
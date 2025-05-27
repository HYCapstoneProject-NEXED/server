from sqlalchemy import create_engine, text  # 📌 text() 추가
from sqlalchemy.orm import sessionmaker, declarative_base  # 📌 SQLAlchemy 2.0 대응
import pymysql

# 📌 pymysql을 MySQL 드라이버로 사용하도록 설정
pymysql.install_as_MySQLdb()

# MySQL 연결 정보
DATABASE_URL = "mysql+pymysql://root:1234@localhost:3306/mydatabase"

# SQLAlchemy 엔진 생성
engine = create_engine(DATABASE_URL)

# 세션 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 📌 SQLAlchemy 2.0 방식으로 변경
Base = declarative_base()

# 데이터베이스 세션을 가져오는 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 📌 MySQL 연결 테스트 함수 (SQLAlchemy 2.0 방식)
def test_mysql_connection():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT VERSION();"))  # 📌 text() 사용
            mysql_version = result.scalar()  # 📌 단일 값 가져오기
            print(f"✅ MySQL 연결 성공! 버전: {mysql_version}")
    except Exception as e:
        print(f"❌ MySQL 연결 실패: {e}")

# 📌 스크립트 실행 시 MySQL 연결 테스트
if __name__ == "__main__":
    test_mysql_connection()

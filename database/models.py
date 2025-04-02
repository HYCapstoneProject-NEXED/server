from sqlalchemy import Column, Integer, String, Date, Boolean
from database.database import Base

class User(Base):
    __tablename__ = "Users"

    user_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)  # PK, 중복 불가능
    google_email = Column(String(255), unique=True, nullable=False)  # 이메일, 중복 불가능, 필수
    name = Column(String(255), nullable=False)  # 이름, 중복 가능, 필수
    user_type = Column(String(255), nullable=False)  # 사용자 타입, 필수
    birthdate = Column(Date, nullable=False)  # 생년월일 (YYYY-MM-DD), 필수
    nationality = Column(String(255), nullable=False)  # 국적, 필수
    address = Column(String(255), nullable=True)  # 주소, 선택 사항
    company_name = Column(String(255), nullable=False)  # 회사명, 필수
    factory_name = Column(String(255), nullable=False)  # 공장명, 필수
    bank_name = Column(String(255), nullable=False)  # 은행명, 필수
    bank_account = Column(String(255), unique=True, nullable=False)  # 계좌번호, 중복 불가능, 필수
    terms_accepted = Column(Boolean, nullable=False)  # 약관 동의, 필수

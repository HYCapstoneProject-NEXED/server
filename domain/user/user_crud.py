from sqlalchemy.orm import Session
from database.models import User
from domain.user.user_schema import UserBase

# 특정 Google 이메일을 가진 사용자 조회
def get_user_by_email(db: Session, google_email: str):
    return db.query(User).filter(User.google_email == google_email).first()

from sqlalchemy.orm import Session

def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.user_id == user_id).first()

# 사용자 등록
def create_user(db: Session, user_data: UserBase):
    user = User(
        google_email=user_data.google_email,
        name=user_data.name,
        user_type=user_data.user_type,
        birthdate=user_data.birthdate,
        nationality=user_data.nationality,
        address=user_data.address,
        company_name=user_data.company_name,
        factory_name=user_data.factory_name,
        bank_name=user_data.bank_name,
        bank_account=user_data.bank_account,
        terms_accepted=user_data.terms_accepted,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

from sqlalchemy.orm import Session
from domain.user.user_schema import UserUpdate
from database.models import User

def update_user_info(db: Session, user: User, user_update: UserUpdate) -> User:
    """
    ✅ 기존 사용자 정보 업데이트 함수
    - 필수 정보가 모두 입력된 경우에만 업데이트 실행
    """
    user.name = user_update.name
    user.user_type = user_update.user_type
    user.birthdate = user_update.birthdate
    user.nationality = user_update.nationality
    user.address = user_update.address  # 주소는 선택 사항
    user.company_name = user_update.company_name
    user.factory_name = user_update.factory_name
    user.bank_name = user_update.bank_name
    user.bank_account = user_update.bank_account
    user.terms_accepted = user_update.terms_accepted  # 약관 동의 여부

    db.commit()
    db.refresh(user)  # 변경 사항 반영
    return user


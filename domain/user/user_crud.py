from sqlalchemy.orm import Session
from database.models import User
from domain.user.user_schema import UserBase, UserUpdate, UserTypeEnum
from typing import List, Optional
from sqlalchemy import or_


# 특정 Google 이메일을 가진 사용자 조회
def get_user_by_email(db: Session, google_email: str):
    return db.query(User).filter(User.google_email == google_email).first()


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
        profile_image=user_data.profile_image,
        is_active=False  # ✅ 항상 False로 고정
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


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
    user.profile_image = user_update.profile_image

    db.commit()
    db.refresh(user)  # 변경 사항 반영
    return user


# 멤버 목록 조회용 함수
def get_members(
        db: Session,
        role: Optional[UserTypeEnum] = None,  # 🔹 타입 명시
        search: Optional[str] = None
) -> List[User]:
    query = db.query(User).filter(User.is_active == True)  # is_active=True인 멤버만 조회되도록 필터링

    # 역할 필터링
    if isinstance(role, UserTypeEnum) and role != UserTypeEnum.all_roles:
        query = query.filter(User.user_type == role.value)

    # 이름 또는 이메일 검색
    if search:
        keyword = f"%{search}%"
        query = query.filter(
            or_(
                User.name.ilike(keyword),
                User.google_email.ilike(keyword)
            )
        )

    # 최신 등록 순 정렬(user_id 기준)
    query = query.order_by(User.user_id.desc())

    return query.all()



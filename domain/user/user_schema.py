from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import date

# 사용자 기본 스키마
class UserBase(BaseModel):
    google_email: EmailStr  # 이메일은 필수
    name: Optional[str] = None
    user_type: Optional[str] = None
    birthdate: Optional[date] = None  # 날짜 값도 None 허용
    nationality: Optional[str] = None
    address: Optional[str] = None  # 선택 사항 (nullable=True)
    company_name: Optional[str] = None
    factory_name: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    terms_accepted: Optional[bool] = False  # 기본값 False


# 사용자 응답 스키마 (user_id 포함)
class UserResponse(UserBase):
    user_id: int

    model_config = ConfigDict(from_attributes=True)  # 📌 Pydantic v2 호환을 위해 추가!


class UserUpdate(BaseModel):
    name: Optional[str]
    user_type: Optional[str]
    birthdate: Optional[date]
    nationality: Optional[str]
    address: Optional[str]  # 선택 사항s
    company_name: Optional[str]
    factory_name: Optional[str]
    bank_name: Optional[str]
    bank_account: Optional[str]
    terms_accepted: Optional[bool]  # 헉 여기를 true로 하면 아까 그거 빼도 되지 않나?


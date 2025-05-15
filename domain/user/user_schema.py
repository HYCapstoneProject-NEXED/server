from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, Union
from datetime import date
from enum import Enum


# 실제 DB 저장용 (all_roles 제외)
class UserTypeEnum(str, Enum):
    admin = "admin"
    customer = "customer"
    ml_engineer = "ml_engineer"
    annotator = "annotator"


class ApprovalStatusEnum(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class GenderEnum(str, Enum):
    female = "female"
    male = "male"


# 사용자 기본 스키마
class UserBase(BaseModel):
    google_email: EmailStr  # 이메일은 필수
    name: Optional[str] = None
    user_type: Optional[UserTypeEnum] = None
    birthdate: Optional[date] = None  # 날짜 값도 None 허용
    nationality: Optional[str] = None
    address: Optional[str] = None  # 선택 사항 (nullable=True)
    company_name: Optional[str] = None
    factory_name: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    terms_accepted: Optional[bool] = None
    profile_image: Optional[str] = None  # 프로필 이미지 경로, 선택 사항
    gender: Optional[GenderEnum] = None  # 성별


# 사용자 응답 스키마 (user_id 포함)
class UserResponse(UserBase):
    user_id: int
    is_active: bool  # 유저 활성 여부 (회원가입 승인 전까지 False)
    approval_status: ApprovalStatusEnum  # 가입 승인 상태 (회원가입 승인 전까지 "pending")

    model_config = ConfigDict(from_attributes=True)  # 📌 Pydantic v2 호환을 위해 추가!


class UserUpdate(BaseModel):
    name: Optional[str]
    user_type: Optional[str]
    birthdate: Optional[date]
    nationality: Optional[str]
    company_factory: Optional[str]  # '회사명/공장명' 하나의 문자열로 받음
    bank_name: Optional[str]
    bank_account: Optional[str]
    terms_accepted: Optional[bool]
    gender: Optional[GenderEnum]


# 조회 필터용 (all_roles 포함)
class UserTypeFilterEnum(str, Enum):
    all_roles = "all_roles"
    admin = "admin"
    customer = "customer"
    ml_engineer = "ml_engineer"
    annotator = "annotator"


# 멤버 목록 조회 응답용 스키마
class UserSummary(BaseModel):
    user_id: int
    name: str
    user_type: str
    google_email: EmailStr
    profile_image: Optional[str] = None

    class Config:
        orm_mode = True


# 멤버 역할 변경 요청용 스키마
class UserRoleUpdate(BaseModel):
    user_type: UserTypeEnum


# 멤버 삭제 응답용 스키마
class UserDeleteResponse(BaseModel):
    user_id: int
    is_active: bool

    class Config:
        orm_mode = True


# 가입 승인 요청 목록 조회 응답용 스키마
class PendingUserResponse(BaseModel):
    user_id: int
    name: str
    google_email: EmailStr
    user_type: UserTypeEnum
    birthdate: date
    gender: GenderEnum

    class Config:
        orm_mode = True


class ApprovalActionEnum(str, Enum):
    approve = "approve"
    reject = "reject"


# 가입 승인 처리 요청용 스키마
class ApprovalRequest(BaseModel):
    action: ApprovalActionEnum


# 작업자별 작업 개요 조회 응답용 스키마
class WorkerOverview(BaseModel):
    user_name: str
    work_count: int

    class Config:
        orm_mode = True


# 작업자별 작업 개요 조회 요청용 스키마
class WorkerOverviewFilter(BaseModel):
    user_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    search: Optional[str] = None  # user_name 검색


# 작업 기록 조회 필터용 사용자 목록 조회 응답용 스키마
class AnnotatorName(BaseModel):
    user_id: int
    name: str

    class Config:
        orm_mode = True
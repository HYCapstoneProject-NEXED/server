from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# 결함 클래스 목록 조회/결함 클래스 추가 응답용 모델
class DefectClassResponse(BaseModel):
    class_id: int
    class_name: str
    class_color: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# 결함 클래스 추가 요청용 모델
class DefectClassCreate(BaseModel):
    class_name: str = Field(..., example="Scratch")
    class_color: str = Field(..., example="#dbe4ff")


# 수정 요청용 Pydantic 모델
class DefectClassUpdate(BaseModel):
    class_name: Optional[str] = Field(None, example="New Name")
    class_color: Optional[str] = Field(None, example="#abcdef")


# 삭제 요청 응답 스키마
class DeleteResult(BaseModel):
    success: bool
    message: str

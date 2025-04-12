from pydantic import BaseModel, Field
from datetime import datetime

# DefectClass 조회 응답 모델
class DefectClassResponse(BaseModel):
    class_id: int
    class_name: str
    class_color: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
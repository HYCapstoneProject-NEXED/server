from pydantic import BaseModel
from datetime import datetime

# 사진 업로드 응답용 스키마
class ImageUploadResponse(BaseModel):
    image_id: int
    file_path: str
    date: datetime

    class Config:
        from_attributes = True  # ✅ Pydantic v2용 설정 (v1에서는 orm_mode=True)
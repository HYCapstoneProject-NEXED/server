from pydantic import BaseModel
from datetime import datetime
from domain.yolo.yolo_schema import BoundingBox  # 기존 추론 스키마 가져오기
from typing import List


# 사진 업로드 응답용 스키마
class ImageUploadResponse(BaseModel):
    image_id: int
    file_path: str
    date: datetime
    results: List[BoundingBox]  # 모델 추론 결과 필드 추가

    class Config:
        from_attributes = True  # Pydantic v2용 설정 (v1에서는 orm_mode=True)
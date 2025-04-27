from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime, date


class DefectCountInfo(BaseModel):
    count: int
    color: str  # HEX 색상 (예: "#dbe4ff")
    change: int  # 전일 대비 증감 수치


class DefectSummaryResponse(BaseModel):
    total_defect_count: int
    most_frequent_defect: str  # class_name
    defect_counts_by_type: Dict[str, DefectCountInfo]  # class_name -> {count, color}

    class Config:
        orm_mode = True


# 조회 응답용 DefectDataItem 스키마 추가
class DefectDataItem(BaseModel):
    image_id: int
    file_path: str
    line_id: str
    camera_id: int
    captured_at: datetime
    defect_types: List[str]

    class Config:
        orm_mode = True


# 필터용 QuerySchema 추가
class DefectDataFilter(BaseModel):
    dates: Optional[List[date]] = None
    class_ids: Optional[List[int]] = None
    camera_ids: Optional[List[int]] = None

# 결함 개요 조회 응답용 스키마
class DefectClassSummaryResponse(BaseModel):
    class_name: str
    class_color: str
    count: int

    class Config:
        orm_mode = True

class DefectDetail(BaseModel):
    annotation_id: int
    class_id: int
    class_name: str
    class_color: str
    conf_score: float
    bounding_box: Dict[str, Any]
    status: str
    user_id: int

class AnnotationDetailResponse(BaseModel):
    image_id: int
    file_path: str
    date: datetime
    camera_id: int
    dataset_id: int
    defects: List[DefectDetail]

    class Config:
        orm_mode = True

class ImageSummary(BaseModel):
    camera_id: int
    image_id: int
    file_path: str
    confidence: Optional[float]
    count: int
    status: str
    bounding_boxes: List[Dict[str, Any]]

    class Config:
        from_attributes = True

class MainScreenResponse(BaseModel):
    profile_image: Optional[str]
    total_images: int
    pending_images: int
    completed_images: int
    image_list: List[ImageSummary]
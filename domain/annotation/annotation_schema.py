from pydantic import BaseModel
from typing import Dict, List, Any
from datetime import datetime


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
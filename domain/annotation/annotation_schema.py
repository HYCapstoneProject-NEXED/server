from pydantic import BaseModel
from typing import Dict, List, Optional, Any, Literal
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


# 실시간 결함 탐지 이력 조회 응답용 스키마
class RealtimeCheckResponse(BaseModel):
    image_url: str  # 이미지 파일 경로
    line_name: str  # 카메라 라인 id
    camera_id: int  # 카메라 id
    time: str  # annotation 생성 시각
    type: List[str]  # 결함 종류 리스트 ex: ["Crack", "Burr"])

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


# 결함 유형별 통계 조회 응답용 스키마
class DefectTypeStatistics(BaseModel):
    class_name: str
    class_color: str
    count: int
    percentage: float

    class Config:
        orm_mode = True


# 주간 요일별 결함 통계 조회 응답용 스키마
class DefectCount(BaseModel):
    class_name: str
    class_color: str
    count: int

class WeekdayDefectSummary(BaseModel):
    day: str
    total: int
    defect_counts: List[DefectCount]

class WeekdayDefectSummaryResponse(BaseModel):
    result: List[WeekdayDefectSummary]


# 기간별 결함 통계 조회 응답용 스키마
class DateRange(BaseModel):
    start: date
    end: date

class Filters(BaseModel):
    defect_type: Optional[List[str]] = None
    camera_ids: Optional[List[int]] = None

class DefectStatisticsItem(BaseModel):
    date: Optional[str] = None  # YYYY-MM-DD (week/month) or YYYY-MM (year)
    label: Optional[str] = None  # defect_type or camera_id
    defect_count: int
    class_color: Optional[str] = None  # defect_type일 경우에만 포함

class DefectStatisticsResponse(BaseModel):
    date_range: DateRange
    unit: Literal["week", "month", "year", "custom"]
    filters: Filters
    data: List[DefectStatisticsItem]


class DeleteImagesRequest(BaseModel):
    image_ids: List[int]

class DeleteImagesResponse(BaseModel):
    success: bool
    message: str
    deleted_ids: List[int]

    class Config:
        orm_mode = True


class UpdateImageStatusRequest(BaseModel):
    image_id: int
    status: str  # "pending" 또는 "completed"

class UpdateImageStatusResponse(BaseModel):
    success: bool
    message: str
    image_id: int
    new_status: str

    class Config:
        orm_mode = True


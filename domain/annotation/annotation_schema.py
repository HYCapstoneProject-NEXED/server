from pydantic import BaseModel
from typing import Dict, List, Optional, Any, Literal, Union
from datetime import datetime, date


class DefectCountInfo(BaseModel):
    count: int
    color: str  # HEX 색상 (예: "#dbe4ff")
    change: int  # 전일 대비 증감 수치


# 금일 결함 개요 조회 응답용 스키마
class DefectSummaryResponse(BaseModel):
    total_defect_count: int
    most_frequent_defect: Optional[List[str]]  # class_name, 🔹 None 허용, 최다 발생 유형이 여러 개일 수도!
    defect_counts_by_type: Dict[str, DefectCountInfo]  # class_name -> {count, color}

    class Config:
        orm_mode = True


# 결함 데이터 목록 조회 응답용 스키마
class DefectDataItem(BaseModel):
    image_id: int
    file_path: str
    line_name: str
    camera_id: int
    captured_at: datetime
    defect_types: List[str]

    class Config:
        orm_mode = True


# 결함 데이터 목록 조회 요청용 스키마
class DefectDataFilter(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
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
    user_id: int


class AnnotationDetailResponse(BaseModel):
    image_id: int
    file_path: str
    date: datetime
    camera_id: int
    dataset_id: int
    width: int
    height: int
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


class MainScreenFilter(BaseModel):
    status: Optional[str] = None
    class_names: Optional[List[str]] = None
    min_confidence: Optional[float] = None
    max_confidence: Optional[float] = None


class FilteredImageListRequest(BaseModel):
    class_names: Optional[List[str]] = None
    status: Optional[str] = None
    min_confidence: Optional[float] = None
    max_confidence: Optional[float] = None

class FilteredImageListResponse(BaseModel):
    image_list: List[ImageSummary]

    class Config:
        orm_mode = True


class AnnotationDetailListResponse(BaseModel):
    details: List[AnnotationDetailResponse]

    class Config:
        orm_mode = True


# 작업 기록 조회 응답용 스키마
class AnnotationHistoryResponse(BaseModel):
    image_id: int
    user_name: Optional[str]
    annotation_date: datetime
    image_status: str

    class Config:
        orm_mode = True


# 작업 기록 조회 요청용 스키마
class AnnotationHistoryFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    user_name: Optional[str] = None
    search: Optional[str] = None  # user_name (문자열) 검색


class AnnotationBase(BaseModel):
    class_id: int
    bounding_box: dict

class AnnotationCreate(AnnotationBase):
    pass

class AnnotationUpdate(AnnotationBase):
    annotation_id: int

class AnnotationResponse(AnnotationBase):
    annotation_id: int
    date: datetime
    conf_score: float
    user_id: int

    class Config:
        from_attributes = True

class AnnotationBulkUpdate(BaseModel):
    annotations: List[AnnotationCreate]
    existing_annotations: List[AnnotationUpdate]
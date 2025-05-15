from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class AnnotatorStats(BaseModel):
    user_id: int
    username: str
    assigned_cameras_count: int
    assigned_images_count: int

class UnassignedCameraStats(BaseModel):
    camera_id: int
    image_count: int

class TaskAssignmentStats(BaseModel):
    total_cameras: int
    assigned_cameras: int
    total_images: int
    assigned_images: int
    unassigned_cameras: List[UnassignedCameraStats]
    annotators: List[AnnotatorStats]

class CameraImageStats(BaseModel):
    camera_id: int
    image_count: int

class UserCameraStats(BaseModel):
    user_id: int
    username: str
    cameras: List[CameraImageStats]

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

class CameraAssignment(BaseModel):
    user_id: int
    camera_ids: List[int] 
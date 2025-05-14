from pydantic import BaseModel
from typing import List, Optional

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
# domain/yolo_schema.py

from pydantic import BaseModel
from typing import List

class Box(BaseModel):
    x_center: float
    y_center: float
    w: float
    h: float

class BoundingBox(BaseModel):
    class_id: int
    confidence: float
    bounding_box: Box

class PredictResponse(BaseModel):
    results: List[BoundingBox]

from pydantic import BaseModel
from typing import List

class BoundingBox(BaseModel):
    box: List[float]  # [x1, y1, x2, y2]

class PredictResponse(BaseModel):
    results: List[BoundingBox]

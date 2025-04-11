from pydantic import BaseModel
from typing import Dict


class DefectSummaryResponse(BaseModel):
    total_defect_count: int
    most_frequent_defect: str
    defect_counts_by_type: Dict[str, Dict[str, int]]

    class Config:
        orm_mode = True
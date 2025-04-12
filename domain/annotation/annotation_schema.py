from pydantic import BaseModel
from typing import Dict


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
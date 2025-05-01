from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.database import get_db
from domain.annotation import annotation_crud, annotation_schema
from typing import List


router = APIRouter(
    prefix="/annotations",
    tags=["Annotations"]
)

@router.get("/summary", response_model=annotation_schema.DefectSummaryResponse)
def get_defect_summary_with_change(db: Session = Depends(get_db)):
    return annotation_crud.get_defect_summary(db)

@router.post("/defect-data/list", response_model=List[annotation_schema.DefectDataItem])
def get_defect_data_list_api(
    filters: annotation_schema.DefectDataFilter,
    db: Session = Depends(get_db)
):
    return annotation_crud.get_filtered_defect_data_list(db, filters)

@router.get("/class-summary", response_model=list[annotation_schema.DefectClassSummaryResponse])
def read_defect_class_summary(db: Session = Depends(get_db)):
    return annotation_crud.get_defect_class_summary(db)

@router.get("/realtime-check", response_model=list[annotation_schema.RealtimeCheckResponse])
def get_realtime_check_list(db: Session = Depends(get_db)):
    raw_data = annotation_crud.get_recent_defect_checks(db)

    result = []
    for row in raw_data:
        result.append({
            "image_url": row.image_url,
            "line_name": row.line_name,
            "camera_id": row.camera_id,
            "time": row.time.strftime("PM %I:%M:%S"),  # 🕒 시간 포맷 변경
            "type": row.types.split(",") if row.types else []  # 결함 종류 여러 개
        })

    return result

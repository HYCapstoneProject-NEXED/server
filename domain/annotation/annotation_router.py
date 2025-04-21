from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.database import get_db
from domain.annotation import annotation_crud, annotation_schema
from typing import List
from fastapi import HTTPException


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

@router.get("/detail/{image_id}", response_model=annotation_schema.AnnotationDetailResponse)
def get_annotation_details(image_id: int, db: Session = Depends(get_db)):
    data = annotation_crud.get_annotation_details_by_image_id(db, image_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return data

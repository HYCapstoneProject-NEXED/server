from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.database import get_db
from domain.annotation import annotation_crud, annotation_schema
from typing import List
from fastapi import HTTPException
from domain.annotation.annotation_schema import MainScreenResponse, ImageSummary


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

@router.get("/detail/{image_id}", response_model=annotation_schema.AnnotationDetailResponse)
def get_annotation_details(image_id: int, db: Session = Depends(get_db)):
    data = annotation_crud.get_annotation_details_by_image_id(db, image_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return data

@router.get("/main/{user_id}", response_model=MainScreenResponse)
def get_main_screen(
    user_id: int,
    db: Session = Depends(get_db)
):
    data = annotation_crud.get_main_data(db, user_id)
    if data is None:
        raise HTTPException(status_code=404, detail="User not found")

    # 결과를 ImageSummary 객체로 변환
    image_list = [
        ImageSummary(
            camera_id=img["camera_id"],
            image_id=img["image_id"],
            file_path=img["file_path"],
            confidence=img["confidence"],
            count=img["count"],
            status=img["status"],
            bounding_boxes=img["bounding_boxes"]
        ) for img in data["image_list"]
    ]

    return MainScreenResponse(
        profile_image=data["profile_image"],
        total_images=data["total_images"],
        pending_images=data["pending_images"],
        completed_images=data["completed_images"],
        image_list=image_list
    )

@router.get("/statistics/defect-type", response_model=List[annotation_schema.DefectTypeStatistics])
def read_defect_type_statistics(db: Session = Depends(get_db)):
    return annotation_crud.get_defect_type_statistics(db)


@router.get("/statistics/weekly-defect", response_model=annotation_schema.WeekdayDefectSummaryResponse)
def read_weekly_defect_summary(db: Session = Depends(get_db)):
    result = annotation_crud.get_weekday_defect_summary(db)
    return {"result": result}

@router.delete("/images", response_model=annotation_schema.DeleteImagesResponse)
def delete_images_api(
    request: annotation_schema.DeleteImagesRequest,
    db: Session = Depends(get_db)
):
    return annotation_crud.delete_images(db, request.image_ids)

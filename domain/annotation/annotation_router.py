from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from database.database import get_db
from domain.annotation import annotation_crud, annotation_schema
from typing import List, Optional
from domain.annotation.annotation_schema import MainScreenResponse, ImageSummary, AnnotationBulkUpdate, AnnotationResponse
from datetime import date, timedelta
from domain.annotation.annotation_crud import AnnotationService
import json  # JSON 파싱을 위한 모듈 추가
from database.models import DefectClass  # DefectClass 모델 추가


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

@router.get("/main/{user_id}", response_model=List[ImageSummary])
def get_main_screen(
    user_id: int,
    db: Session = Depends(get_db)
):
    data = annotation_crud.get_main_data(db, user_id)
    if data is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # DefectClass 정보 가져오기
    defect_classes = db.query(DefectClass.class_id, DefectClass.class_name, DefectClass.class_color).all()
    class_color_map = {cls.class_name: cls.class_color for cls in defect_classes}
    
    # 결과를 ImageSummary 객체로 변환
    image_list = []
    for img in data["image_list"]:
        # bounding_boxes 파싱 및 class_color 추가
        if isinstance(img["bounding_boxes"], str):
            boxes = json.loads(img["bounding_boxes"])
        else:
            boxes = img["bounding_boxes"]
        
        # 각 박스에 class_color 추가 (is_active는 이미 포함되어 있음)
        for box in boxes:
            if "class_name" in box and box["class_name"] in class_color_map:
                box["class_color"] = class_color_map[box["class_name"]]
        
        image_list.append(
            ImageSummary(
                camera_id=img["camera_id"],
                image_id=img["image_id"],
                file_path=img["file_path"],
                confidence=img["confidence"],
                count=img["count"],
                status=img["status"],
                width=img["width"],
                height=img["height"],
                bounding_boxes=boxes
            )
        )

    return image_list

@router.post("/main/filter/{user_id}", response_model=List[ImageSummary])
def get_filtered_image_list(
    user_id: int,
    filters: annotation_schema.FilteredImageListRequest = annotation_schema.FilteredImageListRequest(),
    db: Session = Depends(get_db)
):
    data = annotation_crud.get_main_data(db, user_id, filters)
    if data is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # DefectClass 정보 가져오기
    defect_classes = db.query(DefectClass.class_id, DefectClass.class_name, DefectClass.class_color).all()
    class_color_map = {cls.class_name: cls.class_color for cls in defect_classes}
    
    # 결과를 ImageSummary 객체로 변환
    image_list = []
    for img in data["image_list"]:
        # bounding_boxes 파싱 및 class_color 추가
        if isinstance(img["bounding_boxes"], str):
            boxes = json.loads(img["bounding_boxes"])
        else:
            boxes = img["bounding_boxes"]
        
        # 각 박스에 class_color 추가 (is_active는 이미 포함되어 있음)
        for box in boxes:
            if "class_name" in box and box["class_name"] in class_color_map:
                box["class_color"] = class_color_map[box["class_name"]]
        
        image_list.append(
            ImageSummary(
                camera_id=img["camera_id"],
                image_id=img["image_id"],
                file_path=img["file_path"],
                confidence=img["confidence"],
                count=img["count"],
                status=img["status"],
                width=img["width"],
                height=img["height"],
                bounding_boxes=boxes
            )
        )

    return image_list

@router.get("/statistics/defect-type", response_model=List[annotation_schema.DefectTypeStatistics])
def read_defect_type_statistics(db: Session = Depends(get_db)):
    return annotation_crud.get_defect_type_statistics(db)

@router.get("/statistics/weekly-defect", response_model=annotation_schema.WeekdayDefectSummaryResponse)
def read_weekly_defect_summary(db: Session = Depends(get_db)):
    result = annotation_crud.get_weekday_defect_summary(db)
    return {"result": result}

@router.get("/statistics/defect-by-period", response_model=annotation_schema.DefectStatisticsResponse)
def read_defect_statistics_by_period(
    unit: str = Query(..., enum=["week", "month", "year", "custom"]),
    start_date: Optional[date] = Query(None, description="조회 시작 날짜 (custom일 때 필수)"),
    end_date: Optional[date] = Query(None, description="조회 종료 날짜 (custom일 때 필수)"),
    defect_type: Optional[List[str]] = Query(default=None),
    camera_id: Optional[List[int]] = Query(default=None),
    db: Session = Depends(get_db)
):
    today = date.today()

    # ✅ custom 선택 시 start_date, end_date 필수
    if unit == "custom":
        if not start_date or not end_date:
            raise HTTPException(status_code=400, detail="unit이 'custom'일 경우 start_date와 end_date는 필수입니다.")
    else:
        # ✅ 프리셋 모드 → 날짜 자동 설정
        if unit == "week":
            start_date = today - timedelta(days=6)
            end_date = today
        elif unit == "month":
            start_date = today.replace(day=1)
            next_month = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1)
            end_date = next_month - timedelta(days=1)
        elif unit == "year":
            start_date = date(today.year, 1, 1)
            end_date = date(today.year, 12, 31)
        else:
            raise HTTPException(status_code=400, detail="unit은 'week', 'month', 'year', 'custom' 중 하나여야 합니다.")

    # ✅ defect_type과 camera_id 동시 선택 불가
    if defect_type and camera_id:
        raise HTTPException(status_code=400, detail="defect_type과 camera_id는 동시에 선택할 수 없습니다.")

    try:
        data = annotation_crud.get_defect_statistics_by_period(
            db=db,
            start_date=start_date,
            end_date=end_date,
            unit=unit,
            defect_types=defect_type,
            camera_ids=camera_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "date_range": {
            "start": start_date,
            "end": end_date
        },
        "unit": unit,
        "filters": {
            "defect_type": defect_type,
            "camera_ids": camera_id
        },
        "data": data
    }

@router.delete("/images", response_model=annotation_schema.DeleteImagesResponse)
def delete_images_api(
    request: annotation_schema.DeleteImagesRequest,
    db: Session = Depends(get_db)
):
    return annotation_crud.delete_images(db, request.image_ids)

@router.patch("/image/status", response_model=annotation_schema.UpdateImageStatusResponse)
def update_image_status_api(
    request: annotation_schema.UpdateImageStatusRequest,
    db: Session = Depends(get_db)
):
    return annotation_crud.update_image_status(db, request.image_id, request.status)

@router.post("/details", response_model=annotation_schema.AnnotationDetailListResponse)
def get_multiple_annotation_details(
    image_ids: List[int],
    db: Session = Depends(get_db)
):
    return annotation_crud.get_annotation_details_by_image_ids(db, image_ids)

@router.post("/history", response_model=List[annotation_schema.AnnotationHistoryResponse])
def get_annotation_history(
    filters: annotation_schema.AnnotationHistoryFilter,
    db: Session = Depends(get_db)
):
    return annotation_crud.get_annotation_history(db, filters)

@router.put("/detail/{user_id}/{image_id}", response_model=List[AnnotationResponse])
def update_image_annotations(
    user_id: int,
    image_id: int,
    data: AnnotationBulkUpdate,
    db: Session = Depends(get_db)
):
    annotation_service = AnnotationService(db)
    try:
        return annotation_service.update_image_annotations(image_id, user_id, data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tasks/{user_id}", response_model=annotation_schema.TaskSummaryResponse)
def get_task_summary(
    user_id: int,
    db: Session = Depends(get_db)
):
    data = annotation_crud.get_main_data(db, user_id)
    if data is None:
        raise HTTPException(status_code=404, detail="User not found")

    return annotation_schema.TaskSummaryResponse(
        total_images=data["total_images"],
        pending_images=data["pending_images"],
        completed_images=data["completed_images"]
    )

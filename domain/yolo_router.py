# domain/yolo_router.py

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
import os
import uuid
import shutil

from database.database import get_db
from domain.yolo_inference import run_inference
from domain.yolo_schema import BoundingBox, PredictResponse
from domain.yolo_service import save_inference_results

router = APIRouter()

# 디스크에 저장할 디렉토리 경로
IMAGES_DIR = os.getenv("IMAGES_DIR", "./images")

@router.post("/predict", response_model=PredictResponse)
async def predict(
    file: UploadFile = File(...),
    camera_id: int = Form(...),
    dataset_id: int = Form(...),
    db: Session = Depends(get_db)
):
    # 1) 저장 디렉토리 준비
    os.makedirs(IMAGES_DIR, exist_ok=True)

    # 2) 임시 파일로 저장
    temp_name = f"temp_{uuid.uuid4().hex}_{file.filename}"
    temp_path = os.path.join("/tmp", temp_name)
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 3) 모델 추론
        raw_results = run_inference(temp_path)

        # 4) 영구 저장 위치로 이동
        perm_filename = f"{uuid.uuid4().hex}_{file.filename}"
        perm_path = os.path.join(IMAGES_DIR, perm_filename)
        shutil.move(temp_path, perm_path)

        # 5) DB에 저장
        image_id = save_inference_results(
            db,
            image_path=perm_path,
            camera_id=camera_id,
            dataset_id=dataset_id,
            detections=raw_results
        )

    except Exception as e:
        # 오류 시 임시 파일 정리
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=str(e))

    # 6) 응답 데이터 파싱
    parsed = []
    for det in raw_results:
        parsed.append(
            BoundingBox(
                class_id=det["class_id"],
                confidence=det["confidence"],
                bounding_box=det["bounding_box"]  # dict 그대로 넣으면 Box 모델로 변환
            )
        )


    return PredictResponse(results=parsed)

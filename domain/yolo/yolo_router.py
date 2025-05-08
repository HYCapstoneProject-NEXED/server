# domain/yolo_router.py

from fastapi import APIRouter, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from servers.database.database          import get_db
from servers.database.models            import Image  # Image 레코드 조회용
from servers.domain.yolo.yolo_inference import run_inference
from servers.domain.yolo.yolo_schema    import BoundingBox, PredictResponse
from servers.domain.yolo.yolo_service   import save_inference_results

router = APIRouter()

@router.post("/predict", response_model=PredictResponse)
async def predict(
    image_id: int     = Form(...),         # 카메라 업로드 때 생성된 image_id
    db: Session = Depends(get_db)
):
    # 1) 기존 Image 레코드 조회
    image = db.get(Image, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    # 2) 모델 추론 (이미 저장된 file_path 사용)
    raw_results = run_inference(image.file_path)

    # 3) 상태 업데이트(pending) + 어노테이션 INSERT
    save_inference_results(db, image_id, raw_results)

    # 4) 응답 생성
    parsed = [
        BoundingBox(
            class_id=det["class_id"],
            confidence=det["confidence"],
            bounding_box=det["bounding_box"]
        )
        for det in raw_results
    ]
    return PredictResponse(results=parsed)
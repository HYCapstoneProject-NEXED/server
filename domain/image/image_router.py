from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from database.database import get_db
from domain.image import image_crud, image_schema
from utils.s3 import upload_image_to_s3
from domain.yolo.yolo_inference import run_inference
from domain.yolo.yolo_service import save_inference_results


router = APIRouter(
    prefix="/images",
    tags=["Images"]
)


@router.post("/upload", response_model=image_schema.ImageUploadResponse)
async def upload_image(
        file: UploadFile,
        camera_id: int = Form(...),
        db: Session = Depends(get_db),
):
    print("🔔 [upload_image] 호출됨")

    # 1. 카메라 유효성 확인
    camera = image_crud.get_active_camera(db, camera_id)
    if not camera:
        raise HTTPException(status_code=400, detail="비활성화된 카메라이거나 존재하지 않습니다.")
    print(f"✅ 유효한 카메라: {camera_id}")

    # 2. S3 업로드 + width/height 추출
    s3_url, width, height = upload_image_to_s3(file, camera_id)
    print(f"✅ S3 업로드 완료: {s3_url} (w: {width}, h: {height})")

    # 3. DB에 이미지 정보 저장
    image = image_crud.create_image_record(
        db=db,
        file_path=s3_url,
        camera_id=camera_id,
        width=width,
        height=height,
        dataset_id=0  # 필요 시 조정
    )
    print(f"✅ 이미지 DB 저장 완료: image_id={image.image_id}")

    # 4. 모델 추론 실행
    inference_result = run_inference(s3_url, db)  # List[BoundingBox]
    print(f"✅ 모델 추론 결과 개수: {len(inference_result)}")
    if not inference_result:
        print("⚠️ 모델 추론 결과가 비어 있습니다.")

    # 5. 추론 결과 DB 저장
    print("💾 어노테이션 저장 시작")
    save_inference_results(db, image.image_id, [r.dict() for r in inference_result])
    print("✅ 어노테이션 저장 완료")

    # 6. confidence score 체크 → status 자동 변경
    if inference_result:  # 추론 결과가 존재하면
        min_confidence = min(r.confidence for r in inference_result)
        if min_confidence >= 0.75:
            image.status = "completed"
            db.commit()
            print(f"✅ 이미지 status 'completed'로 자동 업데이트됨 (min_confidence={min_confidence:.3f})")
        else:
            print(f"ℹ️ min_confidence={min_confidence:.3f} < 0.75 → status 변경 없음")

    # 7. 응답 반환 (추론 결과 포함)
    return image_schema.ImageUploadResponse(
        image_id=image.image_id,
        file_path=image.file_path,
        date=image.date,
        results=inference_result  # BoundingBox 리스트
    )
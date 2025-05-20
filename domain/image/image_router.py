from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from database.database import get_db
from domain.image import image_crud, image_schema
from utils.s3 import upload_image_to_s3

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
    # 🔹 1. 카메라 유효성 확인
    camera = image_crud.get_active_camera(db, camera_id)
    if not camera:
        raise HTTPException(status_code=400, detail="비활성화된 카메라이거나 존재하지 않습니다.")

    # 🔹 2. S3 업로드 + width/height 추출
    s3_url, width, height = upload_image_to_s3(file, camera_id)

    # 🔹 3. DB에 이미지 정보 저장
    image = image_crud.create_image_record(
        db=db,
        file_path=s3_url,
        camera_id=camera_id,
        width=width,
        height=height,
        dataset_id=0  # 필요 시 조정
    )

    # 🔹 4. 응답 반환
    return image_schema.ImageUploadResponse.from_orm(image)
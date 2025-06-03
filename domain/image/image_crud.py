from sqlalchemy.orm import Session
from database.models import Camera, Image

# 카메라 유효성 확인 함수
def get_active_camera(db: Session, camera_id: int):
    return db.query(Camera).filter(Camera.camera_id == camera_id, Camera.is_active == True).first()

# 이미지 DB 레코드 생성 함수
def create_image_record(
    db: Session,
    file_path: str,
    camera_id: int,
    width: int,
    height: int,
    dataset_id: int = 0,
    status: str | None = None  # 명시 안 하면 default='pending' 적용됨
):
    image = Image(
        file_path=file_path,
        camera_id=camera_id,
        dataset_id=dataset_id,
        width=width,
        height=height,
        status=status  # 전달된 status 저장
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image

# ID로 이미지 조회하는 함수
def get_image_by_id(db: Session, image_id: int) -> Image:
    return db.query(Image).filter(Image.image_id == image_id).first()

# 이미지 레코드 삭제 함수
def delete_image_record(db: Session, image: Image):
    db.delete(image)
    db.commit()

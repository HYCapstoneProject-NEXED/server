# domain/yolo_service.py

from datetime import datetime
from sqlalchemy.orm import Session
from models import Image, Annotation

def save_inference_results(db: Session, image_path: str, camera_id: int, dataset_id: int, detections: list):
    # 1. Images 테이블에 삽입
    new_image = Image(
        file_path=image_path,
        date = datetime.utcnow(),
        camera_id=camera_id,
        dataset_id=dataset_id,
        status="completed"
    )
    db.add(new_image)
    db.commit()
    db.refresh(new_image)

    # 2. Annotations 테이블에 각각 삽입
    for det in detections:
        bbox = det["bounding_box"]
        new_annotation = Annotation(
            image_id=new_image.image_id,
            class_id=det["class_id"],
            date=datetime.utcnow(),
            conf_score=det["confidence"],
            bounding_box=bbox,
            user_id=None  # 자동 추론이므로 비워둠
        )
        db.add(new_annotation)

    db.commit()
    return new_image.image_id

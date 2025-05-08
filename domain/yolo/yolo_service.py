# domain/yolo_service.py

from datetime import datetime, UTC
from sqlalchemy.orm import Session
from servers.database.models import Image, Annotation

def save_inference_results(db: Session, image_id: int, detections: list):
    # 1. 이미지 상태를 pending으로
    image = db.get(Image, image_id)
    
    if image is None:
        raise ValueError(f"Image with ID {image_id} does not exist.")
    
    image.status = "pending"
    db.commit()

    # 2. 어노테이션 추가
    for det in detections:
        ann = Annotation(
            image_id    = image_id,
            class_id    = det["class_id"],
            conf_score  = det["confidence"],
            bounding_box= det["bounding_box"],
            # date는 DEFAULT CURRENT_TIMESTAMP
        )
        db.add(ann)

    db.commit()
    return image_id

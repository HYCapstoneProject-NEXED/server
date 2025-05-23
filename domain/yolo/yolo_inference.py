from typing import List
from sqlalchemy.orm import Session  # DB 접근용
from domain.yolo.yolo_schema import BoundingBox, Box  # Pydantic 모델 사용
from domain.defect_class.defect_class_crud import get_class_name_by_id  # class_name 조회 함수

model = None

def _set_model(yolo):
    global model
    model = yolo

def run_inference(image_path: str, db: Session) -> List[BoundingBox]:  # 반환 타입 명확하게 지정
    if model is None:
        raise RuntimeError("YOLO model not initialized. Call _set_model first.")

    results = model(image_path, conf=0.1)[0]
    detections = []

    if results.boxes is not None:
        boxes = results.boxes.xywhn.cpu().numpy()  # YOLO 포맷 (x_center, y_center, w, h) — 정규화됨
        scores = results.boxes.conf.cpu().numpy()
        class_ids = results.boxes.cls.cpu().numpy()

        for box, score, class_id in zip(boxes, scores, class_ids):
            class_id_int = int(class_id)  # 명시적 int 변환
            class_name = get_class_name_by_id(db, class_id_int)  # DB에서 클래스명 조회

            # dict가 아니라 BoundingBox 객체로 생성
            detection = BoundingBox(
                class_id=class_id_int,  # YOLO가 출력한 class index
                class_name=class_name,  #  클래스 이름
                confidence=float(score),  # 예측 확률
                bounding_box=Box(
                    x_center=float(box[0]),
                    y_center=float(box[1]),
                    w=float(box[2]),
                    h=float(box[3])
                )
            )
            detections.append(detection)

    return detections  # Pydantic 모델 리스트 반환
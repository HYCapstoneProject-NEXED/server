# domain/yolo_inference.py

from ultralytics import YOLO

model = None

def _set_model(yolo):
    global model
    model = yolo

def run_inference(image_path: str):
    if model is None:
        raise RuntimeError("YOLO model not initialized. Call _set_model first.")
    
    results = model(image_path, conf=0.1)[0]
    detections = []

    if results.boxes is not None:
        boxes = results.boxes.xywhn.cpu().numpy()  # YOLO 포맷 (x_center, y_center, w, h) — 정규화됨
        scores = results.boxes.conf.cpu().numpy()
        class_ids = results.boxes.cls.cpu().numpy()

        for box, score, class_id in zip(boxes, scores, class_ids):
            detection = {
                "class_id": int(class_id),  # YOLO가 출력한 class index
                "confidence": float(score),  # 예측 확률
                "bounding_box": {
                    "x_center": float(box[0]),
                    "y_center": float(box[1]),
                    "w": float(box[2]),
                    "h": float(box[3])
                }
            }
            detections.append(detection)

    return detections

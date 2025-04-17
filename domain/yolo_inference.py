# domain/yolo_inference.py

from ultralytics import YOLO

# 모델 로딩 (한 번만)
model = YOLO("best.pt")

def run_inference(image_path: str):
    results = model(image_path, conf=0.1)
    return results[0].boxes.xyxy.cpu().numpy().tolist()  # 바운딩 박스 리턴
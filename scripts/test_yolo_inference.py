# test_yolo_inference.py

from ultralytics import YOLO

# 1. 모델 로드
model = YOLO("best.pt")

# 2. 테스트할 이미지 경로 (DB에 저장된 file_path 참고)
image_path = ""  # 예: "images/test1.jpg" 또는 절대경로

# 3. 추론
results = model(image_path, conf=0.1)

# 4. 결과 시각화 (bounding box가 보임)
results[0].show()

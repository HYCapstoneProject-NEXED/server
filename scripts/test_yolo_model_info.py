# test_yolo_model_info.py

from ultralytics import YOLO

# 모델 로드
model = YOLO("../best.pt")

# 클래스 이름 출력
print("✅ 모델에 학습된 클래스 목록:")
print(model.names)

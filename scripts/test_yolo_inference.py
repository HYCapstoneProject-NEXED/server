import cv2
import numpy as np
import requests
from ultralytics import YOLO

# 1. 모델 로드
model = YOLO("best.pt")

# 2. 테스트할 이미지 경로
image_url = ""

# 3. 이미지 다운로드 후 OpenCV로 읽기
resp = requests.get(image_url, stream=True).raw
img_array = np.asarray(bytearray(resp.read()), dtype=np.uint8)
img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

# 4.  해상도 별 추론 및 시각화
for size in [320, 480, 640, 800]:
    print(f"\n=== 📐 Testing with imgsz={size} ===")
    results = model(img, conf=0.365, imgsz=size)  # OpenCV 이미지 그대로 전달
    results[0].show()
    print(f"탐지 개수: {len(results[0].boxes)}")

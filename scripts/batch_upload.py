import json
from sqlalchemy.orm import Session
from database.database import SessionLocal
from domain.image import image_crud
from utils.s3 import upload_local_file_to_s3
import os
from domain.annotation import annotation_crud
from domain.yolo.yolo_inference import _set_model, run_inference
from ultralytics import YOLO


# 더미 이미지 S3 + DB 일괄 등록
def upload_dummy_images():
    # 설정
    image_dir = "dummy_images"
    metadata_file = "dummy_data.json"

    # YOLO 모델 수동 로드
    model = YOLO("best.pt")
    _set_model(model)

    with open(metadata_file, "r") as f:
        data = json.load(f)

    db: Session = SessionLocal()

    for item in data:
        file_name = item["file_name"]
        camera_id = item["camera_id"]
        file_path = os.path.join(image_dir, file_name)

        if not os.path.exists(file_path):
            print(f"❌ 파일 없음: {file_path}")
            continue

        try:
            # 🔹 1. S3 업로드 및 이미지 크기 추출
            s3_url, width, height = upload_local_file_to_s3(file_path, camera_id)

            # 🔹 2. DB 삽입
            image = image_crud.create_image_record(
                db=db,
                file_path=s3_url,
                camera_id=camera_id,
                width=width,
                height=height,
                dataset_id=0  # 필요 시 수정
            )

            # 3. 모델 추론 실행
            boxes = run_inference(file_path, db)

            # 4. annotation 저장
            for box in boxes:
                annotation_crud.create_annotation(
                    db=db,
                    image_id=image.image_id,
                    class_id=box.class_id,
                    x=box.bounding_box.x_center,
                    y=box.bounding_box.y_center,
                    width=box.bounding_box.w,
                    height=box.bounding_box.h,
                    confidence=box.confidence
                )

            print(f"✅ 완료: {file_name} (ID: {image.image_id}, 추론 결과: {len(boxes)}개)")

        except Exception as e:
            print(f"⚠️ 오류 발생: {file_name} - {e}")

    db.close()

if __name__ == "__main__":
    upload_dummy_images()
import os
import boto3
from sqlalchemy.orm import Session
from database.database import SessionLocal
from domain.image.image_crud import get_image_by_id, delete_image_record
from urllib.parse import urlparse
from dotenv import load_dotenv

# .env 로딩
load_dotenv()

# 환경변수 가져오기
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET = os.getenv("S3_BUCKET_NAME")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# boto3 client 구성
s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

# s3 key 추출 함수
def extract_s3_key_from_url(url: str) -> str:
    parsed_url = urlparse(url)
    return parsed_url.path.lstrip("/")  # 버킷 이름 이후 경로만 추출

# 사진 삭제 함수
def delete_image_by_id(image_id: int):
    db: Session = SessionLocal()
    image = get_image_by_id(db, image_id)

    if not image:
        print(f"❌ 이미지 ID {image_id}를 찾을 수 없습니다.")
        return

    s3_key = extract_s3_key_from_url(image.file_path)

    try:
        # 🔹 1. S3에서 이미지 삭제
        s3.delete_object(Bucket=S3_BUCKET, Key=s3_key)
        print(f"🗑 S3에서 이미지 삭제 완료: {s3_key}")

        # 🔹 2. DB에서 레코드 삭제
        delete_image_record(db, image)
        print(f"🗑 DB에서 이미지 레코드 삭제 완료 (ID: {image_id})")

    except Exception as e:
        print(f"⚠️ 삭제 중 오류 발생: {e}")

    db.close()

if __name__ == "__main__":
    delete_image_by_id(76)  # ← 삭제할 image_id
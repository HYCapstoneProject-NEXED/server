import boto3
import uuid
from fastapi import UploadFile
from os import getenv
from dotenv import load_dotenv
from PIL import Image as PILImage
import io
from botocore.exceptions import BotoCoreError, ClientError  # 예외 처리용

# .env 로딩
load_dotenv()

# 환경변수 가져오기
AWS_ACCESS_KEY_ID = getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = getenv("AWS_REGION")
S3_BUCKET = getenv("S3_BUCKET_NAME")
print("🧪 S3 설정 확인:", AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET)

# boto3.client 구성
s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)


# 사진 업로드 함수
def upload_image_to_s3(file: UploadFile, camera_id: int) -> tuple[str, int, int]:  # 반환 타입 tuple[str, int, int]
    ext = file.filename.split(".")[-1]
    key = f"{camera_id}/{uuid.uuid4()}.{ext}"  # S3 내부 저장 경로

    # width, height 추출
    file_bytes = file.file.read()
    try:
        image = PILImage.open(io.BytesIO(file_bytes))
        width, height = image.size
    except Exception as e:
        raise ValueError("이미지 파일 열기에 실패했습니다.") from e

    # S3 업로드
    try:
        s3_client.upload_fileobj(
            io.BytesIO(file_bytes),  # 다시 스트림 형태로 변환
            S3_BUCKET,
            key,
            ExtraArgs={"ContentType": file.content_type},
        )
    except (BotoCoreError, ClientError) as e:
        raise RuntimeError("S3 업로드에 실패했습니다.") from e

    # S3 URL 반환
    url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"
    return url, width, height  # S3 URL, width, height 반환


# 로컬 이미지 파일 경로를 받아 S3에 업로드하는 함수
def upload_local_file_to_s3(file_path: str, camera_id: int):
    ext = file_path.split('.')[-1]
    key = f"{camera_id}/{uuid.uuid4()}.{ext}"

    with open(file_path, "rb") as f:
        file_bytes = f.read()
        image = PILImage.open(io.BytesIO(file_bytes))
        width, height = image.size

        s3_client.upload_fileobj(
            io.BytesIO(file_bytes),
            S3_BUCKET,
            key,
            ExtraArgs={"ContentType": f"image/{ext}"}
        )

    url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"
    return url, width, height
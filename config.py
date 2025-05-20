import os
from dotenv import load_dotenv

# 📌 .env 파일 로드
load_dotenv()

# 📌 환경 변수 가져오기
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
JWT_SECRET = os.getenv("JWT_SECRET")
# ✅ 추가: JWT 알고리즘 설정
ALGORITHM = "HS256"  # JWT 토큰 서명에 사용할 해싱 알고리즘

# 📌 환경 변수가 잘 불러와졌는지 확인 (테스트용)
print(f"✅ GOOGLE_CLIENT_ID: {GOOGLE_CLIENT_ID}")
print(f"✅ GOOGLE_CLIENT_SECRET: {GOOGLE_CLIENT_SECRET}")
print(f"✅ GOOGLE_REDIRECT_URI: {GOOGLE_REDIRECT_URI}")
print(f"✅ JWT_SECRET: {JWT_SECRET}")
print(f"✅ ALGORITHM: {ALGORITHM}")  # ✅ 추가된 변수 출력 확인

# Naver 환경 변수 가져오기
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_REDIRECT_URI = os.getenv("NAVER_REDIRECT_URI")

# Naver 환경 변수 잘 불러와졌는지 확인 (테스트용)
print(f"✅ NAVER_CLIENT_ID: {NAVER_CLIENT_ID}")
print(f"✅ NAVER_CLIENT_SECRET: {NAVER_CLIENT_SECRET}")
print(f"✅ NAVER_REDIRECT_URI: {NAVER_REDIRECT_URI}")


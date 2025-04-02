from fastapi import APIRouter, Depends, HTTPException
import requests
import urllib.parse
from sqlalchemy.orm import Session
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI
from database.database import get_db
from domain.user.auth import create_jwt_token
from domain.user.user_crud import get_user_by_email, create_user
from domain.user.user_schema import UserBase, UserResponse

router = APIRouter()


# ✅ Google 로그인 URL 제공
@router.get("/auth/login")
def google_login():
    return {
        "login_url": f"https://accounts.google.com/o/oauth2/auth"
                     f"?client_id={GOOGLE_CLIENT_ID}"
                     f"&redirect_uri={GOOGLE_REDIRECT_URI}"
                     f"&response_type=code"
                     f"&scope=openid email profile"
    }


# ✅ 한 번 사용된 Authorization Code를 저장하는 캐시 (불필요할 수 있음)
used_codes = set()


@router.get("/auth/callback")
def google_callback(code: str, db: Session = Depends(get_db)):
    import urllib.parse
    decoded_code = urllib.parse.unquote(code)

    # Google OAuth 토큰 요청
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": decoded_code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    response = requests.post(token_url, data=data)
    token_json = response.json()

    if "access_token" not in token_json:
        raise HTTPException(status_code=400, detail=f"Failed to get access token: {token_json}")

    # Google에서 사용자 정보 가져오기
    access_token = token_json["access_token"]
    userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    userinfo_response = requests.get(userinfo_url, headers={"Authorization": f"Bearer {access_token}"})
    userinfo = userinfo_response.json()

    if "email" not in userinfo:
        raise HTTPException(status_code=400, detail="Failed to get user email")

    user_email = userinfo["email"]

    # ✅ DB에서 이메일이 있는지 확인
    user = get_user_by_email(db, user_email)
    if not user:
        # ✅ 이메일만 저장된 "임시 계정" 생성 (사용자가 추가 정보 입력 필요)
        new_user_data = UserBase(
            google_email=user_email,
            name=None,  # 이름 미입력 상태. 기본값 None
            user_type=None,
            birthdate=None,
            nationality=None,
            address=None,
            company_name=None,
            factory_name=None,
            bank_name=None,
            bank_account=None,
            terms_accepted=False  # 약관 동의도 아직 안 함
        )
        user = create_user(db, new_user_data)

        # ✅ FastAPI에서 발급한 JWT 토큰 생성
        jwt_token = create_jwt_token(user.user_id)

        return {
            "message": "Additional user information required",
            "access_token": jwt_token,  # ✅ Google OAuth 토큰이 아니라 FastAPI JWT 토큰 반환
            "token_type": "bearer",
            "user": UserResponse.from_orm(user)
        }

    # ✅ 기존 계정이 있다면 JWT 토큰 발급
    jwt_token = create_jwt_token(user.user_id)

    return {
        "message": "Login successful",
        "access_token": jwt_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user)
    }


from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from database.database import get_db
from domain.user.user_crud import get_user_by_email, update_user_info
from domain.user.user_schema import UserUpdate
from domain.user.auth import get_current_user  # ✅ 현재 로그인한 사용자 정보 가져오기


@router.post("/auth/signup")
def complete_profile(
        user_update: UserUpdate,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)  # ✅ JWT에서 현재 로그인한 사용자 가져오기
):
    """
    ✅ 사용자가 필수 정보를 입력하여 회원가입을 완료하는 API (이메일 자동 식별)
    """
    user = get_user_by_email(db, current_user.google_email)  # ✅ JWT에서 가져온 이메일로 사용자 조회
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # ✅ 필수 정보가 비어있으면 회원가입 완료를 허용하지 않음
    required_fields = [
        user_update.name, user_update.user_type, user_update.birthdate,
        user_update.nationality, user_update.company_name,
        user_update.factory_name, user_update.bank_name, user_update.bank_account,
        user_update.terms_accepted
    ]

    if any(field is None for field in required_fields):
        raise HTTPException(status_code=400, detail="All required fields must be filled.")

    # ✅ 사용자 정보 업데이트 (필수 정보 입력됨)
    updated_user = update_user_info(db, user, user_update)

    return {"message": "User profile completed successfully", "user": updated_user}



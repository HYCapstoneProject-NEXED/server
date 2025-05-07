from fastapi import APIRouter, Depends, HTTPException
import requests
import urllib.parse
from sqlalchemy.orm import Session
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI
from database.database import get_db
from domain.user.auth import create_jwt_token
from domain.user.user_crud import get_user_by_email, create_user, get_user_by_id, update_user_info
from domain.user.user_schema import UserBase, UserResponse, UserUpdate
from datetime import date
from domain.user.auth import get_current_user  # ✅ 현재 로그인한 사용자 정보 가져오기
from config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, NAVER_REDIRECT_URI


router = APIRouter(
    tags=["Users"]
)

# ✅ Google 로그인 URL 제공
@router.get("/auth/google/login")
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


@router.get("/auth/google/callback")
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


@router.post("/auth/google/signup")
def google_complete_profile(
        user_update: UserUpdate,
        db: Session = Depends(get_db),
        current_user = Depends(get_current_user)  # ✅ JWT에서 현재 로그인한 사용자 가져오기
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


# ✅ 네이버 로그인 URL 제공
@router.get("/auth/naver/login")
def naver_login():
    base_url = "https://nid.naver.com/oauth2.0/authorize"
    query = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": NAVER_CLIENT_ID,
        "redirect_uri": NAVER_REDIRECT_URI,
        "state": "random_csrf_token"  # 실제 서비스에선 난수 추천
    })
    return {
        "login_url": f"{base_url}?{query}"
    }

# ✅ 네이버 콜백 처리
@router.get("/auth/naver/callback")
def naver_callback(code: str, state: str, db: Session = Depends(get_db)):
    # 1. access_token 요청
    token_url = "https://nid.naver.com/oauth2.0/token"
    token_data = {
        "grant_type": "authorization_code",
        "client_id": NAVER_CLIENT_ID,
        "client_secret": NAVER_CLIENT_SECRET,
        "code": code,
        "state": state
    }
    token_res = requests.post(token_url, data=token_data)
    token_json = token_res.json()
    access_token = token_json.get("access_token")

    if not access_token:
        raise HTTPException(status_code=400, detail="Failed to obtain Naver access token")

    # 2. 사용자 정보 요청
    profile_url = "https://openapi.naver.com/v1/nid/me"
    profile_res = requests.get(profile_url, headers={"Authorization": f"Bearer {access_token}"})
    profile_json = profile_res.json()

    if profile_json.get("resultcode") != "00":
        raise HTTPException(status_code=400, detail="Failed to retrieve user info from Naver")

    naver_user = profile_json["response"]
    user_email = naver_user.get("email")

    if not user_email:
        raise HTTPException(status_code=400, detail="Email not provided by Naver")

    # 3. 사용자 DB 조회 → 없으면 생성
    user = get_user_by_email(db, user_email)
    if not user:
        new_user_data = UserBase(
            google_email=user_email,  # 기존 필드 그대로 활용 (Google/Naver 공통 이메일 필드)
            name='',
            user_type='',
            birthdate=date(2000, 1, 1),
            nationality='',
            address='',
            company_name='',
            factory_name='',
            bank_name='',
            bank_account='',
            terms_accepted=False
        )
        user = create_user(db, new_user_data)

        jwt_token = create_jwt_token(user.user_id)
        return {
            "message": "Additional user information required",
            "access_token": jwt_token,
            "token_type": "bearer",
            "user": UserResponse.from_orm(user)
        }

    # 4. 기존 사용자 → 바로 JWT 발급
    jwt_token = create_jwt_token(user.user_id)

    return {
        "message": "Login successful via Naver",
        "access_token": jwt_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user)
    }

@router.post("/auth/naver/signup")
def naver_complete_profile(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    ✅ 네이버 로그인 사용자가 필수 정보를 입력하여 회원가입을 완료하는 API
    """
    user = get_user_by_email(db, current_user.google_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    required_fields = [
        user_update.name, user_update.user_type, user_update.birthdate,
        user_update.nationality, user_update.company_name,
        user_update.factory_name, user_update.bank_name, user_update.bank_account,
        user_update.terms_accepted
    ]

    if any(field is None for field in required_fields):
        raise HTTPException(status_code=400, detail="All required fields must be filled.")

    updated_user = update_user_info(db, user, user_update)

    return {
        "message": "Naver user profile completed successfully",
        "user": updated_user
    }

@router.get("/users/{user_id}", response_model=UserResponse)
def get_user_profile(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/users/{user_id}", response_model=UserResponse)
def update_user_profile(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db)
):
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    updated_user = update_user_info(db, user, user_update)
    return updated_user
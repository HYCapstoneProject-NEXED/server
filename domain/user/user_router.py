from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, UploadFile, File, Form
import requests
import urllib.parse
from sqlalchemy.orm import Session
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI
from database.database import get_db
from domain.user.auth import create_jwt_token
from domain.user.user_crud import get_user_by_email, create_user, get_user_by_id, update_user_info, get_members, update_user_role, deactivate_user, get_pending_approval_users, update_user_approval_status, get_worker_overview_with_filters, get_active_annotators
from domain.user.user_schema import UserBase, UserResponse, UserUpdate, UserSummary, UserTypeFilterEnum, UserRoleUpdate, UserDeleteResponse, PendingUserResponse, ApprovalRequest, ApprovalActionEnum, ApprovalStatusEnum, WorkerOverview, AnnotatorName, WorkerOverviewFilter
from datetime import date
from domain.user.auth import get_current_user  # ✅ 현재 로그인한 사용자 정보 가져오기
from config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, NAVER_REDIRECT_URI
from typing import List, Optional, Dict
import os
import uuid
from pathlib import Path as FilePath


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
            terms_accepted=False,  # 약관 동의도 아직 안 함
            profile_image=userinfo.get("picture"),  # 구글에서 받아온 사진
            gender = None
        )
        user = create_user(db, new_user_data)

    # 🔷 admin이 삭제한 유저
    elif user.approval_status == ApprovalStatusEnum.approved and user.is_active is False:
        raise HTTPException(status_code=403, detail="관리자에 의해 비활성화된 계정입니다. 관리자에게 문의해주세요.")

    # 🔷 승인 거절된 유저
    elif user.approval_status == ApprovalStatusEnum.rejected:
        raise HTTPException(status_code=403, detail="승인 거절된 계정입니다. 관리자에게 문의해주세요.")

    # 🔷 가입 승인 대기 중인 유저
    elif user.approval_status == ApprovalStatusEnum.pending:
        raise HTTPException(status_code=403, detail="가입 승인 대기 중입니다. 관리자의 승인을 기다려주세요.")

    # 🔷 회원가입 미완료 유저 - 추가 정보 입력 필요
    elif user.approval_status == ApprovalStatusEnum.incomplete:
        jwt_token = create_jwt_token(user.user_id)
        return {
            "message": "Additional user information required",
            "access_token": jwt_token,
            "token_type": "bearer",
            "user": UserResponse.from_orm(user)
        }

    # ✅ 승인 완료된 유저라면 로그인 허용 (is_active=True)
    jwt_token = create_jwt_token(user.user_id)  # FastAPI에서 발급한 JWT 토큰 생성
    return {
        "message": "Login successful" if user.is_active else "Additional user information required",
        "access_token": jwt_token,  # Google OAuth 토큰이 아니라 FastAPI JWT 토큰임
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

    # ✅ "회사명/공장명" 형식의 문자열을 company_name, factory_name으로 분리
    if user_update.company_factory and "/" in user_update.company_factory:
        try:
            company, factory = user_update.company_factory.split("/", 1)
            user.company_name = company.strip()
            user.factory_name = factory.strip()
        except ValueError:
            raise HTTPException(status_code=400, detail="회사명/공장명을 '회사명/공장명' 형식으로 입력해주세요.")
    else:
        raise HTTPException(status_code=400, detail="회사명/공장명을 '회사명/공장명' 형식으로 입력해주세요.")

    # ✅ 필수 정보가 비어있거나 빈 문자열("")이면 회원가입 거부
    required_fields = [
        user_update.name, user_update.user_type, user_update.birthdate,
        user_update.nationality, user_update.company_factory,
        user_update.bank_name, user_update.bank_account,
        user_update.terms_accepted, user_update.gender
    ]

    if any(field is None or (isinstance(field, str) and field.strip() == "") for field in required_fields):
        raise HTTPException(status_code=400, detail="모든 필수 항목을 입력해야 합니다.")

    # ✅ 약관 동의 여부 검사
    if user_update.terms_accepted is not True:
        raise HTTPException(status_code=400, detail="약관에 동의해야 회원가입이 가능합니다.")

    # ✅ 사용자 정보 업데이트 (필수 정보 입력됨)
    updated_user = update_user_info(db, user, user_update)
    
    # 회원가입 완료 후 승인 대기 상태로 변경
    user.approval_status = ApprovalStatusEnum.pending
    db.commit()
    db.refresh(user)

    return {"message": "User profile completed successfully", "user": UserResponse.from_orm(user)}


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
            user_type='customer',
            birthdate=date(2000, 1, 1),
            nationality='',
            address='',
            company_name='',
            factory_name='',
            bank_name='',
            bank_account='',
            terms_accepted=False,
            gender='female'  # 기본값으로 female 설정
        )
        user = create_user(db, new_user_data)

        jwt_token = create_jwt_token(user.user_id)
        return {
            "message": "Additional user information required",
            "access_token": jwt_token,
            "token_type": "bearer",
            "user": UserResponse.from_orm(user)
        }

    # 🔷 admin이 삭제한 유저
    elif user.approval_status == ApprovalStatusEnum.approved and user.is_active is False:
        raise HTTPException(status_code=403, detail="관리자에 의해 비활성화된 계정입니다. 관리자에게 문의해주세요.")

    # 🔷 승인 거절된 유저
    elif user.approval_status == ApprovalStatusEnum.rejected:
        raise HTTPException(status_code=403, detail="승인 거절된 계정입니다. 관리자에게 문의해주세요.")

    # 🔷 가입 승인 대기 중인 유저
    elif user.approval_status == ApprovalStatusEnum.pending:
        raise HTTPException(status_code=403, detail="가입 승인 대기 중입니다. 관리자의 승인을 기다려주세요.")

    # 🔷 회원가입 미완료 유저 - 추가 정보 입력 필요
    elif user.approval_status == ApprovalStatusEnum.incomplete:
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

    # ✅ 사용자 정보 업데이트 및 상태를 pending으로 변경
    updated_user = update_user_info(db, user, user_update)
    
    # 회원가입 완료 후 승인 대기 상태로 변경
    user.approval_status = ApprovalStatusEnum.pending
    db.commit()
    db.refresh(user)

    return {
        "message": "Naver user profile completed successfully",
        "user": UserResponse.from_orm(user)
    }

@router.get("/users/pending-approvals", response_model=List[PendingUserResponse])
def get_pending_approvals(db: Session = Depends(get_db)):
    return get_pending_approval_users(db)

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
    db: Session = Depends(get_db),
    # JSON 요청을 위한 body 파라미터 추가
    user_update: Optional[UserUpdate] = Body(None),
    # Form 데이터를 위한 파라미터들 (기존 유지)
    bank_name: Optional[str] = Form(None),
    bank_account: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    profile_image: Optional[UploadFile] = File(None)
):
    """
    사용자의 은행 정보, 주소, 프로필 이미지를 업데이트합니다.
    
    두 가지 방식 지원:
    1. JSON 요청: Content-Type: application/json
    2. Form 데이터 요청: Content-Type: multipart/form-data (프로필 이미지 업로드 시)
    
    요청:
    - bank_name: 은행명 (선택)
    - bank_account: 계좌번호 (선택)
    - address: 주소 (선택)
    - profile_image: 프로필 이미지 파일 (선택, Form 데이터에서만)
    
    응답:
    - 업데이트된 사용자의 전체 정보
    """
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # JSON 요청인 경우 (user_update가 있는 경우)
    if user_update is not None:
        if user_update.bank_name is not None:
            user.bank_name = user_update.bank_name
        if user_update.bank_account is not None:
            user.bank_account = user_update.bank_account
        if user_update.address is not None:
            user.address = user_update.address
    else:
        # Form 데이터인 경우 (기존 로직)
        if bank_name is not None:
            user.bank_name = bank_name
        if bank_account is not None:
            user.bank_account = bank_account
        if address is not None:
            user.address = address
    
    # 프로필 이미지 업로드 처리 (Form 데이터에서만 가능)
    if profile_image is not None:
        # 이미지 파일 검증
        if not profile_image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="업로드된 파일이 이미지가 아닙니다.")
        
        # 파일 크기 제한 (5MB)
        if profile_image.size > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="이미지 파일 크기는 5MB를 초과할 수 없습니다.")
        
        # 저장 디렉토리 생성
        upload_dir = FilePath("static/profile_images")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 고유한 파일명 생성
        file_extension = profile_image.filename.split(".")[-1] if "." in profile_image.filename else "jpg"
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = upload_dir / unique_filename
        
        # 기존 프로필 이미지 삭제 (기본 이미지가 아닌 경우)
        if user.profile_image and user.profile_image.startswith("/static/profile_images/"):
            old_file_path = FilePath("." + user.profile_image)
            if old_file_path.exists():
                old_file_path.unlink()
        
        # 새 이미지 저장
        with open(file_path, "wb") as buffer:
            content = profile_image.file.read()
            buffer.write(content)
        
        # DB에 저장할 경로 (웹에서 접근 가능한 경로)
        user.profile_image = f"/static/profile_images/{unique_filename}"

    db.commit()
    db.refresh(user)
    return user

@router.get("/users", response_model=List[UserSummary])
def get_member_list(
    role: UserTypeFilterEnum = Query(default=UserTypeFilterEnum.all_roles),
    search: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):
    return get_members(db=db, role=role, search=search)

@router.patch("/users/{user_id}/role", response_model=Dict[str, str])
def change_user_role(
    user_id: int = Path(..., description="역할을 변경할 대상 유저의 ID"),
    request: UserRoleUpdate = Body(...),
    db: Session = Depends(get_db)
):
    updated_user = update_user_role(db, user_id, request.user_type)
    return {
        "message": "User role updated successfully",
        "user_id": str(updated_user.user_id),
        "new_role": updated_user.user_type
    }

@router.patch("/users/{user_id}/deactivate", response_model=UserDeleteResponse)
def deactivate_user_endpoint(user_id: int, db: Session = Depends(get_db)):
    return deactivate_user(db, user_id)


@router.patch("/users/{user_id}/approval")
def handle_approval(user_id: int, req: ApprovalRequest, db: Session = Depends(get_db)):
    updated_user = update_user_approval_status(db, user_id, req.action)

    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")

    action_message = "approved" if req.action == ApprovalActionEnum.approve else "rejected"
    return {"message": f"User has been {action_message} successfully."}

@router.post("/annotators/summary", response_model=List[WorkerOverview])
def get_worker_summary_with_filters(
    filters: WorkerOverviewFilter,
    db: Session = Depends(get_db)
):
    return get_worker_overview_with_filters(db, filters)

@router.get("/annotators/filter-list", response_model=List[AnnotatorName])
def get_annotator_filter_list(db: Session = Depends(get_db)):
    return get_active_annotators(db)
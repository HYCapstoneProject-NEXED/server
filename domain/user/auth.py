from jose import jwt, JWTError, ExpiredSignatureError  # ✅ ExpiredSignatureError 추가
from datetime import datetime, timedelta
from config import JWT_SECRET, ALGORITHM
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from database.database import get_db
from domain.user.user_crud import get_user_by_id  # ✅ user_id로 조회하는 함수 사용
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer_scheme = HTTPBearer()

def create_jwt_token(user_id: int):
    """
    ✅ JWT 토큰 생성 함수
    - user_id를 subject(`sub`)으로 저장
    - 유효 기간(exp)은 7일
    """
    payload = {
        "sub": str(user_id),  # ✅ 문자열 변환
        "exp": datetime.utcnow() + timedelta(days=7)  # ✅ 7일간 유효
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


# ✅ JWT 토큰을 디코딩하여 현재 로그인한 사용자 반환
def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
        db: Session = Depends(get_db)
):
    token = credentials.credentials  # "Bearer <token>"에서 토큰 부분만 추출

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # ✅ user_id를 기반으로 DB에서 사용자 찾기
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user
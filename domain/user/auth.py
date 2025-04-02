from jose import jwt, JWTError, ExpiredSignatureError  # ✅ ExpiredSignatureError 추가
from datetime import datetime, timedelta
from config import JWT_SECRET, ALGORITHM
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from database.database import get_db
from fastapi.security import OAuth2PasswordBearer
from domain.user.user_crud import get_user_by_id  # ✅ user_id로 조회하는 함수 사용

# ✅ OAuth2PasswordBearer 설정 (토큰 엔드포인트 맞게 수정)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/callback")


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


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    ✅ JWT 토큰을 디코딩하여 현재 로그인한 사용자 반환
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id = payload.get("sub")  # ✅ `sub` 값을 가져옴 (문자열이므로 변환 필요)

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        user_id = int(user_id)  # ✅ `sub` 값이 문자열이므로 int로 변환

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")  # ✅ 만료된 토큰 처리

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    # ✅ user_id를 기반으로 DB에서 사용자 찾기
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user

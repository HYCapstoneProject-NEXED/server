# 딥러닝 기반 실시간 생산품 결함 탐지 시스템
이 프로젝트는 공장 생산 라인에서 실시간으로 제품 이미지를 수집하고, 딥러닝 모델을 활용하여 결함 여부를 자동으로 탐지하는 시스템입니다.  
FastAPI 기반의 백엔드 서버를 통해 API를 제공하며, 결함 탐지 모델의 학습 및 추론 기능도 포함할 예정입니다.
---
## 기술 스택

- **FastAPI**: 비동기 REST API 서버 프레임워크
- **Uvicorn**: ASGI 서버 (FastAPI 실행용)
- **SQLAlchemy**: 데이터베이스 ORM
- **Pydantic**: 데이터 검증 및 설정 관리
- **python-jose[cryptography]**: JWT 기반 인증 및 보안

---
## 기여자

- lgr0831
- yumin0411


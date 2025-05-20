from fastapi import FastAPI
from domain.user import user_router
from domain.annotation import annotation_router
from domain.defect_class import defect_class_router
from domain.admin.admin_router import router as admin_router
from domain.image.image_router import router as image_router
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

# 🔹 CORS 설정
app.add_middleware(
    CORSMiddleware,
    # allow_origins=["http://166.104.246.64:3000"],  # 프론트 주소
    allow_origins=["*"],  # 초기 테스트용으로 전체 허용도 가능
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔹 라우터 등록
app.include_router(user_router.router)
app.include_router(annotation_router.router)
app.include_router(defect_class_router.router)
app.include_router(admin_router)
app.include_router(image_router)

# 🔹 정적 파일 서빙 (upload.html 등)
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


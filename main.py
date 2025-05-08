
# main.py
from fastapi import FastAPI
from ultralytics import YOLO
from servers.domain.yolo.yolo_inference import _set_model
from servers.domain.yolo.yolo_router import router as yolo_router

app = FastAPI()

@app.on_event("startup")
async def load_model():
    try:
        app.state.yolo_model = YOLO("best.pt")
        _set_model(app.state.yolo_model)
    except Exception as e:
        print(f"[ERROR] YOLO 모델 로드 실패: {e}")

app.include_router(yolo_router, prefix="/yolo", tags=["yolo"])

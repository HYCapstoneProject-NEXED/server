
# main.py
from fastapi import FastAPI
from ultralytics import YOLO
from domain.yolo_inference import _set_model
from domain.yolo_router import router as yolo_router

app = FastAPI()

@app.on_event("startup")
async def load_model():
    app.state.yolo_model = YOLO("best.pt")
    _set_model(app.state.yolo_model)

app.include_router(yolo_router, prefix="/yolo", tags=["yolo"])

from fastapi import FastAPI
from domain.yolo_router import router as yolo_router

app = FastAPI()

app.include_router(yolo_router)
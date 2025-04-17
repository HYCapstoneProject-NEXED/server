from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
from domain.yolo_inference import run_inference
from domain.yolo_schema import BoundingBox, PredictResponse
import shutil
import uuid
import os

router = APIRouter()

@router.post("/predict", response_model=PredictResponse)
async def predict(file: UploadFile = File(...)):
    filename = f"temp_{uuid.uuid4()}.jpg"
    with open(filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    raw_results = run_inference(filename)
    os.remove(filename)

    parsed = [BoundingBox(box=coords) for coords in raw_results]
    return PredictResponse(results=parsed)

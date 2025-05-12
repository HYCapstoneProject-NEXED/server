from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from api.schemas import annotation as annotation_schema
from api.crud import annotation as annotation_crud
from api.database import get_db

router = APIRouter()

@router.get("/main-data/{user_id}", response_model=annotation_schema.MainScreenResponse)
def get_main_data(
    user_id: int,
    status: Optional[str] = None,
    class_names: Optional[List[str]] = Query(None),
    min_confidence: Optional[float] = None,
    max_confidence: Optional[float] = None,
    db: Session = Depends(get_db)
):
    filters = annotation_schema.MainScreenFilter(
        status=status,
        class_names=class_names,
        min_confidence=min_confidence,
        max_confidence=max_confidence
    )
    return annotation_crud.get_main_data(db=db, user_id=user_id, filters=filters)

@router.post("/main-data/{user_id}", response_model=annotation_schema.MainScreenResponse)
def get_main_data_with_body(
    user_id: int,
    filters: annotation_schema.MainScreenFilter,
    db: Session = Depends(get_db)
):
    return annotation_crud.get_main_data(db=db, user_id=user_id, filters=filters) 
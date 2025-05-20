from fastapi import APIRouter, Depends, Path, Body
from sqlalchemy.orm import Session
from database.database import get_db
from domain.defect_class import defect_class_schema, defect_class_crud


router = APIRouter(
    prefix="/defect-classes",
    tags=["Defect Classes"]
)

@router.get("", response_model=list[defect_class_schema.DefectClassResponse])
def read_defect_classes(db: Session = Depends(get_db)):
    return defect_class_crud.get_all_defect_classes(db)


@router.post("", response_model=defect_class_schema.DefectClassResponse, status_code=201)
def create_defect_class(
    defect_class: defect_class_schema.DefectClassCreate,
    db: Session = Depends(get_db)
):
    return defect_class_crud.create_defect_class(db, defect_class)


@router.patch("/{class_id}", response_model=defect_class_schema.DefectClassResponse)
def update_defect_class_api(
    class_id: int = Path(..., description="ID of the defect class to update"),
    update_data: defect_class_schema.DefectClassUpdate = Body(...),
    db: Session = Depends(get_db)
):
    return defect_class_crud.update_defect_class(db, class_id, update_data)


@router.delete("/{class_id}", response_model=defect_class_schema.DeleteResult)
def delete_defect_class_api(class_id: int, db: Session = Depends(get_db)):
    return defect_class_crud.delete_defect_class(db, class_id)


@router.patch("/{class_id}/deactivate", response_model=defect_class_schema.DeleteResult)
def deactivate_defect_class_api(class_id: int, db: Session = Depends(get_db)):
    return defect_class_crud.delete_defect_class(db, class_id)
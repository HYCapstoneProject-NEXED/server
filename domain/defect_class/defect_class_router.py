from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.database import get_db
from domain.defect_class import defect_class_crud, defect_class_schema

router = APIRouter(
    prefix="/defect-classes",
    tags=["Defect Class"]
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
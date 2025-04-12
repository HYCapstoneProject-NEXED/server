from sqlalchemy.orm import Session
from database.models import DefectClasses
from fastapi import HTTPException
from domain.defect_class import defect_class_schema


def get_all_defect_classes(db: Session):
    return db.query(DefectClasses).order_by(DefectClasses.created_at).all()


def create_defect_class(db: Session, defect_class: defect_class_schema.DefectClassCreate) -> DefectClasses:
    db_class = DefectClasses(
        class_name=defect_class.class_name,
        class_color=defect_class.class_color
    )
    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return db_class


def update_defect_class(db: Session, class_id: int, update_data: defect_class_schema.DefectClassUpdate):
    db_class = db.query(DefectClasses).filter(DefectClasses.class_id == class_id).first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Defect class not found")

    if update_data.class_name is not None:
        db_class.class_name = update_data.class_name
    if update_data.class_color is not None:
        db_class.class_color = update_data.class_color

    db.commit()
    db.refresh(db_class)
    return db_class
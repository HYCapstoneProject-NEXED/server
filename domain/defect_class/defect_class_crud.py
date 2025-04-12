from sqlalchemy.orm import Session
from database.models import DefectClasses  # 모델은 여기에 정의돼 있다고 가정
from .defect_class_schema import DefectClassCreate


def get_all_defect_classes(db: Session):
    return db.query(DefectClasses).order_by(DefectClasses.created_at).all()


def create_defect_class(db: Session, defect_class: DefectClassCreate) -> DefectClasses:
    db_class = DefectClasses(
        class_name=defect_class.class_name,
        class_color=defect_class.class_color
    )
    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return db_class
from sqlalchemy.orm import Session
from database.models import DefectClasses  # 모델은 여기에 정의돼 있다고 가정

def get_all_defect_classes(db: Session):
    return db.query(DefectClasses).order_by(DefectClasses.created_at).all()
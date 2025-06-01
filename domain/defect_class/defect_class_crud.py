from sqlalchemy.orm import Session
from database.models import DefectClass
from fastapi import HTTPException
from domain.defect_class import defect_class_schema


def get_all_defect_classes(db: Session):
    return (
        db.query(DefectClass)
        .filter(DefectClass.is_active == True)   # 필터 추가
        .order_by(DefectClass.created_at)        # created_at 기준 오름차순 정렬
        .all()
    )


def create_defect_class(db: Session, defect_class: defect_class_schema.DefectClassCreate) -> DefectClass:
    # 1. 동일 이름으로 이미 존재하는 클래스 조회
    existing = db.query(DefectClass).filter(
        DefectClass.class_name == defect_class.class_name
    ).first()

    # 2. 이미 존재 + 비활성화 상태면 → is_active = True로 복구
    if existing:
        if not existing.is_active:
            existing.is_active = True
            existing.class_color = defect_class.class_color  # 색상도 갱신할 수 있음
            db.commit()
            db.refresh(existing)
            return existing
        else:
            raise HTTPException(status_code=400, detail="이미 존재하는 결함 클래스입니다.")

    # 3. 없으면 새로 추가
    db_class = DefectClass(
        class_name=defect_class.class_name,
        class_color=defect_class.class_color,
        is_active=True
    )
    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return db_class


def update_defect_class(db: Session, class_id: int, update_data: defect_class_schema.DefectClassUpdate):
    db_class = db.query(DefectClass).filter(DefectClass.class_id == class_id).first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Defect class not found")

    if update_data.class_name is not None:
        db_class.class_name = update_data.class_name
    if update_data.class_color is not None:
        db_class.class_color = update_data.class_color

    db.commit()
    db.refresh(db_class)
    return db_class


def delete_defect_class(db: Session, class_id: int):
    db_class = db.query(DefectClass).filter(DefectClass.class_id == class_id).first()

    if not db_class:
        raise HTTPException(status_code=404, detail="Defect class not found")

    # 소프트 삭제 처리 (updated_at은 자동으로 갱신됨)
    db_class.is_active = False
    db.commit()

    return {"success": True, "message": f"Defect class {class_id} marked as inactive"}


# class_id로 class_name을 조회하는 함수
def get_class_name_by_id(db: Session, class_id: int) -> str:
    obj = db.query(DefectClass).filter_by(class_id=class_id).first()
    return obj.class_name if obj else "unknown"
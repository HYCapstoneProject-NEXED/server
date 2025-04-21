from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, select
from fastapi import HTTPException
from datetime import datetime, timedelta
from database.models import Image, Annotation, DefectClasses


def get_defect_summary(db: Session):
    today = datetime.today().date()
    yesterday = today - timedelta(days=1)

    # 오늘 결함 수 by class
    today_data = (
        db.query(
            DefectClasses.class_name,
            DefectClasses.class_color,
            func.count().label("count")
        )
        .join(Annotation, Annotation.class_id == DefectClasses.class_id)
        .filter(cast(Annotation.date, Date) == today)
        .group_by(DefectClasses.class_id)
        .all()
    )

    # 어제 결함 수 by class
    yesterday_data = (
        db.query(
            DefectClasses.class_name,
            func.count().label("count")
        )
        .join(Annotation, Annotation.class_id == DefectClasses.class_id)
        .filter(cast(Annotation.date, Date) == yesterday)
        .group_by(DefectClasses.class_id)
        .all()
    )

    # 딕셔너리 변환
    today_dict = {row.class_name: {"count": row.count, "color": row.class_color} for row in today_data}
    yesterday_dict = {row.class_name: row.count for row in yesterday_data}

    total_defects = sum([info["count"] for info in today_dict.values()])
    most_frequent = max(today_dict.items(), key=lambda x: x[1]["count"])[0] if today_dict else None

    by_type = {}
    for class_name in set(today_dict.keys()).union(yesterday_dict.keys()):
        today_info = today_dict.get(class_name, {"count": 0, "color": "#ffffff"})
        yesterday_count = yesterday_dict.get(class_name, 0)

        by_type[class_name] = {
            "count": today_info["count"],
            "color": today_info["color"],
            "change": today_info["count"] - yesterday_count
        }

    return {
        "total_defect_count": total_defects,
        "most_frequent_defect": most_frequent,
        "defect_counts_by_type": by_type
    }

def get_annotation_details_by_image_id(db: Session, image_id: int):
    annotations = (
        db.query(Annotation, DefectClasses.class_name, DefectClasses.class_color)
        .join(DefectClasses, Annotation.class_id == DefectClasses.class_id)
        .filter(Annotation.image_id == image_id)
        .all()
    )

    image_info = db.query(Image).filter(Image.image_id == image_id).first()

    if not image_info:
        return None

    result = {
        "image_id": image_info.image_id,
        "file_path": image_info.file_path,
        "date": image_info.date,
        "camera_id": image_info.camera_id,
        "dataset_id": image_info.dataset_id,
        "defects": []
    }

    for annotation, class_name, class_color in annotations:
        defect_data = {
            "annotation_id": annotation.annotation_id,
            "class_id": annotation.class_id,
            "class_name": class_name,
            "class_color": class_color,
            "conf_score": annotation.conf_score,
            "bounding_box": annotation.bounding_box,
            "status": annotation.status,
            "user_id": annotation.user_id
        }
        result["defects"].append(defect_data)

    return result
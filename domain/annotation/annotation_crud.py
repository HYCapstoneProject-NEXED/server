from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from datetime import datetime, timedelta
from database.models import Annotation


def get_defect_summary(db: Session):
    today = datetime.today().date()
    yesterday = today - timedelta(days=1)

    # 오늘 결함 수 by type
    today_data = (
        db.query(Annotation.defect_type, func.count().label("count"))
        .filter(cast(Annotation.date, Date) == today)
        .group_by(Annotation.defect_type)
        .all()
    )

    # 어제 결함 수 by type
    yesterday_data = (
        db.query(Annotation.defect_type, func.count().label("count"))
        .filter(cast(Annotation.date, Date) == yesterday)
        .group_by(Annotation.defect_type)
        .all()
    )

    # 딕셔너리 변환
    today_dict = {row.defect_type.value: row.count for row in today_data}
    yesterday_dict = {row.defect_type.value: row.count for row in yesterday_data}

    # 전체 결함 수 및 변화량 정리
    total_defects = sum(today_dict.values())
    most_frequent = max(today_dict.items(), key=lambda x: x[1])[0] if today_dict else None

    by_type = {}
    for defect_type in set(today_dict.keys()).union(yesterday_dict.keys()):
        today_count = today_dict.get(defect_type, 0)
        yest_count = yesterday_dict.get(defect_type, 0)

        by_type[defect_type] = {
            "count": today_count,
            "change": today_count - yest_count
        }

    return {
        "total_defect_count": total_defects,
        "most_frequent_defect": most_frequent,
        "defect_counts_by_type": by_type
    }

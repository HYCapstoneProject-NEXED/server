from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, and_, or_
from datetime import datetime, timedelta
from database.models import Annotation, DefectClass, Image, Camera
from collections import defaultdict
from domain.annotation import annotation_schema


def get_defect_summary(db: Session):
    today = datetime.today().date()
    yesterday = today - timedelta(days=1)

    # 오늘 결함 수 by class
    today_data = (
        db.query(
            DefectClass.class_name,
            DefectClass.class_color,
            func.count().label("count")
        )
        .join(Annotation, Annotation.class_id == DefectClass.class_id)
        .filter(cast(Annotation.date, Date) == today)
        .group_by(DefectClass.class_id)
        .all()
    )

    # 어제 결함 수 by class
    yesterday_data = (
        db.query(
            DefectClass.class_name,
            func.count().label("count")
        )
        .join(Annotation, Annotation.class_id == DefectClass.class_id)
        .filter(cast(Annotation.date, Date) == yesterday)
        .group_by(DefectClass.class_id)
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


# 결함 데이터 목록 조회를 위한 함수 (기본 전체 조회)
def get_defect_data_list(db: Session):
    result = (
        db.query(
            Image.image_id,
            Image.file_path,
            Image.date.label("captured_at"),
            Camera.line_id,
            Camera.camera_id,
            DefectClass.class_name
        )
        .join(Camera, Camera.camera_id == Image.camera_id)
        .join(Annotation, Annotation.image_id == Image.image_id)
        .join(DefectClass, DefectClass.class_id == Annotation.class_id)
        .order_by(Image.date.desc())
        .all()
    )

    grouped = defaultdict(lambda: {
        "image_id": None,
        "file_path": None,
        "line_id": None,
        "camera_id": None,
        "captured_at": None,
        "defect_types": []
    })

    for row in result:
        key = row.image_id
        grouped[key]["image_id"] = row.image_id
        grouped[key]["file_path"] = row.file_path
        grouped[key]["line_id"] = row.line_id
        grouped[key]["camera_id"] = row.camera_id
        grouped[key]["captured_at"] = row.captured_at
        grouped[key]["defect_types"].append(row.class_name)

    return list(grouped.values())


# 결함 데이터 목록 "필터링 조회"를 위한 함수
def get_filtered_defect_data_list(db: Session, filters: annotation_schema.DefectDataFilter):
    # 👉 아무 필터도 없을 경우 전체 조회로 대체
    if not filters.dates and not filters.class_ids and not filters.camera_ids:
        return get_defect_data_list(db)  # 기존 전체 조회 함수 호출

    query = (
        db.query(
            Image.image_id,
            Image.file_path,
            Image.date.label("captured_at"),
            Camera.line_id,
            Camera.camera_id,
            DefectClass.class_name
        )
        .join(Camera, Camera.camera_id == Image.camera_id)
        .join(Annotation, Annotation.image_id == Image.image_id)
        .join(DefectClass, DefectClass.class_id == Annotation.class_id)
    )

    # ✅ 날짜 필터: 하루 단위 범위 조건 사용 (datetime.date → datetime 범위)
    if filters.dates:
        date_filters = []
        for date_obj in filters.dates:
            start = datetime.combine(date_obj, datetime.min.time())
            end = start + timedelta(days=1)
            date_filters.append((start, end))
        query = query.filter(
            or_(
                and_(Image.date >= start, Image.date < end)
                for start, end in date_filters
            )
        )

    # ✅ 결함 클래스 필터
    if filters.class_ids:
        query = query.filter(Annotation.class_id.in_(filters.class_ids))

    # ✅ 카메라 ID 필터
    if filters.camera_ids:
        query = query.filter(Image.camera_id.in_(filters.camera_ids))

    # ✅ 최신순 정렬
    query = query.order_by(Image.date.desc())

    rows = query.all()

    grouped = defaultdict(lambda: {
        "image_id": None,
        "file_path": None,
        "line_id": None,
        "camera_id": None,
        "captured_at": None,
        "defect_types": []
    })

    for row in rows:
        key = row.image_id
        grouped[key]["image_id"] = row.image_id
        grouped[key]["file_path"] = row.file_path
        grouped[key]["line_id"] = row.line_id
        grouped[key]["camera_id"] = row.camera_id
        grouped[key]["captured_at"] = row.captured_at
        grouped[key]["defect_types"].append(row.class_name)

    return list(grouped.values())


# 결함 개요 조회를 위한 함수
def get_defect_class_summary(db: Session):
    results = (
        db.query(
            DefectClass.class_name,
            DefectClass.class_color,
            func.count(Annotation.annotation_id).label("count")
        )
        .join(Annotation, Annotation.class_id == DefectClass.class_id)
        .group_by(DefectClass.class_id, DefectClass.class_name, DefectClass.class_color)
        .all()
    )

    return [
        annotation_schema.DefectClassSummaryResponse(
            class_name=row.class_name,
            class_color=row.class_color,
            count=row.count
        ) for row in results
    ]

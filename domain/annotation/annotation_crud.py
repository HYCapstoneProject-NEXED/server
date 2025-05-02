from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, and_, or_, desc
from datetime import datetime, timedelta
from database.models import Annotation, DefectClass, Image, Camera, User
from collections import defaultdict
from domain.annotation import annotation_schema
from typing import List
from fastapi import HTTPException


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


# 실시간 결함 탐지 이력을 조회하는 함수
def get_recent_defect_checks(db: Session, limit: int = 10):
    # 최신 이미지 기준으로 정렬된 서브쿼리
    subquery = (
        db.query(
            Image.image_id,
            Image.file_path,
            Image.date,
            Camera.line_name.label("line_name"),
            Camera.camera_id
        )
        .join(Camera, Image.camera_id == Camera.camera_id)
        .order_by(desc(Image.date))
        .limit(limit)
        .subquery()
    )

    # 이미지 ID를 기준으로 결함 유형(class_name)을 그룹화해서 조회
    result = (
        db.query(
            subquery.c.file_path.label("image_url"),
            subquery.c.line_name,
            subquery.c.camera_id,
            subquery.c.date.label("time"),
            func.group_concat(DefectClass.class_name).label("types")
        )
        .join(Annotation, Annotation.image_id == subquery.c.image_id)
        .join(DefectClass, Annotation.class_id == DefectClass.class_id)
        .group_by(subquery.c.image_id)
        .all()
    )

    return result


def get_annotation_details_by_image_id(db: Session, image_id: int):
    annotations = (
        db.query(Annotation, DefectClass.class_name, DefectClass.class_color)
        .join(DefectClass, Annotation.class_id == DefectClass.class_id)
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

def get_main_data(db: Session, user_id: int):
    # 1. 현재 로그인된 사용자의 profile_image 가져오기
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return None

    # 2. 전체 이미지 개수
    total_images = db.query(func.count(Image.image_id)).scalar()

    # 3. pending 상태의 이미지 개수
    pending_images = db.query(func.count(Image.image_id)).filter(Image.status == "pending").scalar()

    # 4. completed 상태의 이미지 개수
    completed_images = db.query(func.count(Image.image_id)).filter(Image.status == "completed").scalar()

    # 5. 이미지 목록 가져오기
    images = db.query(
        Image.camera_id,
        Image.image_id,
        Image.file_path,
        func.min(Annotation.conf_score).label('confidence'),
        func.count(Annotation.annotation_id).label('count'),
        Image.status
    ).outerjoin(Annotation, Image.image_id == Annotation.image_id)\
     .group_by(Image.camera_id, Image.image_id, Image.file_path, Image.status)\
     .all()

    # 각 이미지의 bounding box 정보 가져오기
    image_list = []
    for img in images:
        bounding_boxes = db.query(Annotation.bounding_box)\
            .filter(Annotation.image_id == img.image_id)\
            .all()

        image_list.append({
            "camera_id": img.camera_id,
            "image_id": img.image_id,
            "file_path": img.file_path,
            "confidence": img.confidence,
            "count": img.count,
            "status": img.status,
            "bounding_boxes": [box[0] for box in bounding_boxes]
        })

    return {
        "profile_image": user.profile_image,
        "total_images": total_images,
        "pending_images": pending_images,
        "completed_images": completed_images,
        "image_list": image_list
    }


# 결함 유형별 통계를 위한 함수
def get_defect_type_statistics(db: Session):
    # 전체 결함 주석 개수 구하기
    total_count = (
        db.query(func.count(Annotation.annotation_id))
        .join(Image, Annotation.image_id == Image.image_id)
        .join(DefectClass, Annotation.class_id == DefectClass.class_id)
        .filter(Image.status == 'completed', DefectClass.is_active == True)
        .scalar()
    )

    if total_count == 0:
        return []

    # 클래스별 주석 개수 집계
    results = (
        db.query(
            DefectClass.class_name,
            DefectClass.class_color,
            func.count(Annotation.annotation_id).label("count")
        )
        .join(Annotation, Annotation.class_id == DefectClass.class_id)
        .join(Image, Annotation.image_id == Image.image_id)
        .filter(Image.status == 'completed', DefectClass.is_active == True)
        .group_by(DefectClass.class_id)
        .all()
    )

    # 비율 계산 및 리스트 변환
    return [
        {
            "class_name": r.class_name,
            "class_color": r.class_color,
            "count": r.count,
            "percentage": round((r.count / total_count) * 100, 1)
        }
        for r in results
    ]


# 주간 요일별 결함 통계를 위한 함수
def get_weekday_defect_summary(db: Session):
    raw = (
        db.query(
            func.date_format(Image.date, "%a").label("day"),  # Image.date를 기준으로 요일 문자열 추출 (Mon, Tue, ...)
            DefectClass.class_name,
            DefectClass.class_color,
            func.count(Annotation.annotation_id).label("count")
        )
        .join(Image, Annotation.image_id == Image.image_id)
        .join(DefectClass, Annotation.class_id == DefectClass.class_id)
        .filter(
            Image.status == "completed",  # 작업 완료된 이미지만
            DefectClass.is_active == True  # 활성화된 결함 클래스만
        )
        .group_by("day", DefectClass.class_id)  # 같은 요일 + 같은 결함 클래스별로 그룹을 나눔
        .all()
    )

    # 가공 단계
    result_dict = {}
    for day, class_name, class_color, count in raw:  # 요일별 데이터를 담을 임시 딕셔너리
        if day not in result_dict:
            result_dict[day] = {
                "day": day,
                "total": 0,
                "defect_counts": []
            }
        result_dict[day]["total"] += count  # 같은 요일끼리 total에 누적
        result_dict[day]["defect_counts"].append({  # 요일별로 결함 클래스별 집계 정보 리스트 추가
            "class_name": class_name,
            "class_color": class_color,
            "count": count
        })

    # 요일 순 정렬 및 반환
    weekday_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    result = [result_dict[day] for day in weekday_order if day in result_dict]

    return result


def delete_images(db: Session, image_ids: List[int]):
    # 존재하는 이미지 ID만 필터링
    existing_images = db.query(Image).filter(Image.image_id.in_(image_ids)).all()
    existing_image_ids = [img.image_id for img in existing_images]
    
    # 존재하지 않는 이미지 ID 찾기
    not_found_ids = set(image_ids) - set(existing_image_ids)
    
    if not_found_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Images not found: {list(not_found_ids)}"
        )
    
    # 이미지 삭제 (CASCADE로 인해 관련 어노테이션도 자동 삭제)
    for image in existing_images:
        db.delete(image)
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Successfully deleted {len(existing_images)} images",
        "deleted_ids": existing_image_ids
    }

from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, and_, or_, desc, literal, String, case
from datetime import datetime, timedelta, time
from database.models import Annotation, DefectClass, Image, Camera, User
from database.models import annotator_camera_association
from collections import defaultdict
from domain.annotation import annotation_schema
from typing import Optional
from datetime import date
from typing import List
from fastapi import HTTPException
from domain.annotation.annotation_schema import (
    AnnotationCreate, AnnotationUpdate, AnnotationResponse, 
    AnnotationBulkUpdate
)
from domain.annotation.annotation_schema import ThumbnailAnnotationResponse, ThumbnailBoundingBox, BoundingBox
from sqlalchemy.orm import aliased
import os
import boto3
from urllib.parse import urlparse
from dotenv import load_dotenv


# .env 로딩
load_dotenv()

# 환경변수 가져오기
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET = os.getenv("S3_BUCKET_NAME")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# boto3 client 구성
s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

# s3 key 추출 함수
def extract_s3_key_from_url(url: str) -> str:
    parsed_url = urlparse(url)
    return parsed_url.path.lstrip("/")  # 버킷 이름 이후 경로만 추출


# 금일 결함 개요 조회 함수
def get_defect_summary(db: Session):
    today = datetime.today().date()
    yesterday = today - timedelta(days=1)

    # 날짜 범위 설정
    today_start = datetime.combine(today, time.min)
    today_end = datetime.combine(today + timedelta(days=1), time.min)
    yesterday_start = datetime.combine(yesterday, time.min)
    yesterday_end = datetime.combine(today, time.min)

    # is_active=True인 class만 가져오기
    class_rows = db.query(DefectClass.class_name, DefectClass.class_color).filter(DefectClass.is_active == True).all()
    # class_name → class_color 매핑 미리 가져오기
    class_colors = {row.class_name: row.class_color for row in class_rows}
    active_class_names = set(class_colors.keys())  # 기준 class 목록

    # 오늘 결함 수 by class (Images.status='completed' + 날짜 기준은 Images.date + is_active=True 주석만)
    today_data = (
        db.query(
            DefectClass.class_name,
            func.count().label("count")
        )
        .join(Annotation, Annotation.class_id == DefectClass.class_id)
        .join(Image, Annotation.image_id == Image.image_id)
        .filter(Annotation.is_active == True)  # 주석이 삭제되지 않은 것만
        .filter(Image.date >= today_start)
        .filter(Image.date < today_end)
        .filter(Image.status == 'completed')
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
        .join(Image, Annotation.image_id == Image.image_id)
        .filter(Annotation.is_active == True)  # 주석이 삭제되지 않은 것만
        .filter(Image.date >= yesterday_start)
        .filter(Image.date < yesterday_end)
        .filter(Image.status == 'completed')
        .group_by(DefectClass.class_id)
        .all()
    )

    # 응답 데이터 구성
    today_dict = {row.class_name: row.count for row in today_data}  # today_dict: count만 저장 (color는 class_colors에서 가져옴)
    yesterday_dict = {row.class_name: row.count for row in yesterday_data}

    # total_defects 계산
    total_defects = sum(today_dict.values())
    # max count 찾기
    max_count = max(today_dict.values(), default=0)
    # most frequent class_name 리스트 구성
    most_frequent = [
        class_name
        for class_name, count in today_dict.items()
        if count == max_count and max_count > 0
    ]

    by_type = {}
    # 기준 class: is_active=True인 결함 전체
    for class_name in active_class_names:
        today_count = today_dict.get(class_name, 0)
        yesterday_count = yesterday_dict.get(class_name, 0)
        color = class_colors[class_name]

        by_type[class_name] = {
            "count": today_count,
            "color": color,
            "change": today_count - yesterday_count
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
            Camera.line_name,
            Camera.camera_id,
            DefectClass.class_name
        )
        .join(Camera, Camera.camera_id == Image.camera_id)
        .join(Annotation, Annotation.image_id == Image.image_id)
        .join(DefectClass, DefectClass.class_id == Annotation.class_id)
        .filter(Image.status == 'completed')  # "pending" 제외! status="completed"인 이미지만 조회
        .filter(Annotation.is_active == True)  # 주석이 삭제되지 않은 것만
        .order_by(Image.date.desc())
        .all()
    )

    grouped = defaultdict(lambda: {
        "image_id": None,
        "file_path": None,
        "line_name": None,
        "camera_id": None,
        "captured_at": None,
        "defect_types": []
    })

    for row in result:
        key = row.image_id
        grouped[key]["image_id"] = row.image_id
        grouped[key]["file_path"] = row.file_path
        grouped[key]["line_name"] = row.line_name
        grouped[key]["camera_id"] = row.camera_id
        grouped[key]["captured_at"] = row.captured_at
        grouped[key]["defect_types"].append(row.class_name)

    return list(grouped.values())


# 결함 데이터 목록 "필터링 조회"를 위한 함수
def get_filtered_defect_data_list(db: Session, filters: annotation_schema.DefectDataFilter):
    # 아무 필터도 없을 경우 전체 조회로 대체
    if not (filters.start_date and filters.end_date) and not filters.class_ids and not filters.camera_ids:
        return get_defect_data_list(db)  # 기존 전체 조회 함수 호출

    query = (
        db.query(
            Image.image_id,
            Image.file_path,
            Image.date.label("captured_at"),
            Camera.line_name,
            Camera.camera_id,
            DefectClass.class_name
        )
        .join(Camera, Camera.camera_id == Image.camera_id)
        .join(Annotation, Annotation.image_id == Image.image_id)
        .join(DefectClass, DefectClass.class_id == Annotation.class_id)
        .filter(Image.status == 'completed')  # "pending" 제외! status="completed"인 이미지만 조회
        .filter(Annotation.is_active == True)  # 주석이 삭제되지 않은 것만
    )

    # 날짜 필터(start_date ~ end_date)
    if filters.start_date and filters.end_date:
        start_datetime = datetime.combine(filters.start_date, datetime.min.time())
        end_datetime = datetime.combine(filters.end_date + timedelta(days=1), datetime.min.time())  # 포함 범위
        query = query.filter(Image.date >= start_datetime, Image.date < end_datetime)

    # 결함 클래스 필터
    if filters.class_ids:
        query = query.filter(Annotation.class_id.in_(filters.class_ids))

    # 카메라 ID 필터
    if filters.camera_ids:
        query = query.filter(Image.camera_id.in_(filters.camera_ids))

    # 최신순 정렬
    query = query.order_by(Image.date.desc())

    rows = query.all()

    grouped = defaultdict(lambda: {
        "image_id": None,
        "file_path": None,
        "line_name": None,
        "camera_id": None,
        "captured_at": None,
        "defect_types": []
    })

    for row in rows:
        key = row.image_id
        grouped[key]["image_id"] = row.image_id
        grouped[key]["file_path"] = row.file_path
        grouped[key]["line_name"] = row.line_name
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
        .filter(Annotation.is_active == True)  # is_active=True인 어노테이션만 조회
        .all()
    )

    image_info = db.query(Image).filter(Image.image_id == image_id).first()

    if not image_info:
        return None

    # 데이터베이스에서 가장 마지막(최대) annotation_id 값 조회
    last_annotation_id = (
        db.query(func.max(Annotation.annotation_id))
        .scalar() or 0
    )

    result = {
        "image_id": image_info.image_id,
        "file_path": image_info.file_path,
        "date": image_info.date,
        "camera_id": image_info.camera_id,
        "dataset_id": image_info.dataset_id,
        "status": image_info.status,
        "width": image_info.width,
        "height": image_info.height,
        "last_annotation_id": last_annotation_id,
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
            "user_id": annotation.user_id,
            "is_active": annotation.is_active  # is_active 값 추가
        }
        result["defects"].append(defect_data)

    return result


def get_annotation_details_by_image_ids(db: Session, image_ids: List[int]):
    result = []
    for image_id in image_ids:
        detail = get_annotation_details_by_image_id(db, image_id)
        if detail is not None:
            result.append(detail)
    return {"details": result}


def get_main_data(db: Session, user_id: int, filters: Optional[annotation_schema.MainScreenFilter] = None):
    # 1. 현재 로그인된 사용자의 profile_image 가져오기
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return None

    # 2. 이미지 목록 조회 - 기본 쿼리 구성
    query = (
        db.query(
            Image.camera_id,
            Image.image_id,
            Image.file_path,
            Image.width,
            Image.height,
            Image.status,
            func.count(Annotation.annotation_id).label("count"),
            func.min(Annotation.conf_score).label("confidence")
        )
        .outerjoin(Annotation, Image.image_id == Annotation.image_id)
    )
    
    # is_active=True인 어노테이션만 카운트하도록 수정
    query = query.filter(or_(Annotation.is_active == True, Annotation.annotation_id == None))
    
    # 클래스 이름 필터가 있을 경우, DefectClass 조인
    defect_class_joined = False
    if filters and filters.class_names:
        query = query.join(DefectClass, Annotation.class_id == DefectClass.class_id)
        defect_class_joined = True

    # 3. 필터 적용
    if filters:
        if filters.status:
            query = query.filter(Image.status == filters.status)
        if filters.class_names:
            query = query.filter(DefectClass.class_name.in_(filters.class_names))
        
    # 마지막에 그룹화
    query = query.group_by(Image.image_id)
    
    # Confidence 필터는 그룹화 후 적용
    if filters:
        if filters.min_confidence is not None:
            # min_confidence가 0이면 annotation이 없는 이미지들도 포함
            if filters.min_confidence == 0:
                query = query.having(
                    or_(
                        func.min(Annotation.conf_score) >= filters.min_confidence,
                        func.min(Annotation.conf_score).is_(None)  # annotation이 없는 이미지도 포함
                    )
                )
            else:
                query = query.having(func.min(Annotation.conf_score) >= filters.min_confidence)
        if filters.max_confidence is not None:
            query = query.having(func.min(Annotation.conf_score) <= filters.max_confidence)

    # 4. 결과 조회
    images = query.all()

    # 5. 바운딩 박스 정보 조회
    image_ids = [img.image_id for img in images]
    
    # 바운딩 박스 조회를 위한 서브쿼리
    bounding_boxes_query = (
        db.query(
            Annotation.image_id,
            func.json_arrayagg(
                func.json_object(
                    'bounding_box', Annotation.bounding_box,
                    'class_name', DefectClass.class_name,
                    'is_active', Annotation.is_active
                )
            ).label('boxes')
        )
        .join(DefectClass, Annotation.class_id == DefectClass.class_id)
        .filter(Annotation.image_id.in_(image_ids))
        .filter(Annotation.is_active == True)  # is_active=True인 어노테이션만 포함
        .group_by(Annotation.image_id)
    )
    
    # 실행
    bounding_boxes = bounding_boxes_query.all()

    # 6. 바운딩 박스 정보를 딕셔너리로 변환
    bbox_dict = {row.image_id: row.boxes for row in bounding_boxes}

    # 7. 응답 데이터 구성
    image_list = []
    for img in images:
        image_list.append({
            "camera_id": img.camera_id,
            "image_id": img.image_id,
            "file_path": img.file_path,
            "width": img.width,
            "height": img.height,
            "confidence": float(img.confidence) if img.confidence else None,
            "count": img.count,
            "status": img.status,
            "bounding_boxes": bbox_dict.get(img.image_id, [])
        })

    # 8. 전체 통계 계산
    total_images = len(image_list)
    pending_images = sum(1 for img in image_list if img["status"] == "pending")
    completed_images = sum(1 for img in image_list if img["status"] == "completed")

    return {
        "profile_image": user.profile_image,
        "total_images": total_images,
        "pending_images": pending_images,
        "completed_images": completed_images,
        "image_list": image_list
    }


def get_main_data_filtered(db: Session, user_id: int):
    """
    메인 화면 데이터 조회 (필터링 적용) - annotation이 없는 이미지와 최저 conf_score가 0.75 이상인 이미지 제외
    사용자에게 할당된 카메라의 이미지만 조회
    """
    # 1. 현재 로그인된 사용자의 profile_image 가져오기
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return None

    # 2. 사용자에게 할당된 카메라의 이미지 목록 조회 - annotation이 있는 이미지만, 최저 conf_score < 0.75인 이미지만
    query = (
        db.query(
            Image.camera_id,
            Image.image_id,
            Image.file_path,
            Image.width,
            Image.height,
            Image.status,
            Image.date,  # 정렬을 위해 date 필드 추가
            func.sum(case((Annotation.is_active == True, 1), else_=0)).label("count"),
            func.min(case((and_(Annotation.is_active == True, Annotation.conf_score.isnot(None)), Annotation.conf_score))).label("confidence")
        )
        .join(Annotation, Image.image_id == Annotation.image_id)  # INNER JOIN으로 annotation이 있는 이미지만 (is_active 조건 제거)
        .join(Camera, Image.camera_id == Camera.camera_id)  # 카메라 테이블 JOIN
        .join(                                              # 사용자-카메라 할당 테이블 JOIN
            annotator_camera_association,
            Camera.camera_id == annotator_camera_association.c.camera_id
        )
        .filter(annotator_camera_association.c.user_id == user_id)  # 사용자에게 할당된 카메라만 필터링
        .group_by(Image.image_id)
    )
    
    # 3. 최저 conf_score가 0.75 미만인 이미지만 필터링 (활성 어노테이션 기준)
    query = query.having(
        or_(
            func.min(case((and_(Annotation.is_active == True, Annotation.conf_score.isnot(None)), Annotation.conf_score))) < 0.75,
            func.min(case((and_(Annotation.is_active == True, Annotation.conf_score.isnot(None)), Annotation.conf_score))).is_(None)  # 활성 어노테이션이 없는 경우도 포함
        )
    )
    
    # 4. 최신 날짜 순으로 정렬
    query = query.order_by(Image.date.desc())
    
    images = query.all()

    # 5. 바운딩 박스 정보 조회
    image_ids = [img.image_id for img in images]
    
    if image_ids:  # 이미지가 있을 때만 바운딩 박스 조회
        bounding_boxes_query = (
            db.query(
                Annotation.image_id,
                func.json_arrayagg(
                    func.json_object(
                        'bounding_box', Annotation.bounding_box,
                        'class_name', DefectClass.class_name,
                        'is_active', Annotation.is_active
                    )
                ).label('boxes')
            )
            .join(DefectClass, Annotation.class_id == DefectClass.class_id)
            .filter(Annotation.image_id.in_(image_ids))
            .filter(Annotation.is_active == True)  # is_active=True인 어노테이션만 포함
            .group_by(Annotation.image_id)
        )
        
        bounding_boxes = bounding_boxes_query.all()
        bbox_dict = {row.image_id: row.boxes for row in bounding_boxes}
    else:
        bbox_dict = {}

    # 6. 응답 데이터 구성
    image_list = []
    for img in images:
        image_list.append({
            "camera_id": img.camera_id,
            "image_id": img.image_id,
            "file_path": img.file_path,
            "width": img.width,
            "height": img.height,
            "confidence": float(img.confidence) if img.confidence else None,
            "count": img.count,
            "status": img.status,
            "bounding_boxes": bbox_dict.get(img.image_id, [])
        })

    # 7. 전체 통계 계산
    total_images = len(image_list)
    pending_images = sum(1 for img in image_list if img["status"] == "pending")
    completed_images = sum(1 for img in image_list if img["status"] == "completed")

    return {
        "profile_image": user.profile_image,
        "total_images": total_images,
        "pending_images": pending_images,
        "completed_images": completed_images,
        "image_list": image_list
    }


def get_main_data_filtered_with_filters(db: Session, user_id: int, filters: Optional[annotation_schema.MainScreenFilter] = None):
    """
    메인 화면 데이터 조회 (필터링 적용 + 추가 필터) - annotation이 없는 이미지와 최저 conf_score가 0.75 이상인 이미지 제외
    사용자에게 할당된 카메라의 이미지만 조회
    """
    # 1. 현재 로그인된 사용자의 profile_image 가져오기
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return None

    # 2. 사용자에게 할당된 카메라의 이미지 목록 조회 - annotation이 있는 이미지만
    query = (
        db.query(
            Image.camera_id,
            Image.image_id,
            Image.file_path,
            Image.width,
            Image.height,
            Image.status,
            Image.date,  # 정렬을 위해 date 필드 추가
            func.count(Annotation.annotation_id).label("count"),
            func.min(Annotation.conf_score).label("confidence")
        )
        .join(Annotation, Image.image_id == Annotation.image_id)  # INNER JOIN으로 annotation이 있는 이미지만
        .join(Camera, Image.camera_id == Camera.camera_id)  # 카메라 테이블 JOIN
        .join(                                              # 사용자-카메라 할당 테이블 JOIN
            annotator_camera_association,
            Camera.camera_id == annotator_camera_association.c.camera_id
        )
        .filter(annotator_camera_association.c.user_id == user_id)  # 사용자에게 할당된 카메라만 필터링
        .filter(Annotation.is_active == True)  # 활성 annotation만
        .filter(Annotation.conf_score.isnot(None))  # conf_score가 null이 아닌 annotation만
    )
    
    # 클래스 이름 필터가 있을 경우, DefectClass 조인
    if filters and filters.class_names:
        query = query.join(DefectClass, Annotation.class_id == DefectClass.class_id)

    # 3. 필터 적용
    if filters:
        if filters.status:
            query = query.filter(Image.status == filters.status)
        if filters.class_names:
            query = query.filter(DefectClass.class_name.in_(filters.class_names))
        
    # 마지막에 그룹화
    query = query.group_by(Image.image_id)
    
    # 4. 최저 conf_score가 0.75 미만인 이미지만 필터링
    having_conditions = [func.min(Annotation.conf_score) < 0.75]
    
    # Confidence 필터는 그룹화 후 적용
    if filters:
        if filters.min_confidence is not None:
            having_conditions.append(func.min(Annotation.conf_score) >= filters.min_confidence)
        if filters.max_confidence is not None:
            having_conditions.append(func.min(Annotation.conf_score) <= filters.max_confidence)

    # 모든 HAVING 조건 적용
    query = query.having(and_(*having_conditions))
    
    # 5. 최신 날짜 순으로 정렬
    query = query.order_by(Image.date.desc())
    
    images = query.all()

    # 6. 바운딩 박스 정보 조회
    image_ids = [img.image_id for img in images]
    
    if image_ids:  # 이미지가 있을 때만 바운딩 박스 조회
        bounding_boxes_query = (
            db.query(
                Annotation.image_id,
                func.json_arrayagg(
                    func.json_object(
                        'bounding_box', Annotation.bounding_box,
                        'class_name', DefectClass.class_name,
                        'is_active', Annotation.is_active
                    )
                ).label('boxes')
            )
            .join(DefectClass, Annotation.class_id == DefectClass.class_id)
            .filter(Annotation.image_id.in_(image_ids))
            .filter(Annotation.is_active == True)  # is_active=True인 어노테이션만 포함
            .group_by(Annotation.image_id)
        )
        
        bounding_boxes = bounding_boxes_query.all()
        bbox_dict = {row.image_id: row.boxes for row in bounding_boxes}
    else:
        bbox_dict = {}

    # 7. 응답 데이터 구성
    image_list = []
    for img in images:
        image_list.append({
            "camera_id": img.camera_id,
            "image_id": img.image_id,
            "file_path": img.file_path,
            "width": img.width,
            "height": img.height,
            "confidence": float(img.confidence) if img.confidence else None,
            "count": img.count,
            "status": img.status,
            "bounding_boxes": bbox_dict.get(img.image_id, [])
        })

    # 8. 전체 통계 계산
    total_images = len(image_list)
    pending_images = sum(1 for img in image_list if img["status"] == "pending")
    completed_images = sum(1 for img in image_list if img["status"] == "completed")

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
        .filter(Image.status == 'completed',
                DefectClass.is_active == True,
                Annotation.is_active == True  # 삭제되지 않은 주석만 포함
        )
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
        .filter(Image.status == 'completed',
                DefectClass.is_active == True,
                Annotation.is_active == True  # 삭제되지 않은 주석만 포함
        )
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

# 주간 요일별 결함 통계를 위한 함수 (최근 7일)
def get_weekday_defect_summary(db: Session):
    today = datetime.now().date()  # 오늘 날짜 (예: 2025-06-03)
    seven_days_ago = today - timedelta(days=6)  # 오늘 포함 → 6일만 빼면 7일 범위 됨 (예: 5/28)

    raw = (
        db.query(
            func.date(Image.date).label("date"),  # 날짜 기준으로 group
            DefectClass.class_name,
            DefectClass.class_color,
            func.count(Annotation.annotation_id).label("count")
        )
        .join(Image, Annotation.image_id == Image.image_id)
        .join(DefectClass, Annotation.class_id == DefectClass.class_id)
        .filter(
            Image.status == "completed",
            DefectClass.is_active == True,
            Annotation.is_active == True,  # 삭제되지 않은 주석만 포함
            func.date(Image.date) >= seven_days_ago,  # 시작 날짜
            func.date(Image.date) <= today            # 끝 날짜 (오늘 포함)
        )
        .group_by(func.date(Image.date), DefectClass.class_id)  # 정확한 날짜 단위로 그룹
        .all()
    )

    # 오늘 날짜 기준 최근 7일(오늘 포함) 역순 정렬
    recent_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    weekday_order = [day.strftime("%a") for day in recent_7_days]

    # 미리 모든 요일을 초기화
    result_dict = {
        day: {
            "day": day,
            "total": 0,
            "defect_counts": []
        }
        for day in weekday_order
    }

    # 쿼리 결과 가공: 날짜 → 요일로 변환
    for date, class_name, class_color, count in raw:
        day_str = date.strftime("%a")
        print(f"[DEBUG] {date} → {day_str}")  # 디버깅용 출력

        if day_str in result_dict:
            result_dict[day_str]["total"] += count
            result_dict[day_str]["defect_counts"].append({
                "class_name": class_name,
                "class_color": class_color,
                "count": count
            })

    # 정렬 순서대로 리스트 구성
    result = [result_dict[day] for day in weekday_order]

    return result


# 기간별 결함 통계를 위한 함수
def get_defect_statistics_by_period(
    db: Session,
    start_date: date,
    end_date: date,
    unit: str,
    defect_types: Optional[List[str]] = None,
    camera_ids: Optional[List[int]] = None
):
    # 필터 충돌 방지
    if defect_types and camera_ids:
        raise ValueError("defect_type과 camera_id는 동시에 필터링할 수 없습니다.")

    # 집계 단위에 따라 날짜 포맷 결정
    if unit in ("week", "month", "custom"):  # 일별
        date_format = "%Y-%m-%d"
    elif unit == "year":  # 월별
        date_format = "%Y-%m"
    else:
        raise ValueError("unit은 'week', 'month', 'year', 'custom' 중 하나여야 합니다.")

    # 기본 쿼리 시작
    query = db.query(
        func.date_format(Image.date, date_format).label("period"),
        func.count().label("defect_count")
    ).select_from(Annotation).join(Image, Annotation.image_id == Image.image_id)

    # 결함 유형 필터
    if defect_types:
        query = query.join(
            DefectClass, Annotation.class_id == DefectClass.class_id
        ).filter(
            DefectClass.class_name.in_(defect_types)
        ).add_columns(
            DefectClass.class_name.label("label"),
            DefectClass.class_color.label("class_color")
        )
        group_by_cols = ["period", "label", "class_color"]

    # 카메라 ID 필터
    elif camera_ids:
        query = query.filter(
            Image.camera_id.in_(camera_ids)
        ).add_columns(
            func.cast(Image.camera_id, String).label("label"),
            literal(None).label("class_color")  # 그대로 null 유지
        )
        group_by_cols = ["period", "label"]

    # 전체 집계 (필터 없음)
    else:
        query = query.add_columns(
            literal(None).label("label"),
            literal(None).label("class_color")
        )
        group_by_cols = ["period"]

    # completed 상태 + 삭제되지 않은 주석만 집계
    query = query.filter(
        Image.status == 'completed',
        Annotation.is_active == True  # 삭제되지 않은 주석만 포함
    )

    # 날짜 필터링
    query = query.filter(Image.date >= start_date, Image.date < end_date + timedelta(days=1))  # 🔧 수정
    query = query.group_by(*group_by_cols).order_by("period", "label")

    result = query.all()

    # 1. label → class_color 맵 생성 & data_map 구성
    label_color_map = {}
    data_map = {}
    for row in result:
        label = getattr(row, "label", None)
        color = getattr(row, "class_color", None)
        key = (row.period, label)
        data_map[key] = {
            "defect_count": row.defect_count,
            "class_color": color,
        }
        if label is not None and color is not None:
            label_color_map[label] = color

    # 2. label_list 생성
    label_list = list(set(label for (_, label) in data_map.keys()))
    if not label_list:
        label_list = [None]

    # 3. 모든 기간 내 날짜 리스트 생성
    def generate_date_range(start: date, end: date, unit: str):
        current = start
        dates = []
        while current <= end:
            if unit in ("week", "month", "custom"):
                dates.append(current.strftime("%Y-%m-%d"))
                current += timedelta(days=1)
            elif unit == "year":
                dates.append(current.strftime("%Y-%m"))
                # 다음 달로 이동
                current = (current.replace(day=1) + timedelta(days=32)).replace(day=1)
        return dates

    date_list = generate_date_range(start_date, end_date, unit)

    # 5. 응답 리스트 구성
    final_result = []
    for date_str in date_list:
        for label in label_list:
            key = (date_str, label)
            data = data_map.get(key, {"defect_count": 0, "class_color": None})
            entry = {
                "date": date_str,
                "defect_count": data["defect_count"]
            }
            if label is not None:
                entry["label"] = label
                entry["class_color"] = data["class_color"] or label_color_map.get(label)
            final_result.append(entry)

    return final_result


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

    # S3에서 이미지 파일 삭제
    s3_errors = []
    for image in existing_images:
        try:
            s3_key = extract_s3_key_from_url(image.file_path)
            s3.delete_object(Bucket=S3_BUCKET, Key=s3_key)
        except Exception as e:
            s3_errors.append(f"S3 Error for image {image.image_id}: {str(e)}")

    # 이미지 삭제 (CASCADE로 인해 관련 어노테이션도 자동 삭제)
    for image in existing_images:
        db.delete(image)

    db.commit()

    # S3 오류가 있다면 경고 메시지 추가
    message = f"Successfully deleted {len(existing_images)} images"
    if s3_errors:
        message += f", but encountered {len(s3_errors)} S3 errors"

    return {
        "success": True,
        "message": message,
        "deleted_ids": existing_image_ids
    }


def update_image_status(db: Session, image_id: int, status: str):
    # 유효한 상태 값인지 확인
    if status not in ["pending", "completed"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid status. Status must be either 'pending' or 'completed'"
        )

    # 이미지 존재 여부 확인
    image = db.query(Image).filter(Image.image_id == image_id).first()
    if not image:
        raise HTTPException(
            status_code=404,
            detail=f"Image with ID {image_id} not found"
        )

    # 상태 업데이트
    image.status = status
    db.commit()
    db.refresh(image)

    return {
        "success": True,
        "message": f"Image status updated successfully",
        "image_id": image_id,
        "new_status": status
    }


# 작업 기록 조회 함수
def get_annotation_history(db: Session, filters: annotation_schema.AnnotationHistoryFilter):
    # 서브쿼리: 이미지별 주석 중 대표 주석 1건을 선택하기 위한 row_number 부여
    annot_with_rownum = (
        db.query(
            Annotation.annotation_id,
            Annotation.image_id,
            Annotation.date,
            Annotation.user_id,

            # 동일한 image_id 그룹 내에서 row_number 부여 (date는 모두 동일)
            func.row_number().over(
                partition_by=Annotation.image_id,
                order_by=Annotation.date.desc()
            ).label("row_num")
        )
        .join(Image, Annotation.image_id == Image.image_id)
        .filter(Image.status == 'completed')  # status가 completed인 이미지에 대해서만 조회
        .subquery()
    )

    # 서브쿼리 결과를 참조하기 위한 alias
    RepAnnot = aliased(Annotation, annot_with_rownum)

    # 메인 쿼리: 이미지별 대표 주석 1건만 join (row_num = 1 조건)
    query = (
        db.query(
            Image.image_id,
            User.name.label("user_name"),
            RepAnnot.date.label("annotation_date"),
            Image.status.label("image_status")
        )
        .join(Image, RepAnnot.image_id == Image.image_id)  # 주석 → 이미지 조인
        .join(User, RepAnnot.user_id == User.user_id)  # 주석 → 사용자 조인
        .filter(annot_with_rownum.c.row_num == 1)   # 대표 주석 1건만 조회
    )

    # 날짜 필터
    if filters.start_date and filters.end_date:
        next_day = filters.end_date + timedelta(days=1)
        query = query.filter(RepAnnot.date >= filters.start_date)  # Annotation.date → RepAnnot.date
        query = query.filter(RepAnnot.date < next_day)

    # 사용자 필터
    if filters.user_name not in [None, "", "All"]:
        query = query.filter(User.name == filters.user_name)

    # 검색 (주석자 이름(users.name) 기준)
    if filters.search:
        search_value = str(filters.search).strip()
        query = query.filter(User.name.ilike(f"%{search_value}%"))

    return query.order_by(RepAnnot.date.desc()).all()  # RepAnnot 기준으로 정렬


class AnnotationService:
    def __init__(self, db: Session):
        self.db = db

    def update_image_annotations(self, image_id: int, user_id: int, data: AnnotationBulkUpdate) -> List[AnnotationResponse]:
        # 1. 기존 annotation ID 목록 조회
        existing_annotation_ids = set(
            ann.annotation_id for ann in self.db.query(Annotation)
            .filter(Annotation.image_id == image_id)
            .all()
        )
        
        # 2. 업데이트할 annotation ID 목록
        update_annotation_ids = set(
            ann.annotation_id for ann in data.existing_annotations
        )
        
        # 3. 삭제할 annotation ID 목록 (기존에 있지만 업데이트 목록에 없는 것)
        delete_annotation_ids = existing_annotation_ids - update_annotation_ids
        
        # 4. 소프트 삭제 처리 (is_active = False로 설정)
        if delete_annotation_ids:
            self.db.query(Annotation).filter(
                Annotation.annotation_id.in_(delete_annotation_ids)
            ).update({'is_active': False}, synchronize_session=False)
        
        # 5. 업데이트 처리 (conf_score는 그대로 유지)
        for update_data in data.existing_annotations:
            self.db.query(Annotation).filter(
                Annotation.annotation_id == update_data.annotation_id
            ).update({
                'class_id': update_data.class_id,
                'bounding_box': update_data.bounding_box.dict(),  # BoundingBox 객체를 dict로 변환
                'date': datetime.utcnow(),
                'user_id': user_id
                # conf_score는 업데이트하지 않음 (기존 값 유지)
            })
        
        # 6. 새로운 annotation 생성 (conf_score는 null)
        new_annotations = []
        for create_data in data.annotations:
            new_annotation = Annotation(
                image_id=image_id,
                class_id=create_data.class_id,
                bounding_box=create_data.bounding_box.dict(),  # BoundingBox 객체를 dict로 변환
                date=datetime.utcnow(),
                conf_score=None,  # 새로 추가되는 어노테이션은 conf_score를 null로 설정
                user_id=user_id,
                is_active=True  # 새로 생성하는 어노테이션은 활성 상태
            )
            self.db.add(new_annotation)
            new_annotations.append(new_annotation)
        
        # 7. 변경사항 저장
        self.db.commit()
        
        # 8. 업데이트된 annotation 목록 조회
        updated_annotations = self.db.query(Annotation).filter(
            Annotation.image_id == image_id,
            Annotation.is_active == True
        ).all()
        
        return [AnnotationResponse.from_orm(ann) for ann in updated_annotations]


def get_task_summary_data(db: Session, user_id: int):
    """
    작업 요약 데이터 조회 - main API와 동일한 조회 조건 사용
    """
    # Main API와 동일한 데이터 조회
    main_data = get_main_data_filtered(db, user_id)
    if main_data is None:
        return None

    # Main API에서 이미 계산된 통계 반환
    return {
        "total_images": main_data["total_images"],
        "pending_images": main_data["pending_images"],
        "completed_images": main_data["completed_images"]
    }


# 더미 데이터 삽입 시 주석 생성을 위한 함수
def create_annotation(
    db: Session,
    image_id: int,
    class_id: int,
    x_center: float,
    y_center: float,
    w: float,
    h: float,
    confidence: float,
    user_id: int | None = None  # 필요하면 사용
):
    annotation = Annotation(
        image_id=image_id,
        class_id=class_id,
        bounding_box={
            "x_center": x_center,
            "y_center": y_center,
            "w": w,
            "h": h
        },
        conf_score=confidence,
        user_id=user_id,  # 필요 시 None으로 전달
        is_active=True
    )
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return annotation


# 썸네일 바운딩 박스 표시 함수
def get_thumbnail_annotation(db: Session, image_id: int) -> ThumbnailAnnotationResponse:
    image = db.query(Image).filter(Image.image_id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    results = (
        db.query(Annotation, DefectClass)
        .join(DefectClass, Annotation.class_id == DefectClass.class_id)
        .filter(
            Annotation.image_id == image_id,
            Annotation.is_active == True
        )
        .all()
    )

    annotations = [
        ThumbnailBoundingBox(
            class_name=cls.class_name,
            class_color=cls.class_color,
            confidence=ann.conf_score or 0.0,
            bounding_box=BoundingBox(
                x_center=ann.bounding_box.get("x_center", ann.bounding_box.get("cx")),
                y_center=ann.bounding_box.get("y_center", ann.bounding_box.get("cy")),
                w=ann.bounding_box.get("w", ann.bounding_box.get("width")),
                h=ann.bounding_box.get("h", ann.bounding_box.get("height")),
            )
        )
        for ann, cls in results
    ]

    return ThumbnailAnnotationResponse(
        image_id=image.image_id,
        file_path=image.file_path,
        width=image.width,
        height=image.height,
        annotations=annotations
    )

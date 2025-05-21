from sqlalchemy import Column, Integer, String, Date, Boolean, DateTime, Enum, Float, ForeignKey, JSON, func
from database.database import Base
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from sqlalchemy import Table
from sqlalchemy import Enum as SqlEnum


# 🔹 User-Camera Many-to-Many 중간 테이블
annotator_camera_association = Table(
    "AnnotatorCameras",  # ← 테이블 이름 변경
    Base.metadata,
    Column("user_id", Integer, ForeignKey("Users.user_id", ondelete="CASCADE"), primary_key=True),
    Column("camera_id", Integer, ForeignKey("Cameras.camera_id", ondelete="CASCADE"), primary_key=True)
)


# role Enum
class UserTypeEnum(str, enum.Enum):
    admin = "admin"
    customer = "customer"
    annotator = "annotator"
    ml_engineer = "ml_engineer"


# 가입 승인 상태 Enum
class ApprovalStatusEnum(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


# 성별 Enum
class GenderEnum(str, enum.Enum):
    female = "female"
    male = "male"


class User(Base):
    __tablename__ = "Users"

    user_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)  # PK, 중복 불가능
    google_email = Column(String(255), unique=True, nullable=False)  # 이메일, 중복 불가능, 필수
    name = Column(String(255), nullable=False, index=True)  # 이름, 중복 가능, 필수
    user_type = Column(  # 사용자 타입, 필수
        SqlEnum(UserTypeEnum, name="user_type_enum"),
        nullable=False,
        index=True
    )
    birthdate = Column(Date, nullable=False)  # 생년월일 (YYYY-MM-DD), 필수
    nationality = Column(String(255), nullable=False)  # 국적, 필수
    address = Column(String(255), nullable=True)  # 주소, 선택 사항
    company_name = Column(String(255), nullable=False)  # 회사명, 필수
    factory_name = Column(String(255), nullable=False)  # 공장명, 필수
    bank_name = Column(String(255), nullable=False)  # 은행명, 필수
    bank_account = Column(String(255), unique=True, nullable=False)  # 계좌번호, 중복 불가능, 필수
    terms_accepted = Column(Boolean, nullable=False)  # 약관 동의, 필수
    profile_image = Column(String(500), nullable=True)  # 프로필 이미지 경로, 선택 사항 (NULL이면 default 이미지)
    is_active = Column(Boolean, nullable=False, default=False)  # 유저 활성 여부, 필수, 기본값=False
    approval_status = Column(  # 가입 승인 상태 (pending / approved / rejected), 필수
        SqlEnum(ApprovalStatusEnum, name="approval_status_enum"),
        default=ApprovalStatusEnum.pending,
        nullable=False
    )
    gender = Column(  # 성별(female / male), 필수
        SqlEnum(GenderEnum, name="gender_enum"),
        nullable=False
    )

    # 🔹 Many-to-Many: User ↔ Camera
    assigned_cameras = relationship(
        "Camera",
        secondary=annotator_camera_association,
        back_populates="annotators"
    )


# 이미지 테이블
class Image(Base):
    __tablename__ = "Images"

    image_id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String(500), nullable=False)
    date = Column(DateTime, nullable=False, default=datetime.utcnow)  # 업로드 시점 기준으로 자동으로 시간 기록이 되도록.
    camera_id = Column(Integer, ForeignKey("Cameras.camera_id"), nullable=False)
    dataset_id = Column(Integer, nullable=False)
    status = Column(Enum("pending", "completed", name="statusenum"), nullable=False, default="pending")
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    
    annotations = relationship(
    "Annotation",
    back_populates="image",
    cascade="all, delete-orphan",   # 삭제 연쇄 처리
    passive_deletes=True            # DB에게 cascade 책임 위임
)
    camera = relationship("Camera", back_populates="images")


# 어노테이션 테이블 (defect_type 제거 → class_id로 대체)
class Annotation(Base):
    __tablename__ = "Annotations"

    annotation_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    image_id = Column(Integer, ForeignKey("Images.image_id", ondelete="CASCADE"), nullable=False)
    class_id = Column(Integer, ForeignKey("DefectClasses.class_id", ondelete="RESTRICT"), nullable=False)
    date = Column(DateTime, nullable=False, default=func.now())
    conf_score = Column(Float, nullable=True)
    bounding_box = Column(JSON, nullable=False)
    user_id = Column(Integer, ForeignKey("Users.user_id"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)  # 소프트 삭제용 필드. 삭제 시 is_active=False

    image = relationship("Image", back_populates="annotations")
    defect_class = relationship("DefectClass", back_populates="annotations")
    user = relationship("User", backref="annotations")


# 결함 클래스 테이블
class DefectClass(Base):
    __tablename__ = "DefectClasses"

    class_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    class_name = Column(String(50), unique=True, nullable=False)
    class_color = Column(String(7), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    annotations = relationship("Annotation", back_populates="defect_class")


# Camera 테이블 정의
class Camera(Base):
    __tablename__ = "Cameras"

    camera_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    line_name = Column(String(50), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    images = relationship("Image", back_populates="camera")  # 🔹 Image와 연결

    annotators = relationship(
        "User",
        secondary=annotator_camera_association,
        back_populates="assigned_cameras"
    )




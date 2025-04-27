from sqlalchemy import Column, Integer, String, Date, Boolean, DateTime, Enum, Float, ForeignKey, JSON
from database.database import Base
from sqlalchemy.orm import relationship
import enum
from datetime import datetime


class User(Base):
    __tablename__ = "Users"

    user_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)  # PK, 중복 불가능
    google_email = Column(String(255), unique=True, nullable=False)  # 이메일, 중복 불가능, 필수
    name = Column(String(255), nullable=False)  # 이름, 중복 가능, 필수
    user_type = Column(String(255), nullable=False)  # 사용자 타입, 필수
    birthdate = Column(Date, nullable=False)  # 생년월일 (YYYY-MM-DD), 필수
    nationality = Column(String(255), nullable=False)  # 국적, 필수
    address = Column(String(255), nullable=True)  # 주소, 선택 사항
    company_name = Column(String(255), nullable=False)  # 회사명, 필수
    factory_name = Column(String(255), nullable=False)  # 공장명, 필수
    bank_name = Column(String(255), nullable=False)  # 은행명, 필수
    bank_account = Column(String(255), unique=True, nullable=False)  # 계좌번호, 중복 불가능, 필수
    terms_accepted = Column(Boolean, nullable=False)  # 약관 동의, 필수
    profile_image = Column(String(500), nullable=True)  # 프로필 이미지 경로, 선택 사항


# 결함 유형 Enum
class DefectTypeEnum(str, enum.Enum):
    crack = "Crack"
    scratch = "Scratch"
    dent = "Dent"
    discoloration = "Discoloration"


# 이미지 테이블
class Image(Base):
    __tablename__ = "Images"

    image_id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String(500), nullable=False)
    date = Column(DateTime, nullable=False)
    camera_id = Column(Integer, ForeignKey("Cameras.camera_id"), nullable=False)
    dataset_id = Column(Integer, nullable=False)
    status = Column(Enum("pending", "completed", name="statusenum"), nullable=False, default="pending")

    annotations = relationship("Annotation", back_populates="image")
    camera = relationship("Camera", back_populates="images")


# 어노테이션 테이블 (defect_type 제거 → class_id로 대체)
class Annotation(Base):
    __tablename__ = "Annotations"

    annotation_id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, ForeignKey("Images.image_id", ondelete="CASCADE"), nullable=False)

    class_id = Column(Integer, ForeignKey("DefectClasses.class_id", ondelete="RESTRICT"), nullable=False)

    date = Column(DateTime, nullable=False)
    conf_score = Column(Float, nullable=True)
    bounding_box = Column(JSON, nullable=False)
    user_id = Column(Integer, ForeignKey("Users.user_id"), nullable=True)

    image = relationship("Image", back_populates="annotations")
    defect_class = relationship("DefectClass", back_populates="annotations")


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
    line_id = Column(String(50), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    images = relationship("Image", back_populates="camera")  # 🔹 Image와 연결




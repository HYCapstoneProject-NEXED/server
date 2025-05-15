from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from domain.admin.admin_schema import (
    TaskAssignmentStats, AnnotatorStats, UnassignedCameraStats, 
    UserCameraStats, CameraImageStats, CameraAssignment
)
from database.models import Camera, Image, User, annotator_camera_association
from fastapi import HTTPException
from typing import Dict, List, Any

class AdminService:
    def __init__(self, db: Session):
        self.db = db

    def get_task_assignment_stats(self) -> TaskAssignmentStats:
        # 1. 카메라 통계
        total_cameras = self.db.query(func.count(Camera.camera_id)).scalar()
        assigned_cameras = self.db.query(func.count(distinct(annotator_camera_association.c.camera_id))).scalar()

        # 2. 이미지 통계
        total_images = self.db.query(func.count(Image.image_id)).scalar()
        assigned_images = self.db.query(func.count(distinct(Image.image_id)))\
            .join(annotator_camera_association, Image.camera_id == annotator_camera_association.c.camera_id)\
            .scalar()

        # 3. 어노테이터 통계
        annotators = []
        annotator_users = self.db.query(User).filter(User.user_type == 'annotator').all()
        
        for user in annotator_users:
            assigned_cameras_count = self.db.query(func.count(distinct(annotator_camera_association.c.camera_id)))\
                .filter(annotator_camera_association.c.user_id == user.user_id)\
                .scalar()
            
            assigned_images_count = self.db.query(func.count(distinct(Image.image_id)))\
                .join(annotator_camera_association, Image.camera_id == annotator_camera_association.c.camera_id)\
                .filter(annotator_camera_association.c.user_id == user.user_id)\
                .scalar()
            
            annotators.append(AnnotatorStats(
                user_id=user.user_id,
                username=user.name,
                assigned_cameras_count=assigned_cameras_count,
                assigned_images_count=assigned_images_count
            ))

        # 4. 할당되지 않은 카메라 ID와 이미지 개수
        assigned_camera_ids = self.db.query(distinct(annotator_camera_association.c.camera_id)).subquery()
        unassigned_cameras = self.db.query(
            Camera.camera_id,
            func.count(Image.image_id).label('image_count')
        ).outerjoin(Image, Camera.camera_id == Image.camera_id)\
         .filter(~Camera.camera_id.in_(assigned_camera_ids))\
         .group_by(Camera.camera_id)\
         .all()
        
        unassigned_camera_stats = [
            UnassignedCameraStats(
                camera_id=camera.camera_id,
                image_count=camera.image_count
            ) for camera in unassigned_cameras
        ]

        return TaskAssignmentStats(
            total_cameras=total_cameras,
            assigned_cameras=assigned_cameras,
            total_images=total_images,
            assigned_images=assigned_images,
            unassigned_cameras=unassigned_camera_stats,
            annotators=annotators
        )

    def get_user_camera_stats(self, user_id: int) -> UserCameraStats:
        # 사용자 정보 조회
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return None

        # 사용자에게 할당된 카메라와 각 카메라의 이미지 개수 조회
        camera_stats = self.db.query(
            Camera.camera_id,
            func.count(Image.image_id).label('image_count')
        ).join(annotator_camera_association, Camera.camera_id == annotator_camera_association.c.camera_id)\
         .outerjoin(Image, Camera.camera_id == Image.camera_id)\
         .filter(annotator_camera_association.c.user_id == user_id)\
         .group_by(Camera.camera_id)\
         .all()

        cameras = [
            CameraImageStats(
                camera_id=camera.camera_id,
                image_count=camera.image_count
            ) for camera in camera_stats
        ]

        return UserCameraStats(
            user_id=user.user_id,
            username=user.name,
            cameras=cameras
        )

    def assign_cameras_to_annotator(self, camera_assignment: CameraAssignment) -> Dict[str, Any]:
        # 1. 사용자 존재 여부 확인
        user = self.db.query(User).filter(User.user_id == camera_assignment.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"User with ID {camera_assignment.user_id} not found")
            
        # 2. 카메라 존재 여부 확인
        existing_cameras = self.db.query(Camera.camera_id).filter(
            Camera.camera_id.in_(camera_assignment.camera_ids)
        ).all()
        existing_camera_ids = [camera.camera_id for camera in existing_cameras]
        
        # 요청에 포함된 카메라 중 존재하지 않는 것이 있는지 확인
        non_existing_cameras = set(camera_assignment.camera_ids) - set(existing_camera_ids)
        if non_existing_cameras:
            raise HTTPException(
                status_code=404,
                detail=f"Cameras not found: {list(non_existing_cameras)}"
            )
            
        # 3. 현재 사용자에게 할당된 카메라 조회
        current_cameras = self.db.query(annotator_camera_association.c.camera_id).filter(
            annotator_camera_association.c.user_id == camera_assignment.user_id
        ).all()
        current_camera_ids = [camera.camera_id for camera in current_cameras]
        
        # 4. 추가할 카메라와 삭제할 카메라 식별
        cameras_to_add = set(camera_assignment.camera_ids) - set(current_camera_ids)
        cameras_to_remove = set(current_camera_ids) - set(camera_assignment.camera_ids)
        
        # 5. 카메라 할당 추가
        for camera_id in cameras_to_add:
            self.db.execute(
                annotator_camera_association.insert().values(
                    user_id=camera_assignment.user_id,
                    camera_id=camera_id
                )
            )
            
        # 6. 카메라 할당 제거
        if cameras_to_remove:
            self.db.execute(
                annotator_camera_association.delete().where(
                    (annotator_camera_association.c.user_id == camera_assignment.user_id) &
                    (annotator_camera_association.c.camera_id.in_(cameras_to_remove))
                )
            )
            
        # 7. 변경사항 저장
        self.db.commit()
        
        # 8. 업데이트된 카메라 할당 정보 조회
        updated_cameras = self.db.query(annotator_camera_association.c.camera_id).filter(
            annotator_camera_association.c.user_id == camera_assignment.user_id
        ).all()
        updated_camera_ids = [camera.camera_id for camera in updated_cameras]
        
        # 9. 결과 반환
        return {
            "user_id": user.user_id,
            "username": user.name,
            "assigned_cameras": updated_camera_ids,
            "added": len(cameras_to_add),
            "removed": len(cameras_to_remove),
            "total": len(updated_camera_ids)
        } 
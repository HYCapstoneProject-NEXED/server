from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from domain.admin.admin_crud import AdminService
from domain.admin.admin_schema import TaskAssignmentStats, UserCameraStats, CameraAssignment
from database.database import get_db

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

@router.get("/main", response_model=TaskAssignmentStats)
def get_task_assignment_stats(db: Session = Depends(get_db)):
    admin_service = AdminService(db)
    return admin_service.get_task_assignment_stats()

@router.get("/main/{user_id}", response_model=UserCameraStats)
def get_user_camera_stats(user_id: int, db: Session = Depends(get_db)):
    admin_service = AdminService(db)
    result = admin_service.get_user_camera_stats(user_id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result

@router.post("/main/assign")
def assign_cameras(
    camera_assignment: CameraAssignment,
    db: Session = Depends(get_db)
):
    admin_service = AdminService(db)
    try:
        return admin_service.assign_cameras_to_annotator(camera_assignment)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
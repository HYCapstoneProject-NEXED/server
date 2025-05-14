from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from domain.admin.admin_crud import AdminService
from domain.admin.admin_schema import TaskAssignmentStats
from database.database import get_db

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

@router.get("/main", response_model=TaskAssignmentStats)
def get_task_assignment_stats(db: Session = Depends(get_db)):
    admin_service = AdminService(db)
    return admin_service.get_task_assignment_stats() 
from fastapi import APIRouter
from app.api.v1 import auth, classes, students, subjects, notes, assignments, curriculum, export

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(classes.router, prefix="/classes", tags=["classes"])
router.include_router(students.router, prefix="/students", tags=["students"])
router.include_router(subjects.router, prefix="/subjects", tags=["subjects"])
router.include_router(notes.router, prefix="/notes", tags=["notes"])
router.include_router(assignments.router, prefix="/assignments", tags=["assignments"])
router.include_router(curriculum.router, prefix="/curriculum", tags=["curriculum"])
router.include_router(export.router, prefix="/export", tags=["export"])

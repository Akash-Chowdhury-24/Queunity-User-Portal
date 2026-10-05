from app.modules.parent.auth.routes import parentAuthRouter
from app.modules.student.auth.routes import studentAuthRouter
from fastapi import APIRouter, Depends

mainRouter = APIRouter()

mainRouter.include_router( parentAuthRouter, prefix="/parent/auth" , tags=["Parent Auth"])
mainRouter.include_router( studentAuthRouter, prefix="/student/auth" , tags=["Student Auth"])
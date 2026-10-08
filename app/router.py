from app.modules.parent.auth.routes import parentAuthRouter
from app.modules.parent.cases.case.route import parentCasesRouter
from app.modules.parent.cases.evidence.route import parentEvidenceRouter
from app.modules.parent.cases.suspect.route import parentSuspectsRouter
from app.modules.parent.cases.witness.route import parentWitnessesRouter
from app.modules.student.auth.routes import studentAuthRouter
from app.modules.student.cases.above_8.case.route import studentCasesRouter
from app.modules.student.cases.above_8.evidence.route import studentEvidenceRouter
from app.modules.student.cases.above_8.suspect.route import studentSuspectsRouter
from app.modules.student.cases.above_8.witness.route import studentWitnessesRouter
from app.modules.student.cases.below_8.route import studentBelow8CasesRouter
from fastapi import APIRouter

mainRouter = APIRouter()

mainRouter.include_router( parentAuthRouter, prefix="/parent/auth" , tags=["Parent Auth"])
mainRouter.include_router( studentAuthRouter, prefix="/student/auth" , tags=["Student Auth"])
mainRouter.include_router( parentCasesRouter, prefix="/parent/cases" , tags=["Parent Cases"])
mainRouter.include_router( parentSuspectsRouter, prefix="/parent/cases/{case_id}/suspects" , tags=["Parent Case Suspects"])
mainRouter.include_router( parentWitnessesRouter, prefix="/parent/cases/{case_id}/witnesses" , tags=["Parent Case Witnesses"])
mainRouter.include_router( parentEvidenceRouter, prefix="/parent/cases/{case_id}/evidence" , tags=["Parent Case Evidence"])
mainRouter.include_router( studentCasesRouter, prefix="/student/cases" , tags=["Student Cases (Above 8)"])
mainRouter.include_router( studentSuspectsRouter, prefix="/student/cases/{case_id}/suspects" , tags=["Student Case Suspects (Above 8)"])
mainRouter.include_router( studentWitnessesRouter, prefix="/student/cases/{case_id}/witnesses" , tags=["Student Case Witnesses (Above 8)"])
mainRouter.include_router( studentEvidenceRouter, prefix="/student/cases/{case_id}/evidence" , tags=["Student Case Evidence (Above 8)"])
mainRouter.include_router( studentBelow8CasesRouter, prefix="/student/below-8/cases" , tags=["Student Cases (Below 8)"])

from fastapi import APIRouter

from .upload import router as upload_router
from .units import router as units_router
from .historic import router as historic_router
from .agent import router as agent_router
from .output import router as output_router
from .export import router as export_router
from .taxonomy import router as taxonomy_router

router = APIRouter()
router.include_router(upload_router, tags=["upload"])
router.include_router(units_router, tags=["units"])
router.include_router(historic_router, tags=["historic"])
router.include_router(agent_router, tags=["agent"])
router.include_router(output_router, tags=["output"])
router.include_router(export_router, tags=["export"])
router.include_router(taxonomy_router, tags=["taxonomy"])

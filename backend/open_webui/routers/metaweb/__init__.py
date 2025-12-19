"""
MetaWeb Routers Package
"""
from fastapi import APIRouter

from .knowledge_graph_routes import router as knowledge_graph_router
from .student_profile_routes import router as student_profile_router

# Create main metaweb router
router = APIRouter(prefix='/api/metaweb', tags=['metaweb'])

# Include sub-routers
router.include_router(knowledge_graph_router, prefix='/knowledge-graph', tags=['knowledge-graph'])
router.include_router(student_profile_router, prefix='/profiles', tags=['student-profiles'])

__all__ = ['router']

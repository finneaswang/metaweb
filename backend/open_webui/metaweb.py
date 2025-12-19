"""
MetaWeb Module - Assignment System & Student Profiles
Exports all routers for easy import
"""

from open_webui.apps.metaweb.routes.assignments import router as assignments_router
from open_webui.apps.metaweb.routes.submissions import router as submissions_router
from open_webui.metaweb.routers.profiles import router as profiles_router

# For backward compatibility
__all__ = ['assignments_router', 'submissions_router', 'profiles_router']

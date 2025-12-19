# MetaWeb Student Assignment System
# AI-Powered Assignment Management Platform

__version__ = "0.1.0"

# Import from new location (apps.metaweb.routes) - assignments only for now
from open_webui.apps.metaweb.routes.assignments import router as assignments_router

# Import submissions from old location to avoid syntax errors
from .routers.submissions import router as submissions_router

# Import from old location (metaweb.routers) - for profiles
from .routers.profiles import router as profiles_router

# Import AI Assistant router
from .routers.ai_assistant import router as ai_assistant_router

__all__ = ['assignments_router', 'submissions_router', 'profiles_router', 'ai_assistant_router']

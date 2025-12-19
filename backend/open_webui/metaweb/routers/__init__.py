# Router exports - only profiles (assignments and submissions moved to apps.metaweb.routes)
from .profiles import router as profiles_router

__all__ = ['profiles_router']

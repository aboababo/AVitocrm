"""
Chats API - модульная структура для работы с чатами
"""

from .chats_batch import batch_bp
from .chats_endpoints import chats_bp
from .chats_listing import listing_bp

__all__ = ["chats_bp", "batch_bp", "listing_bp"]

"""
Pydantic схемы для OSAGAMING CRM
"""

from .user import (
    UserBase, UserCreate, UserUpdate, UserResponse, UserListResponse,
    UserLogin, UserLoginResponse, UserPasswordUpdate, CurrentUserUpdate,
    RoleBase, RoleCreate, RoleResponse, PermissionBase, PermissionResponse,
    UserRoleAssignment
)

from .chat import (
    ChatBase, ChatCreate, ChatUpdate, ChatResponse, ChatListResponse,
    ChatStatusUpdate, ChatFilter, MessageBase, MessageCreate, MessageResponse,
    MessageListResponse, MessageReadUpdate, ChatStats, QuickReply,
    ChatStatusEnum, ChatPriorityEnum, MessageTypeEnum
)

__all__ = [
    # User schemas
    "UserBase",
    "UserCreate", 
    "UserUpdate",
    "UserResponse",
    "UserListResponse",
    "UserLogin",
    "UserLoginResponse", 
    "UserPasswordUpdate",
    "CurrentUserUpdate",
    "RoleBase",
    "RoleCreate",
    "RoleResponse",
    "PermissionBase",
    "PermissionResponse",
    "UserRoleAssignment",
    
    # Chat schemas
    "ChatBase",
    "ChatCreate",
    "ChatUpdate", 
    "ChatResponse",
    "ChatListResponse",
    "ChatStatusUpdate",
    "ChatFilter",
    "MessageBase",
    "MessageCreate",
    "MessageResponse",
    "MessageListResponse",
    "MessageReadUpdate",
    "ChatStats",
    "QuickReply",
    "ChatStatusEnum",
    "ChatPriorityEnum", 
    "MessageTypeEnum"
]
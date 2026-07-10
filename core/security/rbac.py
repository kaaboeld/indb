from typing import Dict, List, Set, Optional
from enum import Enum, auto

class Role(str, Enum):
    ADMIN = "admin"
    WRITER = "writer"
    READER = "reader"
    AUDITOR = "auditor"

class Permission(str, Enum):
    # Event Permissions
    EVENT_READ = "event:read"
    EVENT_WRITE = "event:write"
    EVENT_DELETE = "event:delete"
    
    # System Permissions
    SYSTEM_CONFIG = "system:config"
    SYSTEM_STATUS = "system:status"
    
    # Audit Permissions
    AUDIT_READ = "audit:read"

# Role Definitions
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        Permission.EVENT_READ, Permission.EVENT_WRITE, Permission.EVENT_DELETE,
        Permission.SYSTEM_CONFIG, Permission.SYSTEM_STATUS, Permission.AUDIT_READ
    },
    Role.WRITER: {
        Permission.EVENT_READ, Permission.EVENT_WRITE
    },
    Role.READER: {
        Permission.EVENT_READ
    },
    Role.AUDITOR: {
        Permission.AUDIT_READ, Permission.SYSTEM_STATUS
    }
}

class AccessControl:
    """
    Role-Based Access Control Service.
    """
    
    def __init__(self):
        # In a real system, this would load user-role mappings from DB
        # For v0.5.0, we use a simple hardcoded mapping or token-based claim
        self._user_roles: Dict[str, Role] = {
            "admin_user": Role.ADMIN,
            "api_writer": Role.WRITER,
            "api_reader": Role.READER,
            "security_auditor": Role.AUDITOR,
            "anonymous": Role.READER,  # Allow dev access
            "mcp-agent": Role.WRITER,  # Hermes MCP: read + write
        }
        
    def get_role(self, user_id: str) -> Optional[Role]:
        return self._user_roles.get(user_id)
        
    def check_permission(self, user_id: str, required_permission: Permission) -> bool:
        """Check if user has specific permission."""
        role = self.get_role(user_id)
        if not role:
            return False
            
        return required_permission in ROLE_PERMISSIONS.get(role, set())

    def check_role(self, user_id: str, required_role: Role) -> bool:
        """Check if user has specific role or higher (not actually hierarchical here, just exact match)."""
        # For simplicity, just exact match or admin override
        role = self.get_role(user_id)
        if not role:
            return False
        
        if role == Role.ADMIN:
            return True
            
        return role == required_role

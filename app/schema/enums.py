from enum import Enum


class PermissionType(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    UPDATE = "update"
    ADMIN = "admin"
    CREATE = "create"
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    VIEW_REPORTS = "view_reports"
    EXPORT_DATA = "export_data"


class UserType(str, Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    MANAGER = "manager"
    EMPLOYEE = "employee"

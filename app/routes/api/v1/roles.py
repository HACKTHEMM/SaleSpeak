from fastapi import APIRouter, Form, HTTPException, status, Depends
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
from app.database.repositories.roles import roles_repo
from app.database.models.roles import Roles
import app.http_exception as http_exception
from app.schema.enums import PermissionType
from app.oauth import get_current_user
from app.schema.token import TokenData
from app.utils.helper import strip_whitespace

roles = APIRouter()

@roles.post(
    "/create/role",
    response_class=ORJSONResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_role(
    role_name: str = Form(...),
    permissions: str = Form(...),
    current_user: TokenData = Depends(get_current_user)
):
    import json
    permissions_clean = permissions.strip()
    if permissions_clean.lower().startswith("string"):
        permissions_clean = permissions_clean[6:].strip()
    try:
        permissions_dict = json.loads(permissions_clean)
    except json.JSONDecodeError as e:
        raise await http_exception.bad_request_exception(f"Invalid JSON format for permissions: {str(e)}")
    
    if not isinstance(permissions_dict, dict):
        raise await http_exception.bad_request_exception("Permissions must be a JSON object (dictionary)")
    
    valid_permissions = [perm.value for perm in PermissionType]
    for key, value in permissions_dict.items():
        if key not in valid_permissions:
            raise await http_exception.bad_request_exception(
                f"Invalid permission type '{key}'. Valid types: {', '.join(valid_permissions)}"
            )
        if not isinstance(value, bool):
            raise await http_exception.bad_request_exception(
                f"Permission value for '{key}' must be a boolean (true/false), got {type(value).__name__}"
            )

    role = await roles_repo.findOne({
        "role_name": role_name
    })
    if role: 
        if role["role_name"].lower() == role_name.lower():
            raise await http_exception.conflict_exception("Role name already exists")   
        
    role_data = Roles(
        role_name=role_name.capitalize(),
        permissions=permissions_dict
    )

    role_doc = {
        "role_name": role_data.role_name,
        "permissions": role_data.permissions,
    }
    new_role = await roles_repo.new(Roles(**role_doc))

    return {
        "message": "Role created successfully",
        "role_id": new_role["id"]
    }
    
@roles.get("/list/roles", response_class=ORJSONResponse, status_code=status.HTTP_200_OK)
async def list_roles(current_user: TokenData = Depends(get_current_user)):
    roles_data = await roles_repo.findAll()
    
    if not roles_data:
        return {"roles": []}

    roles_list = []
    for role in roles_data:
        roles_list.append({
            "id": role.get("id"),
            "role_name": role.get("role_name"),
            "permissions": role.get("permissions")
        })
    
    return {"roles": roles_list}

@roles.put("/update/role/{role_id}", response_class=ORJSONResponse, status_code=status.HTTP_200_OK)
async def update_role(
    role_id: str,
    role_name: Optional[str] = None,
    permissions: Optional[Dict[PermissionType, bool]] = None,
    current_user: TokenData = Depends(get_current_user)
):
    existing_role = await roles_repo.findOne({"id": role_id})
    if not existing_role:
        raise await http_exception.not_found_exception("Role not found")

    update_data = {}
    
    if role_name:
        role_name = strip_whitespace(role_name).capitalize()
        if role_name != existing_role["role_name"]:
            role_with_same_name = await roles_repo.findOne({"role_name": role_name})
            if role_with_same_name and role_with_same_name["id"] != role_id:
                raise await http_exception.conflict_exception("Role name already exists")
            update_data["role_name"] = role_name

    if permissions is not None:
        update_data["permissions"] = permissions

    if not update_data:
        raise await http_exception.bad_request_exception("No changes detected")

    updated_role = await roles_repo.update({"id": role_id}, update_data)
    
    if not updated_role:
        raise await http_exception.internal_server_error_exception("Failed to update role")

    return {"message": "Role updated successfully"}

from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.responses import ORJSONResponse
from typing import Optional
from uuid import UUID
from app.database.repositories.roles import roles_repo
from app.database.models.roles import Roles
from app.database.repositories.user import user_repo
from app.database.models.user import User
from app.database.models.entity import phoneNumber, username
import json
from app.schema.enums import PermissionType
from app.schema.token import TokenData
from app.oauth import get_current_user
import app.http_exception as http_exception

user = APIRouter()


@user.post(
    "/create/user", response_class=ORJSONResponse, status_code=status.HTTP_201_CREATED
)
async def create_user(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone_number: str = Form(...),
    role_id: str = Form(...),
    country_code: str = Form("+1"),
    current_user: TokenData = Depends(get_current_user)
):
    if not first_name.strip() or not last_name.strip():
        raise await http_exception.bad_request_exception("First name and last name cannot be empty")
    user_name_obj = username(first_name=first_name, last_name=last_name)

    phone_clean = phone_number.strip().replace(" ", "").replace("-", "")
    if phone_clean.startswith("+"):
        parts = phone_clean[1:].split(" ", 1)
        if len(parts) == 2:
            country_code = "+" + parts[0]
            phone_clean = parts[1]
        else:
            for i in range(1, 5):
                if i < len(phone_clean) and phone_clean[i].isdigit():
                    continue
                else:
                    country_code = phone_clean[:i]
                    phone_clean = phone_clean[i:]
                    break
    
    if phone_clean.startswith("0"):
        raise await http_exception.bad_request_exception("Phone number cannot start with 0")
    try:
        user_phone = phoneNumber(country_code=country_code, phone_number=phone_clean)
    except Exception as e:
        raise await http_exception.bad_request_exception(f"Invalid phone number format: {str(e)}")

    existing_user = await user_repo.findOne({"email": email})
    if existing_user:
        raise await http_exception.conflict_exception("User email already registered")

    role = await roles_repo.findOne({"id": role_id})
    if not role:
        raise await http_exception.not_found_exception("Role not found")
    
    user_dict = {
        "role_id": role_id,
        "username": user_name_obj,
        "email": email,
        "phone_number": user_phone,
        "onboarded": False,
        "deactivated": False
    }
    new_user = await user_repo.new(User(**user_dict))
    
    from app.routes.api.v1.auth import userGenerateEmailTokenInternal
    email_token = await userGenerateEmailTokenInternal(user_id=new_user["id"])
    
    return {
        "message": "User created successfully",
        "user_id": new_user["id"],
        "create_account_token": email_token["create_account_token"]
    }


@user.get("/list/users", response_class=ORJSONResponse, status_code=status.HTTP_200_OK)
async def list_users(current_user: TokenData = Depends(get_current_user)):
    users_data = await user_repo.findAll()
    
    if not users_data:
        return {"users": []}
    
    users_list = []
    for user_item in users_data:
        role = await roles_repo.findOne({"id": user_item.get("role_id")})
        
        users_list.append({
            "id": user_item.get("id"),
            "username": user_item.get("username"),
            "email": user_item.get("email"),
            "phone_number": user_item.get("phone_number"),
            "onboarded": user_item.get("onboarded", False),
            "deactivated": user_item.get("deactivated", False),
            "role": {
                "role_id": role.get("id") if role else None,
                "role_name": role.get("role_name") if role else None
            }
        })
    
    return {"users": users_list}


@user.post("/signup", response_class=ORJSONResponse, status_code=status.HTTP_201_CREATED)
async def signup_user(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone_number: str = Form(...),
    password: str = Form(...),
    country_code: str = Form("+1")
):
    if not first_name.strip() or not last_name.strip():
        raise await http_exception.bad_request_exception("First name and last name cannot be empty")
    user_name_obj = username(first_name=first_name, last_name=last_name)

    phone_clean = phone_number.strip().replace(" ", "").replace("-", "")
    if phone_clean.startswith("+"):
        parts = phone_clean[1:].split(" ", 1)
        if len(parts) == 2:
            country_code = "+" + parts[0]
            phone_clean = parts[1]
        else:
            for i in range(1, 5):
                if i < len(phone_clean) and phone_clean[i].isdigit():
                    continue
                else:
                    country_code = phone_clean[:i]
                    phone_clean = phone_clean[i:]
                    break
    
    if phone_clean.startswith("0"):
        raise await http_exception.bad_request_exception("Phone number cannot start with 0")
    try:
        user_phone = phoneNumber(country_code=country_code, phone_number=phone_clean)
    except Exception as e:
        raise await http_exception.bad_request_exception(f"Invalid phone number format: {str(e)}")

    existing_user = await user_repo.findOne({"email": email})
    if existing_user:
        raise await http_exception.conflict_exception("User email already registered")

    default_role = await roles_repo.findOne({"role_name": "User"})
    if not default_role:
        default_role_data = Roles(
            role_name="User",
            permissions={perm.value: False for perm in PermissionType}
        )
        new_role = await roles_repo.new(default_role_data)
        role_id = new_role["id"]
    else:
        role_id = default_role["id"]
    
    from app.utils.hashing import hash_password
    hashed_password = hash_password(password)
    
    user_dict = {
        "role_id": role_id,
        "username": user_name_obj,
        "email": email,
        "phone_number": user_phone,
        "password": hashed_password,
        "onboarded": True,
        "deactivated": False
    }
    new_user = await user_repo.new(User(**user_dict))
    
    return {
        "message": "User signup successful",
        "user_id": new_user["id"],
        "email": email
    }


@user.put("/update/user/{user_id}", response_class=ORJSONResponse, status_code=status.HTTP_200_OK)
async def update_user(
    user_id: str,
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    country_code: Optional[str] = Form(None),
    role_id: Optional[str] = Form(None),
    current_user: TokenData = Depends(get_current_user)
):
    # Validate user_id UUID format
    try:
        UUID(user_id)
    except ValueError:
        raise await http_exception.bad_request_exception("Invalid user ID format. Must be a valid UUID.")
    
    existing_user = await user_repo.findOne({"id": user_id})
    if not existing_user:
        raise await http_exception.not_found_exception("User not found")

    update_data = {}
    
    if first_name or last_name:
        current_first = first_name if first_name else existing_user.get("username", {}).get("first_name", "")
        current_last = last_name if last_name else existing_user.get("username", {}).get("last_name", "")
        
        if not current_first.strip() or not current_last.strip():
            raise await http_exception.bad_request_exception("First name and last name cannot be empty")
        
        user_name_obj = username(first_name=current_first, last_name=current_last)
        update_data["username"] = user_name_obj.model_dump()

    if phone_number:
        phone_clean = phone_number.strip().replace(" ", "").replace("-", "")
        current_country_code = country_code if country_code else "+1"
        
        if phone_clean.startswith("+"):
            parts = phone_clean[1:].split(" ", 1)
            if len(parts) == 2:
                current_country_code = "+" + parts[0]
                phone_clean = parts[1]
            else:
                for i in range(1, 5):
                    if i < len(phone_clean) and phone_clean[i].isdigit():
                        continue
                    else:
                        current_country_code = phone_clean[:i]
                        phone_clean = phone_clean[i:]
                        break
        
        if phone_clean.startswith("0"):
            raise await http_exception.bad_request_exception("Phone number cannot start with 0")
        
        try:
            user_phone = phoneNumber(country_code=current_country_code, phone_number=phone_clean)
            update_data["phone_number"] = user_phone.model_dump()
        except Exception as e:
            raise await http_exception.bad_request_exception(f"Invalid phone number format: {str(e)}")

    if role_id:
        # Validate UUID format
        try:
            UUID(role_id)
        except ValueError:
            raise await http_exception.bad_request_exception("Invalid role ID format. Must be a valid UUID.")
        
        role = await roles_repo.findOne({"id": role_id})
        if not role:
            raise await http_exception.not_found_exception("Role not found")
        update_data["role_id"] = role_id

    if not update_data:
        raise await http_exception.bad_request_exception("No changes detected")

    updated_user = await user_repo.update({"id": user_id}, update_data)
    
    if not updated_user:
        raise await http_exception.internal_server_error_exception("Failed to update user")

    return {"message": "User updated successfully"}


@user.delete("/delete/user/{user_id}", response_class=ORJSONResponse, status_code=status.HTTP_200_OK)
async def deactivate_user(
    user_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    existing_user = await user_repo.findOne({"id": user_id})
    if not existing_user:
        raise await http_exception.not_found_exception("User not found")

    await user_repo.update({"id": user_id}, {"deactivated": True})

    return {"message": "User deactivated successfully"}

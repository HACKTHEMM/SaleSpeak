from loguru import logger
auth_logger = logger
from fastapi import APIRouter, Request, Response, Depends, status, Header
from fastapi.responses import ORJSONResponse
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from pydantic import BaseModel
import app.http_exception as http_exception
from app.database.repositories.user import user_repo
from app.database.repositories.roles import roles_repo
from app.database.repositories.token import refresh_token_repo
from app.oauth import (
    generateEmailTokenforCreateAccount,
    validateCreateAccountToken,
    verify_email_access_token,
    create_access_token,
    set_cookies,
    get_refresh_token,
    get_new_access_token,
    create_forgot_password_access_token,
    verify_forgot_password_access_token,
    get_current_user
)
from app.schema.token import TokenData
from app.schema.password import SetPassword
from app.utils.hashing import hash_password, verify_hash

class Email_Body(BaseModel):
    email: str

auth = APIRouter()


async def userGenerateEmailTokenInternal(user_id: str) -> dict:
    auth_logger.info(f"Internal email token generation for user {user_id}")

    userExists = await user_repo.findOne({"id": user_id})
    
    if not userExists:
        raise await http_exception.not_found_exception("User not found")

    if userExists.get("onboarded"):
        raise await http_exception.conflict_exception("Email already verified for this user")

    createAccountToken = await generateEmailTokenforCreateAccount(
        user_id=user_id,
        user_type="user"
    )
    
    auth_logger.info(f"Internal email token generated successfully for user {user_id}")

    return {
        "success": True,
        "message": "Email verification token generated successfully.",
        "user_email": userExists["email"][:3] + "***@" + userExists["email"].split("@")[1],  # Masked email
        "create_account_token": createAccountToken
    }


@auth.get("/validate/create_account/token/{token}", response_class=ORJSONResponse)
async def validate_Create_Account_token(token: str = ""):
    response = await validateCreateAccountToken(token=token)

    token_data = response[0] if isinstance(response, tuple) else response
    user_data = response[1] if isinstance(response, tuple) and len(response) > 1 else {}
    
    return {
        "user_id": token_data.get("user_id") if isinstance(token_data, dict) else str(token_data.user_id) if hasattr(token_data, "user_id") else None,
        "password": False if user_data.get("password") is None else True,
        "onboarded": user_data.get("onboarded", False),
        "response": response
    }


@auth.post("/user/set/password", response_class=ORJSONResponse)
async def userSetPassword(token: str = "", password: str = ""):
    metadata = {
        "operation": "set_password",
        "has_token": bool(token),
        "has_password": bool(password)
    }

    auth_logger.info("Password set request initiated", extra={"metadata": metadata})

    decodedToken: TokenData = await verify_email_access_token(token=token)
    user_id_str = str(decodedToken.user_id)
    metadata["user_id"] = user_id_str

    userExists = await user_repo.findOne({"id": user_id_str})
    
    if not userExists:
        auth_logger.error("User not found for password set", extra={"metadata": metadata})
        raise await http_exception.not_found_exception(f"User {user_id_str} not found")
    
    if userExists.get("password") is not None:
        auth_logger.warning("Password already set for user", extra={"metadata": metadata})
        raise await http_exception.bad_request_exception("Password has been already credited to your account")
    
    if decodedToken.scope != "create_account":
        auth_logger.error("Invalid token scope for password set", extra={
            "metadata": metadata,
            "expected_scope": "create_account",
            "actual_scope": decodedToken.scope
        })
        raise await http_exception.forbidden_exception(f"Token out of scope {decodedToken.scope}")
    
    await user_repo.update(
        {"id": user_id_str},
        {"onboarded": True, "password": hash_password(password)}
    )
    
    auth_logger.info("Password set successfully", extra={"metadata": metadata})
    return {"success": True, "message": "Password set successfully."}


@auth.post("/user/login", response_class=ORJSONResponse, status_code=status.HTTP_200_OK)
async def login(
    request: Request,
    response: Response,
    user_creds: OAuth2PasswordRequestForm = Depends(),
):
    email = user_creds.username.lower().strip()
    
    if "@" not in email:
        raise await http_exception.bad_request_exception("Please enter a valid email address")
    
    user = await user_repo.findOne(
        {
            "email": email,
            "onboarded": True,
            "deactivated": False,
        }
    )
    
    if user is None:
        raise await http_exception.not_found_exception(f"Account with email {email} not found")
    
    if not user.get("onboarded"):
        raise await http_exception.bad_request_exception(f"Account {email} is not activated yet")
    
    if verify_hash(user_creds.password, user["password"]):
        token_generated = await create_access_token(
            response=response,
            data=TokenData(
                user_id=str(user["id"]),
                user_type="user",
                scope="login"
            )
        )
        
        set_cookies(
            response, token_generated.access_token, token_generated.refresh_token
        )
        
        return {"ok": True}
    
    raise await http_exception.unauthorised_exception("Invalid Credentials")


@auth.post("/user/refresh", response_class=ORJSONResponse, status_code=status.HTTP_200_OK)
async def token_refresh(
    response: Response, refresh_token: str = Depends(get_refresh_token)
):
    await get_new_access_token(response, refresh_token)
    return {"ok": True}


@auth.post(
    "/user/forgot-password",
    response_class=ORJSONResponse,
    status_code=status.HTTP_200_OK,
)
async def user_forgot_password(
    email_body: Email_Body,
    request: Request,
):
    res = await user_repo.findOne({"email": email_body.email})
    
    if res is None:
        raise await http_exception.not_found_exception(f"Account {email_body.email} not found")
    
    access_token = await create_forgot_password_access_token(
        TokenData(
            user_id=str(res["id"]),
            user_type="user",
            scope="forgot_password"
        )
    )
    
    return {
        "message": "Password reset token generated successfully.",
        "access_token": access_token
    }


@auth.get(
    "/user/forgot-password/verify",
    response_class=ORJSONResponse,
    status_code=status.HTTP_200_OK,
)
async def reset_password_verify_token(token: str = Header()):
    await verify_forgot_password_access_token(token)
    return {"ok": True}


@auth.post(
    "/user/forgot-password/set-password/{token}",
    response_class=ORJSONResponse,
    status_code=status.HTTP_200_OK,
)
async def reset_password_set_password(
    set_password: SetPassword,
    response: Response,
    token: str
):
    auth_logger.info("Set Password Token", token)
    
    data = await verify_forgot_password_access_token(token)
    user_id_str = str(data.user_id)
    res = await user_repo.findOne({"id": user_id_str})
    
    if verify_hash(set_password.new_password, res["password"]):
        raise await http_exception.conflict_exception("Old password and new password are same")

    new_password_hash = hash_password(set_password.new_password)
    await user_repo.update(
        {"id": user_id_str},
        {"password": new_password_hash}
    )
    
    count = await refresh_token_repo.deleteAll({"user_id": user_id_str})
    auth_logger.info(
        f"[Updated Password] Deleted: {count} refresh tokens for user_id: {user_id_str}"
    )
    
    await create_access_token(
        response,
        TokenData(user_id=str(data.user_id), user_type=data.user_type, scope="login")
    )
    
    return {"ok": True}


@auth.post("/logout", response_class=ORJSONResponse, status_code=status.HTTP_200_OK)
async def logout(response: Response, refresh_token: str = Depends(get_refresh_token)):
    await refresh_token_repo.deleteOne({"refresh_token": refresh_token})
    
    response.set_cookie(
        key="access_token",
        value="",
        httponly=True,
        max_age=0,
        secure=True,
        samesite="none",
    )
    response.set_cookie(
        key="refresh_token",
        value="",
        httponly=True,
        max_age=0,
        secure=True,
        samesite="none",
    )
    
    return {"ok": True}


@auth.get("/get/current_user", response_class=ORJSONResponse, status_code=status.HTTP_200_OK)
async def get_current_user_details(
    current_user: TokenData = Depends(get_current_user)
):
    user_id_str = str(current_user.user_id)
    user = await user_repo.findOne(
        {
            "id": user_id_str,
            "onboarded": True,
            "deactivated": False,
        }
    )
    
    if user is None:
        raise await http_exception.not_found_exception("Account not found")
    
    role = await roles_repo.findOne({"id": str(user["role_id"])})
    
    if role is None:
        raise await http_exception.not_found_exception("Role not found")
    
    user_response = {
        "user_id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "phone_number": user["phone_number"],
        "role": {
            "role_id": role["id"],
            "role_name": role["role_name"],
            "permissions": role["permissions"]
        }
    }
    
    return {"user": user_response}

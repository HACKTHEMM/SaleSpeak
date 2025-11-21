import time
from app.Config import ENV_SETTINGS
from typing import Optional, Tuple
from jose import jwt, JWTError
import app.http_exception as http_exception
from uuid import UUID
from app.database.repositories.user import user_repo
from app.schema.token import TokenData, BaseToken
from app.database.repositories.token import refresh_token_repo
from fastapi import Response, Depends
from fastapi.security import OAuth2PasswordBearer
import datetime
from typing import Dict
from typing import Optional
from fastapi import Request
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.security import OAuth2
from app.database.models.token import RefreshTokenCreate


async def generateEmailTokenforCreateAccount(user_id: str, user_type: str):
    payload = {
        "user_id": user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + 86400,
        "scope": "create_account",
        "type": user_type,
    }
    encoded_data = jwt.encode(
        payload,
        key=ENV_SETTINGS.SIGNUP_TOKEN_SECRET,
        algorithm="HS256"
    )
    return encoded_data

async def validateCreateAccountToken(token: str):
    try:
        payload = jwt.decode(
            token,
            ENV_SETTINGS.SIGNUP_TOKEN_SECRET,
            algorithms=["HS256"]
        )
        print(payload)
        user_id = payload.get("user_id")
        scope = payload.get("scope", "")

        if not user_id:
            raise await http_exception.unauthorised_exception("Token missing required user_id")
        if scope != "create_account":
            raise await http_exception.unauthorised_exception("Token is not validated for account creation")

        try:
            userExists = await user_repo.findOne({"id": user_id})
        except Exception as db_error:
            raise await http_exception.unauthorised_exception("Invalid user ID in token")

        if userExists is None:
            raise await http_exception.not_found_exception(f"Account Id {user_id} does not exists in our system")
        return payload, userExists

    except JWTError:
        raise await http_exception.unauthorised_exception(
            "Create account token validation failed: "
            "Unable to decode or verify token signature"
        )

async def verify_email_access_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(
            token,
            ENV_SETTINGS.SIGNUP_TOKEN_SECRET,
            algorithms=["HS256"]
        )
        id = payload.get("user_id", None)
        type: str = payload.get("type", None)
        scope: str = payload.get("scope", None)
        
        if id is None or type is None or scope != "create_account":
            raise await http_exception.unauthorised_exception(
                "Email verification token invalid"
            )
        token_data = TokenData(user_id=id, user_type=type, scope=scope)
        return token_data
    except JWTError:
        raise await http_exception.unauthorised_exception(
            "Email verification token validation failed:"
            "Unable to decode or verify token signature"
        )

async def create_refresh_token(data: TokenData):
    if isinstance(data.user_id, UUID):
        data.user_id = str(data.user_id)
    
    print("Data", data)
    to_encode = data.model_dump()
    expire = datetime.timedelta(
        minutes=ENV_SETTINGS.REFRESH_TOKEN_EXPIRE_MINUTES
    ) + datetime.datetime.now(datetime.timezone.utc)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, ENV_SETTINGS.REFRESH_TOKEN_SECRET, algorithm="HS256"
    )
    
    return encoded_jwt


async def create_access_token(
    response: Response, data: TokenData, old_refresh_token: str = None
) -> Tuple[BaseToken, str]:
    print("Data before encoding", data)
    if isinstance(data.user_id, UUID):
        data.user_id = str(data.user_id)
    
    print("Data", data)
    to_encode = data.model_dump()
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=ENV_SETTINGS.LOGIN_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    access_token = jwt.encode(
        to_encode, ENV_SETTINGS.ACCESS_TOKEN_SECRET, algorithm="HS256"
    )
    refresh_token = await create_refresh_token(data=data)
    print("Refresh Token", refresh_token)
    refresh_token_data: RefreshTokenCreate = RefreshTokenCreate(
        refresh_token=refresh_token, user_id=data.user_id, user_type=data.user_type
    )
    set_cookies(
        response,
        access_token=access_token,
        refresh_token=refresh_token
    )
    if old_refresh_token is None:
        res = await refresh_token_repo.new(data=refresh_token_data)
    else:
        res = await refresh_token_repo.update_one(
            {"refresh_token": old_refresh_token, "user_id": data.user_id},
            {
                "refresh_token": refresh_token,
                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
        )
        if not res:
            raise await http_exception.unauthorised_exception(
                f"Failed to update refresh token for user {data.user_id}. "
                "The existing token may have been invalidated."
            )
    if res:
        token: BaseToken = BaseToken(
            access_token=access_token, refresh_token=refresh_token, scope=data.scope
        )
        return token
    raise await http_exception.internal_server_error_exception("Internal Server Error")


def set_cookies(response: Response, access_token: str, refresh_token: str): 
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ENV_SETTINGS.LOGIN_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=True,
        samesite="none",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=ENV_SETTINGS.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        secure=True,
        samesite="none",
    )

async def verify_access_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(
            token, ENV_SETTINGS.ACCESS_TOKEN_SECRET, algorithms=["HS256"]
        )
        id = payload.get("user_id", None)
        type: str = payload.get("user_type", None)
        scope: str = payload.get("scope", None)
        
        if id is None or type is None or scope is None:
            raise await http_exception.unauthorised_exception("Access token invalid")
        if scope != "login":
            raise await http_exception.forbidden_exception(
                f"Invalid token scope: '{scope}'. Only 'login' tokens are allowed."
            )
        
        token_data = TokenData(user_id=id, user_type=type, scope=scope)
        return token_data
    except JWTError:
        raise await http_exception.unauthorised_exception(
            "Access token validation failed "
            "Unable to decode or verify token signature"
        )

async def verify_refresh_token(refresh_token: str) -> TokenData:
    try:
        payload = jwt.decode(
            refresh_token, ENV_SETTINGS.REFRESH_TOKEN_SECRET, algorithms="HS256"
        )
        id: str = payload.get("user_id", None)
        type: str = payload.get("user_type", None)
        scope: str = payload.get("scope", None)
        
        if id is None or type is None or scope is None:
            raise await http_exception.unauthorised_exception(
                f"Invalid refresh token: Missing critical payload information."
            )
        
        token_data = TokenData(user_id=id, user_type=type, scope=scope)
        return token_data
    except JWTError:
        raise await http_exception.unauthorised_exception(
            "Invalid refresh token: Unable to decode or verify token signature"
        )

class OAuth2PasswordBearerWithCookie(OAuth2):
    def __init__(
        self,
        tokenUrl: str,
        scheme_name: Optional[str] = None,
        scopes: Optional[Dict[str, str]] = None,
        auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(password={"tokenUrl": tokenUrl, "scopes": scopes})
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        access_token = request.cookies.get("access_token", "")
        refresh_token = request.cookies.get("refresh_token", "")

        if not refresh_token:
            if self.auto_error:
                raise await http_exception.unauthorised_exception("No refresh token found")
            return None

        try:
            await verify_refresh_token(refresh_token)
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
        except Exception:
            if self.auto_error:
                raise await http_exception.unauthorised_exception("Invalid refresh token")
            return None


oauth2_scheme = OAuth2PasswordBearerWithCookie(
    tokenUrl=ENV_SETTINGS.BASE_API_V1 + "/auth/user/login",
    scheme_name="Tenant Authentication",
)


async def get_current_user(
    tokens: dict = Depends(oauth2_scheme),
) -> TokenData:
    token: TokenData = await verify_access_token(
        tokens["access_token"]
    )
    return token


async def get_refresh_token(tokens: dict = Depends(oauth2_scheme)) -> str:
    refresh_token = tokens.get(f"refresh_token")
    if refresh_token:
        return refresh_token

    raise await http_exception.forbidden_exception("No valid refresh token found")


async def get_new_access_token(response: Response, refresh_token: str):
    token_data = await verify_refresh_token(refresh_token)
    response = await create_access_token(
        response, token_data, old_refresh_token=refresh_token
    )
    return response


async def create_forgot_password_access_token(data: TokenData):
    if isinstance(data.user_id, UUID):
        data.user_id = str(data.user_id)
    
    to_encode = data.model_dump()
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=ENV_SETTINGS.EMAIL_CONFIRMATION_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    access_token = jwt.encode(
        to_encode, ENV_SETTINGS.FORGOT_PASSWORD_TOKEN_SECRET, algorithm="HS256"
    )
    return access_token


async def verify_forgot_password_access_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(
            token,
            ENV_SETTINGS.FORGOT_PASSWORD_TOKEN_SECRET,
            algorithms=["HS256"],
        )
        id = payload.get("user_id", None)
        type: str = payload.get("user_type", None)
        scope: str = payload.get("scope", None)
        
        if id is None or type is None or scope != "forgot_password":   
            raise await http_exception.unauthorised_exception(
                "Forgot password token invalid"
            )
        token_data = TokenData(user_id=str(id), user_type=type, scope=scope)
        return token_data
    except JWTError:
        raise await http_exception.unauthorised_exception(
            "Forgot password token validation failed:"
            "Unable to decode or verify token signature"
        )

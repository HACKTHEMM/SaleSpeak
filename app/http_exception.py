from fastapi import status
from fastapi.exceptions import HTTPException
from fastapi.responses import ORJSONResponse
from starlette.requests import Request

async def http_exception(status_code: int, detail:str, headers:dict=None):
    return HTTPException(status_code=status_code, detail=detail, headers=headers)

async def unauthorised_exception(detail: str="Unauthorized access"):
    return await http_exception(status.HTTP_401_UNAUTHORIZED, detail, {"WWW-Authenticate": "Bearer"})

async def forbidden_exception(detail: str="Forbidden access"):
    return await http_exception(status.HTTP_403_FORBIDDEN, detail, {"WWW-Authenticate": "Bearer"})

async def not_found_exception(detail: str="Resource not found"):
    return await http_exception(status.HTTP_404_NOT_FOUND, detail)

async def bad_request_exception(detail: str="Bad request"):
    return await http_exception(status.HTTP_400_BAD_REQUEST, detail)

async def internal_server_error_exception(detail: str="Internal server error"):
    return await http_exception(status.HTTP_500_INTERNAL_SERVER_ERROR, detail)

async def conflict_exception(detail: str="Conflict occurred"):
    return await http_exception(status.HTTP_409_CONFLICT, detail)

async def rate_limit_exception(detail: str="Too many requests"):
    return await http_exception(status.HTTP_429_TOO_MANY_REQUESTS, detail)

class CustomHTTPException(HTTPException):
    def __init__ (self, detail: str, status_code: int, headers: dict = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
    
async def http_error_handler(_: Request, exc: HTTPException):
    return ORJSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )
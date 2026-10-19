from contextlib import asynccontextmanager
from pathlib import Path

from alembic.config import Config
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from alembic import command
from src.depends import get_templates
from src.logger import logger
from src.routers.auth.router import auth_router
from src.routers.files.router import file_router
from src.routers.index import index_router
from src.routers.user.router import user_router
from src.routers.vote.router import vote_router
from src.schemas import ErrorContext
from src.settings import settings


def run_migrations():
    alembic_cfg = Config(Path(__file__).parent.parent / "alembic.ini")
    command.upgrade(alembic_cfg, "head")


async def setup_admin_user():
    from src.controllers.file_controller import FileController
    from src.controllers.user_controller import (
        UserController,
        UserFilter,
        UserNew,
    )
    from src.routers.auth.depends import PassHasher
    from src.routers.user.models import UserRole

    from .db import get_session

    password = settings.admin_password
    hashed_password = PassHasher.get_password_hash(password)
    async for session in get_session():
        user_controller = UserController(session, FileController(session))
        user = await user_controller.get_one_or_none(UserFilter(email="admin"))
        if user is None:
            await user_controller.create(
                UserNew(
                    email="admin",
                    hashed_password=hashed_password,
                    role=UserRole.admin,
                )
            )
        else:
            await user_controller.update(
                user.model_copy(update={"password": hashed_password})
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    try:
        await asyncio.to_thread(run_migrations)
        await setup_admin_user()
    except Exception:
        logger.exception("Application startup failed")
        raise
    yield


openapi_url: str | None = None
if settings.show_docs:
    openapi_url = "/openapi.json"

app = FastAPI(openapi_url=openapi_url, lifespan=lifespan)
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static",
)
app.include_router(index_router)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(file_router)
app.include_router(vote_router)


@app.exception_handler(status.HTTP_404_NOT_FOUND)
async def not_found_exception_handler(request: Request, exc: HTTPException):
    return get_templates().TemplateResponse(
        request=request,
        name="error.jinja",
        context=ErrorContext(
            message="По вашему запросу ничего не найдено.",
            code=status.HTTP_404_NOT_FOUND,
        ).model_dump(),
    )


@app.exception_handler(status.HTTP_403_FORBIDDEN)
async def forbidden_exception_handler(request: Request, exc: HTTPException):
    return get_templates().TemplateResponse(
        request=request,
        name="error.jinja",
        context=ErrorContext(
            message="Недостаточно прав.",
            code=status.HTTP_403_FORBIDDEN,
        ).model_dump(),
    )


@app.exception_handler(status.HTTP_500_INTERNAL_SERVER_ERROR)
async def internal_exception_handler(request: Request, exc: Exception):
    return get_templates().TemplateResponse(
        request=request,
        name="error.jinja",
        context=ErrorContext(
            message="Ошибка сервера.",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ).model_dump(),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@app.exception_handler(status.HTTP_401_UNAUTHORIZED)
async def unauthorized_exception_handler(request: Request, exc: HTTPException):
    return RedirectResponse(
        url="/auth/login", status_code=status.HTTP_303_SEE_OTHER
    )

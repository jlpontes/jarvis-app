"""Aplicação FastAPI: rotas geradas a partir do registry e, em produção, o front compilado."""

import inspect
import logging
from collections.abc import AsyncGenerator, Callable, Generator
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, Request
from fastapi import Response as HttpResponse
from fastapi.responses import JSONResponse
from pydantic import BaseModel, JsonValue

from jarvis import __version__
from jarvis.api.auth import Auth, AuthMethod
from jarvis.api.errors import ApiError, install_error_handlers
from jarvis.core.command import Command, ErrorResponse, Response
from jarvis.core.config import Environment, Settings, get_settings
from jarvis.core.database import Database
from jarvis.core.module import ActionInfo, Context
from jarvis.core.registry import ModuleRegistry
from jarvis.modules import build_registry

log = logging.getLogger(__name__)


class Health(BaseModel):
    status: Literal["ok"]
    version: str


class LoginArgs(BaseModel):
    password: str


class Me(BaseModel):
    method: Literal["session", "token"]


class ActionSchema(BaseModel):
    name: str
    description: str
    text_arg: str | None
    args_schema: dict[str, JsonValue]
    result_schema: dict[str, JsonValue]


class ModuleInfo(BaseModel):
    name: str
    actions: list[ActionSchema]


_ERRORS: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse, "description": "Entrada inválida ou erro de regra (ok=false)"},
    401: {"model": ErrorResponse, "description": "Sem login"},
}


def _status_for(response: Response[Any]) -> int:
    if response.ok:
        return 200
    return 500 if response.is_internal_error else 400


def _module_info(registry: ModuleRegistry) -> list[ModuleInfo]:
    return [
        ModuleInfo(
            name=module.name,
            actions=[
                ActionSchema(
                    name=info.name,
                    description=info.description,
                    text_arg=info.text_arg,
                    args_schema=info.args.model_json_schema(),
                    result_schema=info.result.json_schema(),
                )
                for info in module.actions()
            ],
        )
        for module in registry.list()
    ]


def _action_endpoint(
    registry: ModuleRegistry,
    module: str,
    info: ActionInfo,
    get_context: Callable[[], Generator[Context]],
    authenticate: Callable[..., AuthMethod],
) -> Callable[..., JSONResponse]:
    """Cria a função de uma rota POST /api/{module}/{action} com o corpo tipado."""

    def endpoint(args: BaseModel, ctx: Context, _auth: AuthMethod) -> JSONResponse:
        # exclude_unset: só os campos enviados (em `editar`, "não mandou" ≠ "mandou null").
        cmd = Command(
            module=module, action=info.name, args=args.model_dump(mode="json", exclude_unset=True)
        )
        response = registry.dispatch(cmd, ctx)
        return JSONResponse(response.model_dump(mode="json"), status_code=_status_for(response))

    # O FastAPI lê os tipos pela assinatura: aqui dizemos qual é o modelo do corpo desta ação.
    kind = inspect.Parameter.POSITIONAL_OR_KEYWORD
    endpoint.__signature__ = inspect.Signature(  # pyright: ignore[reportFunctionMemberAccess]
        [
            inspect.Parameter("args", kind, annotation=info.args),
            inspect.Parameter("ctx", kind, annotation=Context, default=Depends(get_context)),
            inspect.Parameter("_auth", kind, annotation=str, default=Depends(authenticate)),
        ]
    )
    return endpoint


def _strip_422(app: FastAPI) -> None:
    """Nossos erros de validação saem como 400 + Response; tira o 422 padrão do OpenAPI."""
    original = app.openapi

    def openapi() -> dict[str, Any]:
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = original()
        for path in schema.get("paths", {}).values():
            for operation in path.values():
                operation.get("responses", {}).pop("422", None)
        schemas = schema.get("components", {}).get("schemas", {})
        for name in ("HTTPValidationError", "ValidationError"):
            schemas.pop(name, None)
        app.openapi_schema = schema
        return schema

    app.openapi = openapi


def create_app(settings: Settings | None = None, registry: ModuleRegistry | None = None) -> FastAPI:
    settings = settings or get_settings()
    registry = registry or build_registry()

    if settings.env is Environment.production and (problems := settings.secret_problems()):
        raise RuntimeError("Recusando subir em produção: " + "; ".join(problems) + ".")
    if settings.env is Environment.development and settings.secret_problems():
        log.warning("Segredos de exemplo ou ausentes no .env: aceitável só em desenvolvimento.")

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
        with Database.open(settings.db_path) as db:
            registry.init_all(db)  # migrations, uma vez na subida
        yield

    app = FastAPI(title="Jarvis", version=__version__, lifespan=lifespan)
    auth = Auth(settings)

    def get_context() -> Generator[Context]:
        """Uma conexão por requisição, fechada no fim."""
        with Database.open(settings.db_path) as db:
            yield Context.create(db, settings.zone)

    authenticate = auth.authenticate

    @app.get("/api/health", operation_id="health", tags=["sistema"])
    def health() -> Health:
        return Health(status="ok", version=__version__)

    @app.post(
        "/api/login",
        operation_id="login",
        tags=["sessão"],
        responses={
            401: {"model": ErrorResponse, "description": "Senha incorreta"},
            429: {"model": ErrorResponse, "description": "Muitas tentativas"},
        },
    )
    def login(args: LoginArgs, request: Request, response: HttpResponse) -> Response[None]:
        ip = request.client.host if request.client else "desconhecido"
        if (wait := auth.limiter.retry_after(ip)) is not None:
            minutes = max(1, round(wait / 60))
            raise ApiError(
                429,
                f"Muitas tentativas erradas. Tente de novo em {minutes} min.",
                {"Retry-After": str(wait)},
            )
        if not auth.check_password(args.password):
            auth.limiter.fail(ip)
            raise ApiError(401, "Senha incorreta.")
        auth.limiter.reset(ip)
        auth.start_session(response)
        return Response.success("Login feito.", None)

    @app.post("/api/logout", operation_id="logout", tags=["sessão"])
    def logout(response: HttpResponse) -> Response[None]:
        auth.end_session(response)
        return Response.success("Você saiu.", None)

    @app.get("/api/me", operation_id="me", tags=["sessão"], responses=_ERRORS)
    def me(method: Annotated[AuthMethod, Depends(authenticate)]) -> Response[Me]:
        return Response.success("Logado.", Me(method=method))

    @app.get("/api/modules", operation_id="modules", tags=["sistema"], responses=_ERRORS)
    def modules(_: Annotated[AuthMethod, Depends(authenticate)]) -> Response[list[ModuleInfo]]:
        return Response.success("Módulos disponíveis.", _module_info(registry))

    args_models: dict[str, type[BaseModel]] = {}
    for module in registry.list():
        for info in module.actions():
            path = f"/api/{module.name}/{info.name}"
            args_models[path] = info.args
            app.add_api_route(
                path,
                _action_endpoint(registry, module.name, info, get_context, authenticate),
                methods=["POST"],
                operation_id=f"{module.name}_{info.name}",
                summary=info.description,
                tags=[module.name],
                response_model=Response[info.result_type],
                responses=_ERRORS,
            )

    # Rota desconhecida em /api responde 404 em JSON, e não com o index.html do front.
    @app.api_route(
        "/api/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        include_in_schema=False,
    )
    def api_not_found(path: str) -> None:
        module, _, action = path.partition("/")
        if module and action and "/" not in action:  # parece /api/{modulo}/{acao}
            if not registry.has(module):
                raise ApiError(404, f"Módulo desconhecido: {module}")
            raise ApiError(404, f"Ação desconhecida: {module} {action}")
        raise ApiError(404, "Rota não encontrada.")

    install_error_handlers(app, args_models)
    _strip_422(app)

    if settings.env is Environment.production:
        # Navegação do navegador (Accept: text/html) em rota desconhecida recebe o index.html.
        app.frontend("/", directory=settings.web_dir, fallback="index.html", check_dir=True)

    return app

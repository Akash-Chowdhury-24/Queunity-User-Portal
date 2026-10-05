import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import (
    get_openapi,  ##To be removed later on when this part is done
)

from app.core.config import settings
from app.core.database import connect, disconnect
from app.core.exceptions import register_exception_handlers
from app.middleware.logging import RequestLoggingMiddleware
from app.router import mainRouter

logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await connect()
    logger.info("Application started (env=%s)", settings.ENV)
    yield
    await disconnect()
    logger.info("Application shutdown")

def create_app() -> FastAPI:
    app = FastAPI(
        title="Queunity User Portal API",
        version="1.0.0",
        openapi_version="3.0.2",##To be removed later on when this part is done
        lifespan=lifespan,
    )

    register_exception_handlers(app)

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(mainRouter)

##To be removed later on when this part is done
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version="3.0.2",
            description=app.description,
            routes=app.routes,
        )

        def fix_binary_format(obj):
            if isinstance(obj, dict):
                if "anyOf" in obj:
                    binary_item = next(
                        (
                            item for item in obj["anyOf"]
                            if isinstance(item, dict) and (
                                item.get("format") == "binary" or
                                item.get("contentMediaType") == "application/octet-stream"
                            )
                        ),
                        None,
                    )
                    if binary_item:
                        obj["type"] = "string"
                        obj["format"] = "binary"
                        obj.pop("anyOf", None)

                if obj.get("contentMediaType") == "application/octet-stream":
                    obj["format"] = "binary"
                    obj.pop("contentMediaType", None)

                for v in list(obj.values()):
                    fix_binary_format(v)
            elif isinstance(obj, list):
                for item in obj:
                    fix_binary_format(item)

        fix_binary_format(openapi_schema)
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi ##To be removed later on when this part is done

    return app


app = create_app()

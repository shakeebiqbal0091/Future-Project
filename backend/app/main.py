from app.api.routes import api_router, marketplace_router

app.include_router(marketplace_router, prefix="/api/v1/marketplace", tags=["marketplace"])

app.include_router(api_router, prefix="/api/v1", tags=["api"])
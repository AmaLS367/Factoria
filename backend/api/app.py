from fastapi import FastAPI

from backend.api.routes import router

app = FastAPI(title="AI Data Collector API")

app.include_router(router)

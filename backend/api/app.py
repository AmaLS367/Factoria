from fastapi import FastAPI

from api.routes import router

app = FastAPI(title="AI Data Collector API")

app.include_router(router)

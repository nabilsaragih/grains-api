from fastapi import FastAPI

from app.api.routes_manual import router as manual_router
from app.api.routes_misc import router as misc_router
from app.api.routes_ocr import router as ocr_router
from app.core import db

app = FastAPI(title="RAG API with User Profile")

app.include_router(misc_router)
app.include_router(manual_router)
app.include_router(ocr_router)

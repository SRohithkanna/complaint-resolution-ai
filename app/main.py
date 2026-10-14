
from fastapi import FastAPI

from app.database import Base, engine
from app import models
from app.api.complaints import router as complaints_router

# Initial development setup.
# Use database migrations when the schema starts evolving.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Complaint Resolution using AI Agents",
    version="0.1.0"
)

app.include_router(complaints_router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}

from fastapi import FastAPI

import models
from database import engine
from routers import rolls

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(rolls.router)


@app.get("/")
def read_root() -> dict:
    return {"message": "Metal Rolls Warehouse API"}

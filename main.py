from fastapi import FastAPI
from domain.user.user_router import router as user_router
from domain.annotation import annotation_router

app = FastAPI()
app.include_router(user_router)
app.include_router(annotation_router.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


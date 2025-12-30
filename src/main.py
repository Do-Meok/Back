from fastapi import FastAPI
# from api.v1.api import api_router
app = FastAPI()

# app.include_router(api_router, prefix="/api/v1")

#테스트 2
@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
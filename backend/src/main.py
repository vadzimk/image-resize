import uvicorn
from fastapi import FastAPI
from starlette import status

app = FastAPI()

@app.get('/', status_code=status.HTTP_200_OK)
def index():
    return {'Hello': 'World'}

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)

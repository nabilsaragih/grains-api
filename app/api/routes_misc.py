from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def root():
    return {"message": "hello from grains-api"}


@router.post("/req")
def request_echo(data: dict):
    print("Received data:", data)
    return {"received": data}


@router.get("/health")
def health():
    return {"status": "OK"}

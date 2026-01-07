from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def root():
    return {"message": "hello from grains-api"}


@router.get("/health")
def health():
    return {"status": "OK"}

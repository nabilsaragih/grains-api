from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.models.schemas import ManualSearchRequest, ManualSearchResponse
from app.rag.pipeline import rag_chain
from app.services.nutrition import (
    build_product_profile,
    build_search_query,
    build_user_query,
    build_user_profile_text,
)

router = APIRouter()


@router.post("/search/manual", response_model=ManualSearchResponse)
def manual_search(payload: ManualSearchRequest):
    if not payload.product.name and not payload.nutritionFacts:
        raise HTTPException(
            status_code=400,
            detail=(
                "Field product.name atau nutritionFacts harus diisi."
            ),
        )

    user_profile_text = build_user_profile_text(payload.userProfile)
    medical_history = (
        payload.userProfile.medical_history
        if payload.userProfile
        else None
    )
    user_query = build_user_query(medical_history)
    product_profile_text = build_product_profile(
        payload.product, payload.nutritionFacts
    )
    search_query = build_search_query(
        payload.product.name,
        payload.nutritionFacts,
    )

    try:
        answer = rag_chain.invoke(
            {
                "search_query": search_query,
                "user_query": user_query,
                "user_profile": user_profile_text,
                "product_profile": product_profile_text,
            }
        )

        return ManualSearchResponse(
            status="ok",
            answer=answer,
            used_query=search_query,
            user_profile=user_profile_text,
            product_profile=product_profile_text,
        )

    except ValidationError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Output model tidak sesuai skema: {exc}",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Kesalahan RAG: {exc}"
        )

import json

from fastapi import APIRouter, HTTPException

from app.models.schemas import ManualSearchRequest, ManualSearchResponse
from app.rag.pipeline import rag_chain
from app.services.nutrition import (
    build_product_profile,
    build_search_query,
    build_user_profile_text,
)
from app.services.parsing import extract_json_from_llm

router = APIRouter()


@router.post("/search/manual", response_model=ManualSearchResponse)
def manual_search(payload: ManualSearchRequest):
    q = payload.query.strip()
    if not q and not payload.product.name:
        raise HTTPException(
            status_code=400,
            detail="Field 'query' atau product.name harus diisi.",
        )

    user_profile_text = build_user_profile_text(payload.userProfile)
    product_profile_text = build_product_profile(
        payload.product, payload.nutritionFacts
    )
    search_query = build_search_query(
        q,
        payload.product.name,
        payload.nutritionFacts,
    )

    try:
        raw_answer = rag_chain.invoke(
            {
                "search_query": search_query,
                "user_query": q
                or f"Alternatif yang lebih sehat untuk {payload.product.name or 'produk ini'}",
                "user_profile": user_profile_text,
                "product_profile": product_profile_text,
            }
        )

        cleaned = extract_json_from_llm(raw_answer)

        try:
            answer_json = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            snippet = cleaned[:200]
            raise HTTPException(
                status_code=500,
                detail=(
                    "Model tidak mengembalikan JSON yang valid: "
                    f"{exc}. Cuplikan hasil: {snippet}"
                ),
            )

        return ManualSearchResponse(
            status="ok",
            answer=answer_json,
            used_query=search_query,
            user_profile=user_profile_text,
            product_profile=product_profile_text,
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Kesalahan RAG: {exc}"
        )

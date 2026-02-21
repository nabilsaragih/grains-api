import logging

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.core.config import settings
from app.models.schemas import ManualSearchRequest, ManualSearchResponse
from app.services.rag_executor import (
    RagTimeoutError,
    invoke_rag_with_timeout,
)
from app.services.rag_fallback import build_fallback_rag_answer
from app.services.nutrition import (
    build_product_profile,
    build_search_query,
    build_user_query,
    build_user_profile_text,
)

router = APIRouter()
logger = logging.getLogger(__name__)


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
        answer, timings = invoke_rag_with_timeout(
            {
                "search_query": search_query,
                "user_query": user_query,
                "user_profile": user_profile_text,
                "product_profile": product_profile_text,
            },
            timeout_seconds=settings.rag_timeout_seconds,
        )
        if settings.rag_log_timing:
            logger.info("manual_search timings_ms=%s", timings)

        return ManualSearchResponse(
            status="ok",
            answer=answer,
            used_query=search_query,
            user_profile=user_profile_text,
            product_profile=product_profile_text,
        )

    except RagTimeoutError as exc:
        logger.warning("manual_search timed out: %s", exc)
        return ManualSearchResponse(
            status="error",
            answer=build_fallback_rag_answer(
                reason=(
                    "Model generation exceeded server timeout. "
                    "Response built from fallback parser."
                ),
                product_name=payload.product.name,
            ),
            used_query=search_query,
            user_profile=user_profile_text,
            product_profile=product_profile_text,
        )
    except ValidationError:
        logger.exception(
            "RAG output failed schema validation in manual_search."
        )
        return ManualSearchResponse(
            status="error",
            answer=build_fallback_rag_answer(
                reason=(
                    "Model response did not fully match the schema. "
                    "Response built from fallback parser."
                ),
                product_name=payload.product.name,
            ),
            used_query=search_query,
            user_profile=user_profile_text,
            product_profile=product_profile_text,
        )
    except Exception as exc:
        logger.exception("RAG pipeline failed in manual_search: %s", exc)
        return ManualSearchResponse(
            status="error",
            answer=build_fallback_rag_answer(
                reason=(
                    "RAG pipeline failed during execution. "
                    "Response built from fallback parser."
                ),
                product_name=payload.product.name,
            ),
            used_query=search_query,
            user_profile=user_profile_text,
            product_profile=product_profile_text,
        )

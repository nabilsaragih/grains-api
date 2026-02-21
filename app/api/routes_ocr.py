import base64
import json
import logging
import mimetypes
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from mistralai import Mistral
from pydantic import ValidationError

from app.core.config import settings
from app.models.schemas import OcrSearchResponse, UserProfile
from app.services.rag_executor import (
    RagTimeoutError,
    invoke_rag_with_timeout,
)
from app.services.nutrition import build_user_profile_text, build_user_query
from app.services.rag_fallback import build_fallback_rag_answer

router = APIRouter()
logger = logging.getLogger(__name__)


def _encode_image_from_upload(upload: UploadFile) -> tuple[str, str]:
    if not upload.filename:
        raise HTTPException(
            status_code=400, detail="File gambar tidak ditemukan."
        )

    guessed_mime, _ = mimetypes.guess_type(upload.filename)
    mime = upload.content_type or guessed_mime or "image/jpeg"
    try:
        data = upload.file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Gagal membaca gambar: {exc}",
        )

    if not data:
        raise HTTPException(
            status_code=400, detail="File gambar kosong."
        )

    encoded = base64.b64encode(data).decode("utf-8")
    return encoded, mime


def build_search_query(markdown: str) -> str:
    if markdown:
        snippet = " ".join(markdown.strip().splitlines()[:6])
        if snippet:
            return snippet[:500]
    return "alternatif makanan kemasan yang lebih sehat"


@router.post("/search/ocr", response_model=OcrSearchResponse)
def ocr_search(
    image: UploadFile = File(...),
    userProfile: Optional[str] = Form(None),
):
    base64_image, mime_type = _encode_image_from_upload(image)

    parsed_user: Optional[UserProfile] = None
    if userProfile:
        try:
            user_payload = json.loads(userProfile)
            parsed_user = UserProfile.model_validate(user_payload)
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"userProfile tidak valid: {exc}",
            )

    client = Mistral(api_key=settings.mistral_api_key)

    try:
        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "image_url",
                "image_url": f"data:{mime_type};base64,{base64_image}",
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Kesalahan OCR: {exc}"
        )

    ocr_dict = ocr_response.model_dump()
    pages = ocr_dict.get("pages", [])
    if not pages:
        raise HTTPException(
            status_code=500, detail="Hasil OCR kosong."
        )

    markdown_pages = [
        page.get("markdown") or ""
        for page in pages
        if page.get("markdown")
    ]
    markdown = "\n\n".join(markdown_pages).strip()
    if not markdown:
        raise HTTPException(
            status_code=500, detail="Markdown OCR tidak ditemukan."
        )

    user_profile_text = build_user_profile_text(parsed_user)
    product_profile_text = f"Hasil OCR:\n{markdown}"
    search_query = build_search_query(markdown)
    user_query = build_user_query(
        parsed_user.medical_history
        if parsed_user
        else None
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
            logger.info("ocr_search timings_ms=%s", timings)

        return OcrSearchResponse(
            status="ok",
            answer=answer,
            ocr_markdown=markdown,
            used_query=search_query,
            user_profile=user_profile_text,
            product_profile=product_profile_text,
        )

    except RagTimeoutError as exc:
        logger.warning("ocr_search timed out: %s", exc)
        return OcrSearchResponse(
            status="error",
            answer=build_fallback_rag_answer(
                reason=(
                    "Model generation exceeded server timeout. "
                    "Response built from fallback parser."
                )
            ),
            ocr_markdown=markdown,
            used_query=search_query,
            user_profile=user_profile_text,
            product_profile=product_profile_text,
        )
    except ValidationError:
        logger.exception("RAG output failed schema validation in ocr_search.")
        return OcrSearchResponse(
            status="error",
            answer=build_fallback_rag_answer(
                reason=(
                    "Model response did not fully match the schema. "
                    "Response built from fallback parser."
                )
            ),
            ocr_markdown=markdown,
            used_query=search_query,
            user_profile=user_profile_text,
            product_profile=product_profile_text,
        )
    except Exception as exc:
        logger.exception("RAG pipeline failed in ocr_search: %s", exc)
        return OcrSearchResponse(
            status="error",
            answer=build_fallback_rag_answer(
                reason=(
                    "RAG pipeline failed during execution. "
                    "Response built from fallback parser."
                )
            ),
            ocr_markdown=markdown,
            used_query=search_query,
            user_profile=user_profile_text,
            product_profile=product_profile_text,
        )

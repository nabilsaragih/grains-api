from typing import Optional

from app.models.schemas import RagAnswer


def build_fallback_rag_answer(
    *,
    reason: Optional[str] = None,
    product_name: Optional[str] = None,
) -> RagAnswer:
    """Return a schema-compliant fallback answer when model output is invalid."""
    base_reason = (
        reason
        or "Model generation could not be completed. Returning a safe fallback."
    )
    if product_name:
        base_reason = f"{base_reason} Product: {product_name}."

    return RagAnswer(
        product_assessment={
            "product_type": "unknown",
            "is_safe": None,
            "reasons": [base_reason],
            "summary": "Assessment unavailable. Please retry with clearer product details.",
        },
        recommendations=[],
        summary="No suitable alternatives found.",
    )

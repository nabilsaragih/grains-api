from langchain_core.runnables import RunnableLambda

from app.core.llm import llm, retriever
from app.models.schemas import RagAnswer
from app.rag.prompt import PROMPT
from app.services.nutrition import (
    build_product_profile,
    build_search_query,
    build_user_profile_text,
    build_user_query,
    get_attribute,
)


def fmt(value, unit: str = "", nd: int = 2):
    """Format numeric nutrition values for prompt readability."""
    try:
        number = float(value)
        if abs(number - round(number)) < 1e-9:
            return f"{int(round(number))}{unit}"
        return f"{round(number, nd)}{unit}"
    except Exception:
        return "n/a"


def format_docs(docs):
    """Summarize retrieved docs into short, readable context snippets."""
    out = []
    for d in docs:
        m = d.metadata
        out.append(
            f"- {m.get('brand_name', '?')} "
            f"({m.get('category','?')}, porsi {m.get('serving_size_raw','?')}) "
            f"Na={fmt(m.get('sodium_mg_100g'),' mg/100g')}, "
            f"Gula={fmt(m.get('sugars_g_100g'),' g/100g')}, "
            f"Serat={fmt(m.get('fiber_g_100g'),' g/100g')}, "
            f"Protein={fmt(m.get('protein_g_100g'),' g/100g')}, "
            f"Lemak Jenuh={fmt(m.get('fat_sat_g_100g'),' g/100g')}; "
            f"Alergen={m.get('allergens')}.\n"
            f"  teks: {d.page_content}"
        )
    return "\n".join(out)


def coerce_answer(value):
    if isinstance(value, RagAnswer):
        return value
    return RagAnswer.model_validate(value)


def resolve_user_profile(inputs: dict) -> str:
    if "user_profile" in inputs:
        return inputs["user_profile"]
    user = inputs.get("userProfile")
    return build_user_profile_text(user)


def resolve_user_query(inputs: dict) -> str:
    if "user_query" in inputs:
        return inputs["user_query"]
    user = inputs.get("userProfile")
    medical_history = get_attribute(user, "medical_history")
    return build_user_query(medical_history)


def resolve_product_profile(inputs: dict) -> str:
    if "product_profile" in inputs:
        return inputs["product_profile"]
    product = inputs.get("product")
    facts = inputs.get("nutritionFacts") or []
    return build_product_profile(product, facts)


def resolve_search_query(inputs: dict) -> str:
    if "search_query" in inputs:
        return inputs["search_query"]
    product = inputs.get("product")
    facts = inputs.get("nutritionFacts") or []
    product_name = get_attribute(product, "name")
    return build_search_query(product_name, facts)


structured_llm = llm.with_structured_output(
    schema=RagAnswer.model_json_schema(),
    method="json_schema",
)

rag_chain = (
    {
        "context": resolve_search_query | retriever | format_docs,
        "user_query": resolve_user_query,
        "product_profile": resolve_product_profile,
        "user_profile": resolve_user_profile,
    }
    | PROMPT
    | structured_llm
    | RunnableLambda(coerce_answer)
)

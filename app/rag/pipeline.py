from operator import itemgetter

from langchain_core.output_parsers import StrOutputParser

from app.core.llm import llm, retriever
from app.rag.prompt import PROMPT


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


rag_chain = (
    {
        "context": itemgetter("search_query") | retriever | format_docs,
        "user_query": itemgetter("user_query"),
        "product_profile": itemgetter("product_profile"),
        "user_profile": itemgetter("user_profile"),
    }
    | PROMPT
    | llm
    | StrOutputParser()
)

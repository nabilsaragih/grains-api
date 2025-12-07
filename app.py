import os
import json
from urllib.parse import quote_plus, urlparse
from typing import List, Optional

import certifi
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text

from langchain_google_genai import (
    GoogleGenerativeAIEmbeddings,
    ChatGoogleGenerativeAI,
)
from langchain_community.vectorstores import TiDBVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from operator import itemgetter

load_dotenv()

#  ENVIRONMENT VARIABLES
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError("Missing GOOGLE_API_KEY in environment")

TIDB_USER = os.getenv("TIDB_USER")
TIDB_PASSWORD = os.getenv("TIDB_PASSWORD")
TIDB_HOST = os.getenv("TIDB_HOST")
TIDB_PORT = int(os.getenv("TIDB_PORT", "4000"))
TIDB_DB = os.getenv("TIDB_DB", "skripsi")

if not all([TIDB_USER, TIDB_PASSWORD, TIDB_HOST]):
    raise RuntimeError("TiDB environment variables missing (TIDB_USER / TIDB_PASSWORD / TIDB_HOST)")


#  BUILD TiDB CONNECTION STRING
_pw = quote_plus(TIDB_PASSWORD)
_ca = quote_plus(certifi.where())

TIDB_CONN = (
    f"mysql+pymysql://{TIDB_USER}:{_pw}@{TIDB_HOST}:{TIDB_PORT}/{TIDB_DB}"
    f"?ssl_verify_cert=true&ssl_verify_identity=true&ssl_ca={_ca}"
)

DB_NAME = urlparse(TIDB_CONN).path.lstrip("/") or "?"
print(f"[INFO] TiDB_CONN OK. Connected DB = {DB_NAME}")


#  TEST KONEKSI TiDB
engine = create_engine(TIDB_CONN, pool_pre_ping=True)
try:
    with engine.connect() as conn:
        print("Ping TiDB:", conn.execute(text("SELECT 1")).scalar())
except Exception as e:
    raise RuntimeError(f"❌ Failed to connect to TiDB: {e}")


#  RAG COMPONENTS (LangChain + Gemma + TiDBVectorStore)
emb = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    google_api_key=GOOGLE_API_KEY,
)

db = TiDBVectorStore.from_existing_vector_table(
    embedding=emb,
    connection_string=TIDB_CONN,
    table_name=os.getenv("TIDB_VECTOR_TABLE", "products_vector"),
    distance_strategy="cosine",
)

retriever = db.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 6},
)

llm = ChatGoogleGenerativeAI(
    model=os.getenv("GEMMA_MODEL", "gemma-3-27b-it"),
    temperature=0.2,
    max_output_tokens=800,
    google_api_key=GOOGLE_API_KEY,
)

def fmt(x, unit: str = "", nd: int = 2):
    """Format angka nutrisi untuk konteks LLM."""
    try:
        v = float(x)
        if abs(v - round(v)) < 1e-9:
            return f"{int(round(v))}{unit}"
        return f"{round(v, nd)}{unit}"
    except Exception:
        return "n/a"


def format_docs(docs):
    """Format dokumen hasil retriever menjadi teks ringkas."""
    out = []
    for d in docs:
        m = d.metadata
        out.append(
            f"- {m.get('brand_name', '?')} "
            f"({m.get('category','?')}, serving {m.get('serving_size_raw','?')}) "
            f"Na={fmt(m.get('sodium_mg_100g'),' mg/100g')}, "
            f"Gula={fmt(m.get('sugars_g_100g'),' g/100g')}, "
            f"Serat={fmt(m.get('fiber_g_100g'),' g/100g')}, "
            f"Protein={fmt(m.get('protein_g_100g'),' g/100g')}, "
            f"Lemak Jenuh={fmt(m.get('fat_sat_g_100g'),' g/100g')}; "
            f"Alergen={m.get('allergens')}.\n"
            f"  text: {d.page_content}"
        )
    return "\n".join(out)


#  Pydantic MODELS
class Portion(BaseModel):
    size: Optional[float] = None
    unit: str

class Product(BaseModel):
    name: Optional[str] = None
    portion: Portion

class NutritionFact(BaseModel):
    label: str
    value: str

class UserProfile(BaseModel):
    id: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    gender: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    birth_date: Optional[str] = None
    medical_history: Optional[str] = None

class ManualSearchRequest(BaseModel):
    query: str
    product: Product
    nutritionFacts: List[NutritionFact]
    userProfile: Optional[UserProfile] = None

class ManualSearchResponse(BaseModel):
    status: str
    answer: dict
    used_query: str
    user_profile: str
    product_profile: str


#  BUILD PROFILE TEXTS UNTUK PROMPT
def build_user_profile_text(user: Optional[UserProfile]) -> str:
    if not user:
        return "Tidak ada data profil pengguna. Gunakan asumsi umum dan rekomendasi aman."

    lines = []
    if user.full_name:
        lines.append(f"Nama: {user.full_name}")
    if user.gender:
        lines.append(f"Jenis kelamin: {user.gender}")
    if user.height:
        lines.append(f"Tinggi: {user.height} cm")
    if user.weight:
        lines.append(f"Berat: {user.weight} kg")
    if user.birth_date:
        lines.append(f"Lahir: {user.birth_date}")
    if user.medical_history:
        lines.append(f"Riwayat medis penting: {user.medical_history}")

    if not lines:
        return "Profil pengguna minim. Berikan rekomendasi umum yang aman."
    return "\n".join(lines)


def build_product_profile(product: Product, facts: List[NutritionFact]) -> str:
    lines = []
    if product.name:
        lines.append(f"Produk: {product.name}")
    if product.portion.size:
        lines.append(f"Sajian: {product.portion.size} {product.portion.unit}")
    else:
        lines.append(f"Sajian: {product.portion.unit} (jumlah tidak diisi)")

    if facts:
        lines.append("Nutrisi per sajian:")
        for nf in facts:
            lines.append(f"- {nf.label}: {nf.value}")

    return "\n".join(lines)


def build_search_query(query: str, product_name: Optional[str], facts: List[NutritionFact]) -> str:
    parts = []
    if query:
        parts.append(query)
    if product_name:
        parts.append(product_name)
    parts += [f.label for f in facts if f.label]
    return " ; ".join(parts) if parts else "produk makanan kemasan alternatif yang lebih sehat"


PROMPT = ChatPromptTemplate.from_messages([
    (
        "human",
        """You are a nutrition RAG assistant.

ALWAYS RETURN OUTPUT IN VALID JSON FORMAT.
DO NOT PROVIDE ANY EXPLANATION OUTSIDE THE JSON.
DO NOT ADD ANY TEXT BEFORE OR AFTER THE JSON.
DO NOT USE MARKDOWN BLOCKS SUCH AS ```json OR ```.

Here is the REQUIRED JSON structure:

{{
    "recommendations": [
    {{
        "rank": <number>,
        "brand": "<brand name>",
        "category": "<category>",
        "reasons": ["<reason1>", "<reason2>", "..."],
        "nutrition": {{
            "sugar_g_100g": <number or null>,
            "sodium_mg_100g": <number or null>,
            "protein_g_100g": <number or null>,
            "fiber_g_100g": <number or null>,
            "fat_sat_g_100g": <number or null>
        }}
    }}
    ],
    "summary": "<short summary>"
}}

If no products are suitable, return:

{{
    "recommendations": [],
    "summary": "No suitable alternative found."
}}

======================================================
User Profile:
{user_profile}

Product Data:
{product_profile}

Preferences:
{user_query}

Candidate Product Context:
{context}

Now respond with the result in VALID JSON format following the template above."""
    )
])

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


#  HELPER
def extract_json_from_llm(raw: str) -> str:
    s = raw.strip()

    if s.startswith("```"):
        first_newline = s.find("\n")
        if first_newline != -1:
            s = s[first_newline + 1 :]
        if s.endswith("```"):
            s = s[:-3]
        s = s.strip()

    return s


#  FASTAPI APP
app = FastAPI(title="RAG API with User Profile")

@app.get("/")
def root():
    return {"message": "hello from grains-api"}

@app.post("/req")
def request_echo(data: dict):
    print("Received data:", data)
    return {"received": data}

@app.get("/health")
def health():
    return {"status": "OK"}

@app.post("/manual-search", response_model=ManualSearchResponse)
def manual_search(payload: ManualSearchRequest):
    q = payload.query.strip()
    if not q and not payload.product.name:
        raise HTTPException(
            status_code=400,
            detail="Field 'query' atau product.name wajib diisi.",
        )

    user_profile_text = build_user_profile_text(payload.userProfile)
    product_profile_text = build_product_profile(
        payload.product,
        payload.nutritionFacts
    )
    search_query = build_search_query(
        q,
        payload.product.name,
        payload.nutritionFacts,
    )

    try:
        # Invoke RAG chain
        raw_answer = rag_chain.invoke({
            "search_query": search_query,
            "user_query": q or f"Healthier alternatives for {payload.product.name or 'this product'}",
            "user_profile": user_profile_text,
            "product_profile": product_profile_text,
        })

        cleaned = extract_json_from_llm(raw_answer)

        try:
            answer_json = json.loads(cleaned)
        except json.JSONDecodeError as e:
            snippet = cleaned[:200]
            raise HTTPException(
                status_code=500,
                detail=f"Model did not return valid JSON: {e}. Cleaned snippet: {snippet}",
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG error: {e}")

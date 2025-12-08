from langchain_community.vectorstores import TiDBVectorStore
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    GoogleGenerativeAIEmbeddings,
)

from app.core.config import settings

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    google_api_key=settings.google_api_key,
)

vector_store = TiDBVectorStore.from_existing_vector_table(
    embedding=embeddings,
    connection_string=settings.tidb_conn_str,
    table_name=settings.tidb_vector_table,
    distance_strategy="cosine",
)

retriever = vector_store.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 6},
)

llm = ChatGoogleGenerativeAI(
    model=settings.gemma_model,
    temperature=0.2,
    max_output_tokens=800,
    google_api_key=settings.google_api_key,
)

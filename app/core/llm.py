from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_community.vectorstores import TiDBVectorStore

from app.core.config import settings

embeddings = OllamaEmbeddings(
    model=settings.ollama_embedding_model,
    base_url=settings.ollama_base_url,
)

vector_store = TiDBVectorStore.from_existing_vector_table(
    embedding=embeddings,
    connection_string=settings.tidb_conn_str,
    table_name=settings.tidb_vector_table,
    distance_strategy="cosine",
)

retriever = vector_store.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 3},
)

llm = ChatOllama(
    model=settings.ollama_chat_model,
    base_url=settings.ollama_base_url,
    temperature=0,
)

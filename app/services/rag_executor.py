from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Dict, Tuple

from app.models.schemas import RagAnswer
from app.rag.pipeline import run_rag


class RagTimeoutError(RuntimeError):
    """Raised when RAG processing exceeds configured timeout."""


# Keep a small shared pool to avoid creating a thread per request.
_RAG_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="rag")


def invoke_rag_with_timeout(
    inputs: dict,
    timeout_seconds: float,
) -> Tuple[RagAnswer, Dict[str, float]]:
    future = _RAG_EXECUTOR.submit(run_rag, inputs)
    try:
        return future.result(timeout=timeout_seconds)
    except FuturesTimeoutError as exc:
        future.cancel()
        raise RagTimeoutError(
            f"RAG execution exceeded timeout ({timeout_seconds}s)."
        ) from exc

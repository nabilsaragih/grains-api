def extract_json_from_llm(raw: str) -> str:
    """Strip optional Markdown fences around LLM responses."""
    s = raw.strip()

    if s.startswith("```"):
        first_newline = s.find("\n")
        if first_newline != -1:
            s = s[first_newline + 1 :]
        if s.endswith("```"):
            s = s[:-3]
        s = s.strip()

    return s

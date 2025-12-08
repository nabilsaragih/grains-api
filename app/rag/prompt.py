from langchain_core.prompts import ChatPromptTemplate

PROMPT = ChatPromptTemplate.from_messages(
    [
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
    ]
)

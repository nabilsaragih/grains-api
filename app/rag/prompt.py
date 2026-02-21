from langchain_core.prompts import ChatPromptTemplate

PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
Return ONLY valid JSON that matches the schema.

Use best effort and keep output practical, not rigid:
- Assess the original product from user_profile + product_profile.
- If data is unclear or missing, set product_assessment.is_safe = null and explain briefly.
- recommendations must be same product_type as original when possible.
- Do not recommend the original product.
- Keep recommendations unique by brand + category.
- rank should start from 1.
- nutrition fields should be numeric when available, otherwise null.
- If no valid alternatives: recommendations = [] and summary MUST be exactly "No suitable alternatives found."
- All output text must be in ENGLISH (except product/brand names).

IMPORTANT — reasons structure:
- reasons must be List[str].
- Each reasons item MUST follow this exact sentence style:

  "<BRAND> is suitable for people with diabetes. One serving <SERVING_SIZE> contains <ADDED_SUGAR>g added sugar and <TOTAL_SUGAR>g total sugar, which is below the per serving sugar limit of 16.7g based on 3 servings per day."

- For recommendations:
  - If ground_truth_text exists in context, copy it VERBATIM.
  - Do not change wording, numbers, punctuation, or spacing.

- For product_assessment:
  - If ground_truth_text exists in context, copy it VERBATIM.
  - Otherwise generate EXACTLY ONE sentence using the exact format above.
  - If sugar data is missing, write "unknown" and set is_safe = null.

Keep reasons concise (1-3 items per section). Summary should be 1-2 sentences.
""",
        ),
        (
            "human",
            """
User Profile: {user_profile}
Product Data: {product_profile}
User Preferences: {user_query}
Candidate Product Context: {context}
""",
        ),
    ]
)

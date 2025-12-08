from typing import List, Optional

from app.models.schemas import NutritionFact, Product, UserProfile


def build_user_profile_text(user: Optional[UserProfile]) -> str:
    if not user:
        return "No user profile data available. Use general assumptions and provide safe recommendations."

    lines = []
    if user.full_name:
        lines.append(f"Name: {user.full_name}")
    if user.gender:
        lines.append(f"Gender: {user.gender}")
    if user.height:
        lines.append(f"Height: {user.height} cm")
    if user.weight:
        lines.append(f"Weight: {user.weight} kg")
    if user.birth_date:
        lines.append(f"Birth date: {user.birth_date}")
    if user.medical_history:
        lines.append(f"Medical history: {user.medical_history}")

    if not lines:
        return "User profile is minimal. Provide general, safe recommendations."

    return "\n".join(lines)


def build_product_profile(product: Product, facts: List[NutritionFact]) -> str:
    lines = []
    if product.name:
        lines.append(f"Product: {product.name}")

    if product.portion.size:
        lines.append(f"Serving size: {product.portion.size} {product.portion.unit}")
    else:
        lines.append(f"Serving size: {product.portion.unit} (amount not provided)")

    if facts:
        lines.append("Nutrition per serving:")
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
    return " ; ".join(parts) if parts else "healthier packaged food alternatives"

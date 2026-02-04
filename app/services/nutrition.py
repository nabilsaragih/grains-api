from typing import List, Optional

from app.models.schemas import NutritionFact, Product, UserProfile


def get_attribute(obj, key: str):
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def build_user_profile_text(user: Optional[UserProfile]) -> str:
    if not user:
        return (
            "Tidak ada data profil pengguna. Gunakan asumsi umum dan berikan rekomendasi yang aman."
        )

    medical_history = get_attribute(user, "medical_history")
    if medical_history:
        return f"Riwayat medis: {medical_history}"

    return "Profil pengguna minim. Berikan rekomendasi umum yang aman."


def build_user_query(medical_history: Optional[str]) -> str:
    if medical_history:
        return (
            "Rekomendasi alternatif lebih sehat berdasarkan riwayat medis: "
            f"{medical_history}"
        )
    return "Berikan alternatif lebih sehat dan aman berdasarkan profil pengguna."


def build_product_profile(product: Product, facts: List[NutritionFact]) -> str:
    lines = []
    product_name = get_attribute(product, "name")
    if product_name:
        lines.append(f"Produk: {product_name}")

    portion = get_attribute(product, "portion")
    portion_size = get_attribute(portion, "size")
    portion_unit = get_attribute(portion, "unit")
    if portion_unit and portion_size is not None:
        lines.append(
            f"Ukuran porsi: {portion_size} {portion_unit}"
        )
    elif portion_unit:
        lines.append(
            f"Ukuran porsi: {portion_unit} (jumlah tidak tersedia)"
        )
    else:
        lines.append("Ukuran porsi: tidak tersedia")

    if facts:
        lines.append("Nutrisi per porsi:")
        for nf in facts:
            label = get_attribute(nf, "label")
            value = get_attribute(nf, "value")
            if not label and not value:
                continue
            if label and value is not None and value != "":
                lines.append(f"- {label}: {value}")
            elif label:
                lines.append(f"- {label}")
            else:
                lines.append(f"- {value}")

    return "\n".join(lines)


def build_search_query(
    product_name: Optional[str],
    facts: List[NutritionFact],
) -> str:
    parts = []
    if product_name:
        parts.append(product_name)
    for nf in facts or []:
        label = get_attribute(nf, "label")
        value = get_attribute(nf, "value")
        if label and value:
            parts.append(f"{label} {value}")
        elif label:
            parts.append(label)
    return " ; ".join(parts) if parts else "alternatif makanan kemasan yang lebih sehat"

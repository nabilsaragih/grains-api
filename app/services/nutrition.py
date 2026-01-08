from typing import List, Optional

from app.models.schemas import NutritionFact, Product, UserProfile


def build_user_profile_text(user: Optional[UserProfile]) -> str:
    if not user:
        return (
            "Tidak ada data profil pengguna. Gunakan asumsi umum dan berikan rekomendasi yang aman."
        )

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
        lines.append(f"Tanggal lahir: {user.birth_date}")
    if user.medical_history:
        lines.append(f"Riwayat medis: {user.medical_history}")

    if not lines:
        return "Profil pengguna minim. Berikan rekomendasi umum yang aman."

    return "\n".join(lines)


def build_user_query(medical_history: Optional[str]) -> str:
    if medical_history:
        return (
            "Rekomendasi alternatif lebih sehat berdasarkan riwayat medis: "
            f"{medical_history}"
        )
    return "Berikan alternatif lebih sehat dan aman berdasarkan profil pengguna."


def build_product_profile(product: Product, facts: List[NutritionFact]) -> str:
    lines = []
    if product.name:
        lines.append(f"Produk: {product.name}")

    if product.portion.size:
        lines.append(
            f"Ukuran porsi: {product.portion.size} {product.portion.unit}"
        )
    else:
        lines.append(
            f"Ukuran porsi: {product.portion.unit} (jumlah tidak tersedia)"
        )

    if facts:
        lines.append("Nutrisi per porsi:")
        for nf in facts:
            lines.append(f"- {nf.label}: {nf.value}")

    return "\n".join(lines)


def build_search_query(
    query: Optional[str],
    product_name: Optional[str],
    facts: List[NutritionFact],
) -> str:
    parts = []
    if query:
        parts.append(query)
    if product_name:
        parts.append(product_name)
    parts += [f.label for f in facts if f.label]
    return " ; ".join(parts) if parts else "alternatif makanan kemasan yang lebih sehat"

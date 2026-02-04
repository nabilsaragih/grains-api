from typing import Annotated, List, Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
    field_validator,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Portion(StrictModel):
    size: Optional[float] = None
    unit: str


class Product(StrictModel):
    name: Optional[str] = None
    portion: Portion


class NutritionFact(StrictModel):
    label: str
    value: str


class UserProfile(StrictModel):
    medical_history: Optional[str] = None


class ProductAssessment(StrictModel):
    product_type: Literal["minuman", "makanan", "tidak_diketahui"] = Field(
        description=(
            "Jenis produk dalam Bahasa Indonesia: minuman, makanan, atau tidak_diketahui."
        )
    )
    is_safe: Optional[bool] = Field(
        default=None,
        description="True/False/null sesuai aturan penilaian produk.",
    )
    reasons: List[str] = Field(
        description="Daftar alasan singkat dalam Bahasa Indonesia."
    )
    summary: str = Field(
        description="Ringkasan singkat dalam Bahasa Indonesia."
    )

    @field_validator("product_type", mode="before")
    @classmethod
    def _normalize_product_type(cls, value):
        if isinstance(value, str):
            v = value.strip().lower().replace(" ", "_")
            if v == "tidakdiketahui":
                v = "tidak_diketahui"
            return v
        return value


class NutritionSummary(StrictModel):
    sugar_g_100g: Optional[float] = None
    sodium_mg_100g: Optional[float] = None
    protein_g_100g: Optional[float] = None
    fiber_g_100g: Optional[float] = None
    fat_sat_g_100g: Optional[float] = None


class Recommendation(StrictModel):
    rank: Annotated[int, Field(ge=1, description="Urutan rekomendasi dimulai dari 1.")]
    brand: str = Field(
        description="Nama merek (jangan diterjemahkan)."
    )
    category: str = Field(
        description="Kategori sejenis dalam Bahasa Indonesia."
    )
    reasons: List[str] = Field(
        description="Alasan singkat dalam Bahasa Indonesia."
    )
    nutrition: NutritionSummary


class RagAnswer(StrictModel):
    product_assessment: ProductAssessment
    recommendations: List[Recommendation]
    summary: str = Field(
        description=(
            "Ringkasan singkat dalam Bahasa Indonesia. Jika recommendations "
            "kosong, harus persis 'Tidak ada alternatif yang sesuai.'."
        )
    )

    @model_validator(mode="after")
    def _validate_logic(self):
        if not self.recommendations:
            if self.summary.strip() != "Tidak ada alternatif yang sesuai.":
                raise ValueError(
                    "Jika tidak ada rekomendasi, summary harus "
                    '"Tidak ada alternatif yang sesuai."'
                )
            return self

        ranks = [rec.rank for rec in self.recommendations]
        expected = list(range(1, len(ranks) + 1))
        if ranks != expected:
            raise ValueError(
                "Rank rekomendasi harus berurutan mulai dari 1."
            )
        if self.summary.strip() == "Tidak ada alternatif yang sesuai.":
            raise ValueError(
                "Summary tidak boleh menyatakan tidak ada alternatif "
                "jika rekomendasi tersedia."
            )

        seen = set()
        for rec in self.recommendations:
            key = (rec.brand.strip().lower(), rec.category.strip().lower())
            if key in seen:
                raise ValueError(
                    "Rekomendasi tidak boleh duplikat "
                    "(brand + category)."
                )
            seen.add(key)
        return self


class ManualSearchRequest(StrictModel):
    product: Product
    nutritionFacts: List[NutritionFact]
    userProfile: Optional[UserProfile] = None


class ManualSearchResponse(BaseModel):
    status: str
    answer: RagAnswer
    used_query: str
    user_profile: str
    product_profile: str


class OcrSearchRequest(BaseModel):
    image_base64: Optional[str] = None
    image_path: Optional[str] = None
    image_mime: Optional[str] = "image/jpeg"
    userProfile: Optional[UserProfile] = None


class OcrSearchResponse(BaseModel):
    status: str
    answer: RagAnswer
    ocr_markdown: str
    used_query: str
    user_profile: str
    product_profile: str

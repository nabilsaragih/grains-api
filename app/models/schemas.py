import json
import re
from typing import Annotated, Any, List, Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
    field_validator,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _to_string(value: Any, default: Optional[str] = "") -> Optional[str]:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _to_string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        out: List[str] = []
        for item in value:
            text = _to_string(item)
            if text:
                out.append(text)
        return out
    text = _to_string(value)
    return [text] if text else []


def _extract_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        match = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", "."))
        if match:
            try:
                return float(match.group(0))
            except ValueError:
                return None
    return None


class Portion(StrictModel):
    size: Optional[float] = None
    unit: str = "unknown"

    @field_validator("size", mode="before")
    @classmethod
    def _coerce_size(cls, value):
        return _extract_float(value)

    @field_validator("unit", mode="before")
    @classmethod
    def _coerce_unit(cls, value):
        return _to_string(value, default="unknown")


class Product(StrictModel):
    name: Optional[str] = None
    portion: Portion = Field(default_factory=Portion)

    @field_validator("name", mode="before")
    @classmethod
    def _coerce_name(cls, value):
        return _to_string(value, default=None)


class NutritionFact(StrictModel):
    label: str
    value: str

    @field_validator("label", "value", mode="before")
    @classmethod
    def _coerce_text_fields(cls, value):
        return _to_string(value)


class UserProfile(StrictModel):
    medical_history: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_profile(cls, value):
        if isinstance(value, str):
            return {"medical_history": value}
        return value

    @field_validator("medical_history", mode="before")
    @classmethod
    def _coerce_medical_history(cls, value):
        return _to_string(value, default=None)


class ProductAssessment(StrictModel):
    model_config = ConfigDict(extra="ignore")

    product_type: Literal["beverage", "food", "unknown"] = Field(
        description=(
            "Product type in English: beverage, food, or unknown."
        )
    )
    is_safe: Optional[bool] = Field(
        default=None,
        description="True/False/null according to product assessment rules.",
    )
    reasons: List[str] = Field(
        description="List of short reasons in English."
    )
    summary: str = Field(
        description="Short summary in English."
    )

    @field_validator("product_type", mode="before")
    @classmethod
    def _normalize_product_type(cls, value):
        if isinstance(value, str):
            v = value.strip().lower().replace(" ", "_")
            if v == "minuman":
                return "beverage"
            if v == "makanan":
                return "food"
            if v in {"tidakdiketahui", "tidak_diketahui"}:
                return "unknown"
            return v
        return value

    @field_validator("reasons", mode="before")
    @classmethod
    def _coerce_reasons(cls, value):
        return _to_string_list(value)

    @field_validator("summary", mode="before")
    @classmethod
    def _coerce_summary(cls, value):
        return _to_string(value)

    @model_validator(mode="before")
    @classmethod
    def _coerce_assessment(cls, value):
        if isinstance(value, str):
            return {
                "product_type": "unknown",
                "is_safe": None,
                "reasons": [value],
                "summary": value,
            }
        if not isinstance(value, dict):
            return value
        return {
            "product_type": value.get("product_type", "unknown"),
            "is_safe": value.get("is_safe"),
            "reasons": value.get("reasons", value.get("reason", [])),
            "summary": value.get("summary", ""),
        }


class NutritionSummary(StrictModel):
    model_config = ConfigDict(extra="ignore")

    sugar_g_100g: Optional[float] = None
    sodium_mg_100g: Optional[float] = None
    protein_g_100g: Optional[float] = None
    fiber_g_100g: Optional[float] = None
    fat_sat_g_100g: Optional[float] = None

    @field_validator(
        "sugar_g_100g",
        "sodium_mg_100g",
        "protein_g_100g",
        "fiber_g_100g",
        "fat_sat_g_100g",
        mode="before",
    )
    @classmethod
    def _coerce_numbers(cls, value):
        return _extract_float(value)


class Recommendation(StrictModel):
    model_config = ConfigDict(extra="ignore")

    rank: Annotated[
        int, Field(ge=1, description="Recommendation order starting from 1.")
    ]
    brand: str = Field(
        description="Brand name (do not translate)."
    )
    category: str = Field(
        description="Comparable category in English."
    )
    reasons: List[str] = Field(
        description="Short reasons in English."
    )
    nutrition: NutritionSummary

    @model_validator(mode="before")
    @classmethod
    def _coerce_recommendation(cls, value):
        if isinstance(value, str):
            return {
                "rank": 1,
                "brand": "Unknown",
                "category": "Unknown",
                "reasons": [value],
                "nutrition": {},
            }
        if not isinstance(value, dict):
            return value

        brand = value.get("brand") or value.get("name") or "Unknown"
        category = (
            value.get("category")
            or value.get("product_type")
            or value.get("type")
            or "Unknown"
        )
        return {
            "rank": value.get("rank", 1),
            "brand": brand,
            "category": category,
            "reasons": value.get("reasons", value.get("reason", [])),
            "nutrition": value.get("nutrition", {}),
        }

    @field_validator("rank", mode="before")
    @classmethod
    def _coerce_rank(cls, value):
        if value is None:
            return 1
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 1

    @field_validator("brand", "category", mode="before")
    @classmethod
    def _coerce_text(cls, value):
        return _to_string(value, default="Unknown")

    @field_validator("reasons", mode="before")
    @classmethod
    def _coerce_reasons(cls, value):
        return _to_string_list(value)

    @field_validator("nutrition", mode="before")
    @classmethod
    def _coerce_nutrition(cls, value):
        return value if isinstance(value, dict) else {}


class RagAnswer(StrictModel):
    model_config = ConfigDict(extra="ignore")

    product_assessment: ProductAssessment
    recommendations: List[Recommendation]
    summary: str = Field(
        description=(
            "Short summary in English. If recommendations is empty, it must be "
            "exactly 'No suitable alternatives found.'."
        )
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_answer(cls, value):
        if isinstance(value, str):
            raw = value.strip()
            if raw.startswith("```"):
                raw = raw.strip("`")
                if raw.lower().startswith("json"):
                    raw = raw[4:].strip()
            try:
                value = json.loads(raw)
            except Exception:
                value = {
                    "product_assessment": {
                        "product_type": "unknown",
                        "is_safe": None,
                        "reasons": [raw] if raw else [],
                        "summary": "Model output was not valid JSON.",
                    },
                    "recommendations": [],
                    "summary": "No suitable alternatives found.",
                }

        if not isinstance(value, dict):
            return value

        if "answer" in value and isinstance(value["answer"], (dict, str)):
            value = value["answer"]
            if isinstance(value, str):
                return cls._coerce_answer(value)

        product_assessment = value.get("product_assessment") or {}
        recommendations = value.get("recommendations", [])
        if isinstance(recommendations, dict):
            recommendations = list(recommendations.values())
        elif not isinstance(recommendations, list):
            recommendations = [recommendations]

        summary = value.get("summary")
        if summary is None:
            summary = (
                "No suitable alternatives found."
                if not recommendations
                else "Suitable alternatives were found for this product."
            )

        return {
            "product_assessment": product_assessment,
            "recommendations": recommendations,
            "summary": summary,
        }

    @field_validator("summary", mode="before")
    @classmethod
    def _coerce_summary(cls, value):
        return _to_string(value)

    @model_validator(mode="after")
    def _validate_logic(self):
        no_alternatives = "No suitable alternatives found."

        if not self.recommendations:
            self.summary = no_alternatives
            return self

        # Keep first occurrence for each (brand, category) pair.
        unique_recommendations = []
        seen = set()
        for rec in self.recommendations:
            key = (rec.brand.strip().lower(), rec.category.strip().lower())
            if key in seen:
                continue
            seen.add(key)
            unique_recommendations.append(rec)

        self.recommendations = unique_recommendations

        # Normalize rank order to always start from 1 and be sequential.
        for i, rec in enumerate(self.recommendations, start=1):
            rec.rank = i

        if not self.recommendations:
            self.summary = no_alternatives
            return self

        summary_text = self.summary.strip()
        if not summary_text or summary_text == no_alternatives:
            self.summary = (
                "Suitable alternatives were found for this product."
            )
        return self


class ManualSearchRequest(StrictModel):
    product: Product
    nutritionFacts: List[NutritionFact] = Field(default_factory=list)
    userProfile: Optional[UserProfile] = None

    @field_validator("nutritionFacts", mode="before")
    @classmethod
    def _coerce_nutrition_facts(cls, value):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            return [value]
        return []


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

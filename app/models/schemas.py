from typing import List, Optional

from pydantic import BaseModel


class Portion(BaseModel):
    size: Optional[float] = None
    unit: str


class Product(BaseModel):
    name: Optional[str] = None
    portion: Portion


class NutritionFact(BaseModel):
    label: str
    value: str


class UserProfile(BaseModel):
    id: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    gender: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    birth_date: Optional[str] = None
    medical_history: Optional[str] = None


class ManualSearchRequest(BaseModel):
    query: str
    product: Product
    nutritionFacts: List[NutritionFact]
    userProfile: Optional[UserProfile] = None


class ManualSearchResponse(BaseModel):
    status: str
    answer: dict
    used_query: str
    user_profile: str
    product_profile: str

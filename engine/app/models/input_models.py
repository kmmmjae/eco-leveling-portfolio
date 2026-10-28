"""
Eco-Leveling API input models.

Flutter 앱 또는 점주용 관리 시스템에서 전달받는 객관적 상품 데이터를
검증하고 표준화한다.

중요:
- EcoScore, 폐기 경로 확률, 점포 폐기율 등의 계산값은 입력받지 않는다.
- 지역 처리 통계와 점포 폐기 이력은 서버가 별도로 조회한다.
- Enum 값은 화면 표시 문구가 아닌 안정적인 영문 식별자를 사용한다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ---------------------------------------------------------
# 1. 고정 분류값
# ---------------------------------------------------------

class FoodCategory(str, Enum):
    BAKERY = "bakery"
    PREPARED_BAKERY = "prepared_bakery"
    MEAL = "meal"
    SALAD = "salad"
    BEVERAGE = "beverage"
    OTHER = "other"


class PackagingMaterial(str, Enum):
    PAPER = "paper"
    PE_FILM = "pe_film"
    PP = "pp"
    PET = "pet"
    PS = "ps"
    ALUMINUM = "aluminum"
    GLASS = "glass"
    MULTILAYER = "multilayer"
    OTHER = "other"


class ProcessingMethod(str, Enum):
    BAKED = "baked"
    FRIED = "fried"
    STEAMED = "steamed"
    BOILED = "boiled"
    RAW = "raw"
    MIXED = "mixed"


class StorageCondition(str, Enum):
    AMBIENT = "ambient"
    REFRIGERATED = "refrigerated"
    FROZEN = "frozen"
    HOT_HOLDING = "hot_holding"


class MeasurementSource(str, Enum):
    MEASURED = "measured"
    NUTRITION_LABEL = "nutrition_label"
    MERCHANT_INPUT = "merchant_input"
    PRODUCT_CATALOG = "product_catalog"
    CATEGORY_DEFAULT = "category_default"


# ---------------------------------------------------------
# 2. 원재료 데이터
# ---------------------------------------------------------

class IngredientInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    name: str = Field(min_length=1, max_length=100)

    # 배합비를 아는 경우에만 입력한다.
    ratio_percent: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    animal_origin: bool | None = None

    allergens: list[str] = Field(default_factory=list)


# ---------------------------------------------------------
# 3. 영양성분 데이터
# ---------------------------------------------------------

class NutritionInput(BaseModel):
    """
    기본적으로 식품 100g당 영양성분을 입력한다.
    알 수 없는 항목은 None으로 둘 수 있다.
    """

    model_config = ConfigDict(extra="forbid")

    basis_g: float = Field(default=100.0, gt=0, le=1000)

    moisture_g: float | None = Field(default=None, ge=0)
    carbohydrate_g: float | None = Field(default=None, ge=0)
    protein_g: float | None = Field(default=None, ge=0)
    fat_g: float | None = Field(default=None, ge=0)
    dietary_fiber_g: float | None = Field(default=None, ge=0)
    sodium_mg: float | None = Field(default=None, ge=0)

    source: MeasurementSource = MeasurementSource.NUTRITION_LABEL

    @model_validator(mode="after")
    def validate_macronutrient_total(self) -> Self:
        """
        탄수화물·단백질·지방의 합이 기준 중량보다 현저히 큰 입력을 차단한다.
        수분은 다른 성분과 별도로 검증한다.
        """

        macros = [
            self.carbohydrate_g,
            self.protein_g,
            self.fat_g,
        ]

        known_total = sum(value for value in macros if value is not None)

        if known_total > self.basis_g * 1.05:
            raise ValueError(
                "탄수화물, 단백질, 지방의 합이 기준 중량을 초과합니다."
            )

        if self.moisture_g is not None and self.moisture_g > self.basis_g:
            raise ValueError("수분 함량은 기준 중량을 초과할 수 없습니다.")

        return self


# ---------------------------------------------------------
# 4. 포장재 데이터
# ---------------------------------------------------------

class PackagingComponentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    material: PackagingMaterial
    weight_g: float = Field(gt=0, le=1000)

    # 음식물이나 유지류에 의해 오염되었는지 여부
    contaminated: bool = False

    # 소비자가 음식물과 포장재를 물리적으로 분리할 수 있는지 여부
    separable_from_food: bool = True

    # 일반적인 지역 분리배출 체계에서 재활용 가능한지 여부
    recyclable: bool | None = None

    source: MeasurementSource = MeasurementSource.MERCHANT_INPUT


# ---------------------------------------------------------
# 5. 상품 데이터
# ---------------------------------------------------------

class FoodProductInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    store_id: str = Field(min_length=1, max_length=100)
    product_id: str | None = Field(default=None, max_length=100)
    barcode: str | None = Field(default=None, max_length=50)

    product_name: str = Field(min_length=1, max_length=200)
    category: FoodCategory

    quantity: int = Field(default=1, ge=1, le=10_000)
    food_weight_g: float = Field(gt=0, le=100_000)

    food_weight_source: MeasurementSource = MeasurementSource.MERCHANT_INPUT

    ingredients: list[IngredientInput] = Field(default_factory=list)
    nutrition: NutritionInput | None = None
    packaging: list[PackagingComponentInput] = Field(default_factory=list)

    processing_methods: list[ProcessingMethod] = Field(default_factory=list)
    storage_condition: StorageCondition = StorageCondition.AMBIENT

    sale_deadline_at: datetime
    expires_at: datetime | None = None

    @field_validator("sale_deadline_at", "expires_at")
    @classmethod
    def require_timezone(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        """
        서버·Flutter 간 시간대 혼동을 막기 위해
        반드시 UTC 오프셋을 포함한 날짜·시간만 허용한다.
        """

        if value is None:
            return value

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "날짜·시간에는 시간대 정보가 포함되어야 합니다. "
                "예: 2026-07-12T21:00:00+09:00"
            )

        return value

    @model_validator(mode="after")
    def validate_product_relations(self) -> Self:
        ratios = [
            ingredient.ratio_percent
            for ingredient in self.ingredients
            if ingredient.ratio_percent is not None
        ]

        if ratios and sum(ratios) > 100.01:
            raise ValueError("원재료 배합비의 합은 100%를 초과할 수 없습니다.")

        if (
            self.expires_at is not None
            and self.expires_at < self.sale_deadline_at
        ):
            raise ValueError(
                "소비기한은 판매 마감 시각보다 빠를 수 없습니다."
            )

        return self


# ---------------------------------------------------------
# 6. 계산 환경 정보
# ---------------------------------------------------------

class CalculationContextInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    # 지역 폐기물 처리 통계 조회에 사용하는 행정구역 코드
    region_code: str = Field(min_length=2, max_length=20)

    # 요청 시각은 기본적으로 서버의 UTC 시각을 사용한다.
    requested_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @field_validator("requested_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("요청 시각에는 시간대 정보가 필요합니다.")
        return value


# ---------------------------------------------------------
# 7. 최종 API 요청 구조
# ---------------------------------------------------------

class EcoLevelCalculationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product: FoodProductInput
    context: CalculationContextInput
"""
Eco-Leveling internal feature models.

외부 API로 받은 상품 데이터를 계산 엔진이 사용할 수 있는 정규화된 숫자형 특성으로 표현한다.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.models.input_models import FoodCategory


class FoodFeatureVector(BaseModel):
    """
    Eco-Level 산정 전 단계에서 사용하는 표준화된 식품 특성 벡터.
    비율형 값은 원칙적으로 0.0~1.0 범위이며, 원본 데이터가 없으면 None으로 유지한다.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    feature_version: str = "1.0.0"

    product_id: str | None = None
    product_name: str
    category: FoodCategory

    # 원본 중량 정보
    food_weight_g: float = Field(gt=0)
    packaging_weight_g: float | None = Field(default=None, ge=0)
    packaging_to_food_ratio: float | None = Field(default=None, ge=0)

    # 영양성분 비율
    moisture_ratio: float | None = Field(default=None, ge=0, le=1)
    carbohydrate_ratio: float | None = Field(default=None, ge=0, le=1)
    protein_ratio: float | None = Field(default=None, ge=0, le=1)
    fat_ratio: float | None = Field(default=None, ge=0, le=1)

    # 원재료 특성
    animal_origin_ratio: float | None = Field(default=None, ge=0, le=1)

    # 포장 특성
    packaging_complexity: float | None = Field(default=None, ge=0, le=1)
    packaging_contamination: float | None = Field(default=None, ge=0, le=1)
    separation_difficulty: float | None = Field(default=None, ge=0, le=1)
    recycling_difficulty: float | None = Field(default=None, ge=0, le=1)

    # 조리·보관 특성
    processing_intensity: float | None = Field(default=None, ge=0, le=1)
    perishability: float = Field(ge=0, le=1)

    # 시간 특성
    hours_to_sale_deadline: float
    urgency_score: float = Field(ge=0, le=1)

    # 입력 데이터 신뢰도
    data_completeness_score: float = Field(ge=0, le=1)

    warnings: tuple[str, ...] = Field(default_factory=tuple)
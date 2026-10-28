"""
Eco-Leveling feature engineering.

검증된 API 입력 데이터를 Eco-Level 계산에 사용할
표준화된 식품 특성 벡터로 변환한다.
"""

from __future__ import annotations

from app.models.feature_models import FoodFeatureVector
from app.models.input_models import (
    EcoLevelCalculationRequest,
    FoodCategory,
    PackagingMaterial,
    ProcessingMethod,
    StorageCondition,
)


# ---------------------------------------------------------
# 1. 초기 특성 변환 기준값
# ---------------------------------------------------------

PACKAGING_COMPLEXITY = {
    PackagingMaterial.PAPER: 0.25,
    PackagingMaterial.PE_FILM: 0.50,
    PackagingMaterial.PP: 0.40,
    PackagingMaterial.PET: 0.35,
    PackagingMaterial.PS: 0.55,
    PackagingMaterial.ALUMINUM: 0.45,
    PackagingMaterial.GLASS: 0.20,
    PackagingMaterial.MULTILAYER: 1.00,
    PackagingMaterial.OTHER: 0.65,
}


PROCESSING_INTENSITY = {
    ProcessingMethod.RAW: 0.10,
    ProcessingMethod.BOILED: 0.25,
    ProcessingMethod.STEAMED: 0.30,
    ProcessingMethod.BAKED: 0.45,
    ProcessingMethod.MIXED: 0.70,
    ProcessingMethod.FRIED: 1.00,
}


CATEGORY_PERISHABILITY = {
    FoodCategory.BAKERY: 0.35,
    FoodCategory.PREPARED_BAKERY: 0.65,
    FoodCategory.MEAL: 0.80,
    FoodCategory.SALAD: 0.95,
    FoodCategory.BEVERAGE: 0.30,
    FoodCategory.OTHER: 0.50,
}


STORAGE_PERISHABILITY = {
    StorageCondition.AMBIENT: 0.30,
    StorageCondition.REFRIGERATED: 0.75,
    StorageCondition.FROZEN: 0.15,
    StorageCondition.HOT_HOLDING: 0.85,
}


# ---------------------------------------------------------
# 2. 공통 보조 함수
# ---------------------------------------------------------

def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    """숫자를 지정된 범위 안으로 제한한다."""

    return max(minimum, min(value, maximum))


def rounded(value: float | None, digits: int = 12) -> float | None:
    """계산값을 일관된 자릿수로 반올림한다."""

    if value is None:
        return None

    return round(value, digits)


def nutrient_ratio(
    value: float | None,
    basis_g: float,
) -> float | None:
    """
    영양성분 중량을 기준 중량 대비 비율로 변환한다.

    예:
    지방 16g / 기준 중량 100g = 0.16
    """

    if value is None:
        return None

    return clamp(value / basis_g)


# ---------------------------------------------------------
# 3. 원재료 특성
# ---------------------------------------------------------

def calculate_animal_origin_ratio(
    request: EcoLevelCalculationRequest,
) -> tuple[float | None, float]:
    """
    동물성 원재료 비율과 원재료 데이터 품질을 계산한다.

    반환값:
    - 동물성 원재료 추정 비율
    - 원재료 데이터 완성도 0.0~1.0
    """

    ingredients = request.product.ingredients

    if not ingredients:
        return None, 0.0

    ingredients_with_ratio = [
        ingredient
        for ingredient in ingredients
        if (
            ingredient.ratio_percent is not None
            and ingredient.animal_origin is not None
        )
    ]

    if ingredients_with_ratio:
        known_ratio_total = sum(
            ingredient.ratio_percent or 0.0
            for ingredient in ingredients_with_ratio
        )

        animal_ratio_total = sum(
            ingredient.ratio_percent or 0.0
            for ingredient in ingredients_with_ratio
            if ingredient.animal_origin is True
        )

        if known_ratio_total <= 0:
            return 0.0, 0.0

        animal_origin_ratio = animal_ratio_total / known_ratio_total

        declared_ratio_total = sum(
            ingredient.ratio_percent or 0.0
            for ingredient in ingredients
            if ingredient.ratio_percent is not None
        )

        ingredient_data_quality = clamp(declared_ratio_total / 100.0)

        return (
            clamp(animal_origin_ratio),
            ingredient_data_quality,
        )

    ingredients_with_origin = [
        ingredient
        for ingredient in ingredients
        if ingredient.animal_origin is not None
    ]

    if ingredients_with_origin:
        animal_count = sum(
            1
            for ingredient in ingredients_with_origin
            if ingredient.animal_origin is True
        )

        animal_origin_ratio = animal_count / len(ingredients_with_origin)

        known_origin_coverage = (
            len(ingredients_with_origin) / len(ingredients)
        )

        # 배합비 없이 원재료 개수만으로 계산했으므로
        # 신뢰도를 최대 0.5로 제한한다.
        ingredient_data_quality = known_origin_coverage * 0.5

        return (
            clamp(animal_origin_ratio),
            clamp(ingredient_data_quality),
        )

    return None, 0.0


# ---------------------------------------------------------
# 4. 포장 특성
# ---------------------------------------------------------

def calculate_packaging_features(
    request: EcoLevelCalculationRequest,
) -> dict[str, float | None]:
    packaging = request.product.packaging

    if not packaging:
        return {
            "packaging_weight_g": None,
            "packaging_to_food_ratio": None,
            "packaging_complexity": None,
            "packaging_contamination": None,
            "separation_difficulty": None,
            "recycling_difficulty": None,
        }

    total_weight = sum(component.weight_g for component in packaging)

    if total_weight <= 0:
        return {
            "packaging_weight_g": 0.0,
            "packaging_to_food_ratio": 0.0,
            "packaging_complexity": 0.0,
            "packaging_contamination": 0.0,
            "separation_difficulty": 0.0,
            "recycling_difficulty": None,
        }

    complexity = sum(
        PACKAGING_COMPLEXITY[component.material] * component.weight_g
        for component in packaging
    ) / total_weight

    contamination = sum(
        component.weight_g
        for component in packaging
        if component.contaminated
    ) / total_weight

    separation_difficulty = sum(
        component.weight_g
        for component in packaging
        if not component.separable_from_food
    ) / total_weight

    known_recyclability = [
        component
        for component in packaging
        if component.recyclable is not None
    ]

    recycling_difficulty: float | None = None

    if known_recyclability:
        known_weight = sum(
            component.weight_g
            for component in known_recyclability
        )

        non_recyclable_weight = sum(
            component.weight_g
            for component in known_recyclability
            if component.recyclable is False
        )

        recycling_difficulty = (
            non_recyclable_weight / known_weight
            if known_weight > 0
            else None
        )

    return {
        "packaging_weight_g": total_weight,
        "packaging_to_food_ratio": (
            total_weight / request.product.food_weight_g
        ),
        "packaging_complexity": clamp(complexity),
        "packaging_contamination": clamp(contamination),
        "separation_difficulty": clamp(separation_difficulty),
        "recycling_difficulty": (
            clamp(recycling_difficulty)
            if recycling_difficulty is not None
            else None
        ),
    }


# ---------------------------------------------------------
# 5. 조리·부패·시간 특성
# ---------------------------------------------------------

def calculate_processing_intensity(
    request: EcoLevelCalculationRequest,
) -> float | None:
    methods = request.product.processing_methods

    if not methods:
        return None

    # 복수 조리법이 있으면 가장 환경부하가 높은 조리법을 대표값으로 사용한다.
    return max(PROCESSING_INTENSITY[method] for method in methods)


def calculate_perishability(
    request: EcoLevelCalculationRequest,
) -> float:
    category_score = CATEGORY_PERISHABILITY[request.product.category]

    storage_score = STORAGE_PERISHABILITY[
        request.product.storage_condition
    ]

    # 식품군 특성 70%, 보관 상태 30%
    score = category_score * 0.70 + storage_score * 0.30

    return clamp(score)


def calculate_urgency(
    request: EcoLevelCalculationRequest,
) -> tuple[float, float]:
    """
    판매 마감까지 남은 시간과 폐기 임박도를 계산한다.

    - 마감 시간이 지났으면 1.0
    - 48시간 이상 남았으면 0.0
    - 그 사이는 선형으로 증가
    """

    remaining_seconds = (
        request.product.sale_deadline_at
        - request.context.requested_at
    ).total_seconds()

    remaining_hours = remaining_seconds / 3600.0

    urgency = 1.0 - clamp(remaining_hours / 48.0)

    return remaining_hours, urgency


# ---------------------------------------------------------
# 6. 데이터 완성도
# ---------------------------------------------------------

def calculate_data_completeness(
    request: EcoLevelCalculationRequest,
    ingredient_data_quality: float,
) -> float:
    """
    입력 데이터 완성도를 0.0~1.0으로 계산한다.

    필수 상품 정보               0.25
    영양성분                     0.25
    원재료                       0.20
    포장재                       0.20
    조리법                       0.05
    소비기한                     0.05
    """

    score = 0.25

    nutrition = request.product.nutrition

    if nutrition is not None:
        nutrition_values = [
            nutrition.moisture_g,
            nutrition.carbohydrate_g,
            nutrition.protein_g,
            nutrition.fat_g,
        ]

        known_nutrition_count = sum(
            value is not None
            for value in nutrition_values
        )

        score += 0.25 * (
            known_nutrition_count / len(nutrition_values)
        )

    score += 0.20 * ingredient_data_quality

    if request.product.packaging:
        score += 0.20

    if request.product.processing_methods:
        score += 0.05

    if request.product.expires_at is not None:
        score += 0.05

    return clamp(score)


# ---------------------------------------------------------
# 7. 최종 특성 벡터 생성
# ---------------------------------------------------------

def build_food_feature_vector(
    request: EcoLevelCalculationRequest,
) -> FoodFeatureVector:
    warnings: list[str] = []

    nutrition = request.product.nutrition

    if nutrition is None:
        moisture_ratio = None
        carbohydrate_ratio = None
        protein_ratio = None
        fat_ratio = None
        warnings.append("영양성분 데이터가 없습니다.")
    else:
        moisture_ratio = nutrient_ratio(
            nutrition.moisture_g,
            nutrition.basis_g,
        )
        carbohydrate_ratio = nutrient_ratio(
            nutrition.carbohydrate_g,
            nutrition.basis_g,
        )
        protein_ratio = nutrient_ratio(
            nutrition.protein_g,
            nutrition.basis_g,
        )
        fat_ratio = nutrient_ratio(
            nutrition.fat_g,
            nutrition.basis_g,
        )

        if None in {
            moisture_ratio,
            carbohydrate_ratio,
            protein_ratio,
            fat_ratio,
        }:
            warnings.append("일부 영양성분 데이터가 누락되었습니다.")

    animal_origin_ratio, ingredient_data_quality = (
        calculate_animal_origin_ratio(request)
    )

    if animal_origin_ratio is None:
        warnings.append("동물성 원재료 비율을 계산할 수 없습니다.")
    elif ingredient_data_quality < 1.0:
        warnings.append("원재료 배합비가 일부만 입력되었습니다.")

    packaging_features = calculate_packaging_features(request)

    if not request.product.packaging:
        warnings.append("포장재 데이터가 없습니다.")

    processing_intensity = calculate_processing_intensity(request)

    if processing_intensity is None:
        warnings.append("조리 방식 데이터가 없습니다.")

    hours_to_deadline, urgency_score = calculate_urgency(request)

    data_completeness = calculate_data_completeness(
        request,
        ingredient_data_quality,
    )

    return FoodFeatureVector(
        product_id=request.product.product_id,
        product_name=request.product.product_name,
        category=request.product.category,
        food_weight_g=request.product.food_weight_g,

        packaging_weight_g=rounded(
            packaging_features["packaging_weight_g"]
        ),
        packaging_to_food_ratio=rounded(
            packaging_features["packaging_to_food_ratio"]
        ),

        moisture_ratio=rounded(moisture_ratio),
        carbohydrate_ratio=rounded(carbohydrate_ratio),
        protein_ratio=rounded(protein_ratio),
        fat_ratio=rounded(fat_ratio),

        animal_origin_ratio=rounded(animal_origin_ratio),

        packaging_complexity=rounded(
            packaging_features["packaging_complexity"]
        ),
        packaging_contamination=rounded(
            packaging_features["packaging_contamination"]
        ),
        separation_difficulty=rounded(
            packaging_features["separation_difficulty"]
        ),
        recycling_difficulty=rounded(
            packaging_features["recycling_difficulty"]
        ),

        processing_intensity=rounded(processing_intensity),
        perishability=rounded(
            calculate_perishability(request)
        ) or 0.0,

        hours_to_sale_deadline=round(hours_to_deadline, 3),
        urgency_score=rounded(urgency_score) or 0.0,

        data_completeness_score=rounded(
            data_completeness
        ) or 0.0,

        warnings=tuple(warnings),
    )
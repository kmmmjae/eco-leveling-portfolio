"""
Eco-Leveling calculation engine.

이 파일은 화면 UI와 분리된 순수 계산 엔진이다.
입력된 마감식품 데이터를 식품 특성 벡터로 변환하고,
폐기 경로 확률, 오염물질별 환경부하, EcoScore, Eco-Level,
보상 포인트를 순차적으로 계산한다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from parameters import (
    BASE_POINT,
    CATEGORY_PROFILE,
    DISPOSAL_BURDEN_FACTOR,
    ECO_LEVEL_THRESHOLDS,
    ECOSCORE_WEIGHTS,
    INGREDIENT_EFFECTS,
    LEVEL_POINT_WEIGHT,
    PACKAGING_PROFILE,
    POLLUTION_WEIGHTS,
)


# --------------------------------------------------
# 1. 데이터 구조
# --------------------------------------------------

@dataclass
class FoodInput:
    product_name: str
    category: str
    food_weight_g: float
    packaging_weight_g: float
    packaging_type: str
    ingredients: list[str]
    hours_to_deadline: float
    store_waste_rate_percent: float


@dataclass
class EcoLevelResult:
    profile: dict[str, float]
    disposal_probabilities: dict[str, float]
    pollution_vector: dict[str, float]
    composition_score: float
    disposal_score: float
    pollution_score: float
    eco_score: float
    eco_level: str
    reward_point: int
    calculation_log: list[str]


# --------------------------------------------------
# 2. 유틸리티 함수
# --------------------------------------------------

def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(max_value, value))


def clamp_score(value: float) -> float:
    return max(0.0, min(100.0, value))


def softmax(values: list[float]) -> list[float]:
    max_value = max(values)
    exp_values = [math.exp(v - max_value) for v in values]
    total = sum(exp_values)
    return [v / total for v in exp_values]


# --------------------------------------------------
# 3. 식품 특성 벡터 생성
# --------------------------------------------------

def calculate_urgency(hours_to_deadline: float) -> float:
    """
    판매 마감까지 남은 시간이 짧을수록 폐기 임박도가 높아진다.
    """
    if hours_to_deadline <= 1:
        return 0.95
    if hours_to_deadline <= 3:
        return 0.80
    if hours_to_deadline <= 6:
        return 0.55
    if hours_to_deadline <= 12:
        return 0.35
    return 0.20


def infer_food_profile(food_input: FoodInput) -> dict[str, float]:
    """
    입력된 식품 정보를 0~1 범위의 식품 특성 벡터로 변환한다.
    """

    if food_input.category not in CATEGORY_PROFILE:
        raise ValueError(f"지원하지 않는 식품군입니다: {food_input.category}")

    if food_input.packaging_type not in PACKAGING_PROFILE:
        raise ValueError(f"지원하지 않는 포장재 유형입니다: {food_input.packaging_type}")

    profile = CATEGORY_PROFILE[food_input.category].copy()
    packaging = PACKAGING_PROFILE[food_input.packaging_type]

    profile["food_weight"] = clamp(food_input.food_weight_g / 200.0)
    profile["packaging_weight"] = clamp(food_input.packaging_weight_g / 15.0)
    profile["packaging_complexity"] = packaging["packaging_complexity"]
    profile["separation_difficulty"] = packaging["separation_difficulty"]
    profile["urgency"] = calculate_urgency(food_input.hours_to_deadline)
    profile["store_waste_rate"] = clamp(food_input.store_waste_rate_percent / 100.0)

    product_name = food_input.product_name.strip().lower()

    # 상품명 기반 1차 보정
    if any(keyword in product_name for keyword in ["피자", "소시지", "햄", "치즈", "고기"]):
        profile["fat"] += 0.15
        profile["protein"] += 0.08
        profile["animal"] += 0.20
        profile["oil"] += 0.18
        profile["odor"] += 0.12
        profile["packaging_complexity"] += 0.08
        profile["separation_difficulty"] += 0.08

    if any(keyword in product_name for keyword in ["크림", "슈"]):
        profile["fat"] += 0.10
        profile["animal"] += 0.12
        profile["odor"] += 0.10
        profile["moisture"] += 0.05

    if any(keyword in product_name for keyword in ["식빵", "바게트", "모닝빵", "소금빵"]):
        profile["fat"] -= 0.08
        profile["animal"] -= 0.08
        profile["oil"] -= 0.08
        profile["odor"] -= 0.08

    # 원재료 선택 기반 2차 보정
    for ingredient in food_input.ingredients:
        effects = INGREDIENT_EFFECTS.get(ingredient, {})
        for key, value in effects.items():
            profile[key] += value

    for key in profile:
        profile[key] = clamp(profile[key])

    return profile


# --------------------------------------------------
# 4. 폐기 경로 확률 산정
# --------------------------------------------------

def calculate_disposal_probabilities(profile: dict[str, float]) -> dict[str, float]:
    """
    식품 특성 벡터를 바탕으로 폐기 경로별 확률을 계산한다.
    """

    moisture = profile["moisture"]
    fat = profile["fat"]
    animal = profile["animal"]
    oil = profile["oil"]
    packaging_complexity = profile["packaging_complexity"]
    separation_difficulty = profile["separation_difficulty"]
    odor = profile["odor"]

    incineration_score = (
        1.20 * packaging_complexity
        + 0.80 * fat
        + 0.60 * oil
        + 0.50 * separation_difficulty
    )

    landfill_score = (
        0.70 * packaging_complexity
        + 0.50 * separation_difficulty
        + 0.30 * odor
    )

    food_waste_score = (
        1.10 * moisture
        + 0.50 * odor
        - 0.80 * packaging_complexity
        - 0.60 * separation_difficulty
    )

    general_waste_score = (
        1.00 * separation_difficulty
        + 0.90 * packaging_complexity
        + 0.40 * animal
        + 0.30 * fat
    )

    recycling_score = (
        1.20 * (1 - packaging_complexity)
        + 0.80 * (1 - separation_difficulty)
    )

    probabilities = softmax([
        incineration_score,
        landfill_score,
        food_waste_score,
        general_waste_score,
        recycling_score,
    ])

    return {
        "소각": probabilities[0],
        "매립": probabilities[1],
        "음식물류 폐기물 처리": probabilities[2],
        "일반폐기물 처리": probabilities[3],
        "포장재 분리배출": probabilities[4],
    }


# --------------------------------------------------
# 5. 중간 점수 산정
# --------------------------------------------------

def calculate_composition_score(profile: dict[str, float]) -> float:
    """
    식품 성분과 물성 자체가 갖는 폐기 환경부하 점수.
    """

    score = 100 * (
        0.16 * profile["fat"]
        + 0.16 * profile["animal"]
        + 0.13 * profile["oil"]
        + 0.11 * profile["packaging_complexity"]
        + 0.10 * profile["separation_difficulty"]
        + 0.10 * profile["odor"]
        + 0.07 * profile["protein"]
        + 0.05 * profile["moisture"]
        + 0.08 * profile["food_weight"]
        + 0.04 * profile["packaging_weight"]
    )

    return clamp_score(score)


def calculate_disposal_score(disposal_probabilities: dict[str, float]) -> float:
    """
    폐기 경로별 상대 환경부하 계수를 확률 가중합하여 폐기경로점수를 계산한다.
    """

    score = 0.0

    for disposal_path, probability in disposal_probabilities.items():
        score += probability * DISPOSAL_BURDEN_FACTOR[disposal_path]

    return clamp_score(score)


def calculate_pollution_vector(
    profile: dict[str, float],
    disposal_probabilities: dict[str, float],
) -> dict[str, float]:
    """
    폐기 경로 확률과 식품 특성을 결합하여 오염물질별 상대 환경부하 벡터를 산정한다.
    """

    food_weight = profile["food_weight"]
    packaging_weight = profile["packaging_weight"]
    moisture = profile["moisture"]
    fat = profile["fat"]
    protein = profile["protein"]
    animal = profile["animal"]
    oil = profile["oil"]
    packaging_complexity = profile["packaging_complexity"]
    odor = profile["odor"]

    incineration = disposal_probabilities["소각"]
    landfill = disposal_probabilities["매립"]
    food_waste = disposal_probabilities["음식물류 폐기물 처리"]
    general_waste = disposal_probabilities["일반폐기물 처리"]
    recycling = disposal_probabilities["포장재 분리배출"]

    pollution = {
        "CO2e": 100
        * ((0.78 * incineration) + (0.35 * general_waste) + (0.18 * food_waste))
        * (0.55 * food_weight + 0.30 * fat + 0.15 * oil),

        "CH4": 100
        * ((0.85 * landfill) + (0.52 * food_waste))
        * (0.60 * moisture + 0.40 * food_weight),

        "N2O": 100
        * ((0.42 * incineration) + (0.36 * food_waste))
        * (0.55 * protein + 0.45 * animal),

        "NOx/SOx": 100
        * ((0.55 * incineration) + (0.25 * general_waste))
        * (0.45 * protein + 0.35 * animal + 0.20 * packaging_weight),

        "PM": 100
        * ((0.72 * incineration) + (0.42 * general_waste))
        * (0.45 * packaging_complexity + 0.30 * packaging_weight + 0.25 * oil),

        "Leachate": 100
        * ((0.65 * landfill) + (0.45 * food_waste))
        * (0.70 * moisture + 0.30 * odor),

        "Odor": 100
        * ((0.50 * food_waste) + (0.45 * general_waste) + (0.25 * landfill))
        * (0.50 * odor + 0.30 * animal + 0.20 * protein),

        "Packaging": 100
        * ((0.70 * incineration) + (0.55 * general_waste) - (0.30 * recycling))
        * (0.70 * packaging_weight + 0.30 * packaging_complexity),
    }

    return {key: clamp_score(value) for key, value in pollution.items()}


def calculate_pollution_score(pollution_vector: dict[str, float]) -> float:
    """
    오염물질별 점수를 오염물질 가중치로 통합한다.
    """

    raw_score = 0.0

    for pollutant, value in pollution_vector.items():
        raw_score += value * POLLUTION_WEIGHTS[pollutant]

    # 현재 계수는 상대 점수 기반이므로 0~100 스케일로 보정한다.
    return clamp_score(raw_score * 2.6)


# --------------------------------------------------
# 6. 최종 EcoScore, Eco-Level, 포인트 산정
# --------------------------------------------------

def calculate_eco_score(
    profile: dict[str, float],
    composition_score: float,
    disposal_score: float,
    pollution_score: float,
) -> float:
    """
    성분부하, 폐기경로부하, 오염물질부하를 통합하여 최종 EcoScore를 산정한다.
    """

    raw_score = (
        ECOSCORE_WEIGHTS["composition"] * composition_score
        + ECOSCORE_WEIGHTS["disposal"] * disposal_score
        + ECOSCORE_WEIGHTS["pollution"] * pollution_score
    )

    urgency_factor = 1.0 + 0.15 * profile["urgency"]
    reliability_factor = 0.85 + 0.15 * profile["store_waste_rate"]

    final_score = raw_score * urgency_factor * reliability_factor

    return clamp_score(final_score)


def classify_eco_level(eco_score: float) -> str:
    """
    EcoScore를 Lv1~Lv5로 분류한다.
    """

    if eco_score < ECO_LEVEL_THRESHOLDS["Lv1"]:
        return "Lv1"
    if eco_score < ECO_LEVEL_THRESHOLDS["Lv2"]:
        return "Lv2"
    if eco_score < ECO_LEVEL_THRESHOLDS["Lv3"]:
        return "Lv3"
    if eco_score < ECO_LEVEL_THRESHOLDS["Lv4"]:
        return "Lv4"
    return "Lv5"


def calculate_reward_point(eco_level: str, profile: dict[str, float]) -> int:
    """
    Eco-Level, 폐기 임박도, 점포 폐기 가능성을 반영해 보상 포인트를 산정한다.
    """

    urgency_factor = 1.0 + 0.70 * profile["urgency"]
    reliability_factor = 0.85 + 0.15 * profile["store_waste_rate"]

    point = (
        BASE_POINT
        * LEVEL_POINT_WEIGHT[eco_level]
        * urgency_factor
        * reliability_factor
    )

    return round(point)


# --------------------------------------------------
# 7. 전체 계산 실행
# --------------------------------------------------

def calculate_eco_level(food_input: FoodInput) -> EcoLevelResult:
    """
    Eco-Leveling 전체 계산 프로세스.
    """

    log: list[str] = []

    log.append("S100: 마감식품 입력 데이터 수신")

    profile = infer_food_profile(food_input)
    log.append("S110: 식품군, 중량, 포장재, 원재료, 마감시간 기반 식품 특성 벡터 생성")

    disposal_probabilities = calculate_disposal_probabilities(profile)
    log.append("S120: 식품 특성 벡터 기반 폐기 경로 확률 산정")

    composition_score = calculate_composition_score(profile)
    log.append("S130: 성분 및 물성 기반 환경부하 점수 산정")

    disposal_score = calculate_disposal_score(disposal_probabilities)
    log.append("S140: 폐기 경로 확률 및 폐기 방식별 부담계수 기반 폐기경로점수 산정")

    pollution_vector = calculate_pollution_vector(profile, disposal_probabilities)
    log.append("S150: 오염물질별 환경부하 벡터 산출")

    pollution_score = calculate_pollution_score(pollution_vector)
    log.append("S160: 오염물질별 가중치 적용 후 오염물질점수 산정")

    eco_score = calculate_eco_score(
        profile=profile,
        composition_score=composition_score,
        disposal_score=disposal_score,
        pollution_score=pollution_score,
    )
    log.append("S170: 성분부하, 폐기경로부하, 오염물질부하를 통합하여 EcoScore 산정")

    eco_level = classify_eco_level(eco_score)
    log.append("S180: EcoScore 임계값 기준 Eco-Level 분류")

    reward_point = calculate_reward_point(eco_level, profile)
    log.append("S190: Eco-Level, 폐기 임박도, 예측 신뢰도 기반 보상 포인트 산정")

    return EcoLevelResult(
        profile=profile,
        disposal_probabilities=disposal_probabilities,
        pollution_vector=pollution_vector,
        composition_score=composition_score,
        disposal_score=disposal_score,
        pollution_score=pollution_score,
        eco_score=eco_score,
        eco_level=eco_level,
        reward_point=reward_point,
        calculation_log=log,
    )
import pytest

from app.core.feature_engineering import build_food_feature_vector
from app.models.input_models import EcoLevelCalculationRequest


def feature_payload() -> dict:
    return {
        "product": {
            "store_id": "STORE-001",
            "product_id": "PRODUCT-001",
            "product_name": "피자빵",
            "category": "prepared_bakery",
            "quantity": 1,
            "food_weight_g": 150,
            "food_weight_source": "measured",
            "ingredients": [
                {
                    "name": "밀가루",
                    "ratio_percent": 45,
                    "animal_origin": False,
                },
                {
                    "name": "치즈",
                    "ratio_percent": 15,
                    "animal_origin": True,
                },
                {
                    "name": "소시지",
                    "ratio_percent": 20,
                    "animal_origin": True,
                },
            ],
            "nutrition": {
                "basis_g": 100,
                "moisture_g": 35,
                "carbohydrate_g": 48,
                "protein_g": 12,
                "fat_g": 16,
                "sodium_mg": 620,
                "source": "nutrition_label",
            },
            "packaging": [
                {
                    "material": "multilayer",
                    "weight_g": 8,
                    "contaminated": True,
                    "separable_from_food": True,
                    "recyclable": False,
                    "source": "measured",
                }
            ],
            "processing_methods": ["baked"],
            "storage_condition": "ambient",
            "sale_deadline_at": "2026-07-12T21:00:00+09:00",
            "expires_at": "2026-07-13T12:00:00+09:00",
        },
        "context": {
            "region_code": "30170",
            "requested_at": "2026-07-12T18:00:00+09:00",
        },
    }


def test_feature_vector_is_calculated():
    request = EcoLevelCalculationRequest.model_validate(
        feature_payload()
    )

    vector = build_food_feature_vector(request)

    assert vector.product_name == "피자빵"
    assert vector.food_weight_g == 150

    assert vector.moisture_ratio == pytest.approx(0.35)
    assert vector.carbohydrate_ratio == pytest.approx(0.48)
    assert vector.protein_ratio == pytest.approx(0.12)
    assert vector.fat_ratio == pytest.approx(0.16)

    assert vector.animal_origin_ratio == pytest.approx(0.4375)

    assert vector.packaging_weight_g == pytest.approx(8.0)
    assert vector.packaging_to_food_ratio == pytest.approx(8 / 150)

    assert vector.packaging_complexity == pytest.approx(1.0)
    assert vector.packaging_contamination == pytest.approx(1.0)
    assert vector.separation_difficulty == pytest.approx(0.0)
    assert vector.recycling_difficulty == pytest.approx(1.0)

    assert vector.processing_intensity == pytest.approx(0.45)
    assert vector.perishability == pytest.approx(0.545)

    assert vector.hours_to_sale_deadline == pytest.approx(3.0)
    assert vector.urgency_score == pytest.approx(0.9375)

    assert vector.data_completeness_score == pytest.approx(0.96)


def test_missing_optional_data_is_preserved_as_unknown():
    payload = feature_payload()

    payload["product"]["ingredients"] = []
    payload["product"]["nutrition"] = None
    payload["product"]["packaging"] = []
    payload["product"]["processing_methods"] = []
    payload["product"]["expires_at"] = None

    request = EcoLevelCalculationRequest.model_validate(payload)
    vector = build_food_feature_vector(request)

    assert vector.moisture_ratio is None
    assert vector.animal_origin_ratio is None
    assert vector.packaging_weight_g is None
    assert vector.processing_intensity is None

    assert vector.data_completeness_score == pytest.approx(0.25)
    assert len(vector.warnings) >= 4


def test_deadline_passed_has_maximum_urgency():
    payload = feature_payload()

    payload["context"]["requested_at"] = (
        "2026-07-12T22:00:00+09:00"
    )

    request = EcoLevelCalculationRequest.model_validate(payload)
    vector = build_food_feature_vector(request)

    assert vector.hours_to_sale_deadline == pytest.approx(-1.0)
    assert vector.urgency_score == pytest.approx(1.0)


def test_deadline_over_48_hours_has_zero_urgency():
    payload = feature_payload()

    payload["context"]["requested_at"] = (
        "2026-07-10T18:00:00+09:00"
    )

    request = EcoLevelCalculationRequest.model_validate(payload)
    vector = build_food_feature_vector(request)

    assert vector.hours_to_sale_deadline == pytest.approx(51.0)
    assert vector.urgency_score == pytest.approx(0.0)
import pytest
from pydantic import ValidationError

from app.models.input_models import EcoLevelCalculationRequest


def valid_payload() -> dict:
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
                    "allergens": ["milk"],
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
            "region_code": "30170"
        },
    }


def test_valid_request_is_accepted():
    request = EcoLevelCalculationRequest.model_validate(valid_payload())

    assert request.product.product_name == "피자빵"
    assert request.product.food_weight_g == 150
    assert request.product.category.value == "prepared_bakery"
    assert request.context.region_code == "30170"


def test_unknown_field_is_rejected():
    payload = valid_payload()
    payload["product"]["unknown_score"] = 0.75

    with pytest.raises(ValidationError):
        EcoLevelCalculationRequest.model_validate(payload)


def test_ingredient_ratio_over_100_is_rejected():
    payload = valid_payload()
    payload["product"]["ingredients"][0]["ratio_percent"] = 80
    payload["product"]["ingredients"][1]["ratio_percent"] = 40

    with pytest.raises(ValidationError):
        EcoLevelCalculationRequest.model_validate(payload)


def test_naive_datetime_is_rejected():
    payload = valid_payload()
    payload["product"]["sale_deadline_at"] = "2026-07-12T21:00:00"

    with pytest.raises(ValidationError):
        EcoLevelCalculationRequest.model_validate(payload)


def test_expiration_before_sale_deadline_is_rejected():
    payload = valid_payload()
    payload["product"]["expires_at"] = "2026-07-12T20:00:00+09:00"

    with pytest.raises(ValidationError):
        EcoLevelCalculationRequest.model_validate(payload)
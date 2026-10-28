# 코드 검토 포인트

## 누락값과 결과 불변성

다음은 [특징 모델 원본](../engine/app/models/feature_models.py)의 일부입니다.

```python
class FoodFeatureVector(BaseModel):
    """
    Eco-Level 산정 전 단계에서 사용하는 표준화된 식품 특성 벡터.
    비율형 값은 원칙적으로 0.0~1.0 범위이며, 원본 데이터가 없으면 None으로 유지한다.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )
```

입력 자료가 없을 때 수치를 0으로 꾸며 넣지 않고 None으로 유지하며, frozen 모델로 계산 결과의 우발적인 변경을 방지합니다.

## 입력 검증

[입력 모델](../engine/app/models/input_models.py)은 extra="forbid"로 허용하지 않은 필드를 거부하고, 필드 범위와 원재료 비율 합계 및 시각 관계를 검증합니다.

[테스트](../engine/tests/test_input_models.py)에서 정상 입력과 각 오류 경로를 확인할 수 있습니다. [특징 변환 테스트](../engine/tests/test_feature_engineering.py)는 정상 값과 누락 정보 및 마감 경계 조건을 다룹니다.

## 계산과 화면의 분리

[초기 계산 엔진](../prototype/eco_engine.py)은 UI에 의존하지 않습니다. [Streamlit 화면](../prototype/app.py)이 입력을 모아 엔진에 전달하고 결과를 표시합니다.

모든 예시는 코드 열람을 위한 설명이며 별도의 재사용 라이선스를 부여하지 않습니다.

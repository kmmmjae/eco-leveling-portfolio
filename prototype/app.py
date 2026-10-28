import time
import streamlit as st

from eco_engine import FoodInput, calculate_eco_level
from parameters import CATEGORY_PROFILE, PACKAGING_PROFILE, INGREDIENT_EFFECTS


# --------------------------------------------------
# 1. 화면 기본 설정
# --------------------------------------------------

st.set_page_config(
    page_title="들고가유 Eco-Leveling Prototype",
    layout="centered",
)


# --------------------------------------------------
# 2. 보조 함수
# --------------------------------------------------

def format_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def get_level_description(level: str) -> str:
    descriptions = {
        "Lv1": "폐기 시 환경부하가 매우 낮은 식품으로 산정되었습니다.",
        "Lv2": "폐기 시 환경부하가 낮은 편인 식품으로 산정되었습니다.",
        "Lv3": "폐기 시 환경부하가 보통 수준인 식품으로 산정되었습니다.",
        "Lv4": "폐기 시 환경부하가 높은 식품으로 산정되었습니다.",
        "Lv5": "폐기 시 환경부하가 매우 높은 식품으로 산정되었습니다.",
    }
    return descriptions.get(level, "")


# --------------------------------------------------
# 3. 메인 화면
# --------------------------------------------------

st.title("들고가유 Eco-Leveling Prototype")

st.write(
    "마감 식품의 성분·포장재·폐기 임박도 정보를 입력하면, "
    "시스템이 내부적으로 폐기 경로와 환경부하를 계산하여 Eco-Level과 보상 포인트를 산정합니다."
)

st.caption(
    "본 프로토타입은 기술 검토를 위한 초기 계산 모델이며, "
    "계수는 향후 실측 데이터와 운영 데이터에 따라 보정될 수 있습니다."
)

st.markdown("---")


# --------------------------------------------------
# 4. 입력 폼
# --------------------------------------------------

with st.form("eco_level_form"):
    st.subheader("1. 상품 정보 입력")

    product_name = st.text_input(
        "상품명",
        placeholder="예: 피자빵, 크림빵, 식빵",
    )

    category = st.selectbox(
        "식품군",
        list(CATEGORY_PROFILE.keys()),
        index=list(CATEGORY_PROFILE.keys()).index("조리빵"),
    )

    col1, col2 = st.columns(2)

    with col1:
        food_weight_g = st.number_input(
            "식품 중량(g)",
            min_value=1.0,
            max_value=1000.0,
            value=150.0,
            step=10.0,
        )

    with col2:
        packaging_weight_g = st.number_input(
            "포장재 중량(g)",
            min_value=0.0,
            max_value=100.0,
            value=8.0,
            step=1.0,
        )

    packaging_type = st.selectbox(
        "포장재 유형",
        list(PACKAGING_PROFILE.keys()),
        index=list(PACKAGING_PROFILE.keys()).index("복합 포장"),
    )

    ingredients = st.multiselect(
        "주요 원재료 및 조리 특성",
        list(INGREDIENT_EFFECTS.keys()),
        default=["치즈", "육류/햄/소시지", "소스류"],
    )

    col3, col4 = st.columns(2)

    with col3:
        hours_to_deadline = st.number_input(
            "판매 마감까지 남은 시간",
            min_value=0.0,
            max_value=24.0,
            value=2.0,
            step=0.5,
        )

    with col4:
        store_waste_rate_percent = st.slider(
            "점포 평균 폐기 가능성(%)",
            min_value=0,
            max_value=100,
            value=70,
            step=5,
        )

    show_detail = st.checkbox("계산 세부값 보기", value=False)

    submitted = st.form_submit_button("Eco-Level 계산하기")


# --------------------------------------------------
# 5. 계산 실행 및 결과 출력
# --------------------------------------------------

if submitted:
    if not product_name.strip():
        st.warning("상품명을 입력해주세요.")
    else:
        food_input = FoodInput(
            product_name=product_name,
            category=category,
            food_weight_g=food_weight_g,
            packaging_weight_g=packaging_weight_g,
            packaging_type=packaging_type,
            ingredients=ingredients,
            hours_to_deadline=hours_to_deadline,
            store_waste_rate_percent=store_waste_rate_percent,
        )

        with st.spinner("계산 중..."):
            time.sleep(1.2)
            result = calculate_eco_level(food_input)

        st.markdown("---")
        st.subheader("2. Eco-Level 산정 결과")

        col_result_1, col_result_2, col_result_3 = st.columns(3)

        with col_result_1:
            st.metric("Eco-Level", result.eco_level)

        with col_result_2:
            st.metric("EcoScore", f"{result.eco_score:.1f}")

        with col_result_3:
            st.metric("예상 지급 포인트", f"{result.reward_point} P")

        st.info(get_level_description(result.eco_level))

        st.markdown("---")
        st.subheader("3. 요약")

        st.write(
            f"입력된 `{product_name}`은/는 식품군 `{category}`, 포장재 유형 `{packaging_type}`으로 처리되었으며, "
            f"폐기 임박도와 점포 폐기 가능성을 반영한 결과 **{result.eco_level}**로 산정되었습니다."
        )

        if show_detail:
            st.markdown("---")
            st.subheader("4. 내부 계산 세부값")

            st.write("계산 단계 로그")
            for step in result.calculation_log:
                st.write(f"- {step}")

            st.write("식품 특성 벡터")
            st.json({key: round(value, 4) for key, value in result.profile.items()})

            st.write("폐기 경로 확률")
            st.json({
                key: format_percent(value)
                for key, value in result.disposal_probabilities.items()
            })

            st.write("오염물질별 환경부하 벡터")
            st.json({
                key: round(value, 2)
                for key, value in result.pollution_vector.items()
            })

            st.write("중간 점수")
            st.json({
                "성분부하점수": round(result.composition_score, 2),
                "폐기경로점수": round(result.disposal_score, 2),
                "오염물질점수": round(result.pollution_score, 2),
                "최종 EcoScore": round(result.eco_score, 2),
                "Eco-Level": result.eco_level,
                "보상 포인트": result.reward_point,
            })
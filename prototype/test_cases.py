"""
Eco-Leveling representative test cases.

이 파일은 대표 식품군에 대해 Eco-Leveling 계산 결과를 일괄 산출한다.
포트폴리오 검토용 대표 시나리오 데이터를 생성하는 목적이다.

실행 결과:
- 터미널에 대표 식품별 계산 결과 출력
- outputs/eco_level_test_results.csv 파일 생성
"""

import csv
from pathlib import Path

from eco_engine import FoodInput, calculate_eco_level


OUTPUT_DIR = Path("outputs")
OUTPUT_CSV_PATH = OUTPUT_DIR / "eco_level_test_results.csv"


def run_test_case(food_input: FoodInput) -> dict:
    result = calculate_eco_level(food_input)

    return {
        "상품명": food_input.product_name,
        "식품군": food_input.category,
        "식품중량(g)": food_input.food_weight_g,
        "포장재중량(g)": food_input.packaging_weight_g,
        "포장재유형": food_input.packaging_type,
        "주요원재료": ", ".join(food_input.ingredients),
        "마감까지남은시간(h)": food_input.hours_to_deadline,
        "점포폐기가능성(%)": food_input.store_waste_rate_percent,

        "성분부하점수": round(result.composition_score, 2),
        "폐기경로점수": round(result.disposal_score, 2),
        "오염물질점수": round(result.pollution_score, 2),
        "EcoScore": round(result.eco_score, 2),
        "Eco-Level": result.eco_level,
        "지급포인트": result.reward_point,

        "소각확률(%)": round(result.disposal_probabilities["소각"] * 100, 2),
        "매립확률(%)": round(result.disposal_probabilities["매립"] * 100, 2),
        "음식물류처리확률(%)": round(result.disposal_probabilities["음식물류 폐기물 처리"] * 100, 2),
        "일반폐기물처리확률(%)": round(result.disposal_probabilities["일반폐기물 처리"] * 100, 2),
        "분리배출확률(%)": round(result.disposal_probabilities["포장재 분리배출"] * 100, 2),

        "CO2e": round(result.pollution_vector["CO2e"], 2),
        "CH4": round(result.pollution_vector["CH4"], 2),
        "N2O": round(result.pollution_vector["N2O"], 2),
        "NOx/SOx": round(result.pollution_vector["NOx/SOx"], 2),
        "PM": round(result.pollution_vector["PM"], 2),
        "Leachate": round(result.pollution_vector["Leachate"], 2),
        "Odor": round(result.pollution_vector["Odor"], 2),
        "Packaging": round(result.pollution_vector["Packaging"], 2),
    }


def print_result_table(results: list[dict]) -> None:
    print("\n=== Eco-Leveling 대표 식품 테스트 결과 ===\n")

    for item in results:
        print(f"[{item['상품명']}]")
        print(f"- 식품군: {item['식품군']}")
        print(f"- 포장재: {item['포장재유형']}")
        print(f"- 주요 원재료: {item['주요원재료']}")
        print(f"- 성분부하점수: {item['성분부하점수']}")
        print(f"- 폐기경로점수: {item['폐기경로점수']}")
        print(f"- 오염물질점수: {item['오염물질점수']}")
        print(f"- EcoScore: {item['EcoScore']}")
        print(f"- Eco-Level: {item['Eco-Level']}")
        print(f"- 지급포인트: {item['지급포인트']} P")
        print(
            f"- 폐기경로확률: "
            f"소각 {item['소각확률(%)']}%, "
            f"매립 {item['매립확률(%)']}%, "
            f"음식물류 {item['음식물류처리확률(%)']}%, "
            f"일반폐기물 {item['일반폐기물처리확률(%)']}%, "
            f"분리배출 {item['분리배출확률(%)']}%"
        )
        print()


def save_results_to_csv(results: list[dict], output_path: Path) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    if not results:
        raise ValueError("저장할 결과가 없습니다.")

    fieldnames = list(results[0].keys())

    with output_path.open("w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"CSV 파일 저장 완료: {output_path}")


def main() -> None:
    test_cases = [
        FoodInput(
            product_name="피자빵",
            category="조리빵",
            food_weight_g=150,
            packaging_weight_g=8,
            packaging_type="복합 포장",
            ingredients=["치즈", "육류/햄/소시지", "소스류"],
            hours_to_deadline=2,
            store_waste_rate_percent=70,
        ),
        FoodInput(
            product_name="크림빵",
            category="제과류",
            food_weight_g=110,
            packaging_weight_g=5,
            packaging_type="비닐 포장",
            ingredients=["크림/유제품"],
            hours_to_deadline=3,
            store_waste_rate_percent=60,
        ),
        FoodInput(
            product_name="식빵",
            category="제과류",
            food_weight_g=90,
            packaging_weight_g=4,
            packaging_type="종이 포장",
            ingredients=[],
            hours_to_deadline=6,
            store_waste_rate_percent=45,
        ),
        FoodInput(
            product_name="돈까스 도시락",
            category="도시락",
            food_weight_g=420,
            packaging_weight_g=25,
            packaging_type="플라스틱 용기",
            ingredients=["육류/햄/소시지", "튀김/기름", "소스류"],
            hours_to_deadline=1,
            store_waste_rate_percent=75,
        ),
        FoodInput(
            product_name="닭가슴살 샐러드",
            category="샐러드",
            food_weight_g=250,
            packaging_weight_g=18,
            packaging_type="플라스틱 용기",
            ingredients=["육류/햄/소시지", "채소/과일"],
            hours_to_deadline=4,
            store_waste_rate_percent=55,
        ),
    ]

    results = [run_test_case(case) for case in test_cases]

    print_result_table(results)
    save_results_to_csv(results, OUTPUT_CSV_PATH)


if __name__ == "__main__":
    main()
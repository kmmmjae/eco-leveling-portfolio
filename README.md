# 들고가유 Eco-Leveling 코드 포트폴리오

마감 식품의 특성과 포장 정보를 바탕으로 상대 환경부하를 계산하고, 등급과 보상 포인트로 연결하는 Python 프로토타입 및 후속 입력 검증 모듈입니다.

**공개 목적: 개발 역량 검토를 위한 코드 열람. 오픈소스 재사용 라이선스를 부여한 프로젝트가 아닙니다.**

## 프로젝트 개요

- 작성자: 김민재 (GitHub: kmmmjae)
- 담당 범위: 초기 계산 엔진, Streamlit 시연 UI, 후속 입력 모델과 특징 변환 개발
- 상태: 연구·개발 단계의 포트폴리오 스냅샷
- 기술: Python, Streamlit, Pydantic, pytest
- 현재 계수는 실증 전 초기값입니다. EcoScore는 상대 점수이며 실측 탄소 감축량이나 검증된 예측 정확도를 의미하지 않습니다.

## 코드 탐색 순서

| 파일 | 확인할 내용 |
| --- | --- |
| [prototype/eco_engine.py](prototype/eco_engine.py) | 계산 엔진과 UI의 분리, 단계별 계산과 로그 |
| [prototype/parameters.py](prototype/parameters.py) | 시연 계수, 가중치와 등급 임계값 분리 |
| [prototype/app.py](prototype/app.py) | Streamlit 입력 폼과 결과 표시 |
| [prototype/test_cases.py](prototype/test_cases.py) | 대표 식품 5종 계산과 CSV 생성 |
| [engine/app/models/input_models.py](engine/app/models/input_models.py) | 잘못된 필드, 비율, 시간대와 시각 관계의 검증 |
| [engine/app/core/feature_engineering.py](engine/app/core/feature_engineering.py) | 특징 변환, 누락값 보존과 데이터 완전성 |
| [engine/tests](engine/tests) | 입력 모델과 특징 변환의 회귀 테스트 |

## 구현 구조

### 초기 계산 프로토타입

상품 입력 → 식품 특성 벡터 → 5개 폐기 경로의 상대 확률 → 8개 환경부하 항목 → EcoScore → Lv1~Lv5 → 보상 포인트

계산 로직과 화면, 파라미터를 분리했습니다. 높은 등급은 해당 모델에서 폐기 시 상대 환경부하가 높게 산정되었다는 뜻이며, 식품 안전성이나 영양 품질을 나타내지 않습니다.

### 후속 입력 검증 모듈

Pydantic 입력 모델 → 필드와 관계 검증 → 표준 특징 벡터 → 누락값과 경고 및 데이터 완전성 점수

후속 모듈은 초기 프로토타입과 독립된 개발 단계입니다. 이 공개본에서 두 모듈이 실제 앱이나 배포 API로 연결되어 있다고 주장하지 않습니다.

## 검증 결과

2026-10-28 검증:

- 초기 프로토타입의 대표 식품 5종 계산 결과 재현
- 후속 모듈의 입력 모델 테스트 5개와 특징 변환 테스트 4개, 총 9개 통과
- 네트워크 호출이나 실제 고객 데이터를 사용하지 않은 로컬 검증

상세 결과는 [검증 기록](docs/VALIDATION.md), 설계 설명은 [구현 안내](docs/ARCHITECTURE.md)를 참고하세요. 검증 결과는 실측 환경성과나 서비스 전체의 안정성 보장이 아닙니다.

## 열람과 권한

Copyright (c) 2026 김민재. All rights reserved.

이 저장소는 포트폴리오 검토를 위해 공개합니다. MIT, Apache 또는 기타 오픈소스 재사용 라이선스를 부여하지 않습니다. 관련 법률 및 GitHub 이용약관에 따른 권리를 제외하고 코드의 수정, 재배포, 상업적 이용 등에 대한 추가 권한을 부여하지 않습니다. 그 밖의 이용은 권리자의 별도 허락을 받아야 합니다.

Public 저장소의 코드는 열람·다운로드될 수 있으며 GitHub 이용약관에 따른 포크가 가능합니다. 이 고지는 다운로드나 포크를 기술적으로 차단하지 않습니다. 외부 방문자에게 원본 저장소의 쓰기 권한은 부여하지 않습니다.

자세한 사항은 [권리 고지](RIGHTS.md)를 참고하세요. 이 저장소는 공개 검토용 스냅샷으로, 외부 기여를 접수하지 않습니다.

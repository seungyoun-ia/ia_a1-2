# 국내 여행지 추천 CLI 프로그램

여행 날짜를 입력하면 Gemini API와 Kakao Local API를 사용해 여행지와 맛집을 찾고 마크다운 리포트를 만들어주는 프로그램입니다.

## 1. 동작 순서

1. **날짜 확인:** 입력한 날짜(`--date`)가 올바른 형식(`YYYY-MM-DD`)인지 확인합니다.
2. **API 키 점검:** `.env` 파일에 필요한 키가 있는지 확인합니다.
3. **여행지 추천:** Gemini로 날짜에 맞는 추천 도시, 날씨, 행사, 이유를 JSON으로 받습니다.
4. **맛집 검색:** Kakao 로컬 API로 해당 도시의 맛집 5곳을 검색합니다.
5. **리포트 작성:** 모은 정보를 합쳐 Gemini가 마크다운 리포트를 작성합니다.
6. **파일 저장:** `results/` 폴더에 원본 JSON과 최종 마크다운 리포트를 저장합니다.

| 구분 | 사용 API | 방식 | 역할 |
| :--- | :--- | :--- | :--- |
| LLM | Google Gemini (`gemini-1.5-flash`) | POST | 1차 추천 JSON 생성, 최종 리포트 작성 |
| 장소 검색 | Kakao Local 키워드 검색 | GET | 추천 도시 맛집 5곳 조회 |

## 2. 폴더 구조

```text
travel_mission/
├── travel_planner.py     # 메인 실행 파일
├── .gitignore            # Git 제외 설정 (.env, .venv/ 등)
├── README.md             # 프로젝트 설명서
└── results/              # 실행 결과 폴더
    ├── *_data.json       # 원본 데이터 및 에러 기록
    └── *_report.md       # 최종 여행 리포트
```

## 3. 실행 방법

### 라이브러리 설치
```bash
pip install requests python-dotenv google-genai
```

### 실행 명령어
```bash
python travel_planner.py --date "2026-11-20"
```
날짜 형식이 틀리거나 없는 날짜면 안내 문구를 띄우고 종료됩니다.

## 4. API 키 설정

프로젝트 폴더에 `.env` 파일을 만들고 발급받은 키를 넣습니다.

```env
GEMINI_API_KEY=구글_API_키
KAKAO_REST_API_KEY=카카오_REST_API_키
```

- 카카오 개발자 사이트에서 `카카오맵` 활성화(ON) 및 플랫폼 Web에 `http://localhost` 등록이 필요합니다.
- 키가 없으면 안내 후 바로 종료됩니다.

## 5. 결과 파일 안내

실행하면 `results/` 폴더에 파일 2개가 만들어집니다.

- `results/*_data.json`: 1차 추천 JSON, 맛집 5곳 데이터, 오류 기록(`errors`)
- `results/*_report.md`: 추천 이유, 날씨, 행사, 맛집 목록, 1일 일정 제안

## 6. 오류 처리 방식

- **날짜 오류 / 키 누락:** 안내 메시지 출력 후 바로 종료합니다.
- **JSON 파싱 실패:** 1회 다시 요청합니다.
- **맛집 검색 실패 / 0건:** 맛집 항목을 '데이터 없음'으로 비워두고 리포트를 끝까지 만듭니다.
- **오류 기록:** 발생한 문제는 `errors` 리스트에 모아 JSON과 리포트에 남깁니다.

## 7. 보안 주의사항

- 코드나 문서에 실제 API 키를 직접 적지 않습니다.
- 키가 적힌 `.env` 파일과 `.venv/` 폴더는 `.gitignore`로 제외해 Git에 올리지 않습니다.

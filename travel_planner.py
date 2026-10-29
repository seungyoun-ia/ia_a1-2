import argparse
import datetime
import json
import os
import re
import sys
import urllib.parse
from dotenv import load_dotenv
from google import genai
import requests

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")

if not GEMINI_API_KEY or not KAKAO_REST_API_KEY:
    print("[오류] 필수 API 키가 설정되지 않았습니다.")
    print("'.env' 파일에 GEMINI_API_KEY와 KAKAO_REST_API_KEY를 입력해주세요.")
    sys.exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)
errors = []

def validate_date(date_str):
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        print("[입력 오류] 날짜 형식이 올바르지 않거나 존재하지 않는 날짜입니다.")
        print('사용법: python travel_planner.py --date "YYYY-MM-DD" (예: 2026-11-20)')
        sys.exit(1)

def get_recommendation(date_str, retry=False):
    prompt = f"""
    당신은 국내 여행 전문가입니다. 여행 날짜는 '{date_str}'입니다.
    이 시기에 방문하기 좋은 국내 여행지 1곳을 추천해주세요.
    반드시 마크다운 코드블록 없이 순수 JSON 형식으로만 응답해야 합니다.
    JSON 스키마:
    {{
      "recommended_city": "도시/지역명 (예: 제주, 강릉, 전주)",
      "weather": "해당 시기 일반적 날씨 요약 1문장",
      "events": ["행사나 축제 1~2개"],
      "reason": "추천 근거 2~3문장"
    }}
    """
    if retry:
        prompt += "\n주의: 이전 응답의 JSON 형식이 올바르지 않았습니다. 반드시 유효한 JSON만 반환하세요."

    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        text = response.text.strip()
        clean_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
        data = json.loads(clean_text)

        required_keys = ["recommended_city", "weather", "events", "reason"]
        if not all(k in data for k in required_keys):
            raise ValueError("필수 키 누락")
        return data
    except Exception as e:
        if not retry:
            print("  └ [재시도] JSON 파싱 오류로 1회 재요청합니다...")
            return get_recommendation(date_str, retry=True)
        else:
            errors.append({"step": "1차_추천", "type": "JSON_PARSE_ERROR", "message": str(e)})
            return {
                "recommended_city": "제주",
                "weather": "온화하고 여행하기 쾌적함 (기본값)",
                "events": ["지역 문화 축제"],
                "reason": "응답 파싱 오류로 인해 기본 추천 지역으로 대체합니다."
            }

def search_restaurants(city):
    query = f"{city} 맛집"
    enc_query = urllib.parse.quote(query)
    url = f"https://dapi.kakao.com/v2/local/search/keyword.json?query={enc_query}&size=5"
    headers = {
        "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"
    }
    restaurants = []
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            documents = res.json().get("documents", [])
            if not documents:
                errors.append({"step": "맛집_검색", "type": "EMPTY_RESULT", "message": f"'{city}' 검색 결과 0건"})
            for doc in documents:
                restaurants.append({
                    "name": doc.get("place_name", ""),
                    "category": doc.get("category_name", ""),
                    "address": doc.get("road_address_name") or doc.get("address_name", ""),
                    "url": doc.get("place_url", ""),
                    "x": doc.get("x", ""),
                    "y": doc.get("y", "")
                })
        else:
            errors.append({"step": "맛집_검색", "type": f"HTTP_{res.status_code}", "message": res.text})
    except Exception as e:
        errors.append({"step": "맛집_검색", "type": "NETWORK_ERROR", "message": str(e)})
    return restaurants

def create_report(date_str, rec_data, restaurants):
    prompt = f"""
    아래 정보를 바탕으로 깔끔한 Markdown 형식의 국내 여행 추천 리포트를 작성해주세요.

    날짜: {date_str}
    추천도시: {rec_data.get('recommended_city')}
    날씨: {rec_data.get('weather')}
    행사/축제: {', '.join(rec_data.get('events', []))}
    추천이유: {rec_data.get('reason')}
    맛집목록: {json.dumps(restaurants, ensure_ascii=False)}
    오류내역: {json.dumps(errors, ensure_ascii=False)}

    [작성 규칙]
    - # {date_str} 국내 여행 추천 리포트
    - ## 추천 지역 및 추천 이유
    - ## 날씨 요약
    - ## 행사 및 축제
    - ## 맛집 추천 (맛집 목록이 비어 있으면 반드시 '데이터 없음 (장소 검색 결과 0건 또는 API 오류)'으로 표기)
    - ## 1일 여행 코스 제안 (오전 / 오후 / 저녁)
    - ## 오류 요약(errors) (오류가 없으면 '특이사항 없음'으로 표기)
    """
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        errors.append({"step": "리포트_생성", "type": "LLM_ERROR", "message": str(e)})
        return f"# {date_str} 여행 추천 리포트 (기본형)\n\n리포트 생성 중 오류가 발생했습니다.\n- 추천 도시: {rec_data.get('recommended_city')}"

def main():
    parser = argparse.ArgumentParser(description="CLI 기반 국내 여행지 추천 프로그램")
    parser.add_argument("--date", required=True, help="여행 날짜 (YYYY-MM-DD)")
    args = parser.parse_args()

    travel_date = validate_date(args.date)
    os.makedirs("results", exist_ok=True)

    print(f"[1/3] 1차 추천 생성 중(LLM)... (날짜: {travel_date})")
    rec = get_recommendation(travel_date)
    city = rec.get("recommended_city")
    print(f"  └ 추천 지역: {city}")

    print(f"[2/3] 맛집 검색 중(카카오 로컬 API)...")
    rests = search_restaurants(city)
    print(f"  └ 맛집 {len(rests)}곳 검색 완료" if rests else "  └ 검색 결과 없음 (데이터 없음 처리)")

    print(f"[3/3] 최종 리포트 생성 중(LLM)...")
    report = create_report(travel_date, rec, rests)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = f"results/{timestamp}_{travel_date}_data.json"
    md_path = f"results/{timestamp}_{travel_date}_report.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "date": travel_date,
            "recommendation": rec,
            "restaurants": rests,
            "errors": errors
        }, f, ensure_ascii=False, indent=2)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n[완료] 결과물이 성공적으로 생성되었습니다!")
    print(f"- 원본 데이터 JSON: {json_path}")
    print(f"- 최종 리포트 MD:   {md_path}")

if __name__ == "__main__":
    main()
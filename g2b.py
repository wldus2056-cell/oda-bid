import requests
import time
from urllib.parse import unquote

def fetch_all_pages(url: str, params: dict) -> list[dict]:
    all_data = []
    page = 1
    max_retries = 3  # 💡 최대 3번까지 끈질기게 재시도

    while True:
        params["pageNo"] = page
        params["numOfRows"] = 999
        
        response_successful = False
        
        # 💡 에러 방어막: 서버가 뻗었을 때를 대비한 3회 반복 재시도 로직
        for attempt in range(max_retries):
            try:
                print(f"📡 공공데이터포털 요청 중... (페이지 {page}, 시도 {attempt+1}/{max_retries})")
                r = requests.get(url, params=params, timeout=60)
                r.raise_for_status()
                response_successful = True
                break  # 성공하면 재시도 반복문 탈출!
                
            except requests.exceptions.RequestException as e:
                print(f"⚠️ 공공데이터포털 응답 지연 (시도 {attempt+1}/{max_retries}). 10초 후 다시 시도합니다...")
                time.sleep(10) # 💡 서버가 쉴 수 있게 10초 대기
                
        # 3번이나 재시도했는데도 실패했다면, 빈 리스트 반환 (에러로 뻗지 않음)
        if not response_successful:
            print("❌ 공공데이터포털 서버가 완전히 응답하지 않습니다. 오늘의 수집을 종료합니다.")
            break

        data = r.json()
        items = data.get("response", {}).get("body", {}).get("items", [])
        
        if not items:
            break
            
        all_data.extend(items)
        
        if len(items) < 999:
            break
            
        page += 1

    return all_data

def fetch_bid_list(api_key: str, start_dt: str, end_dt: str) -> list[dict]:
    """본공고(입찰공고) 수집 함수"""
    url = "http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc"
    params = {
        "inqryDiv": 1,
        "serviceKey": unquote(api_key.strip()),
        "inqryBgnDt": start_dt,
        "inqryEndDt": end_dt,
        "type": "json",
    }
    return fetch_all_pages(url, params)

def fetch_prebid_list(api_key: str, start_dt: str, end_dt: str) -> list[dict]:
    """사전규격공고 수집 함수"""
    url = "http://apis.data.go.kr/1230000/ao/HrcspSsstndrdInfoService/getPublicPrcureThngInfoServc"
    params = {
        "inqryDiv": 1,
        "serviceKey": unquote(api_key.strip()),
        "inqryBgnDt": start_dt,
        "inqryEndDt": end_dt,
        "type": "json",
    }
    return fetch_all_pages(url, params)

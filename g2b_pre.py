# g2b_pre.py
import requests
from urllib.parse import unquote

def fetch_pre_bid_list(api_key: str, start_dt: str, end_dt: str) -> list:
    """나라장터 사전규격공고 API를 호출하여 데이터를 가져오는 함수"""
    url = "http://apis.data.go.kr/1230000/ao/HrcspSsstndrdInfoService/getPublicPrcureThngInfoServc"
    
    params = {
        "ServiceKey": unquote(api_key),
        "inqryBgnDt": start_dt,  # YYYYMMDDHHMM
        "inqryEndDt": end_dt,    # YYYYMMDDHHMM
        "pageNo": 1,
        "numOfRows": 999,
        "type": "json"
    }
    
    try:
        res = requests.get(url, params=params, timeout=30)
        if not res.ok:
            print(f"사전공고 API 호출 실패: {res.status_code}")
            return []
            
        data = res.json()
        
        # 공공데이터 API의 JSON 구조 파싱
        items = data.get("response", {}).get("body", {}).get("items", [])
        
        # items가 dict(단일 건)일 경우 list로 묶어줌
        if isinstance(items, dict):
            items = items.get("item", [])
            if not isinstance(items, list):
                items = [items]
                
        return items
        
    except Exception as e:
        print(f"사전공고 API 파싱 에러: {e}")
        return []

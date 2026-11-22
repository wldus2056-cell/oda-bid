import time
from urllib.parse import unquote

import requests


class BidCollectionError(Exception):
    pass


def _parse_response(response: requests.Response) -> tuple[list[dict], int]:
    try:
        payload = response.json()
    except ValueError as e:
        raise BidCollectionError("나라장터 API가 JSON이 아닌 응답을 반환했습니다.") from e

    response_body = payload.get("response")
    if not isinstance(response_body, dict):
        raise BidCollectionError("나라장터 API 응답에 response가 없습니다.")

    header = response_body.get("header", {})
    result_code = str(header.get("resultCode", "00"))
    if result_code != "00":
        result_message = header.get("resultMsg", "알 수 없는 오류")
        raise BidCollectionError(
            f"나라장터 API 오류 {result_code}: {result_message}"
        )

    body = response_body.get("body")
    if not isinstance(body, dict):
        raise BidCollectionError("나라장터 API 응답에 body가 없습니다.")

    items = body.get("items") or []
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise BidCollectionError("나라장터 API 응답의 items 형식이 올바르지 않습니다.")

    try:
        total_count = int(body.get("totalCount", len(items)))
    except (TypeError, ValueError) as e:
        raise BidCollectionError("나라장터 API 응답의 totalCount가 올바르지 않습니다.") from e

    return items, total_count


def fetch_all_pages(url: str, params: dict) -> list[dict]:
    all_data = []
    page = 1
    max_retries = 3
    page_size = 999

    while True:
        request_params = dict(params, pageNo=page, numOfRows=page_size)
        last_error = None

        for attempt in range(max_retries):
            try:
                print(f"나라장터 요청: 페이지 {page}, 시도 {attempt + 1}/{max_retries}")
                response = requests.get(url, params=request_params, timeout=60)
                response.raise_for_status()
                items, total_count = _parse_response(response)
                break
            except (requests.exceptions.RequestException, BidCollectionError) as e:
                last_error = e
                print(f"나라장터 응답 오류: {e}")
                if attempt + 1 < max_retries:
                    time.sleep(10 * (2**attempt))
        else:
            raise BidCollectionError(
                f"나라장터 수집 실패: 페이지 {page}, 원인: {last_error}"
            ) from last_error

        all_data.extend(items)
        print(f"나라장터 수집: {len(all_data)}/{total_count}건")

        if not items or len(all_data) >= total_count or len(items) < page_size:
            break

        page += 1

    if len(all_data) < total_count:
        raise BidCollectionError(
            f"나라장터 수집 누락: 전체 {total_count}건 중 {len(all_data)}건만 수집"
        )

    return all_data


def fetch_bid_list(api_key: str, start_dt: str, end_dt: str) -> list[dict]:
    url = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc"
    params = {
        "inqryDiv": 1,
        "serviceKey": unquote(api_key.strip()),
        "inqryBgnDt": start_dt,
        "inqryEndDt": end_dt,
        "type": "json",
    }
    return fetch_all_pages(url, params)


def fetch_prebid_list(api_key: str, start_dt: str, end_dt: str) -> list[dict]:
    url = "https://apis.data.go.kr/1230000/ao/HrcspSsstndrdInfoService/getPublicPrcureThngInfoServc"
    params = {
        "inqryDiv": 1,
        "serviceKey": unquote(api_key.strip()),
        "inqryBgnDt": start_dt,
        "inqryEndDt": end_dt,
        "type": "json",
    }
    return fetch_all_pages(url, params)

# main_pre.py
import os
from datetime import datetime, timedelta, timezone

from g2b import fetch_prebid_list        # 💡 사전공고 함수 임포트
from filters import keyword_match
from discord_notify import send_discord
from ai_filter import gemini_is_oda

KST = timezone(timedelta(hours=9))

print("MAIN_PRE.PY TOP LOADED (사전공고)")

def to_dt_str(dt: datetime) -> str:
    return dt.strftime("%Y%m%d%H%M")

def build_embed(item: dict) -> dict:
# 💡 수정: 여러 변수명을 훑어보고, 정 없으면 규격번호라도 제목으로 띄웁니다.
    raw_title = item.get("prcureItemNm") or item.get("bfSpecRgstNm") or item.get("bizNm") or ""
    reg_no = item.get("bfSpecRgstNo", "번호알수없음")
    title = str(raw_title).strip() if raw_title else f"(제목 누락 - 규격번호: {reg_no})"
    
    org = item.get("dminsttNm", "-")
    deadline = item.get("opnEndDt", "-")  # 의견등록 마감일시
    
    raw_budget = item.get("asignBdgtAmt")
    if raw_budget and str(raw_budget).isdigit():
        budget = f"{int(raw_budget):,}원"
    else:
        budget = str(raw_budget) if raw_budget else "-"

    # 사전공고 상세페이지 링크 조합
    reg_no = item.get("bfSpecRgstNo", "")
    if reg_no:
        url = f"https://www.g2b.go.kr:8101/ep/preparation/prestd/preStdPublishTenderDetail.do?preStdRegNo={reg_no}"
    else:
        url = ""

    ai_reason = item.get("_ai_reason")

    fields = [
        {"name": "수요기관", "value": str(org), "inline": True},
        {"name": "의견등록마감일시", "value": str(deadline), "inline": True},
        {"name": "배정예산액", "value": str(budget), "inline": False},
    ]
    if url:
        fields.append({"name": "링크", "value": url, "inline": False})
    if ai_reason:
        fields.append({"name": "필터링 근거", "value": str(ai_reason), "inline": False})

    # 💡 사전공고는 구분을 위해 초록색 띠 지정
    return {"title": f"[사전공고] {title}", "color": 0x2ecc71, "fields": fields}

def main():
    api_key = os.environ["G2B_API_KEY"].strip()
    webhook_url = os.environ["DISCORD_WEBHOOK_URL"].strip()

    now = datetime.now(KST)
    start = now - timedelta(days=1) 
    start_dt = to_dt_str(start)
    end_dt = to_dt_str(now)

    # 💡 사전공고 데이터 수집
    items = fetch_prebid_list(api_key, start_dt, end_dt)
    print("TOTAL PRE-BID ITEMS:", len(items))

    filtered = []
    skipped_ai = 0
    keyword_passed = 0

    for it in items:
        # 💡 수정: 로그창(Actions)에도 비어있지 않고 텍스트가 무조건 찍히도록 안전망 구성
        raw_title = it.get("prcureItemNm") or it.get("bfSpecRgstNm") or it.get("bizNm") or ""
        reg_no = it.get("bfSpecRgstNo", "번호없음")
        title = str(raw_title).strip() if raw_title else f"(제목 누락 - 규격번호: {reg_no})"
        
        org = str(it.get("dminsttNm", ""))
        url = f"https://www.g2b.go.kr:8101/ep/preparation/prestd/preStdPublishTenderDetail.do?preStdRegNo={reg_no}" if reg_no != "번호없음" else ""

        # 1차 키워드 필터 (filters.py)
        if not keyword_match(title):
            print(f"[1차탈락-사전] {title}")
            continue
            
        print(f"[1차통과-사전] {title}")
        keyword_passed += 1

        # 2차 하이브리드 필터 (ai_filter.py)
        is_oda, reason = gemini_is_oda(title, org, url)
        if is_oda:
            it["_ai_reason"] = reason
            filtered.append(it)
        else:
            skipped_ai += 1
            print(f"[제외-사전] {title[:30]}... | 사유: {reason}")
            
        if not is_oda:
            print(f"[2차탈락-사전] {title} | {reason}")
        
    ai_passed = keyword_passed - skipped_ai
    
    display_start = start.strftime("%m월 %d일 %H:%M")
    display_end = now.strftime("%m월 %d일 %H:%M")
    
    summary_text = (
        f"- 조회기간: {display_start} ~ {display_end} (최근 1일)\n"
        f"- 사전공고 전체: {len(items)}건\n"
        f"- 1차 키워드 통과: {keyword_passed}건\n"
        f"- 2차 AI 필터링 통과: {ai_passed}건 (제외 {skipped_ai}건)"
    )

    if not filtered:
        send_discord(
            webhook_url,
            content=f"🟢 **ODA 사전공고 알림(일일 요약)**\n{summary_text}\n오늘은 조건에 맞는 사전공고가 없습니다.",
            embeds=None
        )
        return

    # 10개씩 묶어서 디스코드로 전송
    chunk_size = 10
    chunks = [filtered[i:i+chunk_size] for i in range(0, len(filtered), chunk_size)]

    for i, chunk in enumerate(chunks, start=1):
        if not chunk:
            continue
        embeds = [build_embed(it) for it in chunk]
        
        content_msg = f"🟢 신규 ODA 사전규격공고 알림 ({i}/{len(chunks)})"
        if i == 1:
            content_msg = f"🟢 **ODA 사전공고 알림(일일 요약)**\n{summary_text}\n\n{content_msg}"

        send_discord(
            webhook_url,
            content=content_msg,
            embeds=embeds
        )

if __name__ == "__main__":
    main()

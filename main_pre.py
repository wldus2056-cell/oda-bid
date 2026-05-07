# main_pre.py
import os
import re
from datetime import datetime, timedelta, timezone

from g2b_pre import fetch_pre_bid_list   # 💡 사전공고용으로 교체
from filters import keyword_match        # 💡 기존 1차 그물망 그대로 사용!
from discord_notify import send_discord  # 💡 기존 디스코드 알림 그대로 사용!
from ai_filter import gemini_is_oda      # 💡 기존 AI 컨설턴트 그대로 사용!

KST = timezone(timedelta(hours=9))

def to_dt_str(dt: datetime) -> str:
    return dt.strftime("%Y%m%d%H%M")

def build_embed(item: dict) -> dict:
    # 💡 사전공고 API 변수명에 맞게 매핑
    title = item.get("prcureItemNm") or item.get("bfSpecRgstNm") or "(제목 없음)"
    org = item.get("dminsttNm", "-")
    deadline = item.get("opnEndDt", "-")  # 사전공고 의견등록 마감일시
    
    raw_budget = item.get("asignBdgtAmt")
    if raw_budget and str(raw_budget).isdigit():
        budget = f"{int(raw_budget):,}원"
    else:
        budget = str(raw_budget) if raw_budget else "-"

    # 사전공고 상세페이지 링크 조립 (사전규격등록번호 활용)
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
        fields.append({"name": "AI 판별 근거", "value": str(ai_reason), "inline": False})

    # 💡 사전공고는 눈에 잘 띄게 초록색(Green)으로 지정
    return {"title": f"[사전공고] {title}", "color": 0x2ecc71, "fields": fields}

def main():
    api_key = os.environ["G2B_API_KEY"].strip()
    webhook_url = os.environ["DISCORD_WEBHOOK_URL"].strip()

    now = datetime.now(KST)
    start = now - timedelta(days=2) # 신규 사전공고 최근 2일치
    start_dt = to_dt_str(start)
    end_dt = to_dt_str(now)

    items = fetch_pre_bid_list(api_key, start_dt, end_dt)
    print("TOTAL PRE-BIDS:", len(items))

    filtered = []
    skipped_ai = 0

    for it in items:
        # 사전공고용 제목과 기관명 가져오기
        title = it.get("prcureItemNm") or it.get("bfSpecRgstNm", "")
        org = str(it.get("dminsttNm", ""))
        reg_no = it.get("bfSpecRgstNo", "")
        url = f"https://www.g2b.go.kr:8101/ep/preparation/prestd/preStdPublishTenderDetail.do?preStdRegNo={reg_no}"
        
        # 1. 기존 1차 필터(filters.py) 적용
        if not keyword_match(title):
            continue
            
        # 2. 기존 2차 하이브리드 필터(ai_filter.py) 적용
        is_oda, reason = gemini_is_oda(title, org, url)
        
        if is_oda:
            it["_ai_reason"] = reason
            filtered.append(it)
        else:
            skipped_ai += 1
            print(f"[제외] {title[:30]}... | 사유: {reason}")

    # ====================================================
    # 디스코드 전송
    # ====================================================
    display_start = start.strftime("%m월 %d일 %H:%M")
    display_end = now.strftime("%m월 %d일 %H:%M")
    
    summary_text = (
        f"- 조회기간: {display_start} ~ {display_end}\n"
        f"- 사전공고 수집: {len(items)}건\n"
        f"- ODA 사전공고 발견: {len(filtered)}건\n"
        f"(💡 AI 제외: {skipped_ai}건)"
    )

    if not filtered:
        send_discord(
            webhook_url,
            content=f"🟢 **오늘의 신규 ODA 사전공고**\n{summary_text}\n오늘은 조건에 맞는 신규 사전공고가 없습니다.",
            embeds=None
        )
    else:
        chunk_size = 10
        chunks = [filtered[i:i+chunk_size] for i in range(0, len(filtered), chunk_size)]
        for i, chunk in enumerate(chunks, start=1):
            embeds = [build_embed(it) for it in chunk]
            content_msg = f"🟢 신규 ODA 사전공고 알림 ({i}/{len(chunks)})"
            if i == 1:
                content_msg = f"🟢 **오늘의 신규 ODA 사전공고**\n{summary_text}\n\n{content_msg}"
            send_discord(webhook_url, content=content_msg, embeds=embeds)

if __name__ == "__main__":
    main()

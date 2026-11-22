import os
import time
from datetime import datetime, timedelta, timezone

from ai_filter import (
    classify_candidates,
    make_candidate_id,
    mandatory_inclusion_reason,
)
from discord_notify import send_discord
from filters import keyword_match
from g2b import BidCollectionError, fetch_bid_list

KST = timezone(timedelta(hours=9))


def to_dt_str(dt: datetime) -> str:
    return dt.strftime("%Y%m%d%H%M")


def build_embed(item: dict, review: bool = False) -> dict:
    title = item.get("bidNtceNm", "(제목 없음)")
    org = item.get("dminsttNm", "-")
    deadline = item.get("bidNtceEndDt") or item.get("bidQlfctRgstDt") or "-"

    raw_budget = item.get("asignBdgtAmt")
    if raw_budget and str(raw_budget).isdigit():
        budget = f"{int(raw_budget):,}원"
    else:
        budget = str(raw_budget) if raw_budget else "-"

    fields = [
        {"name": "수요기관", "value": str(org), "inline": True},
        {"name": "입찰 마감", "value": str(deadline), "inline": True},
        {"name": "예산금액", "value": str(budget), "inline": False},
    ]
    url = item.get("bidNtceDtlUrl", "")
    if url:
        fields.append({"name": "링크", "value": str(url), "inline": False})
    reason = item.get("_filter_reason")
    if reason:
        fields.append({"name": "필터링 근거", "value": str(reason), "inline": False})

    return {
        "title": str(title),
        "color": 0xE67E22 if review else 0x3498DB,
        "fields": fields,
    }


def send_items(webhook_url: str, items: list[dict], label: str, review: bool = False):
    chunk_size = 10 if review else 1
    chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
    for index, chunk in enumerate(chunks, start=1):
        send_discord(
            webhook_url,
            content=f"{label} ({index}/{len(chunks)})",
            embeds=[build_embed(item, review) for item in chunk],
        )
        time.sleep(0.6)


def main():
    api_key = os.environ["G2B_API_KEY"].strip()
    webhook_url = os.environ["DISCORD_WEBHOOK_URL"].strip()

    now = datetime.now(KST)
    start = now - timedelta(days=1)
    start_dt = to_dt_str(start)
    end_dt = to_dt_str(now)

    try:
        items = fetch_bid_list(api_key, start_dt, end_dt)
    except BidCollectionError as e:
        send_discord(
            webhook_url,
            content=(
                "ODA 입찰공고 수집에 실패했습니다.\n"
                "정상적인 0건이 아니므로 GitHub Actions 로그를 확인해 주세요.\n"
                f"오류: {e}"
            ),
        )
        raise

    print(f"전체 본공고: {len(items)}건")
    filtered = []
    candidates = []

    for item in items:
        title = str(item.get("bidNtceNm", ""))
        org = str(item.get("dminsttNm", ""))

        mandatory_reason = mandatory_inclusion_reason(title, org)
        if mandatory_reason:
            item["_filter_reason"] = mandatory_reason
            filtered.append(item)
            continue

        if not keyword_match(f"{title} {org}"):
            continue

        candidates.append({
            "id": make_candidate_id(
                item.get("bidNtceNo"), item.get("bidNtceOrd"), title, org
            ),
            "title": title,
            "org": org,
            "item": item,
        })

    results = classify_candidates(candidates)
    review_required = []
    ai_passed = 0
    rule_rejected = 0
    ai_rejected = 0
    model_review = 0
    system_review = 0

    for candidate in candidates:
        item = candidate["item"]
        result = results.get(candidate["id"])
        if result is None:
            item["_filter_reason"] = "분류 결과가 없어 사람 검토가 필요합니다."
            review_required.append(item)
            system_review += 1
            continue

        item["_filter_reason"] = result.reason
        if result.decision == "pass":
            filtered.append(item)
            ai_passed += 1
        elif result.decision == "review":
            review_required.append(item)
            if result.source == "system":
                system_review += 1
            else:
                model_review += 1
        elif result.source == "rule":
            rule_rejected += 1
        else:
            ai_rejected += 1

    summary_text = (
        f"- 조회기간: {start.strftime('%m월 %d일 %H:%M')} ~ "
        f"{now.strftime('%m월 %d일 %H:%M')}\n"
        f"- 수집 상태: 정상\n"
        f"- 전체 공고: {len(items)}건\n"
        f"- 강제 포함(KOICA·KOFIH·EDCF): {len(filtered) - ai_passed}건\n"
        f"- AI 분류 통과: {ai_passed}건\n"
        f"- 조건 미충족: 규칙 {rule_rejected}건, AI {ai_rejected}건\n"
        f"- 사람 검토 필요: {len(review_required)}건 "
        f"(모델 보류 {model_review}건, 시스템 오류 {system_review}건)"
    )
    send_discord(
        webhook_url,
        content=f"ODA 입찰공고 알림(일일 요약)\n{summary_text}",
    )

    if filtered:
        send_items(webhook_url, filtered, "ODA 관련 입찰공고")
    if review_required:
        send_items(webhook_url, review_required, "사람 검토 필요 공고", review=True)
    if not filtered and not review_required:
        send_discord(webhook_url, content="오늘은 조건에 맞는 입찰공고가 없습니다.")


if __name__ == "__main__":
    main()

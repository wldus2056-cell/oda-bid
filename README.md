# ODA 입찰 알림 봇

나라장터 본공고와 사전규격공고에서 팀세일러스의 수주 대상 사업을 찾아 Discord로 알리는 자동화 봇입니다.

## 처리 방식

1. 나라장터에서 최근 24시간 공고를 수집하고 응답 코드·건수·페이지 누락을 검증합니다.
2. KOICA·한국국제협력단, KOFIH·한국국제보건의료재단 공고는 무조건 포함합니다.
3. 수출입은행 공고 중 EDCF·대외경제협력기금 관련 공고는 무조건 포함합니다.
4. 나머지 공고는 제목·사업명·수요기관을 함께 검사해 1차 후보로 추출합니다.
5. 명백한 행정·운영 공고를 규칙으로 제외한 후, 나머지 후보를 DeepSeek Flash에 10건씩 배치 분류합니다.
6. 분류 결과를 `통과`, `제외`, `사람 검토`로 나누어 Discord에 전송합니다.

강제 포함 규칙은 제외 키워드와 AI보다 먼저 적용되며 API 비용이 발생하지 않습니다.

## DeepSeek 설정

- 모델: `deepseek-flash`
- Thinking Mode: 비활성화
- JSON Output: `response_format={"type": "json_object"}`
- 기본 배치: 10건
- 기본 동시 호출: 1개
- API 오류: 최대 3회 재시도
- 결과 누락: 누락 건만 배치 재요청 후 개별 재요청

`ODA_BATCH_SIZE`는 1~20, `ODA_MAX_WORKERS`는 1~2로 조정할 수 있습니다.

JSON 문법뿐 아니라 공고 ID, 중복 결과, 누락 결과, 판별값도 검증합니다. 최종적으로 판별하지 못한 공고는 탈락시키지 않고 사람 검토 알림으로 별도 전송합니다.

## 장애 처리

나라장터 수집 실패와 정상적인 공고 0건을 구분합니다. 수집에 실패하면 Discord에 장애를 알리고 GitHub Actions 작업을 실패로 종료합니다. DeepSeek 호출 실패 공고는 `시스템 오류` 검토 대상으로 표시합니다.

## 파일 구조

- `main.py`: 본공고 수집·분류·알림
- `main_pre.py`: 사전규격공고 수집·분류·알림
- `g2b.py`: 나라장터 API 수집과 응답 검증
- `filters.py`: 1차 키워드 후보 추출
- `ai_filter.py`: 강제 포함, DeepSeek 배치 분류와 결과 복구
- `discord_notify.py`: Discord 웹후크와 전송 재시도
- `.github/workflows/run_bot.yml`: 매일 08:30 KST 자동 실행

## 설정

GitHub 저장소의 `Settings > Secrets and variables > Actions`에 다음을 등록합니다.

- `G2B_API_KEY`: 나라장터 입찰공고·사전규격공고 API 키
- `DISCORD_WEBHOOK_URL`: Discord 채널 웹후크
- `DEEPSEEK_API_KEY`: DeepSeek API 키

Gemini API 키는 더 이상 사용하지 않습니다.

## 실행

```bash
pip install -r requirements.txt
python main.py
python main_pre.py
```

GitHub Actions는 매일 08:30 KST에 실행되며 `workflow_dispatch`로 수동 실행할 수도 있습니다. 현재 시간은 DeepSeek 오프피크에 해당합니다.

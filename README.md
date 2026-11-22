# 🌍 오다(ODA)주웠다 봇

나라장터(G2B)에 올라오는 수천 건의 공고 중, 팀세일러스의 타겟인 **ODA(국제개발협력) 관련 사업**만 정확하게 솎아내어 디스코드로 알려주는 자동화 봇입니다. 

단순 키워드 매칭의 한계를 극복하기 위해 **[1차 정규식 키워드 필터링 + 2차 LLM(AI) 문맥 분석]**이라는 하이브리드 필터링 시스템을 도입하여 오탐지율을 최소화했습니다.

## ✨ 주요 기능 (Key Features)

* **투트랙(Two-Track) 공고 수집**
  * 📢 **본공고 (입찰공고):** 매일 신규 입찰 공고를 수집 (파란색 띠)
  * 🔔 **사전공고 (사전규격공고):** 본공고가 뜨기 전 규격 검토 단계의 용역 사업을 남들보다 빠르게 수집 (초록색 띠)
* **하이브리드 AI 필터링 (Hybrid Filtering)**
  * **1차 그물망 (`filters.py`):** 파이썬 정규식을 통해 ODA 관련 단어, 전 세계 개도국 명단, 실무 키워드가 하나라도 포함된 공고만 1차로 빠르게 추출 (비용 0원, 초고속)
  * **2차 AI 판별 (`ai_filter.py`):** 1차를 통과한 애매한 공고들을 Gemini(및 DeepSeek) AI에게 넘겨, "단순 행정/물품/교류행사"인지 "진성 ODA 컨설팅 용역"인지 문맥을 파악해 최종 선별
* **완전 자동화 (GitHub Actions)**
  * 별도의 서버 없이 GitHub Actions의 Cron 스케줄러를 통해 매일 정해진 시간(오전 11시경)에 본공고와 사전공고 봇이 연속으로 실행됨

## 🗂️ 파일 구조 (File Structure)

* `main.py` : 본공고(입찰공고) 수집 및 알림 메인 실행 파일
* `main_pre.py` : 사전규격공고(용역) 수집 및 알림 메인 실행 파일
* `g2b.py` : 공공데이터포털(나라장터) API 통신 및 데이터 페칭(Fetching) 담당
* `filters.py` : 1차 키워드 필터링 (ODA 핵심 용어, 기관명, 개도국 리스트 총망라)
* `ai_filter.py` : 2차 AI 필터링 (LLM 프롬프트 세팅 및 Gemini/DeepSeek API 호출)
* `discord_notify.py` : 디스코드 웹후크(Webhook) 메시지 전송 모듈
* `.github/workflows/run_bot.yml` : 자동 실행 스케줄 및 환경 변수(Secrets) 세팅 파일

## ⚙️ 설정 및 실행 방법 (Setup)

이 봇을 포크(Fork)하거나 새 환경에서 세팅하려면 아래의 **API Keys**가 필요합니다. GitHub 저장소의 `Settings` > `Secrets and variables` > `Actions`에 다음 변수들을 등록하세요.

1. `G2B_API_KEY`: 공공데이터포털 나라장터 입찰공고 & 사전규격공고(용역) API 활용 승인 키
2. `DISCORD_WEBHOOK_URL`: 알림을 받을 디스코드 채널의 웹후크 URL
3. `GEMINI_API_KEY`: Google Gemini API 키 (1순위 AI 판별기)
4. `DEEPSEEK_API_KEY`: DeepSeek API 키 (Gemini 한도 초과 시 2순위 폴백용)

## 🛠️ 유지보수 가이드 (Maintenance)

* **새로운 타겟 국가나 기관이 생겼을 때:** `filters.py`의 리스트에 단어를 추가하세요.
* **자꾸 엉뚱한(필요 없는) 공고가 AI를 통과할 때:** `ai_filter.py`의 `prompt` (즉시 탈락 기준) 부분에 해당 공고의 패턴이나 예시를 추가하여 AI를 재학습시키세요.

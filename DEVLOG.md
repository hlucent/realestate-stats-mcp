# DEVLOG.md — realestate-stats-mcp

진행 기록 템플릿. 매 작업 세션마다 아래 형식으로 항목을 추가한다.

```
## YYYY-MM-DD
- 진행한 작업:
- 확인된 사실 (실측 결과):
- 확인 필요 / 미해결:
- 다음 할 일:
```

---

## 2026-08-16
- 진행한 작업: DEVPLAN/CLAUDE/README/DEVLOG 4종 문서 작성 완료 (Claude 웹챗 단계).
  기술문서(`기술문서_부동산통계 Open API 서비스_240905.docx`) 분석 완료.
- 확인된 사실:
  - 이 API는 통계별 고정 엔드포인트가 아니라 STATBL_ID로 분기하는 3개 공용 엔드포인트 구조.
  - 인증키는 R-ONE 사이트 자체 발급 필요 (공공데이터포털 키와 별개일 가능성 높음).
  - 에러코드 체계는 서울시(INFO-000/ERROR-3xx/5xx/6xx)와 유사하나 세부 코드는 다름 (300/290/336/337/333/310/500/600/601).
- 확인 필요 / 미해결 (Claude Code가 실측할 항목 — DEVPLAN.md 2절 참고):
  1. STATBL_ID 생략 시 전체 통계표 목록 조회 가능 여부
  2. 통계표를 "이름"으로 찾는 구체적 방법 확정
  3. DTACYCLE_CD별 시점 포맷(YY/HY/QY/MM/WK) 실제 동작 확인
  4. "부동산거래현황", "시세/가격지수" 관련 실제 STATBL_ID 후보 확보
  5. 선택 파라미터 부분 채움 시 500 에러 재현 여부
- 다음 할 일: 사용자가 mcp-docs 폴더에 문서 저장 → 부트스트랩 스크립트 실행 → Claude Code가
  CLAUDE.md 기준으로 위 실측 항목부터 검증하며 구현 시작.

## 2026-08-16 (2)
- 진행한 작업: `requirements.txt`, `reb_api.py`, `server.py`, `Dockerfile`, `fly.toml` 구현.
  `.env`에 이미 REB_API_KEY가 있어(앞 4자리 dc3b..., 길이 32) 실제 키로 실측 진행.
  `.env.example`의 잘못된 변수명(SEOUL_API_KEY, 다른 프로젝트 잔재)을 REB_API_KEY로 수정.
- 확인된 사실 (실측 결과):
  1. **STATBL_ID 생략 시 전체 목록 조회 가능**: `SttsApiTbl.do`를 파라미터 없이 호출하면
     INFO-000과 함께 전체 738건(2026-08-16 기준) 목록이 페이징되어 반환됨.
  2. **이름으로 찾는 법 확정**: 전체 목록을 1회 캐시 후 STATBL_NM 문자열 포함 매칭으로 필터링.
     `search_statistics` 툴로 구현.
  3. **DTACYCLE_CD 포맷 실측**: MM(예: A_2024_00178, 202301)과 YY(예: A_2024_00900, 2022)
     모두 DEVPLAN 표대로 정상 동작 확인. WRTTIME_DESC 필드로 사람이 읽기 쉬운 시점 설명도
     함께 반환됨(예: "2023년 1월").
  4. **거래/매매/가격 관련 STATBL_ID 후보 확보**: 키워드 매칭으로 340건 확보, README.md에
     대표 7건 기록 (A_2024_00178, A_2024_00180, A_2024_00176, A_2024_00900, A_2024_00175,
     A_2024_00162, T247493131863202).
  5. **선택 파라미터 부분 채움 이슈 없음**: (a) CLS_ID만 채움(유효값) → 정상 데이터 반환,
     (b) 필수값 생략(STATBL_ID 없음) → ERROR-300 정상 반환, (c) 존재하지 않는 CLS_ID만
     채움 → 500이 아니라 INFO-200(데이터 없음) 정상 반환. 서울시 API 사례 같은 500 재현 없음.
  6. **(중요, 문서에 없던 이슈) `Type=json` 응답 인코딩 버그 발견**: `Type=json`으로 요청하면
     한글 필드(STATBL_NM 등)가 복구 불가능한 손상 바이트(U+FFFD 유발)로 반환됨. 반면 `Type`을
     생략한 기본 XML 응답은 UTF-8 정상. 원인은 서버 측 문제로 판단, 클라이언트에서 우회 불가.
     → **대응: `reb_api.py`는 항상 XML(Type 파라미터 미지정)만 사용**하도록 구현.
  7. **(중요) 응답 루트 구조가 정상/에러 시 다름**: 정상 또는 빈결과(INFO-200)는
     `<엔드포인트명><head><RESULT>...`, 필수값 누락 등 에러(ERROR-300)는 `<head>` 없이
     루트가 바로 `<RESULT>`. `reb_api._call`에서 두 경우 모두 파싱하도록 처리.
  8. `SttsApiTblItm.do`(그룹/분류/항목 조회)도 정상 동작 확인 — A_2024_00178의 "분류"
     항목으로 전국(500001)/수도권(500002)/지방(500003)/서울(500007) 등 29건 반환.
- 확인 필요 / 미해결: 없음 (DEVPLAN 2절 5개 항목 전부 검증 완료).
- 다음 할 일: FastMCP 서버 스모크 테스트(완료 — initialize 200 OK, 3개 툴 정상 노출),
  git add/commit/push 후 CLAUDE.md 4절 안내 문구 출력하고 정지.

## 2026-08-17
- 진행한 작업: DEVPLAN.md 4절 정정(2026-08-16, "공개 무인증 서버이므로 rate limit 예외 아님")에
  따라 CLAUDE.md 2-7절 기준 rate limit 미들웨어를 `server.py`에 추가.
  Starlette `BaseHTTPMiddleware`로 구현, `mcp.http_app(middleware=[...])`가 받는
  `middleware: list[ASGIMiddleware]` 파라미터를 통해 `mcp.run(..., middleware=[Middleware(RateLimitMiddleware)])`
  형태로 주입(FastMCP 3.4.5, `run`/`run_async`가 `**transport_kwargs`를 `http_app`으로 그대로 전달함을
  코드 확인 후 적용).
- 규칙 구현 내용:
  - 분당 3회 초과 시 429 (`{"error":"rate_limited",...}`)
  - 1시간 내 429가 5회 발생하면 해당 IP 24시간 차단 (`{"error":"blocked",...}`)
  - 일일 30회 제한 (초과 시 마찬가지로 429, violation으로 카운트)
  - IP 추출: `X-Forwarded-For` 헤더의 첫 값 사용 (fly.io 프록시 뒤에서 동작 전제, 헤더 없으면
    `request.client.host` fallback)
  - 저장소: in-memory (`dict[str, deque[float]]`), 서버 프로세스 생명주기 동안만 유지, 재시작 시 리셋
- 확인된 사실 (로컬 실측 결과, PORT=8099 임시 인스턴스):
  1. 정상 호출(분당 3회 이내) → `initialize` 요청에 200 정상 응답 확인.
  2. 같은 IP로 4번째, 5번째 연속 요청 → 429 확인, 바디 `{"error":"rate_limited","message":"분당 요청 제한(3회)을 초과했습니다."}` 확인.
  3. `X-Forwarded-For` 헤더로 다른 IP(9.9.9.9)를 준 요청은 별도 쿼터로 취급되어 200 정상 응답
     → IP별 격리 정상 동작 확인.
  4. 24시간 차단 로직(1시간 내 429 5회) 및 일일 30회 제한은 시간 스케일 문제로 이번 세션에서
     실시간 재현 테스트는 생략(로직 리뷰로 확인) — **확인 필요로 기록**. 실제 운영 중 위반이
     누적되면 `_violation_log`/`_blocked_until` 딕셔너리 상태로 fly.io 로그에서 관찰 가능.
- 확인 필요 / 미해결:
  - 24시간 차단 및 일일 30회 제한의 실시간(long-duration) 재현 테스트는 미실시 (로직 검토로 대체).
  - fly.io 멀티머신 환경에서는 in-memory 저장소가 머신마다 분리되므로, 머신 간 rate limit이
    공유되지 않음 (설계상 허용된 단순화 — CLAUDE.md "확실하지 않으면 기본값 1개로 구현" 원칙 적용).
- 다음 할 일: git add/commit/push 완료 후 CLAUDE.md 5절 안내 문구 출력하고 정지.

## 2026-08-17 (2)
- 진행한 작업: 실제 배포 후 `flyctl logs` 확인 결과, Claude.ai 커넥터 연결 시도 자체가 429로
  차단되는 문제 발견 → 원인 분석 후 `server.py`의 `RateLimitMiddleware`에 경로 예외 처리 추가.
- 원인: Claude.ai가 MCP 서버에 연결할 때 OAuth 핸드셰이크로 `GET /.well-known/oauth-authorization-server`
  (및 관련 `.well-known` 디스커버리 경로), `POST /register`(동적 클라이언트 등록)를 자동으로
  먼저 호출하는데, 기존 미들웨어는 모든 경로에 동일하게 분당 3회 제한을 적용하고 있었다.
  커넥터가 연결/재연결할 때마다 이 핸드셰이크 경로를 여러 번 호출하면서 자체적으로 3회 한도를
  넘겨 정상적인 연결 시도 자체가 429로 막히는 문제였다. 이 경로들은 실제 API 데이터 조회
  (`POST /mcp`)가 아니라 프로토콜 수준의 인증/디스커버리 절차이므로 rate limit 대상이 아니다.
- 수정 내용: `_is_rate_limit_exempt(path)` 함수를 추가해 `RateLimitMiddleware.dispatch`
  진입 시 가장 먼저 확인 — `path.startswith("/.well-known/")` 또는 `path == "/register"`인
  경우 카운트/차단 로직을 전혀 거치지 않고 즉시 `call_next(request)`로 통과시킨다.
  실제 데이터 요청 경로(`/mcp`)는 기존 로직(분당 3회, 일일 30회, 위반 누적 24시간 차단) 그대로 유지.
- 확인된 사실 (로컬 실측 결과, `starlette.testclient.TestClient`로 미들웨어 단위 테스트):
  1. `/.well-known/oauth-authorization-server`에 10회 연속 요청 → 전부 200, 한 번도 429 없음
     (예외 처리 전이었다면 4번째 요청부터 429였을 것).
  2. `POST /register`에 10회 연속 요청 → 전부 200, 한 번도 429 없음.
  3. 예외 대상이 아닌 `/mcp` 경로는 기존과 동일하게 3회까지 200, 4번째부터 429 확인
     → 예외 처리가 실제 데이터 요청 경로의 rate limit 자체는 약화시키지 않음을 확인.
- 확인 필요 / 미해결: 없음.
- 다음 할 일: git add/commit/push 완료. 배포는 사용자가 직접 `flyctl deploy` 수행.

## 2026-08-17 (3)
- 진행한 작업: `flyctl logs`에서 재차 확인된 429 오탐 이슈에 대해, 실제로 배포된 커밋(f5831d6)의
  `server.py`를 로컬에서 `python server.py`로 직접 기동(PORT=8123, TestClient가 아닌 실 HTTP
  서버)한 뒤 `curl`로 세 가지 재현 테스트 수행. 코드 변경은 없음 — 기존 예외 처리(`_is_rate_limit_exempt`)가
  실제 서버 프로세스에서도 의도대로 동작하는지 재검증하는 것이 목적.
- 확인된 사실 (실 HTTP 재현 결과):
  1. `GET /.well-known/oauth-authorization-server` 연속 6회 호출 → 전부 404 (rate limit
     미들웨어를 통과해 라우팅 단계까지 갔으나 해당 경로에 매핑된 핸들러가 없어 404 — 이 서버는
     FastMCP 기본 앱이라 OAuth 디스커버리 라우트 자체를 구현하지 않음. 핵심은 6회 모두 429가
     아니라는 점: rate limit에 걸리지 않고 통과함을 확인).
  2. `POST /register` 연속 6회 호출 → 전부 404, 마찬가지로 429 없음. rate limit 예외 정상 동작.
  3. `POST /mcp`(initialize 요청) 연속 5회 호출 → 1~3회차 200, 4~5회차 429
     (`{"error":"rate_limited","message":"분당 요청 제한(3회)을 초과했습니다."}`) 확인.
     실제 데이터 요청 경로의 rate limit 자체는 이번 예외 처리로 약화되지 않음을 재확인.
- 확인 필요 / 미해결: `/.well-known/*`, `/register`가 404를 반환하는 것은 rate limit과는 별개
  이슈로, Claude.ai 커넥터가 이 경로들에서 정상적인 OAuth 흐름을 기대한다면 404 자체가 연결
  실패 원인이 될 수 있음. 다만 이번 작업 범위는 "rate limit이 이 경로를 막지 않는지"였고 이는
  확인됨. OAuth 라우트 미구현 여부는 별도 확인 필요 항목으로 남김 (fly.io 배포본에서 실제
  Claude.ai 연결이 성공하는지 사용자 측 확인 필요).
- 다음 할 일: 코드 변경 없음(이미 커밋된 f5831d6로 충분) — 커밋할 내용 없어 git push 생략.
  사용자는 기존 배포본(f5831d6 반영본)이 fly.io에 이미 배포되어 있는지 확인 필요.

# CLAUDE.md — realestate-stats-mcp (한국부동산원 R-ONE 부동산통계 MCP)

## 0. 절대 규칙

- **DEVPLAN.md 하나만 먼저 읽고 시작한다.** 다른 문서 재탐색 금지.
- **웹서치 금지.** API 스펙은 DEVPLAN.md에 이미 있다. STATBL_ID 후보를 찾아야 할 때도 웹서치가 아니라
  R-ONE API(`SttsApiTbl.do`) 자체를 호출해서 확보한다.
- 불확실하면 추측성 재설계 대신 기본값 1개로 구현 후 DEVLOG.md에 "확인 필요"로 기록한다.
- 동일 오류 최대 3회까지만 재시도한다. 3회 실패 시 기록하고 사용자에게 보고한다.
- **역할은 "코드 구현 + 로컬 실측 테스트"까지다.** `fly launch`, `fly secrets set`, `flyctl deploy`,
  `fly logs` 등 fly.io 관련 명령은 절대 스스로 실행하지 않는다. 배포는 사용자가 PowerShell에서
  직접 수행한다.
- 배포 준비(코드 구현, 로컬 테스트, git commit/push)가 끝나면 아래 "작업 순서"의 정지 시점에서
  멈추고, 마지막 절의 "사용자 안내 문구"를 그대로 출력한다.

---

## 1. 이 프로젝트 고유 컨텍스트 (DEVPLAN.md 요약 — 반드시 숙지)

이 MCP는 서울시류 API와 달리 **범용 통계조회 구조**다. "부동산거래현황"이라는 고정 엔드포인트는
없고, 통계표코드(STATBL_ID)로 원하는 통계를 지정하는 3개 공용 엔드포인트(`SttsApiTbl.do`,
`SttsApiTblItm.do`, `SttsApiTblData.do`)를 재사용한다. 툴도 딱 3개(`search_statistics`,
`get_statistics_items`, `get_statistics_data`)만 만든다 — 통계표별로 툴을 늘리지 않는다.

인증키 이름: `REB_API_KEY` (R-ONE 사이트에서 별도 발급, 공공데이터포털 키와 다를 수 있음 — 사용자가
어느 키를 넣었는지 실측 전 반드시 1회 확인).

---

## 2. 기술적으로 반드시 적용할 것

### 2-1. `.env`
BOM 문제로 `python-dotenv`가 키를 못 읽는 사례가 있었다. `.env`를 새로 쓸 때는 항상
UTF-8(BOM 없음)으로 저장한다.

### 2-2. `server.py`의 `mcp.run()`
항상 `stateless_http=True`를 포함한다:
```python
mcp.run(transport="streamable-http", host="0.0.0.0", port=port, stateless_http=True)
```
이 옵션이 없으면 fly.io 멀티머신 환경에서 세션 라우팅 문제로 커넥터가 "사용 가능한 도구 없음"으로
보이는 문제가 발생한다. 절대 빠뜨리지 않는다.

### 2-3. API 키 취급
- 실제 키 값은 코드에 하드코딩하지 않고 항상 `os.environ`으로 읽는다.
- `.env`를 갱신했다고 사용자가 말하면, 재테스트 전에 실제로 값이 바뀌었는지 파일 크기나 값의
  앞 몇 글자로 확인한다.
- 키를 표준출력에 그대로 찍지 않는다. 필요하면 앞 4자리 + `...` + 길이만 마스킹해서 출력한다.
- 재테스트 요청을 받으면 "이전과 동일한 키인지, 새 키인지"를 먼저 확인한다.
- **이 프로젝트 고유 주의**: R-ONE 키와 공공데이터포털 키를 혼동할 수 있다. 인증 에러(코드 290)가
  나면 가장 먼저 "R-ONE 사이트에서 직접 발급받은 키가 맞는지"부터 확인한다.

---

## 3. 작업 순서

1. `requirements.txt` (`fastmcp`, `httpx`, `python-dotenv`)
2. `reb_api.py` — R-ONE API 호출 + 에러코드 매핑(DEVPLAN 1-6절) + 전체 통계표 목록 캐싱/검색 로직
   - `SttsApiTbl.do`를 STATBL_ID 없이 호출했을 때의 실제 동작을 가장 먼저 실측(DEVPLAN 2절 항목1)
   - 전체 목록이 많으면(예상: 수백 건) pIndex/pSize로 페이징 전량 수집 → 인메모리 캐시.
     캐시 TTL은 서버 프로세스 생명주기 동안 유지(간단하게, 재시작 시 리셋 허용).
3. `server.py` — 툴 3개 정의(`search_statistics`, `get_statistics_items`, `get_statistics_data`),
   docstring에 각 필드 설명 + 단위(UI_NM) + DTACYCLE_CD별 시점 포맷 표 반드시 명시,
   `stateless_http=True` 필수 반영.
   - 이 서버는 사용자 개인 API 키 기반 배포이므로 2-7 rate limit 미들웨어는 생략해도 된다
     (DEVPLAN 4절 참고 — 공개 무인증 서버가 아님).
4. `.env.example`, `.gitignore`
5. 로컬 테스트 (실제 키로 각 툴 호출)
   - **DEVPLAN.md 2절의 실측 필요 항목 5개를 전부 확인**하고 결과를 DEVLOG.md에 기록:
     1) STATBL_ID 생략 시 목록 조회 가능 여부
     2) 이름으로 통계표 찾는 방법 확정
     3) DTACYCLE_CD별 시점 포맷 최소 2개(YY, MM) 실측
     4) "거래", "매매", "가격" 관련 STATBL_ID 후보 최소 3~5개 확보해서 DEVLOG.md에 목록 기록
        (사용자가 이후 원하는 통계를 바로 쓸 수 있도록)
     5) 선택 파라미터 부분 채움 시 500 에러 재현 여부 (조합별 최소 3가지: 일부만/전부/전부생략)
   - 5번에서 문제가 재현되면 절차대로: 재현 확인(2회 이상) → 원인 분리 → DEVLOG 기록 →
     `reb_api.py`에 사전 검증 로직 추가(예: `ERROR-CLIENT-PARTIAL-PARAMS`) → README/DEVPLAN 갱신
6. FastMCP 서버 스모크 테스트 (initialize 요청까지만)
7. `Dockerfile`, `fly.toml`
8. README/DEVLOG 갱신 — 특히 실측으로 확인된 "STATBL_ID 찾는 법", "시점 포맷", "부분 채움 제약
   여부"는 명세서 문구가 아니라 실제 동작 기준으로 정확히 기술
9. `git add/commit/push`까지 수행 (자동 진행 가능 — private 저장소 백업일 뿐)
10. **여기서 정지** — 아래 4절 "사용자 안내 문구"를 그대로 출력

---

## 4. 하지 말 것

- 툴 개수를 3개(search_statistics / get_statistics_items / get_statistics_data)보다 늘리지 않기.
  특정 통계표 전용 툴을 따로 만들지 않는다 (예: "get_apt_price_index" 같은 개별 툴 금지 — 범용
  구조가 이 프로젝트의 핵심 설계 원칙).
- 인증키 하드코딩 금지
- `stateless_http=True` 누락 금지
- `fly launch` / `fly secrets set` / `flyctl deploy` / `fly logs` 자동 실행 금지
- 매 파일 생성마다 개별 승인이 반복되면, 사용자에게 "이번 세션 전체 편집 허용"으로 넘어가라고 첫
  승인 시점에 안내한다 (단, 실제 API 키로 네트워크 호출하는 `python -c` 류는 매번 개별 확인 권장)

---

## 5. 정지 시 출력할 사용자 안내 문구

```
1) PowerShell에서 프로젝트 폴더로 이동 후 배포를 진행하세요:
   cd "C:\Users\hwang\Projects\realestate-stats-mcp"
   fly launch --no-deploy

2) fly secrets set REB_API_KEY=발급받은키
   (R-ONE 사이트에서 직접 발급받은 키를 사용하세요 — 공공데이터포털 키와 다를 수 있습니다)

3) flyctl deploy

4) 배포 완료 메시지에 나온 주소 뒤에 "/mcp"를 붙여서
   Claude.ai > 설정 > 커넥터 에서 연결하세요.
   예: https://<앱이름>.fly.dev/mcp

5) 연결 후 반드시 "새 대화창"을 열어서 "사용 가능한 도구" 목록에
   search_statistics / get_statistics_items / get_statistics_data 가 뜨는지 확인하세요.
```

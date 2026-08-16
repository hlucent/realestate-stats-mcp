# DEVPLAN.md — 한국부동산원(R-ONE) 부동산통계 API MCP

## 0. 이 프로젝트의 성격 (중요 — 반드시 먼저 읽을 것)

이 API는 서울시 오픈API류(엔드포인트별 고정 응답 구조)와 다르다.
**"부동산거래현황", "아파트매매가격지수", "지가변동률" 같은 개별 통계는 각각 별도 엔드포인트가 아니라,
딱 3개의 공용 엔드포인트를 통계표코드(STATBL_ID)로 분기해서 재사용하는 구조**다.

그래서 이 MCP는 "부동산거래현황 MCP"처럼 특정 통계 하나만 다루는 게 아니라,
**범용 통계조회 MCP 1개**로 만든다 — 사용자가 원하는 통계표를 이름/키워드로 찾고,
조건(기간, 지역 등)을 지정해 실제 수치를 가져오는 것까지 전부 이 MCP 하나가 담당한다.

- 제공기관: 한국부동산원 (R-ONE)
- API 서비스 URL 베이스: `https://www.reb.or.kr/r-one/openapi`
- 인증 방식: `KEY` 쿼리파라미터 (ServiceKey 방식)
- 데이터 포맷: XML 또는 JSON (`Type` 파라미터로 지정, JSON 사용 권장)
- 비용: 무료
- 문서 출처: `기술문서_부동산통계 Open API 서비스_240905.docx` (공공데이터포털 제공)

---

## 1. API 스펙 요약

### 1-1. 공용 엔드포인트 3개

| 상세기능명 | 엔드포인트 | 역할 |
|---|---|---|
| 서비스 통계목록 | `GET /SttsApiTbl.do` | 통계표(STATBL_ID) 목록/검색 |
| 통계 세부항목 목록 | `GET /SttsApiTblItm.do` | 특정 통계표의 그룹/분류/항목 코드 조회 |
| 통계 조회 조건 설정(=실제 데이터) | `GET /SttsApiTblData.do` | 실제 통계 수치 조회 |

전체 URL 형태: `https://www.reb.or.kr/r-one/openapi/{엔드포인트}?KEY=인증키&...`

### 1-2. 공통 기본 파라미터 (3개 엔드포인트 모두 동일)

| 파라미터 | 설명 | 필수 | 기본값 |
|---|---|---|---|
| KEY | 인증키 | 필수 | - |
| Type | 응답 포맷 (xml/json) | 옵션 | xml → **MCP에서는 항상 json 고정 사용** |
| pIndex | 페이지 위치 | 옵션 | 1 |
| pSize | 페이지당 요청 건수 | 옵션 | 100 (최대 1,000 — 에러코드 336 참고) |

### 1-3. ① 서비스 통계목록 (`SttsApiTbl.do`)

**요청 파라미터**

| 파라미터 | 설명 | 크기 | 구분 | 예시 |
|---|---|---|---|---|
| STATBL_ID | 통계표ID | 50 | 옵션(0) | A_2024_00900 |

- STATBL_ID를 생략하면 전체 통계표 목록이 나올 것으로 추정됨(문서에 명시 없음 — **실측 필요**).
  이 동작이 "검색으로 통계표 찾기" 기능의 핵심이므로 실측 최우선 항목.

**응답 필드**

| 필드 | 설명 |
|---|---|
| STATBL_ID | 통계표ID |
| STATBL_NM | 통계표명 (예: "(연) 지역별 지가지수") |
| DTACYCLE_CD | 주기코드 (YY/HY/QY/MM/WK) |
| DTACYCLE_NM | 주기명 (매년/반기 등) |
| STAT_ID | 통계메타ID |
| TOP_ORG_NM | 제공기관 |
| OPEN_STATE | 공개여부 (Y/N) |
| DATA_START_YY / DATA_END_YY | 통계자료 시작/종료 연도 |
| STATBL_IDTFR | 통계표주석 식별자 |
| STATBL_CMMT | 통계표 주석(문의처 등) |
| V_ORDER | 출력순서 |

### 1-4. ② 통계 세부항목 목록 (`SttsApiTblItm.do`)

**요청 파라미터**

| 파라미터 | 설명 | 크기 | 구분 | 예시 |
|---|---|---|---|---|
| STATBL_ID | 통계표ID | 50 | **필수(1)** | A_2024_00900 |
| ITM_TAG | 항목정보 구분 (그룹/분류/항목 중 하나) | 5 | 옵션(0) | 분류 |

**응답 필드**: STATBL_ID, ITM_TAG, ITM_ID, PAR_ITM_ID(상위항목ID), ITM_NM(항목명), ITM_FULLNM(항목전체명),
UI_NM(단위명), ITM_CMMT_IDTFR, ITM_CMMT_CONT, V_ORDER

이 엔드포인트로 지역 코드(CLS_ID 등)를 미리 조회해야 ③에서 지역 필터링이 가능하다.
예: "종로구"의 CLS_ID가 510008이라는 걸 이 엔드포인트로 먼저 알아내야 함.

### 1-5. ③ 통계 조회 조건 설정 = 실제 데이터 조회 (`SttsApiTblData.do`)

**요청 파라미터**

| 파라미터 | 설명 | 크기 | 구분 | 예시 |
|---|---|---|---|---|
| STATBL_ID | 통계표ID | 50 | **필수(1)** | A_2024_00900 |
| DTACYCLE_CD | 주기코드 | 50 | **필수(1)** | YY |
| WRTTIME_IDTFR_ID | 자료작성 시점(특정 시점 단건 조회용) | 8 | 옵션(0) | - |
| GRP_ID | 그룹ID | 8 | 옵션(0) | - |
| CLS_ID | 분류ID (지역 등) | 8 | 옵션(0) | 510008 |
| ITM_ID | 항목ID | 8 | 옵션(0) | - |
| START_WRTTIME | 조회 시작 시점 | 8 | 옵션(0) | 2022 |
| END_WRTTIME | 조회 종료 시점 | 8 | 옵션(0) | 2023 |

**⚠️ 실측 필요 — 파라미터 형식은 DTACYCLE_CD 값에 따라 완전히 달라짐**

| 주기코드 | WRTTIME/START/END 형식 | 예시 |
|---|---|---|
| YY(년) | YYYY | 2022, 2024 |
| HY(반기) | YYYY0X (X=1 or 2) | 202301, 202302 |
| QY(분기) | YYYY0X (X=1~4) | 202301, 202304 |
| MM(월) | YYYYMM | 202301, 202312 |
| WK(주) | YYYYWW | 202301, 202353 |

**응답 필드**: STATBL_ID, DTACYCLE_CD, WRTTIME_IDTFR_ID, GRP_ID, GRP_NM, GRP_FULLNM,
CLS_ID, CLS_NM, CLS_FULLNM, ITM_ID, ITM_NM, ITM_FULLNM, **DTA_VAL(통계 자료값)**, **UI_NM(단위명 — 반드시 함께 표시)**

### 1-6. 에러 코드

| 구분 | 코드 | 설명 |
|---|---|---|
| ERROR | 300 | 필수 값 누락 |
| ERROR | 290 | 인증키 유효하지 않음 |
| ERROR | 336 | 1회 최대 1,000건 초과 요청 |
| ERROR | 337 | 일별 트래픽 제한 초과 |
| ERROR | 333 | 요청위치(pIndex) 타입 오류 (정수 아님) |
| ERROR | 310 | 서비스를 찾을 수 없음 |
| ERROR | 500 | 서버 오류 |
| ERROR | 600 | DB 연결 오류 |
| ERROR | 601 | SQL 오류 |
| INFO | 000 | 정상 처리 |
| INFO | 200 | 해당 데이터 없음 |
| INFO | 300 | 관리자에 의해 인증키 사용 제한 |

응답 XML/JSON의 `head.r.CODE`, `head.r.MESSAGE`로 확인. `INFO-000` 외에는 전부 처리 실패로 간주.

---

## 2. 실측 필요 항목 (Claude Code가 로컬 테스트 단계에서 반드시 확인 — CLAUDE.md 2-6절 절차 적용)

1. **STATBL_ID 생략 시 ①번(SttsApiTbl.do) 동작** — 전체 목록이 나오는지, 아니면 에러(300)가 나는지.
   전체 목록이 나온다면 이것이 "통계표 이름으로 검색" 기능의 기반이 됨.
   전체 목록이 안 나온다면, `STATBL_NM`에 키워드를 넣는 방식이 되는지도 함께 테스트.
2. **STATBL_ID를 모를 때 이름으로 찾는 방법**: 문서에 STATBL_NM으로 검색하는 파라미터가 별도로
   없으므로, ①을 파라미터 없이 호출해 전체를 받아온 뒤 MCP 내부에서 이름 문자열 매칭(파이썬 필터링)
   하는 방식이 유력. 실측으로 전체 목록 건수를 확인하고, 너무 많으면(예: 수백 건) pSize/pIndex로
   페이징하며 전량 수집해 로컬 캐시(파일 또는 메모리)로 들고 있는 구조를 고려.
3. **DTACYCLE_CD별 WRTTIME 포맷**이 표(1-5절)대로 실제 동작하는지 YY/MM 최소 2개 주기코드로 실측.
4. **부동산거래현황, 시세 관련 실제 STATBL_ID 확보**: 사용자가 원하는 통계표코드를 R-ONE 통계코드
   검색 페이지(`https://www.reb.or.kr/r-one/portal/openapi/openApiGuideCdPage.do`)에서 확인하거나,
   ①번 전체 목록에서 STATBL_NM에 "거래", "매매", "가격", "실거래" 등이 포함된 항목을 찾아서 사용자에게
   후보를 제시. **Claude Code가 웹서치 없이 API 호출만으로 이 목록을 확보할 것** (2-6절 원칙 준수 —
   웹서치 금지이므로 R-ONE API 자체를 호출해서 목록을 받아온다).
5. **선택 파라미터 부분 채움 이슈 여부**: 서울시 API처럼 옵션 파라미터를 일부만 채우면 500이 나는지
   조합별(예: CLS_ID만 채움 / GRP_ID+CLS_ID+ITM_ID 모두 채움 / 전부 생략) 실측. 문서에 명시된 바는
   없으나 과거 유사 사례가 있었으므로 확인 후 DEVLOG.md에 기록.

---

## 3. MCP 툴 설계 (최소 개수 원칙)

범용 구조이므로 3개 엔드포인트에 얇게 대응하는 3개 툴 + 사용 편의를 위한 헬퍼 성격의 검색 툴로 구성.
과도하게 쪼개지 않는다.

### Tool 1: `search_statistics`
- 설명: 통계표를 이름/키워드로 검색한다. 예) "아파트 매매", "지가변동률", "실거래가"
- 내부 동작: `SttsApiTbl.do`를 (실측 결과에 따라) 파라미터 없이 또는 페이징으로 호출해 전체
  통계표 목록을 가져온 뒤, STATBL_NM에 키워드가 포함된 것만 필터링해 반환.
- 반환: STATBL_ID, STATBL_NM, DTACYCLE_CD, DATA_START_YY~DATA_END_YY 요약 리스트

### Tool 2: `get_statistics_items`
- 설명: 특정 통계표(STATBL_ID)의 지역/분류/그룹 코드를 조회한다. 실제 데이터 조회 전 CLS_ID 등을
  알아내는 용도.
- 파라미터: statbl_id(필수), itm_tag(옵션: 그룹/분류/항목)
- 반환: ITM_ID, ITM_NM, ITM_FULLNM, UI_NM 리스트

### Tool 3: `get_statistics_data`
- 설명: 통계표의 실제 수치 데이터를 조회한다.
- 파라미터: statbl_id(필수), dtacycle_cd(필수), start_wrttime/end_wrttime(옵션),
  cls_id/grp_id/itm_id(옵션)
- 반환: 시점(WRTTIME_IDTFR_ID)별 DTA_VAL + UI_NM(단위) + CLS_NM/GRP_NM/ITM_NM 리스트
- docstring에 "DTACYCLE_CD 값에 따라 시점 파라미터 형식이 다름" 표(1-5절)를 그대로 명시할 것

**3개 툴 조합으로 "부동산거래현황 알려줘" 같은 자연어 요청 처리 흐름**:
1. `search_statistics("거래현황")` 또는 `search_statistics("실거래")` 로 STATBL_ID 후보 확보
2. 필요시 `get_statistics_items(statbl_id)` 로 지역 코드(CLS_ID) 확보
3. `get_statistics_data(statbl_id, dtacycle_cd, cls_id=...)` 로 실제 수치 조회

---

## 4. 기술 스택 / 디렉토리 구조

```
realestate-stats-mcp/
├── requirements.txt        # fastmcp, httpx, python-dotenv
├── reb_api.py               # R-ONE API 호출 + 에러코드 매핑 + 전체 통계표 캐시/검색 로직
├── server.py                 # MCP 툴 3개 정의, stateless_http=True 필수
├── .env.example
├── .gitignore
├── Dockerfile
├── fly.toml
├── DEVPLAN.md / CLAUDE.md / README.md / DEVLOG.md
```

- 환경변수명: `REB_API_KEY` (R-ONE 인증키. 공공데이터포털에서 별도 신청한 키와 다를 수 있음 —
  R-ONE 자체 "인증키 발급"이 필요할 수 있으므로 사용자가 실제로 어느 쪽 키를 받았는지 CLAUDE.md
  실측 단계에서 먼저 확인)
- **Rate limit 미들웨어 (정정, 2026-08-16): 반드시 적용한다.**
  최초 설계 시 "API 키를 사용자 본인이 발급받아 넣었으니 예외"로 잘못 판단했으나, CLAUDE.md
  2-7절의 예외 조건은 "**사용자가** API 키(Authorization 헤더 등)로 **인증**하는 방식의 MCP
  서버"를 말하는 것이다. 이 MCP는 REB_API_KEY를 fly.io secret으로 서버가 들고 있을 뿐,
  Claude.ai 커넥터로 붙는 사용자 쪽에는 어떤 인증도 요구하지 않는다 — 즉 fly.dev 주소만 알면
  누구나 호출 가능한 **공개 무인증 서버**이므로 예외 조건에 해당하지 않는다.
  CLAUDE.md 2-7절의 3단계 IP 기반 rate limit(분당 3회, 반복위반 시 24시간 차단, 일일 30회)을
  `server.py`에 그대로 적용한다.

---

## 5. 사용자가 먼저 할 일

1. R-ONE(한국부동산원 오픈API) 사이트에서 인증키 발급
   - `https://www.reb.or.kr/r-one/portal/openapi/openApiActKeyPage.do` (로그인 필요)
   - 주의: 공공데이터포털에서 받은 키와 **별개**일 가능성이 높음. R-ONE 사이트에서 직접 발급받은
     키를 사용할 것.
2. 발급받은 키를 로컬 개인 파일(`api-keys.env.example` 등)에 `REB_API_KEY=...` 형식으로 기록
3. 이 문서 4종(DEVPLAN/CLAUDE/README/DEVLOG)을 `mcp-docs` 폴더로 이동 (전달 직후 안내 별도 제공)

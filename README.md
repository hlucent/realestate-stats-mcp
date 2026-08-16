# realestate-stats-mcp

한국부동산원(R-ONE) 부동산통계 Open API를 위한 MCP 서버. 아파트 매매/전세가격지수, 지가변동률,
부동산 거래현황 등 R-ONE이 제공하는 수백 개 통계표를 이름으로 검색하고 실제 수치를 조회할 수 있는
**범용 통계조회 도구**입니다.

> 이 API는 통계마다 별도 엔드포인트가 있는 게 아니라, 통계표코드(STATBL_ID)로 원하는 통계를 지정해
> 조회하는 구조입니다. 그래서 이 MCP도 통계별 전용 툴이 아니라 3개의 범용 툴로 모든 통계표를
> 다룹니다.

## 제공 도구 (Tools)

### `search_statistics(keyword)`
통계표를 이름/키워드로 검색합니다. 예: "아파트 매매", "지가변동률", "실거래가"
→ STATBL_ID, 통계표명, 주기, 데이터 존재 기간을 반환합니다.

### `get_statistics_items(statbl_id, itm_tag=None)`
특정 통계표의 지역/분류/그룹 코드를 조회합니다. 실제 데이터를 조회하기 전에 지역 코드(CLS_ID)
등을 알아내는 용도입니다.

### `get_statistics_data(statbl_id, dtacycle_cd, start_wrttime=None, end_wrttime=None, cls_id=None, grp_id=None, itm_id=None)`
실제 통계 수치를 조회합니다. 단위(UI_NM)와 함께 값을 반환합니다.

**주기코드(DTACYCLE_CD)별 시점 형식**

| 주기 | 코드 | 형식 | 예시 |
|---|---|---|---|
| 년 | YY | YYYY | 2024 |
| 반기 | HY | YYYY0X (X=1,2) | 202301 |
| 분기 | QY | YYYY0X (X=1~4) | 202301 |
| 월 | MM | YYYYMM | 202401 |
| 주 | WK | YYYYWW | 202401 |

## 설치 및 실행

```bash
pip install -r requirements.txt
cp .env.example .env
# .env에 REB_API_KEY 입력 (R-ONE 사이트에서 직접 발급 — 공공데이터포털 키와 다를 수 있음)
python server.py
```

## 환경변수

| 변수명 | 설명 |
|---|---|
| `REB_API_KEY` | 한국부동산원 R-ONE 오픈API 인증키 (`https://www.reb.or.kr/r-one/portal/openapi/openApiActKeyPage.do` 에서 발급) |

## 배포 (fly.io)

```bash
fly launch --no-deploy
fly secrets set REB_API_KEY=발급받은키
flyctl deploy
```

배포 후 Claude.ai 커넥터 연결 시 주소 끝에 `/mcp`를 붙여서 연결하세요.
예: `https://realestate-stats-mcp.fly.dev/mcp`

## 실제 동작 기준 제약사항 (실측 결과로 갱신 예정)

- 1회 요청 최대 1,000건 (`ERROR-336`)
- 일별 트래픽 제한 있음 (`ERROR-337`, 초과 시 익일까지 대기)
- STATBL_ID 없이 전체 통계표 목록 조회 가능 여부: **실측 필요 (DEVLOG.md 참고)**
- 선택 파라미터 부분 채움 시 에러 발생 여부: **실측 필요 (DEVLOG.md 참고)**

## 라이선스

한국부동산원 제공 공공데이터, 이용허락범위 제한 없음(공공데이터포털 명시 기준).

## 데이터 출처

한국부동산원(REB) R-ONE 부동산통계 Open API — `https://www.reb.or.kr/r-one/openapi`

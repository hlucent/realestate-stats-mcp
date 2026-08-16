"""realestate-stats-mcp — 한국부동산원(R-ONE) 부동산통계 범용 조회 MCP 서버.

3개 공용 엔드포인트(SttsApiTbl.do / SttsApiTblItm.do / SttsApiTblData.do)를
STATBL_ID로 분기해 재사용하는 R-ONE API 구조를 그대로 반영해, 통계표별 전용 툴을
만들지 않고 딱 3개의 범용 툴로 구성한다.
"""

import os
import time
from collections import defaultdict, deque

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

import reb_api

load_dotenv()

mcp = FastMCP("realestate-stats-mcp")


# --- Rate limit 미들웨어 (CLAUDE.md 2-7절 / DEVPLAN.md 4절 — 공개 무인증 서버이므로 적용) ---
#
# 규칙:
#   - 분당 3회 초과 시 429
#   - 1시간 내 429가 5회 발생하면 해당 IP를 24시간 차단
#   - 일일 30회 제한
#   - IP는 X-Forwarded-For 헤더에서 추출 (fly.io 프록시 뒤에서 동작)
#   - in-memory 저장 (서버 프로세스 생명주기 동안만 유지, 재시작 시 리셋)
_MINUTE_LIMIT = 3
_DAILY_LIMIT = 30
_VIOLATION_LIMIT = 5
_BLOCK_SECONDS = 24 * 60 * 60
_VIOLATION_WINDOW_SECONDS = 60 * 60

_request_log: dict[str, deque[float]] = defaultdict(deque)
_violation_log: dict[str, deque[float]] = defaultdict(deque)
_blocked_until: dict[str, float] = {}


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _is_rate_limit_exempt(path: str) -> bool:
    """OAuth 핸드셰이크 경로(.well-known 디스커버리, 동적 클라이언트 등록)는
    Claude.ai 연결 시마다 자동 호출되며 실제 데이터 조회가 아니므로 rate limit에서 제외한다."""
    return path.startswith("/.well-known/") or path == "/register"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if _is_rate_limit_exempt(request.url.path):
            return await call_next(request)

        ip = _client_ip(request)
        now = time.time()

        blocked_at = _blocked_until.get(ip)
        if blocked_at is not None:
            if now < blocked_at:
                return JSONResponse(
                    {"error": "blocked", "message": "반복적인 요청 제한 위반으로 24시간 차단되었습니다."},
                    status_code=429,
                )
            del _blocked_until[ip]
            _violation_log.pop(ip, None)

        req_times = _request_log[ip]
        while req_times and now - req_times[0] > _VIOLATION_WINDOW_SECONDS * 24:
            req_times.popleft()

        minute_count = sum(1 for t in req_times if now - t <= 60)
        daily_count = sum(1 for t in req_times if now - t <= 24 * 60 * 60)

        limited = False
        message = ""
        if minute_count >= _MINUTE_LIMIT:
            limited = True
            message = "분당 요청 제한(3회)을 초과했습니다."
        elif daily_count >= _DAILY_LIMIT:
            limited = True
            message = "일일 요청 제한(30회)을 초과했습니다."

        if limited:
            violations = _violation_log[ip]
            violations.append(now)
            while violations and now - violations[0] > _VIOLATION_WINDOW_SECONDS:
                violations.popleft()
            if len(violations) >= _VIOLATION_LIMIT:
                _blocked_until[ip] = now + _BLOCK_SECONDS
            return JSONResponse({"error": "rate_limited", "message": message}, status_code=429)

        req_times.append(now)
        return await call_next(request)


@mcp.tool()
def search_statistics(keyword: str) -> dict:
    """통계표를 이름 키워드로 검색한다 (예: "아파트 매매", "지가변동률", "실거래", "전세").

    한국부동산원(R-ONE)이 제공하는 전체 통계표(738건, 2026-08 기준) 중 통계표명(STATBL_NM)에
    키워드가 포함된 항목만 반환한다. 여기서 얻은 STATBL_ID와 DTACYCLE_CD를
    get_statistics_items / get_statistics_data 호출에 사용한다.

    Args:
        keyword: 통계표명에서 찾을 검색어 (예: "매매", "전세", "지가")

    Returns:
        results: 통계표 목록. 각 항목은 다음 필드를 포함한다.
            - STATBL_ID: 통계표ID (다음 툴 호출에 사용)
            - STATBL_NM: 통계표명
            - DTACYCLE_CD: 주기코드 (YY=년, HY=반기, QY=분기, MM=월, WK=주.
              쉼표로 여러 개인 경우 해당 통계표가 여러 주기를 모두 지원함)
            - DTACYCLE_NM: 주기명 (한글)
            - DATA_START_YY / DATA_END_YY: 통계 자료 시작/종료 연도
            - RPSTUI_NM: 대표 단위/기준시점 설명 (있는 경우)
        count: 검색된 통계표 수
    """
    rows = reb_api.search_statistics_tables(keyword)
    results = [
        {
            "STATBL_ID": r.get("STATBL_ID"),
            "STATBL_NM": r.get("STATBL_NM"),
            "DTACYCLE_CD": r.get("DTACYCLE_CD"),
            "DTACYCLE_NM": r.get("DTACYCLE_NM"),
            "DATA_START_YY": r.get("DATA_START_YY"),
            "DATA_END_YY": r.get("DATA_END_YY"),
            "RPSTUI_NM": r.get("RPSTUI_NM"),
        }
        for r in rows
    ]
    return {"count": len(results), "results": results}


@mcp.tool()
def get_statistics_items(statbl_id: str, itm_tag: str | None = None) -> dict:
    """특정 통계표의 그룹/분류/항목 코드를 조회한다.

    실제 데이터를 조회하기 전에, 원하는 지역(예: "종로구")이나 항목의 CLS_ID/ITM_ID/GRP_ID를
    알아내는 용도로 사용한다. 예: "종로구"의 CLS_ID가 510008이라는 것을 이 툴로 먼저 확인한 뒤
    get_statistics_data 호출 시 cls_id 파라미터로 넘긴다.

    Args:
        statbl_id: search_statistics로 확보한 통계표ID (필수)
        itm_tag: 항목정보 구분 필터. "그룹" / "분류" / "항목" 중 하나 (옵션, 생략 시 전체 반환)

    Returns:
        results: 항목 목록. 각 항목은 다음 필드를 포함한다.
            - ITM_TAG: 그룹/분류/항목 구분
            - ITM_ID: 항목ID (get_statistics_data의 grp_id/cls_id/itm_id에 사용)
            - PAR_ITM_ID: 상위항목ID
            - ITM_NM / ITM_FULLNM: 항목명 / 항목전체명 (예: "종로구" / "서울>종로구")
            - UI_NM: 단위명
        count: 항목 수
    """
    rows = reb_api.get_statistics_items(statbl_id, itm_tag)
    results = [
        {
            "ITM_TAG": r.get("ITM_TAG"),
            "ITM_ID": r.get("ITM_ID"),
            "PAR_ITM_ID": r.get("PAR_ITM_ID"),
            "ITM_NM": r.get("ITM_NM"),
            "ITM_FULLNM": r.get("ITM_FULLNM"),
            "UI_NM": r.get("UI_NM"),
        }
        for r in rows
    ]
    return {"count": len(results), "results": results}


@mcp.tool()
def get_statistics_data(
    statbl_id: str,
    dtacycle_cd: str,
    start_wrttime: str | None = None,
    end_wrttime: str | None = None,
    wrttime_idtfr_id: str | None = None,
    grp_id: str | None = None,
    cls_id: str | None = None,
    itm_id: str | None = None,
) -> dict:
    """통계표의 실제 수치 데이터를 조회한다.

    DTACYCLE_CD 값에 따라 시점(wrttime) 파라미터의 형식이 완전히 다르므로 반드시 아래 표를
    따른다 (start_wrttime / end_wrttime / wrttime_idtfr_id 공통):

        | 주기코드(dtacycle_cd) | 형식      | 예시              |
        |------------------------|-----------|-------------------|
        | YY (년)                | YYYY      | 2022, 2024        |
        | HY (반기)              | YYYY0X (X=1,2) | 202301, 202302 |
        | QY (분기)              | YYYY0X (X=1~4) | 202301, 202304 |
        | MM (월)                | YYYYMM    | 202301, 202312    |
        | WK (주)                | YYYYWW    | 202301, 202353    |

    grp_id/cls_id/itm_id는 get_statistics_items로 미리 조회해 확보한다 (예: 지역 필터는 cls_id).
    이 파라미터들은 일부만 채워도 정상 동작한다 (실측 확인됨 — 부분 채움으로 인한 500 에러 없음).

    Args:
        statbl_id: 통계표ID (필수)
        dtacycle_cd: 주기코드. YY/HY/QY/MM/WK 중 하나 (필수)
        start_wrttime: 조회 시작 시점 (옵션, 형식은 위 표 참고)
        end_wrttime: 조회 종료 시점 (옵션, 형식은 위 표 참고)
        wrttime_idtfr_id: 특정 시점 단건 조회용 (옵션, 형식은 위 표 참고)
        grp_id: 그룹ID 필터 (옵션)
        cls_id: 분류ID 필터, 주로 지역 코드 (옵션)
        itm_id: 항목ID 필터 (옵션)

    Returns:
        results: 데이터 목록. 각 항목은 다음 필드를 포함한다.
            - WRTTIME_IDTFR_ID / WRTTIME_DESC: 자료 시점 (원본 코드 / 사람이 읽기 쉬운 설명)
            - CLS_NM / CLS_FULLNM: 분류명 (예: 지역명)
            - GRP_NM: 그룹명
            - ITM_NM / ITM_FULLNM: 항목명
            - DTA_VAL: 통계 자료값
            - UI_NM: 단위명 (DTA_VAL과 함께 반드시 표시할 것)
        count: 데이터 건수 (0이면 해당 조건의 데이터 없음 — 파라미터 조합을 재확인)
    """
    rows = reb_api.get_statistics_data(
        statbl_id=statbl_id,
        dtacycle_cd=dtacycle_cd,
        start_wrttime=start_wrttime,
        end_wrttime=end_wrttime,
        wrttime_idtfr_id=wrttime_idtfr_id,
        grp_id=grp_id,
        cls_id=cls_id,
        itm_id=itm_id,
    )
    results = [
        {
            "WRTTIME_IDTFR_ID": r.get("WRTTIME_IDTFR_ID"),
            "WRTTIME_DESC": r.get("WRTTIME_DESC"),
            "CLS_NM": r.get("CLS_NM"),
            "CLS_FULLNM": r.get("CLS_FULLNM"),
            "GRP_NM": r.get("GRP_NM"),
            "ITM_NM": r.get("ITM_NM"),
            "ITM_FULLNM": r.get("ITM_FULLNM"),
            "DTA_VAL": r.get("DTA_VAL"),
            "UI_NM": r.get("UI_NM"),
        }
        for r in rows
    ]
    return {"count": len(results), "results": results}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=port,
        stateless_http=True,
        middleware=[Middleware(RateLimitMiddleware)],
    )

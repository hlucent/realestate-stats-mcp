"""R-ONE(한국부동산원) 부동산통계 Open API 클라이언트.

실측으로 확인된 사항 (DEVLOG.md 참고):
- Type=json 요청 시 서버가 한글을 깨진 바이트로 반환하는 버그가 있어, 이 클라이언트는
  항상 기본(XML) 응답을 사용하고 XML을 파싱해 dict로 변환한다.
- 정상 처리 시 루트 태그는 엔드포인트명(예: <SttsApiTblData>)이고 그 아래 <head><RESULT>에
  CODE/MESSAGE가 있다. 에러 시(ERROR-300 등)에는 <head> 없이 루트가 바로 <RESULT>다.
  두 형태를 모두 처리해야 한다.
- SttsApiTbl.do는 STATBL_ID 없이 호출하면 전체 통계표 목록(738건, 2026-08 기준)을 반환한다.
  이를 이용해 이름 키워드 검색을 구현한다.
"""

import os
import xml.etree.ElementTree as ET

import httpx

BASE_URL = "https://www.reb.or.kr/r-one/openapi"
MAX_PAGE_SIZE = 1000

ERROR_MESSAGES = {
    "ERROR-300": "필수 값 누락",
    "ERROR-290": "인증키가 유효하지 않음 (R-ONE 사이트에서 직접 발급받은 키가 맞는지 확인 필요)",
    "ERROR-336": "1회 최대 1,000건 초과 요청",
    "ERROR-337": "일별 트래픽 제한 초과",
    "ERROR-333": "요청위치(pIndex) 타입 오류",
    "ERROR-310": "서비스를 찾을 수 없음",
    "ERROR-500": "서버 오류",
    "ERROR-600": "DB 연결 오류",
    "ERROR-601": "SQL 오류",
}


class RebApiError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def _get_api_key() -> str:
    key = os.environ.get("REB_API_KEY")
    if not key:
        raise RuntimeError("REB_API_KEY 환경변수가 설정되지 않았습니다.")
    return key


def _row_to_dict(row: ET.Element) -> dict:
    return {child.tag: (child.text or "") for child in row}


def _call(endpoint: str, params: dict) -> tuple[list[dict], int]:
    """R-ONE 엔드포인트를 호출해 (row 목록, list_total_count)를 반환한다.

    XML만 사용한다 — Type=json은 서버 인코딩 버그로 한글이 깨진다 (실측 확인됨).
    """
    key = _get_api_key()
    query = {"KEY": key, "pIndex": 1, "pSize": 100}
    query.update(params)

    resp = httpx.get(f"{BASE_URL}/{endpoint}", params=query, timeout=30)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)

    # 에러 시 루트가 바로 <RESULT>, 정상 시 <head><RESULT> (실측 확인됨)
    if root.tag == "RESULT":
        result = root
    else:
        result = root.find("head/RESULT")

    code = result.findtext("CODE") if result is not None else None
    message = result.findtext("MESSAGE") if result is not None else None

    if code is None:
        raise RebApiError("UNKNOWN", f"응답 형식을 해석할 수 없습니다: {resp.text[:300]}")

    if code == "INFO-200":
        return [], 0
    if code != "INFO-000":
        raise RebApiError(code, ERROR_MESSAGES.get(code, message or "알 수 없는 오류"))

    total_count_el = root.find("head/list_total_count")
    total_count = int(total_count_el.text) if total_count_el is not None and total_count_el.text else 0

    rows = [_row_to_dict(row) for row in root.findall("row")]
    return rows, total_count


def _call_all_pages(endpoint: str, params: dict, page_size: int = 200) -> list[dict]:
    """전체 페이지를 pIndex/pSize로 순회하며 모든 row를 모아 반환한다."""
    all_rows: list[dict] = []
    page_index = 1
    while True:
        query = dict(params)
        query["pIndex"] = page_index
        query["pSize"] = page_size
        rows, total = _call(endpoint, query)
        all_rows.extend(rows)
        if not rows or len(all_rows) >= total:
            break
        page_index += 1
    return all_rows


# 서버 프로세스 생명주기 동안 유지되는 인메모리 캐시 (재시작 시 리셋)
_table_list_cache: list[dict] | None = None


def get_all_statistics_tables() -> list[dict]:
    """전체 통계표 목록을 조회한다 (최초 1회 API 호출 후 캐시)."""
    global _table_list_cache
    if _table_list_cache is None:
        _table_list_cache = _call_all_pages("SttsApiTbl.do", {})
    return _table_list_cache


def search_statistics_tables(keyword: str) -> list[dict]:
    """STATBL_NM에 키워드가 포함된 통계표를 검색한다."""
    tables = get_all_statistics_tables()
    return [t for t in tables if keyword in t.get("STATBL_NM", "")]


def get_statistics_items(statbl_id: str, itm_tag: str | None = None) -> list[dict]:
    params = {"STATBL_ID": statbl_id}
    if itm_tag:
        params["ITM_TAG"] = itm_tag
    return _call_all_pages("SttsApiTblItm.do", params)


def get_statistics_data(
    statbl_id: str,
    dtacycle_cd: str,
    start_wrttime: str | None = None,
    end_wrttime: str | None = None,
    wrttime_idtfr_id: str | None = None,
    grp_id: str | None = None,
    cls_id: str | None = None,
    itm_id: str | None = None,
) -> list[dict]:
    params = {"STATBL_ID": statbl_id, "DTACYCLE_CD": dtacycle_cd}
    if start_wrttime:
        params["START_WRTTIME"] = start_wrttime
    if end_wrttime:
        params["END_WRTTIME"] = end_wrttime
    if wrttime_idtfr_id:
        params["WRTTIME_IDTFR_ID"] = wrttime_idtfr_id
    if grp_id:
        params["GRP_ID"] = grp_id
    if cls_id:
        params["CLS_ID"] = cls_id
    if itm_id:
        params["ITM_ID"] = itm_id
    return _call_all_pages("SttsApiTblData.do", params)

import re
from google.oauth2 import service_account
from googleapiclient.discovery import build

def update_sheet(sheet_id, range_name, values, service_account_file):
    """
    sheet_id: 스프레드시트 ID (URL 중간의 긴 문자열)
    range_name: 예) "시트이름!A1" (Sheet1!A1 등)
    values: 2차원 리스트로 표현할 데이터 [[컬럼,컬럼,...],[...],...]
    service_account_file: 서비스 계정 JSON 키 파일 경로
    """

    # 1) 자격증명 생성
    creds = service_account.Credentials.from_service_account_file(
        service_account_file,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    # 2) Sheets API 클라이언트 생성
    service = build("sheets", "v4", credentials=creds)

    # 3) 값 업데이트
    body = {
        "values": values
    }
    result = service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=range_name,
        valueInputOption="RAW",  # RAW로 하면 그대로 입력
        body=body
    ).execute()

    print(f"업데이트된 셀 수: {result.get('updatedCells')}")

def read_sheet(sheet_id, range_name, service_account_file):
    """
    sheet_id: 스프레드시트 ID
    range_name: 읽을 범위 (예: "Sheet1!A1:E10")
    service_account_file: 서비스 계정 JSON 경로
    """
    creds = service_account.Credentials.from_service_account_file(
        service_account_file,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    service = build("sheets", "v4", credentials=creds)
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=range_name
    ).execute()

    rows = result.get("values", [])
    return rows


def parse_hotel_name(raw_str: str) -> str:
    """
    예)
      "미아 리조트 ): 인터콘티넨탈 나트랑"  -> "인터콘티넨탈 나트랑"
      "베스트 웨스턴 푸꾸옥): 뉴월드 리조트" -> "뉴월드 리조트"
      "베스트 웨스턴 푸꾸옥 ): 솔바이멜리아" -> "솔바이멜리아"
      "로얄 펠리스 호텔): 21 Phố Nam Ngư Tầng" -> "21 Phố Nam Ngư Tầng"

    패턴: 괄호 + 콜론 ) : 이후에 있는 텍스트를 추출
    """
    # 이 정규식은 ")", " )", "):", " ):" 등에 이어지는 부분을 group(1)로 캡처
    # 예:  "베스트 웨스턴 푸꾸옥 ): 솔바이멜리아"에서 group(1)은 "솔바이멜리아"
    pattern = r"\)\s*:\s*(.+)$"
    match = re.search(pattern, raw_str)
    if match:
        return match.group(1).strip()
    else:
        # 혹시 매칭이 안 된다면, 원본 반환 (또는 빈 문자열 등)
        return raw_str.strip()


def extract_use_date(raw_str: str) -> str:
    """
    ex) raw_str = "이용날짜(예시 : 2024-xx-xx ): 2025-02-15"
        -> "2025-02-15" 만 반환
    """
    # 방법 A) 정규식
    match = re.search(r":\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", raw_str)
    if match:
        return match.group(1).strip()

    # 방법 B) split 대안
    # parts = raw_str.split("):")
    # if len(parts) > 1:
    #     return parts[1].strip()

    return raw_str  # fallback (혹시 못 찾으면 원본 리턴)


def parse_category_with_qty(category_str: str) -> tuple[int, int, int]:
    """
    category_str 예) "성인 (키 140cm 이상)(2명)" or "아동(1명)" or "노인 (3명)"
    반환: (성인수, 아동수, 노인수)
    """
    # 1) 몇 명인지 숫자 파싱 (기본=1명으로 가정)
    qty_match = re.search(r"\((\d+)명\)", category_str)
    qty = 1
    if qty_match:
        qty = int(qty_match.group(1))

    # 2) 성인/아동/노인 구분
    # 소아도 아동으로 처리
    cat_lower = category_str.lower()  # 소문자로
    adult = 0
    child = 0
    old = 0

    if "성인" in cat_lower:
        adult = qty
    elif ("아동" in cat_lower) or ("소아" in cat_lower):
        child = qty
    elif ("노인" in cat_lower) or ("60세이상" in cat_lower):
        old = qty
    else:
        # 혹은 default: 성인으로?
        adult = qty

    return (adult, child, old)

def to_spreadsheet_rows(parsed_list):
    """
    parsed_list: 파싱된 주문 목록, 각 항목은 dict로 가정
    [
      {
        "name": "이경원",
        "useDate": "이용날짜(예시 : 2024-xx-xx ): 2025-02-15",
        "category": "성인 (키 140cm 이상)(2명)",
        "hotelName": "비다 로카 푸꾸옥 리조트",
        "productName": "[QR+차량]...",
        "courseOption": "B코스 (키스오브더씨 티켓 포함)",
        "payMethod": "완납",
        "tel": "010-..."
      }, ...
    ]
    """
    rows = []
    """
    # 1) 헤더
    header = [
        "한글성명",  # A
        "영문성명",  # B (비워둠)
        "이용날짜",  # C
        "성인",      # D
        "아동",      # E
        "노인",      # F
        "상품명",    # G
        "숙소이름(픽업장소)",  # H
        "코스옵션",  # I
        "결제방식",  # J
        "전화번호"   # K
    ]
    rows.append(header)
    """
    for item in parsed_list:
        name = item.get("name", "")
        use_date = item.get("useDate", "") # 불완전한 형식
        adult = str(item.get("adult", 0))
        child = str(item.get("child", 0))
        old = str(item.get("old", 0))
        product_name = item.get("productName", "")
        hotel_name = item.get("hotelName", "")
        course_option = item.get("courseOption", "")
        pay_method = item.get("payMethod", "")
        tel = item.get("tel", "")
        course_option_side_1 = item.get("sideOption1", "")
        course_option_side_2 = item.get("sideOption2", "")
        tower = str(item.get("tower", 0))

        # 2) 영문명등 쓰지않는 칸들 비워두기 / 추후에 구현 예정
        eng_name = ""
        drop = ""
        pick_up_time = ""
        airplane = ""
        use_date_1 = "" # 이용날짜 (스프레드시트 함수가 자동으로 채워주는 자리)

        # 3) 한 행 구성
        row = [
            name,         # A: 한글성명
            use_date_1,   # B: 이용날짜(함수가 자동으로 채워주는 자리임)
            eng_name,     # C: 영문성명(비워둠)
            adult,        # D: 성인 수
            child,        # E: 아동 수
            old,          # F: 노인 수
            hotel_name,   # G: 숙소(픽업 장소)
            drop,         # H: drop 장소
            product_name, # I: 상품명
            course_option,# J: 코스 메인 옵션
            course_option_side_1, # K: 코스 사이드 옵션 1
            course_option_side_2, # L: 코스 사이드 옵션 2
            pick_up_time, # M: 픽업 시간
            pay_method,   # N: 결제방식
            airplane,     # O: 비행기
            tel,          # P: 전화번호
            tower,        # Q: 타월 갯수
            use_date      # R: 이용날짜(불완전한 형식)
        ]
        rows.append(row)

    return rows

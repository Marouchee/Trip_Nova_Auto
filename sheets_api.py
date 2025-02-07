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
        kor_name = item.get("korName", "")
        eng_name = item.get("engName", "")
        use_date = item.get("useDate", "")
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
        course_option_side_3 = item.get("sideOption3", "")
        course_option_side_4 = item.get("sideOption4", "")
        tower = str(item.get("tower", 0))
        airplane = item.get("airplane", "")
        shipping_memo = item.get("shippingMemo", "")
        initial_amount = str(item.get("initialProductAmount", 0))
        final_amount = str(item.get("finalProductAmount", 0))

        if product_name == "푸꾸옥 프라이빗 렌트카 기사포함 km무제한 SUV 미니벤":
            pay_method = "완납"

        # 2) 영문명등 쓰지않는 칸들 비워두기 / 추후에 구현 예정
        drop = ""
        pick_up_time = ""
        use_date1 = ""
        use_date2 = ""
        use_date3 = ""

        # 3) 한 행 구성
        row = [
            kor_name,         # A: 한글성명
            use_date,     # B: 이용날짜(불완전 형식은 코드 내부에서 자동 변환)
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
            use_date1,    # R
            use_date2,    # S
            use_date3,    # T
            shipping_memo,# U: 배송 메모
            initial_amount, # V: 초기 상품금액
            final_amount,    # W: 최종 상품금액
            course_option_side_3, # X: 코스 사이드 옵션 3
            course_option_side_4, # Y: 코스 사이드 옵션 4
        ]
        rows.append(row)

    return rows

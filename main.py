from naver_api import *
from sheets_api import *
from parsing import *

if __name__ == "__main__":
    client_id = "######################"
    client_secret = "###############################"
    token = get_token(client_id, client_secret)

    # 디버깅용 출력
    print("발급된 토큰:", token)

    # 1) 상태 변경 API로 상품주문번호 목록 가져오기
    changed_items = get_last_changed_list(token)
    # changed_items 예시:
    # [
    #   {"productOrderId": "2025010464018221", "orderId": "...", ...},
    #   {"productOrderId": "2025010634083331", ...},
    #   ...
    # ]

    product_order_ids = [item["productOrderId"] for item in changed_items]
    if not product_order_ids:
        print("새로운 상태변경 주문 없음")
        exit(1)


    # 2) 주문 상세조회 API로 실제 상세 정보 얻기
    detail_res = get_product_orders_detail(token, product_order_ids)
    # detail_res 구조 예시:
    # {
    #   "data": {
    #       "productOrders": [
    #          {
    #            "productOrderId": "2025010464018221",
    #            "product": { "productName": "...", "option": "...", ...},
    #            "orderer": {...},
    #            "shippingAddress": {...},
    #            "payment": {...},
    #            ...
    #          },
    #          ...
    #       ]
    #   }
    # }

    # 필요한 데이터 파싱 과정
    # parse_orders() -> [{...}, ...] (name, useDate, category, ...)
    # 이미 'combine_by_orderid' 한 상태
    parsed_list = parse_orders(detail_res)

    # to_spreadsheet_rows(parsed_list) -> 2차원 list로 변환
    sheet_rows = to_spreadsheet_rows(parsed_list)


    # 스프레드시트에 업로드
    # 1) 스프레드시트 ID & JSON 키 파일 설정
    SHEET_ID = "####################################"
    SERVICE_ACCOUNT_FILE = "######################################.json"

    # 2) 테스트용 밸류
    test_values = sheet_rows

    # 3) 시트에 업데이트
    update_sheet(
        sheet_id=SHEET_ID,
        range_name="input!A40",
        values=test_values,
        service_account_file=SERVICE_ACCOUNT_FILE
    )

    # 4) 읽어오기
    read_result = read_sheet(
        sheet_id=SHEET_ID,
        range_name="input!A40:Q40",
        service_account_file=SERVICE_ACCOUNT_FILE
    )
    # (위에서 추출한 데이터를 2차원 리스트로 만들어 구글 시트에 업로드 가능)

    print("시트에서 읽어온 값:")
    for row in read_result:
        print(row)

    # 5) DB 저장 구현 예정

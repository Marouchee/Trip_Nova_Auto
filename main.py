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
    SERVICE_ACCOUNT_FILE = "######################################"

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

    # 5) DB 저장
    # 1) DB 연결
    connection = pymysql.connect(
        host="###############",
        user="#############",
        password="##########",
        database="###################",
        charset="utf8"
    )

    data_list = detail_res.get("data", [])

    for elem in data_list:
        po = elem.get("productOrder", {})
        order_info = po.get("order", {})
        shipping = po.get("shippingAddress", {})

        # (A) orders 테이블 저장
        order_data = {
            "orderId": order_info.get("orderId", ""),
            "orderDate": order_info.get("orderDate", ""),  # "2025-01-07T20:49:12.0+09:00" -> 필요시 문자열 파싱
            "ordererId": order_info.get("ordererId", ""),
            "ordererName": order_info.get("ordererName", ""),
            "ordererTel": order_info.get("ordererTel", ""),
            "payLocationType": order_info.get("payLocationType", "")
        }
        save_order_to_db(connection, order_data)

        # (B) product_orders 테이블 저장
        product_order_data = {
            "productOrderId": po.get("productOrderId", ""),
            "orderId": order_info.get("orderId", ""),
            "productName": po.get("productName", ""),
            "productOption": po.get("productOption", ""),
            "quantity": po.get("quantity", 0),
            "freeGift": po.get("freeGift", ""),
            "productClass": po.get("productClass", ""),
            "optionCode": po.get("optionCode", ""),
            "optionPrice": po.get("optionPrice", 0),
            "unitPrice": po.get("unitPrice", 0),
            "initialPaymentAmount": po.get("initialPaymentAmount", 0),
            "remainPaymentAmount": po.get("remainPaymentAmount", 0),
            "initialProductAmount": po.get("initialProductAmount", 0),
            "remainProductAmount": po.get("remainProductAmount", 0),
            "merchantChannelId": po.get("merchantChannelId", ""),
            "sellerProductCode": po.get("sellerProductCode", "")
        }
        save_product_order_to_db(connection, product_order_data)

        # (C) shipping_address 테이블 저장
        shipping_data = {
            "productOrderId": po.get("productOrderId", ""),
            "name": shipping.get("name", ""),
            "baseAddress": shipping.get("baseAddress", ""),
            "detailedAddress": shipping.get("detailedAddress", ""),
            "tel1": shipping.get("tel1", ""),
            "tel2": shipping.get("tel2", ""),
            "city": shipping.get("city", ""),
            "state": shipping.get("state", ""),
            "country": shipping.get("country", ""),
            "zipCode": shipping.get("zipCode", "")
        }
        save_shipping_address_to_db(connection, shipping_data)

        product_order_id = po.get("productOrderId", "")
        # (A) parse productOption
        option_str = po.get("productOption", "")
        opt_fields = parse_product_option(option_str)

        # (B) DB에 insert
        save_product_option_details(connection, product_order_id, opt_fields)

    connection.close()

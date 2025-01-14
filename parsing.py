import re

def parse_product_option(product_option_str: str) -> dict:
    """
    product_option_str 예:
      "이용날짜(예시 : 2024-xx-xx ): 2025-02-15 / 숙소 이름( 예시 : 베스트 웨스턴 푸꾸옥): 비다 로카 푸꾸옥 리조트
       / 구분 (성인/소아): 성인 (키 140cm 이상) / 결제방식 (잔금/완납): 완납
       / 코스옵션 (기본/키스오브더씨 공연): B코스 (키스오브더씨 티켓 포함)"

    필요한 항목:
      - 이용 날짜
      - 숙소 이름(픽업장소)
      - 구분(성인/아동/노인)
      - 결제방식
      - 코스 옵션
    """

    # 결과를 담을 딕셔너리
    result = {
        "useDate": "",
        "hotelName": "",
        "category": "",        # 성인/아동/노인 등
        "payMethod": "",       # 잔금 or 완납 등
        "courseOption": ""
    }

    # 1) 이용날짜
    #   예: "이용날짜(예시 : 2024-xx-xx ): 2025-02-15"
    use_date_match = re.search(r"이용.?날짜.*?:\s*([^/]+)", product_option_str)
    if use_date_match:
        result["useDate"] = use_date_match.group(1).strip()

    # 2) 숙소 이름(픽업장소)
    #   예: "숙소 이름.*?: 비다 로카 푸꾸옥 리조트"
    hotel_match = re.search(r"숙소.?이름.*?:\s*([^/]+)", product_option_str)
    if hotel_match:
        result["hotelName"] = hotel_match.group(1).strip()

    # 3) 구분 (성인/소아/노인 등)
    #   예: "구분.*?: 성인 (키 140cm 이상)"
    category_match = re.search(r"구분.*?:\s*([^/]+)", product_option_str)
    if category_match:
        result["category"] = category_match.group(1).strip()

    # 4) 결제방식 (잔금/완납)
    pay_method_match = re.search(r"결제.?방식.*?:\s*([^/]+)", product_option_str)
    if pay_method_match:
        result["payMethod"] = pay_method_match.group(1).strip()

    # 5) 코스옵션 (기본/키스오브더씨 공연 등)
    course_option_match = re.search(r"코스.?옵션.*?:\s*(.*)$", product_option_str)
    if course_option_match:
        # 여기선 정규식 뒤쪽에 /가 없을 수도 있으니, 끝까지 잡도록
        result["courseOption"] = course_option_match.group(1).strip()

    return result


def parse_orders(detail_res: dict) -> list[dict]:
    """
    detail_res 구조:
    {
      "timestamp": "2025-01-09T17:49:00.827+09:00",
      "data": [
        {
          "productOrder": {
            "productOrderId": "...",
            "productName": "...",
            "productOption": "...",
            "shippingAddress": {
                "name": "수령인한글성명",
                "tel1": "010-9999-9999"
                ...
            },
            ...
          }
        },
        ...
      ],
      "traceId": "..."
    }

    반환값:
    [
      {
        "name": "...",
        "useDate": "...",
        "category": "성인(2명)",
        "hotelName": "...",
        "productName": "...",
        "courseOption": "...",
        "payMethod": "...",
        "tel": "010-..."
      },
      ...
    ]
    """

    items = []  # '아이템' 수준 저장 (중간 데이터)

    data_list = detail_res.get("data", [])
    for elem in data_list:
        po = elem.get("productOrder", {})
        order = elem.get("order", {})
        shipping = po.get("shippingAddress", {})

        # 1) orderId
        order_id = order.get("orderId", "")

        # 2) 한글성명, 전화번호
        name = shipping.get("name", "")
        tel = shipping.get("tel1", "")

        # 3) 이용날짜 (예: "이용날짜(예시 : 2024-xx-xx ): 2025-02-15" 에서 뒤쪽만)
        use_date_str = po.get("productOption", "")
        use_date = extract_use_date(use_date_str)  # <-- 아래 예시 함수

        # 4) 숙소 이름 (예: "베스트 웨스턴 푸꾸옥): 뉴월드 리조트" -> "뉴월드 리조트")
        hotel_name = extract_hotel_name(use_date_str)  # <-- 아래 예시 함수

        # 5) 상품명
        product_name = po.get("productName", "")

        # 6) 결제방식 (예: "결제방식 (잔금/완납): 완납") -> 정규식 or parse_option
        pay_method = extract_pay_method(use_date_str)

        # 7) 성인/아동/노인 파싱:
        #    예: "성인 (키 140cm 이상)(2명)" -> adult=2, child=0, old=0
        category_str = extract_category_str(use_date_str)  # parse_option 내부 or 별도
        # 7-1) 실제 인원수
        quantity = po.get("quantity", 0)
        adult, child, old = parse_category_and_quantity(category_str, quantity)  # <-- 아래 예시

        # 8) 메인 옵션 파싱
        course_option_str = extract_course_option(use_date_str)

        # packageNumber - 채널 상품 번호? (병합용 식별자)
        productId = po.get("productId", None)  # 예: "2025010825643147"

        # ---------------------
        # (A) Side options
        #  - 조건: productName(또는 productOption)에 추가 옵션이 들어있나?
        #  - 예: "스피드보트 업그레이드(잔금 30USD)", "북부지역 6인 이하(잔금 20USD)", etc.
        side_option = None
        is_side = False
        # 예시판별: 만약 productName에 "스피드보트 업그레이드" or "북부지역" 텍스트 포함되어 있으면 side_option = productName
        if any(x in product_name for x in ["스피드보트 업그레이드", "북부지역", "잔금 30USD", "잔금 20USD"]):
            is_side = True
            side_option = product_name  # sideOption 필드에 저장
        # 혹은 productOption 안에서도 판별 가능

        # (B) Tower
        #  - if productName == "원하시는 개수 만큼 선택해주세요." => Tower = quantity
        tower = 0
        is_tower = False
        if "원하시는 개수 만큼 선택해주세요" in product_name:
            is_tower = True
            tower = quantity

        # 성인 / 아동 / 노인 계산
        if is_side or is_tower:
            # 추가옵션/타월 주문은 adult/child/old=0
            adult = 0
            child = 0
            old = 0
        else:
            # 일반 메인 상품은 quantity로 adult/child/old
            adult, child, old = parse_category_and_quantity(category_str, quantity)

        # 9) items에 누적
        items.append({
            "orderId": order_id,
            "productId": productId,
            "name": name,
            "tel": tel,
            "useDate": use_date,
            "hotelName": hotel_name,
            "productName": product_name,
            "courseOption": course_option_str,
            "payMethod": pay_method,
            "adult": adult,
            "child": child,
            "old": old,
            "sideOption": side_option,
            "tower": tower
        })

    # 이제 items를 orderId별로 합산
    combined = _combine_by_pkg(items)
    return combined


def _combine_by_pkg(items: list[dict]) -> list[dict]:
    """
    병합 키: (orderId, productId)
    - 만약 side item에는 productId가 동일 -> 병합
    - useDate, hotelName, productName 등은 '메인 상품'에서만 유효
      -> side item은 빈값이므로, 병합 시 메인 상품의 값 유지
    - adult/child/old/tower -> 합산
    - sideOption -> sideOption1/2
    """

    data_by_key = {}

    for it in items:
        # group key
        oid = it["orderId"]
        pkg = it["productId"]
        key = (oid, pkg)
        if key not in data_by_key:
            # 초기화
            data_by_key[key] = {
                "orderId": oid,
                "productId": pkg,
                "name": it["name"],
                "tel": it["tel"],
                "useDate": it["useDate"],
                "hotelName": it["hotelName"],
                "productName": it["productName"],
                "courseOption": it["courseOption"],
                "payMethod": it["payMethod"],
                "adult": it["adult"],
                "child": it["child"],
                "old": it["old"],
                "tower": it["tower"],
                "sideOption1": "",
                "sideOption2": "",
            }
            # productName: 만약 메인상품이 있으면 그걸로. 추가옵션이면 ""
            if it["adult"] > 0 or it["child"] > 0 or it["old"] > 0:
                # => 메인상품이라 판단
                data_by_key[key]["productName"] = it["productName"]
            else:
                # side option => sideOption1에 기록
                if it["sideOption"]:
                    data_by_key[key]["sideOption1"] = it["sideOption"]
        else:
            # adult/child/old 누적
            data_by_key[key]["adult"] += it["adult"]
            data_by_key[key]["child"] += it["child"]
            data_by_key[key]["old"] += it["old"]
            data_by_key[key]["tower"] += it["tower"]  # 타월 수량 합산

            # 메인상품명은 adult/child/old>0인 항목에서 가져온다(또는 이미 있으면 덮어쓰지 않음)
            if it["adult"] > 0 or it["child"] > 0 or it["old"] > 0:
                if not data_by_key[key]["productName"]:
                    data_by_key[key]["productName"] = it["productName"]

                # useDate/hotelName/payMethod도 메인상품 행에서만 유효 -> update if empty
                if not data_by_key[key]["useDate"] and it["useDate"]:
                    data_by_key[key]["useDate"] = it["useDate"]
                if not data_by_key[key]["hotelName"] and it["hotelName"]:
                    data_by_key[key]["hotelName"] = it["hotelName"]
                if not data_by_key[key]["payMethod"] and it["payMethod"]:
                    data_by_key[key]["payMethod"] = it["payMethod"]

            # 다른 필드는 같은 값이어야 하는 경우가 대부분
            # 만약 productName이 다르면? -> 첫번째 or 합쳐야 함(이하 생략)
            # 여기서는 첫 항목 그대로 둠
            # sideOption 누적
            if it["sideOption"]:
                # sideOption1이 비어 있으면 채움, 아니면 sideOption2로
                if not data_by_key[key]["sideOption1"]:
                    data_by_key[key]["sideOption1"] = it["sideOption"]
                else:
                    # sideOption2가 비어있으면 넣고, 이미 있으면 병합(슬래시?)
                    if not data_by_key[key]["sideOption2"]:
                        data_by_key[key]["sideOption2"] = it["sideOption"]
                    else:
                        # 예: "북부지역 ... / 스피드보트 업그레이드"
                        data_by_key[key]["sideOption2"] += " / " + it["sideOption"]

    return list(data_by_key.values())


def extract_use_date(option_str: str) -> str:
    """
    예: "이용날짜(예시 : 2024-xx-xx ): 2025-02-15 / 숙소 이름... "
         -> "2025-02-15"
    """
    match = re.search(r"이용.?날짜.*?:\s*([^/]+)", option_str)
    if match:
        parts = match.group(1).split("):")
        if len(parts) > 1:
            # parts[1]은 " 뉴월드 리조트"처럼 앞에 공백이 있을 수 있으니 strip()
            return parts[1].strip()
        else:
            return match.group(1).strip()
    return ""

def extract_hotel_name(option_str: str) -> str:
    """
    예: "베스트 웨스턴 푸꾸옥): 뉴월드 리조트"
      -> "뉴월드 리조트"
    정규식 or split으로 "):" 뒤쪽
    """
    pattern = r"\)\s*:\s*(.+)$"
    match = re.search(r"숙소.?이름.*?:\s*([^/]+)", option_str)
    if match:
        match_1 = re.search(pattern, match.group(1))
        if match_1:
            return match_1.group(1).strip()
    match = re.search(r"픽업.?장소.*?:\s*([^/]+)", option_str)
    if match:
        match_1 = re.search(pattern, match.group(1))
        if match_1:
            return match_1.group(1).strip()
    return ""

def extract_pay_method(option_str: str) -> str:
    """
    예: "결제방식 (잔금/완납): 잔금"
        -> "잔금"
    (정규식 or split)
    """
    match = re.search(r"결제.?방식.*?:\s*([^/]+)", option_str)
    if match:
        return match.group(1).strip()
    return ""

def extract_category_str(option_str: str) -> str:
    """
    예: "구분 (성인/소아): 성인 (키 140cm 이상)(2명)"
    -> "성인 (키 140cm 이상)(2명)"
    """
    match = re.search(r"구분.*?:\s*([^/]+)", option_str)
    if match:
        return match.group(1).strip()
    return ""

def extract_course_option(option_str: str) -> str:
    """
    예: "코스 옵션 (기본/빈원더스 추가): B코스 (사파리+빈원더스+그랜드월드)"
        -> "B코스 (사파리+빈원더스+그랜드월드)"
    (정규식 or split)
    """
    match = re.search(r"코스.?옵션.*?:\s*(.*)$", option_str)
    if match:
        return match.group(1).strip()
    return ""

def parse_category_and_quantity(category_str: str, quantity: int) -> tuple[int, int, int]:
    """
    category_str 예: "성인 (키 140cm 이상)", "아동(만 8세 이하)", "노인(3명)" 등
    실제 인원수는 'quantity'로 결정
      - 만약 category_str에 "성인" 있으면 adult=quantity
      - "아동"/"소아" 있으면 child=quantity
      - "노인" or "60세 이상" 등 있으면 old=quantity
      - 기타 경우 => adult=quantity
    => 반환: (adult, child, old)
    """
    cat_lower = category_str.lower()
    if "성인" in cat_lower:
        return (quantity, 0, 0)
    elif ("아동" in cat_lower) or ("소아" in cat_lower):
        return (0, quantity, 0)
    elif ("노인" in cat_lower) or ("60세" in cat_lower):
        return (0, 0, quantity)
    else:
        # 기본적으로 성인으로 처리
        return (quantity, 0, 0)
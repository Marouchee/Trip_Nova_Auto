import re

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
        # 8-1) 메인 옵션이 2가지인 상품의 경우 side_option에 파싱
        if product_name == "[푸꾸옥 에센셜] 프라이빗 모닝투어 체크인 비엣젯, 제주항공, 진에어, 대한항공":
            side_option = extract_course_option_2(use_date_str)

        # 9) 비행기 편명 파싱
        airplane = extract_plane(use_date_str)

        # packageNumber - 채널 상품 번호? (병합용 식별자)
        productId = po.get("productId", None)  # 예: "2025010825643147"

        # ---------------------
        # (A) Side options
        #  - 조건: productName(또는 productOption)에 추가 옵션이 들어있나?
        #  - 예: "스피드보트 업그레이드(잔금 30USD)", "북부지역 6인 이하(잔금 20USD)", etc.
        side_option = None
        is_side = False
        # 예시판별: 만약 productName에 "스피드보트 업그레이드" or "북부지역" 텍스트 포함되어 있으면 side_option = productName
        if any(x in product_name for x in ["스피드보트 업그레이드", "북부지역", "잔금 30USD", "잔금 20USD",
                                           "북부(완납)", "남부(완납)", "중부(완납)", "소나시(무료)", "북부(잔금)", "남부(잔금)", "중부(잔금)" ]):
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

        # 10) items에 누적
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
            "tower": tower,
            "airplane": airplane
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
                "airplane": it["airplane"],
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
    match = re.search(r"코스.?옵션.*?:\s*([^/]+)", option_str)
    if match:
        return match.group(1).strip()
    match = re.search(r"옵션.?선택.*?:\s*([^/]+)", option_str)
    if match:
        return match.group(1).strip()
    match = re.search(r"차량.?옵션.*?:\s*([^/]+)", option_str)
    if match:
        return match.group(1).strip()
    match = re.search(r"투어.?선택.*?:\s*([^/]+)", option_str)
    if match:
        return match.group(1).strip()
    return ""

# 상품에 메인옵션이 2가지 있는경우에 사용.
def extract_course_option_2(option_str: str) -> str:
    """
    예: "코스 옵션 (기본/빈원더스 추가): B코스 (사파리+빈원더스+그랜드월드)"
        -> "B코스 (사파리+빈원더스+그랜드월드)"
    (정규식 or split)
    """
    match = re.search(r"마사지.?시간.?선택.*?:\s*([^/]+)", option_str)
    if match:
        return match.group(1).strip()
    return ""

def extract_plane(option_str: str) -> str:
    """
    예: " 비행기 편명(예시: VJ979): VJ0975"
        -> "VJ0975"
    (정규식 or split)
    """
    match = re.search(r"비행기.?편명.*?:\s*([^/]+)", option_str)
    if match:
        parts = match.group(1).split("):")
        if len(parts) > 1:
            # parts[1]은 " 뉴월드 리조트"처럼 앞에 공백이 있을 수 있으니 strip()
            return parts[1].strip()
        else:
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


def parse_product_option(option_str: str) -> dict:
    """
    productOption에서
    - useDate (YYYY-MM-DD)
    - engName (영문 이름)
    - hotelName (숙소 이름)
    - courseOption (코스 옵션)
    - sideOption (기존 sideOption1/2 처리?), 혹은 우리가 parse_orders에서 sideOption 로직이 있다면, 그쪽에 맡길 수도 있음
    - adult, child, old (혹은 parse_category_and_quantity)
    - payMethod
    - birthDay(6자)
    - tower(수건 개수)
    - airplane(항공편)
    - drop(샌드다운 장소)
    """
    result = {
        "useDate": "",
        "engName": "",
        "hotelName": "",
        "courseOption": "",
        # sideOption1, sideOption2는 parse_orders 쪽에서 관리? 혹은 여기서 파싱
        "adult": 0,
        "child": 0,
        "old": 0,
        "payMethod": "",
        "birthDay": "",
        "tower": 0,
        "airplane": "",
        "drop": ""
    }

    # 예시 정규식들 (필요에 맞춰 수정)
    # 1) 이용 날짜
    m_usedate = re.search(r":\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", option_str)
    if m_usedate:
        result["useDate"] = m_usedate.group(1)

    # 2) 영문 이름
    m_eng = re.search(r"영문.?이름.*?:\s*([^/]+)", option_str)
    if m_eng:
        result["engName"] = m_eng.group(1).strip()

    # 3) 숙소 이름
    m_hotel = re.search(r"숙소.?이름.*?:\s*([^/]+)", option_str)
    if m_hotel:
        result["hotelName"] = m_hotel.group(1).strip()

    # 4) 코스 옵션
    m_course = re.search(r"코스.?옵션.*?:\s*([^/]+)", option_str)
    if m_course:
        result["courseOption"] = m_course.group(1).strip()

    # 5) 성인/아동/노인 (간단 예시)
    #    "구분(성인/소아/노인): 성인(2명), 아동(1명), 노인(0명)"
    cat_match = re.search(r"구분.*?:\s*(.+)", option_str)
    if cat_match:
        cat_str = cat_match.group(1).lower()
        # ex: "성인(2명), 아동(1명), 노인(0명)"
        adult_m = re.search(r"성인.*?\((\d+)명\)", cat_str)
        if adult_m:
            result["adult"] = int(adult_m.group(1))
        child_m = re.search(r"(아동|소아).*?\((\d+)명\)", cat_str)
        if child_m:
            result["child"] = int(child_m.group(2))
        old_m = re.search(r"(노인|60세).*?\((\d+)명\)", cat_str)
        if old_m:
            result["old"] = int(old_m.group(2))

    # 6) 결제방식
    m_pay = re.search(r"결제.?방식.*?:\s*([^/]+)", option_str)
    if m_pay:
        result["payMethod"] = m_pay.group(1).strip()

    # 7) 생년월일 6자
    birth_m = re.search(r"생년.?월일.*?:\s*(\d{6})", option_str)
    if birth_m:
        result["birthDay"] = birth_m.group(1)

    # 8) 타월(수건) 개수
    tower_m = re.search(r"(타월|수건).*?개수.*?:\s*(\d+)", option_str)
    if tower_m:
        result["tower"] = int(tower_m.group(2))

    # 9) 항공편
    plane_m = re.search(r"항공편.*?:\s*([^/]+)", option_str)
    if plane_m:
        result["airplane"] = plane_m.group(1).strip()

    # 10) 샌드다운(drop)
    drop_m = re.search(r"(샌드다운|drop).*?:\s*([^/]+)", option_str.lower())
    if drop_m:
        result["drop"] = drop_m.group(2).strip()

    return result

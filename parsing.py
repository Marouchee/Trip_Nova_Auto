import re
import datetime

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
        use_date = parse_user_date(use_date)

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
        """
        # 8-1) 메인 옵션이 2가지인 상품의 경우 side_option에 파싱 - 순서 문제로 ㅈ버그 발생, 나중에 다른 방법으로 수정해야함.
        if product_name == "[푸꾸옥 에센셜] 프라이빗 모닝투어 체크인 비엣젯, 제주항공, 진에어, 대한항공":
            side_option = extract_course_option_2(use_date_str)
        """

        # 9) 비행기 편명 파싱
        airplane = extract_plane(use_date_str)

        # packageNumber - 채널 상품 번호? (병합용 식별자)
        productId = po.get("productId", None)  # 예: "2025010825643147"

        # db 저장용
        product_order_id = po.get("productOrderId", "")

        # 배송 메모 파싱
        shipping_memo = po.get("shippingMemo", "")

        # 초기 상품 금액(할인 전)
        initial_amount = po.get("initialProductAmount", 0)
        # 최초 결제 금액(할인 적용 후 금액)
        final_amount = po.get("initialPaymentAmount", 0)

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
            # 렌트카 사용인원 파싱
            if product_name == "푸꾸옥 프라이빗 렌트카 기사포함 km무제한 SUV 미니벤":
                adult = int(extract_rent_car_quantity(use_date_str))

        # 10) items에 누적
        items.append({
            "orderId": order_id,
            "productOrderId": product_order_id,
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
            "airplane": airplane,
            "shippingMemo": shipping_memo,
            "initialProductAmount": initial_amount,
            "finalProductAmount": final_amount
        })

    # 사이드 아이템 useDate="" -> 메인 날짜 복사
    items = _fix_side_items_date(items)

    # 이제 items를 orderId별로 합산
    combined = _combine_by_pkg(items)
    return combined


def _fix_side_items_date(items: list[dict]) -> list[dict]:
    """
    같은 (orderId, productId) 그룹 내:
    - 메인 아이템(성인/아동/노인>0)이 있다면, 그 아이템의 useDate를 side item에 복사
    - side item useDate가 '' -> fill with main's date
    - 만약 여러 메인상품(서로 다른 date)이면?
      -> 첫 메인상품 or 나중에 구분 로직이 필요
    """
    # 1) 그룹화 by (orderId, productId)
    group_map = {}
    for it in items:
        key = (it["orderId"], it["productId"])
        if key not in group_map:
            group_map[key] = []
        group_map[key].append(it)

    # 2) 각 그룹에서 main item의 useDate를 찾는다
    for key, group in group_map.items():
        # find if there's any main item with useDate != ""
        # (adult+child+old>0) => main
        # 만약 여러개면? 본인 로직 결정(첫것 사용 or ...)
        main_date = None
        for it in group:
            if (it["adult"] + it["child"] + it["old"])>0 and it["useDate"]:
                main_date = it["useDate"]
                break

        # 3) side items => useDate="" -> fill with main_date if exist
        if main_date:
            for it in group:
                if not it["useDate"]:
                    it["useDate"] = main_date

    # 4) flatten
    #   group_map 내부에서 수정하였으므로, items도 이미 반영됨
    #   그냥 return items
    return items


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
        dt = it["useDate"]
        key = (oid, pkg, dt)
        if key not in data_by_key:
            # 초기화
            data_by_key[key] = {
                "orderId": oid,
                "productId": pkg,
                "productOrderId": it["productOrderId"],
                "name": it["name"],
                "tel": it["tel"],
                "useDate": dt,
                "hotelName": it["hotelName"],
                "productName": it["productName"],
                "courseOption": it["courseOption"],
                "payMethod": it["payMethod"],
                "adult": it["adult"],
                "child": it["child"],
                "old": it["old"],
                "tower": it["tower"],
                "airplane": it["airplane"],
                "shippingMemo": it["shippingMemo"],
                "initialProductAmount": it["initialProductAmount"],
                "finalProductAmount": it["finalProductAmount"],
                "sideOption1": it["sideOption"],
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
            data_by_key[key]["initialProductAmount"] += it["initialProductAmount"]
            data_by_key[key]["finalProductAmount"] += it["finalProductAmount"]

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

def extract_rent_car_quantity(option_str: str) -> str:
    """
    예: "사용 인원: 4"
    -> "4"
    """
    match = re.search(r"사용.?인원.*?:\s*([^/]+)", option_str)
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
    match = re.search(r"마사지 시간 선택:\s*([^/]+)", option_str)
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


def parse_user_date(date_str: str) -> str:
    """
    사용자 입력 날짜를 다양하게 수용해 'YYYY-MM-DD'로 통일하는 함수.
    - "250114" => "2025-01-14"
    - "2025.01.14", "25.01.14" => "2025-01-14"
    - "20250114" => "2025-01-14"
    - "25-1-14" => "2025-01-14"
    - "25114" => "2025-01-14"
    - "23.5.7" => "2023-05-07"
    - 그 외 패턴도 최대한 처리
    - 실패 시 "" 반환
    """

    if not date_str or not date_str.strip():
        return ""

    s = date_str.strip()

    # 한글 패턴: "YYYY년 M월 D일"
    # ex) "2025년 1월 29일", "2025년 01월 29일" 등
    match_ko = re.match(r"^\s*([0-9]{4})\s*년\s*([0-9]{1,2})\s*월\s*([0-9]{1,2})\s*일\s*$", s)
    if match_ko:
        yyyy = int(match_ko.group(1))
        mm = int(match_ko.group(2))
        dd = int(match_ko.group(3))
        try:
            dt = datetime.date(yyyy, mm, dd)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # 1) 구두점/하이픈/슬래시/공백 등 제거
    #    예: "25.1.14" -> "25114", "23.5.7" -> "2357" 또는 "23507" (아래서 처리)
    s_clean = re.sub(r"[.\-/\s]", "", s)  # "25.01.14" -> "250114"

    # 2) 길이별 처리

    # (A) 길이가 8 => yyyy mm dd
    if len(s_clean) == 8:
        yyyy = s_clean[0:4]
        mm = s_clean[4:6]
        dd = s_clean[6:8]
        try:
            dt = datetime.date(int(yyyy), int(mm), int(dd))
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # (B) 길이가 6 => yy mm dd
    if len(s_clean) == 6:
        yy = s_clean[0:2]
        mm = s_clean[2:4]
        dd = s_clean[4:6]
        try:
            yyyy = _two_digit_year_to_full(yy)
            dt = datetime.date(yyyy, int(mm), int(dd))
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # (C) 길이가 5 => "yy m dd" or "yy mm d" 등의 변형 가정
    if len(s_clean) == 5:
        # 예: "25114" => "25 1 14" => 2025-01-14
        # 가능성 1) yy m dd => s_clean[0:2], s_clean[2:3], s_clean[3:5]
        # 가능성 2) yy mm d => s_clean[0:2], s_clean[2:4], s_clean[4:5]

        # 우선 시도1: yy m dd
        yy = s_clean[0:2]
        m = s_clean[2:3]
        dd = s_clean[3:5]
        try:
            yyyy = _two_digit_year_to_full(yy)
            dt = datetime.date(yyyy, int(m), int(dd))
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

        # 시도2: yy mm d
        yy = s_clean[0:2]
        mm = s_clean[2:4]
        d = s_clean[4:5]
        try:
            yyyy = _two_digit_year_to_full(yy)
            dt = datetime.date(yyyy, int(mm), int(d))
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # (D) 길이가 4 => "y m d"?? (예: "2357" -> 23 5 7 => 2023-05-07)
    #     매우 모호하므로 필요하면 여기도 처리
    if len(s_clean) == 4:
        # ex: "2357" => yy=23, m=5, d=7
        #   -> 2023-05-07
        #   But ambiguous if user meant 02-35-07?
        # 여기서는 간단히 yy, m, d
        yy = s_clean[0:2]
        m = s_clean[2:3]
        d = s_clean[3:4]
        try:
            yyyy = _two_digit_year_to_full(yy)
            dt = datetime.date(yyyy, int(m), int(d))
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # (E) strptime 여러 패턴 시도
    #   "25.1.14" -> ...
    possible_patterns = [
        "%Y.%m.%d",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%y.%m.%d",
        "%y-%m-%d",
        "%y/%m/%d",
    ]
    for pat in possible_patterns:
        try:
            dt = datetime.datetime.strptime(s, pat).date()
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # 실패
    return date_str


def _two_digit_year_to_full(yy_str: str) -> int:
    """
    2자리 연도 -> 4자리 연도 변환 규칙
    예:
      00~69 => 2000~2069
      70~99 => 1970~1999
    """
    yy = int(yy_str)
    return 2000 + yy


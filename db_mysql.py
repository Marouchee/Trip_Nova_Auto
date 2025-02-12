import pymysql

def save_order_to_db(connection, order_data):
    """
    order_data:
      {
        "orderId": str,
        "orderDate": str (ISO8601),
        "ordererId": str,
        "ordererName": str,
        "ordererTel": str,
        "payLocationType": str
      }
    """

    order_date_str = order_data["orderDate"]

    # 1) 만약 값이 빈 문자열이면 None 으로 교체
    if not order_date_str:
        order_date_str = None

    with connection.cursor() as cursor:
        sql = """
        INSERT INTO orders (order_id, order_date, orderer_id, orderer_name, orderer_tel, pay_location_type)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
          order_date=VALUES(order_date),
          orderer_id=VALUES(orderer_id),
          orderer_name=VALUES(orderer_name),
          orderer_tel=VALUES(orderer_tel),
          pay_location_type=VALUES(pay_location_type)
        """
        cursor.execute(sql, (
            order_data["orderId"],
            order_date_str,    # None -> INSERT NULL   # 파싱해서 DATETIME 형식 (e.g. 2025-01-07T20:49:12+09:00 -> 2025-01-07 20:49:12)
            order_data["ordererId"],
            order_data["ordererName"],
            order_data["ordererTel"],
            order_data["payLocationType"]
        ))
    connection.commit()


def save_product_order_to_db(connection, product_order_data):
    """
    product_order_data:
      {
        "productOrderId": str,
        "orderId": str,
        "productName": str,
        "productOption": str,
        "quantity": int,
        ...
      }
    """
    with connection.cursor() as cursor:
        sql = """
        INSERT INTO product_orders (
          product_order_id, order_id, product_name,
          quantity, free_gift, product_class, option_code, option_price,
          unit_price, initial_payment_amount, remain_payment_amount,
          initial_product_amount, remain_product_amount, merchant_channel_id,
          seller_product_code
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          order_id=VALUES(order_id),
          product_name=VALUES(product_name),
          quantity=VALUES(quantity),
          free_gift=VALUES(free_gift), 
          product_class=VALUES(product_class),
          option_code=VALUES(option_code),
          option_price=VALUES(option_price),
          unit_price=VALUES(unit_price),
          initial_payment_amount=VALUES(initial_payment_amount),
          remain_payment_amount=VALUES(remain_payment_amount),
          initial_product_amount=VALUES(initial_product_amount),
          remain_product_amount=VALUES(remain_product_amount),
          merchant_channel_id=VALUES(merchant_channel_id),
          seller_product_code=VALUES(seller_product_code)
        """
        cursor.execute(sql, (
            product_order_data["productOrderId"],
            product_order_data["orderId"],
            product_order_data["productName"],
            product_order_data["quantity"],
            product_order_data["freeGift"],
            product_order_data["productClass"],
            product_order_data["optionCode"],
            product_order_data["optionPrice"],
            product_order_data["unitPrice"],
            product_order_data["initialPaymentAmount"],
            product_order_data["remainPaymentAmount"],
            product_order_data["initialProductAmount"],
            product_order_data["remainProductAmount"],
            product_order_data["merchantChannelId"],
            product_order_data["sellerProductCode"]
        ))
    connection.commit()


def save_shipping_address_to_db(connection, shipping_data):
    """
    shipping_data:
      {
        "productOrderId": str,
        "name": str,
        "baseAddress": str,
        "detailedAddress": str,
        "tel1": str,
        ...
      }
    """
    with connection.cursor() as cursor:
        sql = """
        INSERT INTO shipping_address (
          product_order_id, name, base_address, detailed_address,
          tel1, tel2, city, state, country, zip_code
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          name=VALUES(name),
          base_address=VALUES(base_address),
          detailed_address=VALUES(detailed_address),
          tel1=VALUES(tel1),
          tel2=VALUES(tel2),
          city=VALUES(city),
          state=VALUES(state),
          country=VALUES(country),
          zip_code=VALUES(zip_code)
        """
        cursor.execute(sql, (
            shipping_data["productOrderId"],
            shipping_data["name"],
            shipping_data["baseAddress"],
            shipping_data["detailedAddress"],
            shipping_data["tel1"],
            shipping_data["tel2"],
            shipping_data["city"],
            shipping_data["state"],
            shipping_data["country"],
            shipping_data["zipCode"]
        ))
    connection.commit()


def save_product_option_details(connection, row_data):
    """
    row_data 예:
    {
      "product_order_id": "2025012026399471",
      "kor_name": "김철수",
      "use_date": "2025-01-22",
      "eng_name": "KIM CHULSU",
      "adult": 4,
      "child": 0,
      "elder": 0,
      "hotel_name": "코랄베이 리조트",
      "sending": "공항샌딩",
      "product_name": "나트랑 스노쿨링...",
      "course_option": "B코스",
      "side_option1": "...",
      "side_option2": "...",
      "pick_up_time": "07:00",
      "pay_method": "완납",
      "airplane": "VN1234",
      "tel": "010-1234-5678",
      "tower": 0,
      "day1": "20250121",
      "day2": "20250122",
      "day3": "",
      "message": "메모",
      "initial_product_amount": 300000,
      "final_product_amount": 250000
    }
    """

    sql = """
    INSERT INTO product_option_details (
      product_order_id,
      kor_name,
      use_date,
      eng_name,
      adult,
      child,
      elder,
      hotel_name,
      sending,
      product_name,
      course_option,
      side_option1,
      side_option2,
      pick_up_time,
      pay_method,
      airplane,
      tel,
      tower,
      side_option3,
      side_option4,
      product_id,
      message,
      initial_product_amount,
      final_product_amount,
      statement
    )
    VALUES (
      %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
      %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
      %s, %s, %s, %s, %s
    )
    ON DUPLICATE KEY UPDATE
      kor_name=VALUES(kor_name),
      use_date=VALUES(use_date),
      eng_name=VALUES(eng_name),
      adult=VALUES(adult),
      child=VALUES(child),
      elder=VALUES(elder),
      hotel_name=VALUES(hotel_name),
      sending=VALUES(sending),
      product_name=VALUES(product_name),
      course_option=VALUES(course_option),
      side_option1=VALUES(side_option1),
      side_option2=VALUES(side_option2),
      pick_up_time=VALUES(pick_up_time),
      pay_method=VALUES(pay_method),
      airplane=VALUES(airplane),
      tel=VALUES(tel),
      tower=VALUES(tower),
      side_option3=VALUES(side_option3),
      side_option4=VALUES(side_option4),
      product_id=VALUES(product_id),
      message=VALUES(message),
      initial_product_amount=VALUES(initial_product_amount),
      final_product_amount=VALUES(final_product_amount),
      statement=VALUES(statement)
    """

    order_date_str = row_data.get("useDate", None)
    # 1) 만약 값이 빈 문자열이면 None 으로 교체
    if not order_date_str:
        order_date_str = None

    with connection.cursor() as cursor:
        cursor.execute(sql, (
            row_data.get("productOrderId",""),
            row_data.get("korName",""),
            order_date_str,  # use_date -> DATETIME or str
            row_data.get("engName",""),
            row_data.get("adult",0),
            row_data.get("child",0),
            row_data.get("old",0),
            row_data.get("hotelName",""),
            row_data.get("sending",""),
            row_data.get("productName",""),
            row_data.get("courseOption",""),
            row_data.get("sideOption1",""),
            row_data.get("sideOption2",""),
            row_data.get("pickUpTime",""),
            row_data.get("payMethod",""),
            row_data.get("airplane",""),
            row_data.get("tel",""),
            row_data.get("tower",0),
            row_data.get("sideOption3",""),
            row_data.get("sideOption4",""),
            row_data.get("product_id",""),
            row_data.get("shippingMemo",""),
            row_data.get("initialProductAmount",0),
            row_data.get("finalProductAmount",0),
            "PAYED"
        ))
    connection.commit()

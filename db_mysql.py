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
          product_order_id, order_id, product_name, product_option,
          quantity, free_gift, product_class, option_code, option_price,
          unit_price, initial_payment_amount, remain_payment_amount,
          initial_product_amount, remain_product_amount, merchant_channel_id,
          seller_product_code
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          order_id=VALUES(order_id),
          product_name=VALUES(product_name),
          product_option=VALUES(product_option),
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
            product_order_data["productOption"],
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


def save_product_option_details(connection, product_order_id, opt_fields: dict):
    """
    opt_fields는 parse_product_option() 결과 예:
    {
      "useDate": "2025-02-15",
      "engName": "PETER PARKER",
      "hotelName": "베스트 웨스턴...",
      "courseOption": "B코스",
      "sideOption1": "스피드보트 업그레이드",
      "sideOption2": "북부지역 6인 이하",
      "adult": 2,
      "child": 1,
      "old": 0,
      "payMethod": "완납",
      "birthDay": "990101",
      "tower": 3,
      "airplane": "OZ1234",
      "drop": "노보텔"
    }
    Insert or Update into `product_option_details` table
    """

    with connection.cursor() as cursor:
        sql = """
        INSERT INTO product_option_details (
          product_order_id, use_date, eng_name, hotel_name,
          course_option, side_option1, side_option2,
          adult, child, old,
          pay_method, birth_day, tower, airplane, drop
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          use_date=VALUES(use_date),
          eng_name=VALUES(eng_name),
          hotel_name=VALUES(hotel_name),
          course_option=VALUES(course_option),
          side_option1=VALUES(side_option1),
          side_option2=VALUES(side_option2),
          adult=VALUES(adult),
          child=VALUES(child),
          old=VALUES(old),
          pay_method=VALUES(pay_method),
          birth_day=VALUES(birth_day),
          tower=VALUES(tower),
          airplane=VALUES(airplane),
          drop=VALUES(drop)
        """

        cursor.execute(sql, (
            product_order_id,
            opt_fields["useDate"],
            opt_fields["engName"],
            opt_fields["hotelName"],
            opt_fields["courseOption"],
            opt_fields["sideOption1"],
            opt_fields["sideOption2"],
            opt_fields["adult"],
            opt_fields["child"],
            opt_fields["old"],
            opt_fields["payMethod"],
            opt_fields["birthDay"],
            opt_fields["tower"],
            opt_fields["airplane"],
            opt_fields["drop"]
        ))
    connection.commit()

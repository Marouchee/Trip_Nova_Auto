import requests
import bcrypt
import base64  # pybase64 말고 내장 base64 모듈 사용도 가능
import time
import urllib.parse
from datetime import datetime, timedelta


def get_token(client_id: str, client_secret: str, type_: str = "SELF", max_retries: int = 3) -> str:
    """
    - bcrypt + Base64를 통해 client_secret_sign 생성
    - timestamp(밀리초)와 함께 client_credentials 방식으로 토큰 발급
    - max_retries: 실패 시 최대 재시도 횟수 (기본 3회)
    """

    # 1) 밀리초 timestamp
    timestamp = str(int((time.time() - 3) * 1000))  # 3초 빼는 이유는 예제 코드 상의 관행

    # 2) bcrypt hash => Base64
    pwd = f"{client_id}_{timestamp}"
    hashed = bcrypt.hashpw(pwd.encode('utf-8'), client_secret.encode('utf-8'))
    client_secret_sign = base64.b64encode(hashed).decode('utf-8')

    # 3) 쿼리스트링 파라미터 구성
    data_ = {
        "client_id": client_id,
        "timestamp": timestamp,
        "client_secret_sign": client_secret_sign,
        "grant_type": "client_credentials",
        "type": type_
    }
    query_string = urllib.parse.urlencode(data_)

    # 4) API 엔드포인트
    url = f"https://api.commerce.naver.com/external/v1/oauth2/token?{query_string}"

    # 5) 요청 헤더
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    # 재시도 로직
    for attempt in range(1, max_retries + 1):
        res = requests.post(url, headers=headers)

        if res.status_code == 200:
            res_data = res.json()
            if "access_token" in res_data:
                return res_data["access_token"]
            else:
                # 200이지만 access_token이 없다? => 문서 확인 필요
                raise ValueError(f"200 OK but no 'access_token' in response: {res_data}")
        else:
            # 에러 응답
            try:
                error_data = res.json()
            except:
                error_data = res.text
            print(f"[Attempt {attempt}] 토큰 요청 실패: status={res.status_code}, {error_data}")
            time.sleep(1)

    raise RuntimeError("토큰 요청이 반복 실패했습니다. 확인 필요.")


def get_last_changed_list(token):
    """
    예시: /last-changed-statuses API를 통해
    DISPATCHED 상태로 변경된 productOrderId 목록을 가져온다고 가정
    """
    url = "https://api.commerce.naver.com/external/v1/pay-order/seller/product-orders/last-changed-statuses"
    headers = {"Authorization": token}

    # 3) 조회 시작 시점 설정 (기본 3시간 전)
    now = datetime.now()
    before_date = now - timedelta(days=1)
    # 필요하다면 minutes=10, ,hours=3, days=1 등 호출부에서 조정

    # 4) ISO8601 포맷(UTC/로컬) 변환
    # 주의: astimezone() 호출 시 어떤 타임존인지 문서나 실제 응답을 보고 결정
    ios_format = before_date.astimezone().isoformat()

    params = {
        "lastChangedFrom": ios_format,
        "lastChangedType": "PAYED"
    }

    res = requests.get(url, headers=headers, params=params)
    res.raise_for_status()
    data = res.json()
    # data["data"]["lastChangeStatuses"] 배열
    return data.get("data", {}).get("lastChangeStatuses", [])


def get_product_orders_detail(token: str, product_order_ids: list[str]) -> dict:
    """
    네이버 커머스 API - '상품 주문 상세 내역 조회' (POST /external/v1/pay-order/seller/product-orders/query)

    Args:
        token: "Bearer ..." 형태로 사용될 인증 토큰 (문서/샘플에 따르면 Bearer prefix 필요)
        product_order_ids: 조회할 상품주문번호 리스트. 예: ["2025010791027401", "2025010791996471", ...]

    Returns:
        dict: 응답 JSON 객체
    """
    url = "https://api.commerce.naver.com/external/v1/pay-order/seller/product-orders/query"

    # 1) 요청 바디(payload) -> JSON
    payload = {
        "productOrderIds": product_order_ids,
        # 문서/샘플 코드 상 "quantityClaimCompatibility": True/False 여부가 필요할 수 있음
        "quantityClaimCompatibility": True
    }

    # 2) 요청 헤더
    #   - 샘플 코드에 따르면 'Authorization': "Bearer REPLACE_BEARER_TOKEN",
    #   - 'Content-Type': 'application/json'
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 3) POST 요청 (json=payload 로 하면, requests 가 자동으로 JSON 직렬화)
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()  # 4xx, 5xx 시 예외

    return response.json()

# SUNKREAM Legacy Backend API Design (V1)

## 1) 문서 목적
- 버전업(V2) 설계를 위해 현재 V1 백엔드의 구조와 API 계약을 코드 기준으로 정리한다.
- 기준 코드: 현재 레포지토리의 `users`, `products`, `orders` 앱 (`urls.py`, `views.py`, `models.py`, `tests.py`).

## 2) 아키텍처 구조

### 앱 경계
- `users`: 카카오 소셜 로그인, JWT 발급
- `products`: 상품 목록/상세, 브랜드 목록, 위시리스트
- `orders`: 입찰 생성/조회, 주문 생성, 가격 히스토리, 마이페이지 주문/입찰 내역
- `core`: 공통 `TimeStampModel(created_at, updated_at)`

### URL 구성
- 루트 라우팅(`sunkream/urls.py`)
- `/users` -> `users.urls`
- `/products` -> `products.urls`
- `/orders` -> `orders.urls`

### 인증/인가
- 로그인 API: `GET /users/login/kakao`
- 앱 내부 보호 API: `users.utils.login_decorator` 사용
- 보호 API 호출 시 `Authorization` 헤더에 서비스 JWT를 그대로 전달해야 함
- `Bearer <token>` 파싱 로직은 없음

## 3) 도메인 모델 요약

### User
- `id, email(unique), password(nullable), kakao_id(nullable), name, phone_number, address, point(default=1000000)`

### Product Domain
- `Brand(1) - (N) Product`
- `Product(1) - (N) ProductImage`
- `Product(1) - (N) ProductSize - (N) Size`
- `Wishlist`: `User` 와 `Product`의 N:M 연결

### Order/Bidding Domain
- `Bidding`: `user`, `bidding_status`, `bidding_position`, `product_size`, `price`
- `Order`: `order_status`, `bidding`, `buyer`, `seller`

### 상태값 ID 계약(코드 하드코딩)
- `BiddingStatus`
- `1: ON_BIDDING`
- `2: CONTRACTED`
- `BiddingPosition`
- `1: BUY`
- `2: SELL`
- `OrderStatus`
- `1: INSPECTION`
- `2: IN_TRANSIT`
- `3: DELIVERED`

## 4) API 명세 (V1 As-Is)

## 4.1 Users

### `GET /users/login/kakao`
- 설명: 카카오 액세스 토큰으로 사용자 조회/자동 가입 후 서비스 JWT 발급
- 인증: 카카오 토큰 필요 (`Authorization: <kakao_access_token>`)
- Request Body: 없음
- Success `201`
```json
{
  "access_token": "<service_jwt>"
}
```
- Error
- `401 {"messsage":"INVALID_TOKEN"}` (키 오타 존재)
- `400 {"message":"KEY_ERROR"}`
- `400 {"message":"JSON_DECODE_ERROR"}`
- `400 {"message":"JWT_DECODE_ERROR"}`
- `400 {"message":"CONNECTION_ERROR"}`

## 4.2 Products

### `POST /products/wishlist?product_id={id}`
- 설명: 위시리스트 토글(없으면 생성, 있으면 삭제)
- 인증: 필요
- Success
- `201 {"message":"WISH_CREATE_SUCCESS","wish_count":number}`
- `200 {"message":"WISH_DELETE_SUCCESS","wish_count":number}`
- Error
- `404 {"message:":"INVALID_PRODUCT_ID"}`
- `400 {"message":"KEY_ERROR"}`

### `GET /products/wishlist`
- 설명: 내 위시리스트 조회
- 인증: 필요
- Success `200`
```json
{
  "results": [
    {
      "id": 1,
      "brand": "nike",
      "name": "Jordan 1",
      "price": 100000,
      "image": [{"thumbnail": "https://..."}]
    }
  ]
}
```

### `GET /products/wishflag?product_id={id}`
- 설명: 특정 상품의 전체 위시 수 + 내 위시 여부
- 인증: 필요
- Success `200`
```json
{
  "results": {
    "wish_count": 10,
    "check_my_wish": true
  }
}
```
- Error
- `404 {"message:":"INVALID_PRODUCT_ID"}`

### `GET /products`
- 설명: 상품 리스트 조회(필터/정렬/페이지네이션)
- 인증: 불필요
- Query
- `brand_id`(복수 가능), `size_id`(복수 가능)
- `sort`: `now_buy_price | now_sell_price | premium`
- `search`, `start`, `stop`, `limit`(default 40), `offset`(default 0)
- Success `200`
```json
{
  "products_list": [
    {
      "id": 1,
      "brand": "nike",
      "name": "Jordan 1",
      "thumbnail_url": "https://...",
      "product_price": 300000,
      "release_price": 199000
    }
  ]
}
```

### `GET /products/brand`
- 설명: 브랜드 목록
- 인증: 불필요
- Success `200`
```json
{
  "brand_list": [
    {"brand_id": 1, "brand_name": "nike"}
  ]
}
```

### `GET /products/{product_id}`
- 설명: 상품 상세(이미지, 최근 체결가, 즉시구매/판매가, 관심 수)
- 인증: 불필요
- Success `200`
```json
{
  "product_detail": [
    {
      "product_id": 1,
      "name": "Jordan 1",
      "brand_name": "nike",
      "release_price": 199000,
      "model_number": "DZ5485-612",
      "image_list": ["https://..."],
      "recent_price": 310000,
      "buy_price": 320000,
      "sell_price": 300000,
      "total_wishlist": 55
    }
  ]
}
```
- Error
- `404 {"MESSAGE":"product_id_not_exist"}`

## 4.3 Orders

### `POST /orders/bidding/{productsize_id}/{position_id}`
- 설명: 입찰 생성
- 인증: 필요
- Path
- `position_id`: `1(BUY)` or `2(SELL)`
- Body
```json
{"price": 300000}
```
- Success `201 {"message":"SUCCESS"}`
- Error
- `404 {"message":"PRODUCT_SIZE_DOES_NOT_EXIST"}`
- `400 {"message":"INVALID_BIDDING_POSITION"}`
- `400 {"message":"KEY_ERROR"}`
- `400 {"message":"JSON_DECODE_ERROR"}`

### `GET /orders/bidding/{productsize_id}/{position_id}`
- 설명: 입찰 페이지 데이터 조회(상품/사이즈/호가/내 포인트)
- 인증: 필요
- Success `200`
```json
{
  "data": {
    "product_image_url": "https://...",
    "product_name": "Jordan 1",
    "product_brand": "nike",
    "product_model_number": "DZ5485-612",
    "size": 270,
    "sell_price": 300000,
    "buy_price": 320000,
    "user_point": 1000000,
    "bidding_id": 17,
    "bidding_price": 320000
  }
}
```

### `GET /orders/size-price/{product_id}/{position_id}`
- 설명: 주문 페이지 진입 시 사이즈별 최우선 호가 조회
- 인증: 필요
- Success `200`
```json
{
  "product_info": {
    "product_image_url": "https://...",
    "product_name": "Jordan 1",
    "product_brand": "nike",
    "product_model_number": "DZ5485-612"
  },
  "size_price_list": [
    {"productsize_id": 1, "size": 270, "bidding_id": 33, "bidding_price": 320000}
  ]
}
```

### `POST /orders/{bidding_id}`
- 설명: 즉시 체결 주문 생성 + 포인트 정산 + 입찰 상태 변경
- 인증: 필요
- Success `201 {"message":"SUCCESS"}`
- Error
- `404 {"message":"BIDDING_DOES_NOT_EXIST"}`
- `400 {"message":"INVALID_BIDDING_ID"}` (이미 체결된 입찰)
- `400 {"message":"INSUFFICIENT_POINT"}`

### `GET /orders/price/{product_id}`
- 설명: 시세 페이지 데이터(그래프, 체결 내역, 매도/매수 호가 집계)
- 인증: 불필요
- Query
- `size`(optional)
- `period`: `1m | 3m | 6m | 1y` (default `1y`)
- `sort`: `low_price | high_price | low_size | high_size | recent`
- `limit`(default 5), `offset`(default 0)
- Success `200`
```json
{
  "data": {
    "order_graph_data": [],
    "order_list": [],
    "sell_bidding_list": [{"price": 300000, "size": 270, "count": 2}],
    "buy_bidding_list": [{"price": 320000, "size": 270, "count": 1}]
  }
}
```

### `GET /orders`
- 설명: 마이페이지(구매/판매 주문, 진행중 입찰)
- 인증: 필요
- Success `200`
```json
{
  "data": {
    "user_name": "홍길동",
    "user_email": "user@example.com",
    "user_point": 1000000,
    "buy_order_count": 1,
    "buy_order_list": [],
    "sell_order_count": 1,
    "sell_order_list": [],
    "buy_on_bidding_count": 2,
    "buy_bidding_list": [],
    "sell_on_bidding_count": 1,
    "sell_bidding_list": []
  }
}
```

## 5) 비즈니스 규칙 요약
- 주문 생성 시(`POST /orders/{bidding_id}`)
- 기존 입찰 상태가 `ON_BIDDING(1)`이어야 함
- 주문 생성 후 해당 입찰 상태를 `CONTRACTED(2)`로 변경
- 포지션 기준으로 buyer/seller 및 포인트 이동 방향 결정
- 포인트 부족 시 주문 실패(`INSUFFICIENT_POINT`)

## 6) 문서화 누락 보강 항목

### 공통 인증 실패 응답
- 보호 API(`@login_decorator`) 공통 에러
- 헤더 누락: `401 {"message":"UNAUTHORIZED"}`
- 토큰 decode 실패: `401 {"MESSAGE":"INVALID_TOKEN"}`
- 사용자 없음: `401 {"MESSAGE":"INVALID_USER"}`

### 데이터/상태 전이 제약(암묵 규칙)
- 주문 생성은 단일 입찰(`bidding_id`)에 대해 1회 체결을 의도
- `bidding_status_id=2(CONTRACTED)`이면 재체결 불가
- 주문 생성 시 포인트는 buyer/seller 양쪽 계정에서 동시에 이동
- 주문 생성은 `transaction.atomic` 적용되어 포인트/주문/입찰상태가 한 트랜잭션으로 처리됨

### 운영 전 필수 Seed 데이터
- 다음 테이블의 고정 ID가 존재해야 API 정상 동작
- `bidding_status`: `1 ON_BIDDING`, `2 CONTRACTED`
- `bidding_positions`: `1 BUY`, `2 SELL`
- `order_status`: `1 INSPECTION`, `2 IN_TRANSIT`, `3 DELIVERED`

### 알려진 구현 이슈(As-Is)
- `DetailProductView`의 위시카운트 계산식이 `Wishlist.objects.filter(id=product_id)`라 실제 상품별 합계와 다를 수 있음
- `OrderListView`는 상품 이미지가 없는 경우 `productimage_set.all()[0]` 접근으로 예외 가능
- `PriceHistoryView`에서 `period`가 잘못된 값이면 기본 기간 계산이 datetime이 아닌 문자열로 들어갈 수 있음
- `POST /products/wishlist`는 Query String(`product_id`)에 의존하고 Body 스키마가 없음
- 에러 키가 `message`, `MESSAGE`, `message:`로 혼재

### 테스트와 실제 구현 차이(문서상 주의)
- `products/tests.py`의 상세 응답 예시는 현재 구현(`product_detail` list)과 다른 형태가 포함되어 있음
- 테스트 데이터/기대값 일부가 현재 뷰 코드와 불일치하므로, 계약 기준은 테스트보다 뷰 코드를 우선해야 함

## 7) V2 버전업 시 우선 정비 포인트 (개선안)

### P0 (반드시 먼저)
- 인증 표준화
- `Authorization: Bearer <access_token>` 고정
- JWT 파싱/예외 응답을 전역 인증 클래스에서 일괄 처리
- 응답/에러 규격 통일
- 성공/실패 공통 스키마 정의 (`code`, `message`, `data`, `errors`)
- 대소문자/오타/콜론 포함 key 제거
- URL 버저닝
- `/api/v1/...`로 분리하고 레거시는 유지(점진 이관)
- 상태값 하드코딩 제거
- 코드 enum ID 의존 제거, enum-like 모델 + fixture/seed로 보장

### P1 (초기 안정화)
- DB 정합성 제약 추가
- `Wishlist(user_id, product_id)` unique
- `ProductSize(product_id, size_id)` unique
- 주문 중복 방지 정책 수립(입찰 1건당 주문 1건 강제 여부 명시)
- 동시성 제어 강화
- 주문 체결 시 `select_for_update` 등으로 race condition 방지
- 입력 검증 강화
- 쿼리 파라미터 타입/범위 검증 (`limit`, `offset`, `period`, `sort`)

### P2 (운영/포트폴리오 품질)
- OpenAPI 자동 문서화
- DRF serializer 기반 request/response schema 생성
- Swagger UI/ReDoc 제공
- 테스트 전략 재정립
- API 계약 테스트(성공/실패/권한/경계값)
- 서비스 레이어 단위 테스트 추가
- 관측성
- 요청 ID, 구조화 로그, 에러 코드 기반 모니터링

## 8) DRF 재구축 시 권장 리소스 설계
- `POST /api/v1/auth/kakao`
- `GET /api/v1/products`
- `GET /api/v1/products/{product_id}`
- `POST /api/v1/products/{product_id}/wishlist`
- `DELETE /api/v1/products/{product_id}/wishlist`
- `GET /api/v1/products/{product_id}/price-history`
- `POST /api/v1/bids`
- `GET /api/v1/bids`
- `POST /api/v1/orders`
- `GET /api/v1/me/orders`

## 9) 마이그레이션 체크리스트(요약)
- 레거시 API 계약 스냅샷 확정
- V2 API 명세(OpenAPI) 먼저 확정
- 엔드포인트 단위 병행 운영/스위칭
- 레거시 제거 전 클라이언트 전환 완료 확인

## 10) DRF 구현 최소 계약

### 공통 규약
- Base URL: `/api/v1`
- 인증 헤더: `Authorization: Bearer <access_token>`
- Content-Type: `application/json`
- 페이지네이션: `limit`(default 20, max 100), `offset`(default 0)

### 공통 응답 포맷
- 성공: `{"code":"OK","message":"success","data":...}`
- 실패: `{"code":"<ERROR_CODE>","message":"...","errors":{...}}`
- 필수 에러코드: `UNAUTHORIZED`, `INVALID_PARAMETER`, `NOT_FOUND`, `CONFLICT`, `INSUFFICIENT_POINT`

### 리소스/권한
- 익명 허용
- `POST /api/v1/auth/kakao`
- `GET /api/v1/products`
- `GET /api/v1/products/{product_id}`
- `GET /api/v1/products/{product_id}/price-history`
- 인증 필요
- `POST /api/v1/products/{product_id}/wishlist`
- `DELETE /api/v1/products/{product_id}/wishlist`
- `POST /api/v1/bids`
- `GET /api/v1/bids`
- `POST /api/v1/orders`
- `GET /api/v1/me/orders`

### 핵심 입력 검증
- `price >= 1`
- `position in ["BUY", "SELL"]`
- `period in ["1m","3m","6m","1y"]`
- `sort`는 엔드포인트별 허용값만 통과
- FK 미존재(`product_id`, `product_size_id`, `bidding_id`)는 일관된 `NOT_FOUND` 처리

### 정합성/동시성 제약
- `Wishlist(user_id, product_id)` unique
- `ProductSize(product_id, size_id)` unique
- 주문 생성 시 `bidding` row lock(`select_for_update`) 적용
- 이미 체결된 입찰은 `CONFLICT` 반환

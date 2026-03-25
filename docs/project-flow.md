# 프로젝트 흐름

## 이 문서가 다루는 범위

이 문서는 SUNKREAM API에서 요청이 어떻게 처리되는지와 주요 엔드포인트가 어떤 흐름으로 동작하는지를 요약합니다.

정적 아키텍처, 도메인 경계, 운영 메모는 `docs/architecture-overview.md`를 보면 됩니다.

## 전역 요청 생명주기

### 미들웨어부터 응답까지

```text
Client Request
  -> SecurityMiddleware
  -> SessionMiddleware
  -> CommonMiddleware
  -> CsrfViewMiddleware
  -> AuthenticationMiddleware
  -> MessageMiddleware
  -> XFrameOptionsMiddleware
  -> DRF View
     -> permission check
     -> serializer validation
     -> business logic
     -> ORM queries / transaction
     -> serializer or helper response
  -> custom_exception_handler on error
  -> Client Response
```

### 공통 응답 규칙

- 성공 응답은 `success_response()`로 감쌉니다.
- 에러 응답은 `custom_exception_handler`가 공통 형식으로 정규화합니다.
- 목록 API는 공통 페이지네이션 형식이 필요할 때 `SuccessResponseListMixin`을 사용합니다.

## 엔드포인트별 흐름

### 1. 카카오 로그인

`POST /api/v1/auth/kakao/`

```text
access_token payload
  -> KakaoLoginSerializer validation
  -> GET https://kapi.kakao.com/v2/user/me
  -> request failure => 401 UNAUTHORIZED
  -> non-200 response => 401 UNAUTHORIZED
  -> parse kakao_id, email, nickname
  -> find user by kakao_id
     -> exists: reuse account
     -> missing: get_or_create by email
        -> new email: create new user
        -> existing email without kakao_id: link account
        -> existing email with another kakao_id: 409 CONFLICT
  -> issue SimpleJWT refresh/access token
  -> return access, refresh, is_new_user
```

### 2. 토큰 재발급

`POST /api/v1/auth/token/refresh/`

```text
refresh token payload
  -> SimpleJWT TokenRefreshView
  -> valid token: return new access token
  -> invalid token: 401 UNAUTHORIZED
```

### 3. 상품 목록

`GET /api/v1/products/`

```text
public request
  -> Product queryset with brand select_related
  -> optional brand_id filter
  -> optional size_id filter through product_sizes
  -> optional name search
  -> distinct()
  -> paginate with limit/offset
  -> ProductListSerializer
  -> common paginated success response
```

### 4. 상품 상세

`GET /api/v1/products/<id>/`

```text
public request
  -> Product queryset with brand, images, wishlist count
  -> object lookup
  -> 404 if missing
  -> ProductDetailSerializer
  -> success response
```

### 5. 관리자 상품 생성, 수정, 삭제

`POST /api/v1/products/`
`PATCH /api/v1/products/<id>/`
`DELETE /api/v1/products/<id>/`

```text
admin-only request
  -> serializer validation
  -> create: validate brand + sizes, create product, bulk_create ProductSize rows
  -> update: patch fields from validated payload
  -> delete: remove product
     -> pre_delete signal marks active bids on that product as CANCELLED
```

### 6. 브랜드 목록

`GET /api/v1/products/brands/`

```text
public request
  -> Brand.objects.all()
  -> model ordering by name
  -> BrandSerializer
  -> success response
```

### 7. 위시리스트 추가 및 삭제

`POST /api/v1/products/<id>/wishlist/`
`DELETE /api/v1/products/<id>/wishlist/`

```text
authenticated request
  -> get product or 404
  -> POST:
     -> create Wishlist row
     -> uniqueness violation => 409 CONFLICT
     -> success 201
  -> DELETE:
     -> delete Wishlist row for user + product
     -> no row deleted => 404
     -> success 204
```

### 8. 입찰 생성과 내 입찰 목록

`POST /api/v1/bids/`
`GET /api/v1/bids/`

```text
authenticated request
  -> POST:
     -> BidCreateSerializer validates product_size_id, position, price
     -> fetch ProductSize or 404
     -> create Bidding with ON_BIDDING status
     -> success 201
  -> GET:
     -> filter bids by request.user
     -> join product and size
     -> order by newest first
     -> paginate and serialize
```

### 9. 입찰 기반 주문 생성

`POST /api/v1/orders/`

```text
authenticated request with bidding_id
  -> OrderCreateSerializer validation
  -> transaction.atomic()
  -> select_for_update() on target bid
  -> reject missing bid => 404
  -> reject contracted bid => 409
  -> reject own bid => 400
  -> determine buyer/seller from bid position
     -> SELL bid: buyer=request.user, seller=bid.user
     -> BUY bid: buyer=bid.user, seller=request.user
  -> update buyer point with F("point") - price
  -> update seller point with F("point") + price
  -> check constraint violation => 400 INSUFFICIENT_POINT
  -> set bid status to CONTRACTED
  -> create Order row
  -> commit
  -> success 201
```

### 10. 내 주문 요약

`GET /api/v1/me/orders/`

```text
authenticated request
  -> fetch latest 100 buy orders
  -> fetch latest 100 sell orders
  -> fetch latest 100 active bids
  -> include user profile summary and point balance
  -> serialize each list
  -> success response
```

### 11. 주문 상태 변경

`PATCH /api/v1/orders/<id>/status/`

```text
authenticated request
  -> transaction.atomic()
  -> select_for_update() on order
  -> reject missing order => 404
  -> reject non-seller => 403
  -> validate requested status
  -> enforce forward-only transition
     INSPECTION -> IN_TRANSIT -> DELIVERED
  -> save new status
  -> success response
```

### 12. 입찰 취소

`DELETE /api/v1/bids/<id>/`

```text
authenticated request
  -> transaction.atomic()
  -> select_for_update() on user's bid
  -> reject missing/other user's bid => 404
  -> reject non-active bid => 409
  -> set status to CANCELLED
  -> success response
```

### 13. 시세 히스토리

`GET /api/v1/products/<id>/price-history/`

```text
public request
  -> confirm product exists
  -> fetch latest 100 orders for the product
  -> map order history with price, size, created_at
  -> aggregate active SELL bids by price/size ascending
  -> aggregate active BUY bids by price/size descending
  -> success response with order_history, sell_bids, buy_bids
```

## 현재 공통 메모

- 대부분의 에러 처리는 직접 응답을 만들기보다 예외를 발생시키는 방식으로 통일돼 있습니다.
- 주문 생성, 입찰 취소, 주문 상태 변경은 동시성에 민감한 엔드포인트입니다.
- 주문 생성에서는 아직 취소된 입찰을 명시적으로 거부하지 않는 논리 공백이 남아 있습니다.

## 권장 읽기 순서

1. `docs/architecture-overview.md`
2. `docs/project-flow.md`
3. `orders/views.py`
4. `products/views.py`
5. `users/views.py`

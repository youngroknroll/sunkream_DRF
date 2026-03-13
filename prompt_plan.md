# Sunkream API - 구현 계획

## Phase 1: 입찰 취소 (Bid Cancellation) ✅

- [x] `orders/models.py` — Bidding.Status에 CANCELLED 추가
- [x] `orders/views.py` — BidCancelView 구현
- [x] `orders/urls.py` — DELETE /bids/<id>/ URL 추가
- [x] 마이그레이션 생성 및 적용
- [x] `tests/test_orders.py` — 입찰 취소 테스트 4건

## Phase 2: 주문 상태 변경 (Order Status Update) ✅

- [x] `orders/serializers.py` — OrderStatusUpdateSerializer, VALID_STATUS_TRANSITIONS 추가
- [x] `orders/views.py` — OrderStatusUpdateView 구현
- [x] `orders/urls.py` — PATCH /orders/<id>/status/ URL 추가
- [x] `core/exceptions.py` — ForbiddenError 추가
- [x] `tests/test_orders.py` — 상태 전이 테스트 5건

## Phase 3: 상품 Admin CRUD ✅

- [x] `products/serializers.py` — ProductCreateSerializer, ProductUpdateSerializer 추가
- [x] `products/views.py` — ProductListView를 ListCreateAPIView로 변경, ProductDetailView에 patch/delete 추가
- [x] 기존 경로 공유 방식 채택 (get_permissions()로 method-based 권한 분리)
- [x] `tests/test_products.py` — Admin CRUD 테스트 12건

## Phase 4: 앱 간 결합 분리 (Signal Decoupling) ✅

- [x] `orders/signals.py` — pre_delete signal로 상품 삭제 시 활성 입찰 연쇄 취소
- [x] `orders/apps.py` — ready()에서 signal 등록
- [x] `products/views.py` — orders 앱 import 제거 (단방향 의존성 유지)

## Phase 5: DB 마이그레이션 ✅

- [x] SQLite → PostgreSQL 전환
- [x] `psycopg[binary]` 패키지 추가
- [x] `django-environ`으로 DATABASE_URL 환경변수 처리
- [x] 전체 테스트 통과 확인 (83건)

## 의존성

- Phase 1 → Phase 2 → Phase 3 순서 구현 완료
- Phase 4는 Phase 3의 상품 삭제 로직에서 발견된 결합 문제 해결
- Phase 5는 독립적 (인프라 변경)

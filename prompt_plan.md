# Sunkream API - 구현 계획

## Phase 1: 입찰 취소 (Bid Cancellation)

- [ ] `orders/models.py` — Bidding.Status에 CANCELLED 추가
- [ ] `orders/views.py` — BidCancelView 구현
- [ ] `orders/urls.py` — DELETE /bids/<id>/ URL 추가
- [ ] 마이그레이션 생성 및 적용
- [ ] `tests/test_orders.py` — 입찰 취소 테스트 (성공/CONTRACTED 실패/타인 입찰/미인증)

## Phase 2: 주문 상태 변경 (Order Status Update)

- [ ] `orders/serializers.py` — OrderStatusUpdateSerializer 추가
- [ ] `orders/views.py` — OrderStatusUpdateView 구현
- [ ] `orders/urls.py` — PATCH /orders/<id>/status/ URL 추가
- [ ] `tests/test_orders.py` — 상태 전이 테스트 (순방향 성공/역방향 실패/비판매자/미인증)

## Phase 3: 상품 Admin CRUD

- [ ] `products/serializers.py` — ProductCreateSerializer, ProductUpdateSerializer 추가
- [ ] `products/views.py` — ProductCreateView, ProductUpdateView, ProductDeleteView 추가
- [ ] `products/urls.py` 또는 별도 admin URL — Admin 엔드포인트 추가
- [ ] `sunkream_api/urls.py` — admin products URL include
- [ ] `tests/test_products.py` — Admin CRUD 테스트 (생성/수정/삭제/권한/활성입찰 삭제불가)

## 의존성

- Phase 1 → Phase 2 → Phase 3 순서 권장
- Phase 1의 CANCELLED 상태는 Phase 3의 삭제 제약 로직에서 참조됨

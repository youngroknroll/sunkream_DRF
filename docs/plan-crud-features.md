# CRUD 기능 확장 계획

> 3가지 기능: 주문 상태 변경, 입찰 취소, 상품 관리(Admin CRUD)

---

## 1. 주문 상태 변경

### 현재 상태

- Order.Status: `INSPECTION` → `IN_TRANSIT` → `DELIVERED` (모델에 정의됨)
- 상태 변경 API 없음 — 주문 생성 후 항상 `INSPECTION`에 머무름

### 설계

**엔드포인트**: `PATCH /api/v1/orders/<int:order_id>/status/`

**권한**: `IsAuthenticated` — 판매자(seller)만 상태 변경 가능

**비즈니스 규칙**:
- 순방향 전이만 허용: `INSPECTION → IN_TRANSIT → DELIVERED`
- 역방향 전이 불가 (400 Bad Request)
- 판매자가 아닌 사용자가 요청 시 403 Forbidden

**요청/응답**:
```json
// Request
{ "status": "IN_TRANSIT" }

// Response (200)
{ "code": "OK", "message": "Order status updated.", "data": { "id": 1, "status": "IN_TRANSIT" } }

// Error (400)
{ "code": "INVALID_PARAMETER", "message": "Invalid status transition." }
```

**변경 파일**:
| 파일 | 변경 내용 |
|------|-----------|
| `orders/views.py` | `OrderStatusUpdateView` 추가 |
| `orders/serializers.py` | `OrderStatusUpdateSerializer` 추가 |
| `orders/urls.py` | URL 패턴 추가 |
| `core/exceptions.py` | `ForbiddenError` 추가 (선택) |
| `tests/test_orders.py` | 상태 변경 테스트 추가 |

### 상태 전이 검증 로직

```python
VALID_TRANSITIONS = {
    "INSPECTION": "IN_TRANSIT",
    "IN_TRANSIT": "DELIVERED",
}
```

현재 상태에서 다음 상태로만 전이 가능. 그 외는 `ValidationError`.

---

## 2. 입찰 취소

### 현재 상태

- Bidding.Status: `ON_BIDDING`, `CONTRACTED`
- 취소 기능 없음 — 한번 등록하면 변경/삭제 불가

### 설계

**방법 A — 새 상태 추가** (권장):
- `CANCELLED` 상태를 Bidding.Status에 추가
- 기존 데이터/로직에 영향 최소화
- PriceHistoryView 등에서 `ON_BIDDING` 필터 이미 적용되어 있어 호환성 좋음

**방법 B — 레코드 삭제**:
- DB에서 실제 삭제
- 이력 추적 불가 → 비추천

**엔드포인트**: `DELETE /api/v1/bids/<int:bid_id>/`

**권한**: `IsAuthenticated` — 본인 입찰만 취소 가능

**비즈니스 규칙**:
- `ON_BIDDING` 상태만 취소 가능
- `CONTRACTED` 상태는 취소 불가 (409 Conflict)
- 다른 사용자의 입찰 취소 불가 (404 Not Found — 소유자가 아니면 존재 자체를 노출하지 않음)

**요청/응답**:
```json
// Response (200)
{ "code": "OK", "message": "Bid cancelled." }

// Error (409)
{ "code": "CONFLICT", "message": "Contracted bid cannot be cancelled." }
```

**변경 파일**:
| 파일 | 변경 내용 |
|------|-----------|
| `orders/models.py` | `Bidding.Status`에 `CANCELLED` 추가 |
| `orders/views.py` | `BidCancelView` 추가 |
| `orders/urls.py` | URL 패턴 추가 |
| `tests/test_orders.py` | 입찰 취소 테스트 추가 |

### 마이그레이션 영향

- `CANCELLED` 상태 추가는 기존 데이터에 영향 없음 (새 choice 값만 추가)
- `MyOrdersView`의 `active_bids` 쿼리는 이미 `status=ON_BIDDING` 필터 → 호환

---

## 3. 상품 관리 (Admin CRUD)

### 현재 상태

- 상품 조회(List/Detail)만 존재
- 생성/수정/삭제 API 없음
- KREAM은 관리자만 상품 등록 가능 (사용자는 입찰만)

### 설계

**권한**: `IsAdminUser` — 관리자(is_staff=True)만 접근 가능

**엔드포인트**:

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/products/` | 상품 생성 |
| PATCH | `/api/v1/products/<int:pk>/` | 상품 수정 |
| DELETE | `/api/v1/products/<int:pk>/` | 상품 삭제 |

**상품 생성 요청**:
```json
{
  "brand_id": 1,
  "name": "Air Jordan 1 Retro High OG",
  "model_number": "DZ5485-612",
  "release_price": 209000,
  "thumbnail_url": "https://...",
  "sizes": [250, 260, 270, 280]
}
```

**상품 수정 요청** (부분 수정 지원):
```json
{
  "name": "Air Jordan 1 Retro High OG Chicago",
  "release_price": 219000
}
```

**비즈니스 규칙**:
- 상품 생성 시 `brand_id`는 기존 Brand 참조 필수 (없으면 404)
- `sizes` 배열의 각 값은 Size 테이블에 존재해야 함 (없으면 자동 생성 or 404 — 확인 필요)
- 상품 삭제 시 연관된 활성 입찰(ON_BIDDING)이 있으면 삭제 불가 (409 Conflict)
- 상품 수정 시 `sizes`는 별도 엔드포인트로 분리 가능 (복잡도 관리)

**변경 파일**:
| 파일 | 변경 내용 |
|------|-----------|
| `products/views.py` | `ProductCreateView`, `ProductUpdateView`, `ProductDeleteView` 추가 |
| `products/serializers.py` | `ProductCreateSerializer`, `ProductUpdateSerializer` 추가 |
| `products/urls.py` | URL 패턴 추가 |
| `core/exceptions.py` | 필요 시 예외 추가 |
| `tests/test_products.py` | Admin CRUD 테스트 추가 |

### URL 설계 고려사항

기존 `ProductListView`(GET)와 `ProductCreateView`(POST)가 같은 경로(`/api/v1/products/`)를 공유할 수 있음:
- **방법 A**: `ProductListView`를 `ListCreateAPIView`로 변경 (권한 분리 필요)
- **방법 B**: 별도 Admin prefix 사용 — `POST /api/v1/admin/products/`

**방법 B 권장** — 권한 분리가 명확하고 기존 코드 수정 최소화.

---

## 구현 순서

```
Phase 1: 입찰 취소 (가장 단순, 모델 변경 포함)
  ├── models.py — CANCELLED 상태 추가
  ├── views.py — BidCancelView
  ├── urls.py — URL 추가
  ├── migration 생성/적용
  └── tests — 취소 성공/실패 케이스

Phase 2: 주문 상태 변경 (모델 변경 없음)
  ├── serializers.py — OrderStatusUpdateSerializer
  ├── views.py — OrderStatusUpdateView
  ├── urls.py — URL 추가
  └── tests — 전이 성공/실패, 권한 케이스

Phase 3: 상품 Admin CRUD (가장 복잡)
  ├── serializers.py — Create/Update serializer
  ├── views.py — Create/Update/Delete views
  ├── urls.py — Admin URL 추가
  └── tests — CRUD 전체 + 권한 + 삭제 제약
```

---

## 의사결정 필요 사항

| # | 질문 | 선택지 | 권장 |
|---|------|--------|------|
| 1 | 입찰 취소 방식 | A: CANCELLED 상태 추가 / B: DB 삭제 | **A** (이력 보존) |
| 2 | 상품 Admin URL | A: 기존 경로 공유 / B: `/admin/` prefix | **B** (권한 분리 명확) |
| 3 | 상품 생성 시 없는 Size | A: 자동 생성 / B: 404 에러 | 확인 필요 |
| 4 | 상품 삭제 시 활성 입찰 존재 | A: 삭제 불가(409) / B: 연쇄 취소 후 삭제 | **A** (안전) |

---

## 테스트 계획

### Phase 1: 입찰 취소
- [ ] ON_BIDDING 입찰 취소 성공
- [ ] CONTRACTED 입찰 취소 실패 (409)
- [ ] 타인 입찰 취소 시도 (404)
- [ ] 미인증 사용자 (401)

### Phase 2: 주문 상태 변경
- [ ] INSPECTION → IN_TRANSIT 성공
- [ ] IN_TRANSIT → DELIVERED 성공
- [ ] 역방향 전이 실패 (400)
- [ ] 판매자가 아닌 사용자 (403)
- [ ] 미인증 사용자 (401)

### Phase 3: 상품 Admin CRUD
- [ ] Admin 상품 생성 성공
- [ ] Admin 상품 수정 성공 (부분 수정)
- [ ] Admin 상품 삭제 성공
- [ ] 활성 입찰 있는 상품 삭제 실패 (409)
- [ ] 일반 사용자 접근 (403)
- [ ] 미인증 사용자 (401)
- [ ] 존재하지 않는 brand_id (404)

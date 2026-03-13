# CRUD 기능 확장 계획

> 3가지 기능: 주문 상태 변경, 입찰 취소, 상품 관리(Admin CRUD)
> **상태: 구현 완료**

---

## 1. 주문 상태 변경 ✅

### 현재 상태

- Order.Status: `INSPECTION` → `IN_TRANSIT` → `DELIVERED` (모델에 정의됨)
- ~~상태 변경 API 없음~~ → **구현 완료**

### 설계

**엔드포인트**: `PATCH /api/v1/orders/<int:order_id>/status/`

**권한**: `IsAuthenticated` — 판매자(seller)만 상태 변경 가능

**비즈니스 규칙**:
- 순방향 전이만 허용: `INSPECTION → IN_TRANSIT → DELIVERED`
- 역방향 전이 불가 (400 Bad Request)
- 판매자가 아닌 사용자가 요청 시 403 Forbidden (`ForbiddenError`)

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
| `orders/serializers.py` | `OrderStatusUpdateSerializer`, `VALID_STATUS_TRANSITIONS` 추가 |
| `orders/urls.py` | URL 패턴 추가 |
| `core/exceptions.py` | `ForbiddenError` 추가 |
| `tests/test_orders.py` | 상태 변경 테스트 5건 추가 |

### 상태 전이 검증 로직

```python
VALID_STATUS_TRANSITIONS = {
    Order.Status.INSPECTION: Order.Status.IN_TRANSIT,
    Order.Status.IN_TRANSIT: Order.Status.DELIVERED,
}
```

현재 상태에서 다음 상태로만 전이 가능. 그 외는 `ValidationError`.

---

## 2. 입찰 취소 ✅

### 현재 상태

- Bidding.Status: `ON_BIDDING`, `CONTRACTED`, **`CANCELLED`** (추가됨)
- ~~취소 기능 없음~~ → **구현 완료**

### 설계

**채택: 방법 A — CANCELLED 상태 추가** (soft delete 패턴)
- 기존 데이터/로직에 영향 최소화
- PriceHistoryView 등에서 `ON_BIDDING` 필터 이미 적용되어 있어 호환성 좋음

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
{ "code": "CONFLICT", "message": "Only active bids can be cancelled." }
```

**변경 파일**:
| 파일 | 변경 내용 |
|------|-----------|
| `orders/models.py` | `Bidding.Status`에 `CANCELLED` 추가 |
| `orders/views.py` | `BidCancelView` 추가 |
| `orders/urls.py` | URL 패턴 추가 |
| `tests/test_orders.py` | 입찰 취소 테스트 4건 추가 |

---

## 3. 상품 관리 (Admin CRUD) ✅

### 현재 상태

- ~~상품 조회(List/Detail)만 존재~~ → **CRUD 전체 구현 완료**

### 설계

**권한**: `IsAdminUser` — 관리자(is_staff=True)만 접근 가능

**채택: 기존 경로 공유** (method-based `get_permissions()` 분리)
- 별도 `/admin/` prefix 없이 기존 endpoint에서 GET=AllowAny, POST/PATCH/DELETE=IsAdminUser
- 오버코딩 방지, DRF의 `get_permissions()` 패턴 활용

**엔드포인트**:

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/products/` | 상품 생성 (Admin) |
| PATCH | `/api/v1/products/<int:pk>/` | 상품 수정 (Admin) |
| DELETE | `/api/v1/products/<int:pk>/` | 상품 삭제 (Admin) |

**비즈니스 규칙**:
- 상품 생성 시 `brand_id`는 기존 Brand 참조 필수 (없으면 404)
- `sizes` 배열의 각 값은 Size 테이블에 존재해야 함 (**없으면 에러** — 자동 생성 안함)
- 상품 삭제 시 **활성 입찰 연쇄 취소 후 삭제** (`pre_delete` signal)

**변경 파일**:
| 파일 | 변경 내용 |
|------|-----------|
| `products/views.py` | `ProductListView` → `ListCreateAPIView`, `ProductDetailView`에 `patch()`/`delete()` 추가 |
| `products/serializers.py` | `ProductCreateSerializer`, `ProductUpdateSerializer` 추가 |
| `tests/test_products.py` | Admin CRUD 테스트 12건 추가 |

### Signal 기반 앱 간 결합 분리

상품 삭제 시 활성 입찰 취소 로직을 `products` 앱에서 직접 처리하면 `orders` 앱과의 양방향 결합이 발생.

**해결**: `orders/signals.py`에 `pre_delete` signal 등록

```python
# orders/signals.py
@receiver(pre_delete, sender=Product)
def cancel_active_bids_on_product_delete(sender, instance, **kwargs):
    Bidding.objects.filter(
        product_size__product=instance,
        status=Bidding.Status.ON_BIDDING,
    ).update(status=Bidding.Status.CANCELLED)
```

- `orders` → `products` 방향 참조만 유지 (단방향)
- `products` 앱은 `orders` 앱의 존재를 알 필요 없음
- `orders/apps.py`의 `ready()`에서 signal 모듈 import

---

## 의사결정 결과

| # | 질문 | 선택 | 이유 |
|---|------|------|------|
| 1 | 입찰 취소 방식 | **A: CANCELLED 상태 추가** | 이력 보존, 기존 쿼리 호환 |
| 2 | 상품 Admin URL | **A: 기존 경로 공유** | 오버코딩 방지, get_permissions() 활용 |
| 3 | 상품 생성 시 없는 Size | **B: 에러 반환** | 데이터 정합성 우선 |
| 4 | 상품 삭제 시 활성 입찰 | **B: 연쇄 취소 후 삭제** | pre_delete signal로 결합 분리 |

---

## 테스트 결과 (83건 전체 통과)

### Phase 1: 입찰 취소
- [x] ON_BIDDING 입찰 취소 성공
- [x] CONTRACTED 입찰 취소 실패 (409)
- [x] 타인 입찰 취소 시도 (404)
- [x] 미인증 사용자 (401/403)

### Phase 2: 주문 상태 변경
- [x] INSPECTION → IN_TRANSIT 성공
- [x] IN_TRANSIT → DELIVERED 성공
- [x] 역방향 전이 실패 (400)
- [x] 판매자가 아닌 사용자 (403)
- [x] 미인증 사용자 (401/403)

### Phase 3: 상품 Admin CRUD
- [x] Admin 상품 생성 성공
- [x] Admin 상품 수정 성공 (부분 수정)
- [x] Admin 상품 삭제 성공
- [x] 활성 입찰 있는 상품 삭제 → 연쇄 취소 확인
- [x] 일반 사용자 접근 (403)
- [x] 미인증 사용자 (401/403)
- [x] 존재하지 않는 brand_id (404)
- [x] 존재하지 않는 size (400)
- [x] 필수 필드 누락 (400)
- [x] 빈 요청 수정 (200)
- [x] 삭제 시 활성 입찰 연쇄 취소
- [x] 삭제 시 204 No Content

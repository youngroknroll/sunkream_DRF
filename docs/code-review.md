# SUNKREAM DRF 코드 리뷰 — 버그 및 개선사항

## 1. 버그 / 동시성 이슈

### 1-1. User point 갱신 시 race condition (심각도: 높음)

**파일:** `orders/views.py` L98-101

**현상:**
`OrderCreateView.create()`에서 `Bidding`만 `select_for_update()`로 잠기고,
buyer/seller User 행은 잠기지 않는다.
동일 buyer가 동시에 두 건 이상 주문하면 point가 정확히 차감되지 않을 수 있다 (lost update).

**현재 코드:**
```python
with transaction.atomic():
    bidding = Bidding.objects.select_for_update().get(pk=bidding_id)
    # ... 검증 로직 ...
    buyer.point -= bidding.price
    seller.point += bidding.price
    buyer.save(update_fields=["point"])
    seller.save(update_fields=["point"])
```

**문제 시나리오:**
1. Transaction A: buyer.point 읽음 → 1,000,000
2. Transaction B: buyer.point 읽음 → 1,000,000 (A 커밋 전)
3. Transaction A: point = 1,000,000 - 300,000 = 700,000 저장
4. Transaction B: point = 1,000,000 - 200,000 = 800,000 저장
5. 결과: 500,000 차감되어야 하지만 200,000만 차감됨

> SQLite는 DB 레벨 잠금이라 재현이 어렵지만, PostgreSQL/MySQL 프로덕션 환경에서는 실제 발생한다.

**수정안 A — F() expression:**
```python
from django.db.models import F

User.objects.filter(pk=buyer.pk).update(point=F('point') - bidding.price)
User.objects.filter(pk=seller.pk).update(point=F('point') + bidding.price)
```

**수정안 B — User도 select_for_update:**
```python
buyer = User.objects.select_for_update().get(pk=buyer.pk)
seller = User.objects.select_for_update().get(pk=seller.pk)
buyer.point -= bidding.price
seller.point += bidding.price
buyer.save(update_fields=["point"])
seller.save(update_fields=["point"])
```

### 1-2. 잔액 부족 체크와 차감 사이 gap (심각도: 높음)

**파일:** `orders/views.py` L92-100

**현상:**
잔액 체크(`buyer.point < bidding.price`)는 잠금 없이 읽은 값을 기준으로 한다.
수정안 A(F expression)를 적용하면, 잔액 체크 시점의 point가 최신 값인지 보장할 수 없다.

**수정안:**
F expression + DB 제약(CheckConstraint)을 조합하여 음수 방지:
```python
# models.py
class CustomUser(...):
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(point__gte=0),
                name="point_non_negative",
            ),
        ]
```
또는 수정안 B(select_for_update)로 잠금 후 체크하면 읽기 시점이 보장된다.

---

## 2. 설계 / 일관성 문제

### 2-1. 에러 응답 방식 불일치 (심각도: 중간)

**현상:**
일부 에러는 custom exception handler를 경유하고, 일부는 직접 `Response()`를 반환한다.
handler가 변경되면 직접 Response 부분은 영향받지 않아 포맷이 분기될 수 있다.

| 위치 | 에러 | 방식 |
|------|------|------|
| `orders/views.py` L79-82 | CONFLICT (이미 체결) | 직접 Response |
| `orders/views.py` L93-96 | INSUFFICIENT_POINT | 직접 Response |
| `products/views.py` L95-98 | CONFLICT (위시 중복) | 직접 Response |
| `orders/views.py` L85 | 자기 입찰 매칭 | raise ValidationError → handler 경유 |

**수정안:**
커스텀 예외 클래스를 정의하고 모두 raise로 통일:
```python
# core/exceptions.py
from rest_framework.exceptions import APIException

class ConflictError(APIException):
    status_code = 409
    default_detail = "Conflict."
    default_code = "CONFLICT"

class InsufficientPointError(APIException):
    status_code = 400
    default_detail = "Insufficient points."
    default_code = "INSUFFICIENT_POINT"
```

### 2-2. Serializer에서 NotFound raise (심각도: 중간)

**파일:** `orders/serializers.py` L13-15

**현상:**
`BidCreateSerializer.validate_product_size_id()`에서 `NotFound`를 raise하면
serializer 검증 흐름(여러 필드 에러 수집)을 중단한다.
DRF serializer validation에서는 `ValidationError`가 표준이며,
리소스 존재 여부 검증은 view 레벨에서 수행하는 것이 관례.

**수정안:**
```python
# orders/serializers.py — validate만 수행
class BidCreateSerializer(serializers.Serializer):
    product_size_id = serializers.IntegerField()
    position = serializers.ChoiceField(choices=Bidding.Position.choices)
    price = serializers.IntegerField(min_value=1)

# orders/views.py — 존재 여부는 view에서
def create(self, request, *args, **kwargs):
    serializer = BidCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        product_size = ProductSize.objects.get(pk=serializer.validated_data["product_size_id"])
    except ProductSize.DoesNotExist:
        raise NotFound("Product size not found.")
    ...
```

### 2-3. PriceHistoryView 내부 import (심각도: 낮음)

**파일:** `orders/views.py` L148

**현상:**
`from products.models import Product`가 메서드 내부에 있다.
같은 파일 상단에서 `from products.models import ProductSize`는 이미 import하고 있으므로
순환참조 문제가 아니다. 상단으로 이동 가능.

### 2-4. KAKAO_REST_API_KEY 미사용 (심각도: 낮음)

**파일:** `sunkream_api/settings.py` L116

**현상:**
`KAKAO_REST_API_KEY = env("KAKAO_REST_API_KEY", default="")`가 정의되어 있지만
어디에서도 참조하지 않는다. Dead code.

---

## 3. 테스트 커버리지 부족

### 3-1. BUY 입찰에 대한 주문 테스트 없음 (심각도: 중간)

**파일:** `tests/test_orders.py` — `TestOrderCreateAPI`

**현상:**
모든 주문 테스트가 SELL 입찰 기반이다.
BUY 입찰 시 buyer/seller 할당 로직(`buyer=bidding.user, seller=request.user`)이
테스트되지 않아 로직 오류를 놓칠 수 있다.

**추가해야 할 테스트:**
```python
def test_create_order_from_buy_bid(self, ...):
    """BUY 입찰에 대해 판매자가 매칭하면, 입찰자=buyer, 요청자=seller"""
    buy_bid = Bidding.objects.create(
        user=buyer, product_size=product_size,
        position=Bidding.Position.BUY, price=300000,
    )
    # seller_client가 주문 생성
    response = seller_client.post(self.URL, {"bidding_id": buy_bid.id})
    assert response.status_code == 201
    buyer.refresh_from_db()
    seller.refresh_from_db()
    assert buyer.point == 1_000_000 - 300000
    assert seller.point == 1_000_000 + 300000
```

### 3-2. 에러 메시지 내용 검증 부족 (심각도: 낮음)

**현상:**
대부분 `status_code`와 `code` 키만 확인하고, `message` 값은 검증하지 않는다.
메시지가 의도한 문구인지 테스트에서 확인하면 regression 방지에 도움이 된다.

---

## 4. 사소한 개선사항

### 4-1. BrandListView 정렬 없음

**파일:** `products/views.py` L73

**현상:** `Brand.objects.all()`이 정렬 없이 반환되어 순서가 비결정적이다.

**수정안:** `.order_by("name")` 추가 또는 모델 Meta에 `ordering = ["name"]` 정의.

### 4-2. MyOrdersView / PriceHistoryView 페이지네이션 없음

**파일:** `orders/views.py` L119-141, L144-200

**현상:** 데이터가 많아지면 응답 크기가 무한히 커질 수 있다.
MVP에서는 허용 가능하지만 프로덕션에서는 커서/페이지네이션이 필요하다.

### 4-3. list() 오버라이드 중복 패턴

**파일:** `products/views.py` L37-50, `orders/views.py` L33-44

**현상:** pagination을 `success_response`로 감싸는 동일 로직이 반복된다.

**수정안:** 공통 mixin 추출:
```python
# core/mixins.py
class SuccessResponseListMixin:
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated = self.paginator.get_paginated_response(serializer.data)
            return success_response(data={
                "count": paginated.data["count"],
                "results": paginated.data["results"],
            })
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data={"results": serializer.data})
```

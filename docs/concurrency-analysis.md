# 동시성 분석: 입찰-주문 거래 시스템

## 개요

KREAM 같은 리셀 마켓플레이스에서 동시성 제어는 **돈이 오가는 로직**에 직결된다. 두 명이 같은 입찰에 동시에 체결을 시도하거나, 체결과 취소가 동시에 발생하면 데이터 정합성이 깨진다.

이 문서는 현재 코드의 동시성 보호 상태를 분석하고, 취약점과 개선 방안을 정리한다.

---

## 1. 거래 흐름과 상태 머신

### 입찰(Bidding) 상태 전이

```
              체결 요청
ON_BIDDING ──────────────▶ CONTRACTED
    │
    │ 취소 요청
    ▼
 CANCELLED
```

### 주문(Order) 상태 전이

```
INSPECTION ──▶ IN_TRANSIT ──▶ DELIVERED
```

### 핵심 불변식 (Invariants)

이 시스템이 항상 보장해야 하는 규칙:

| # | 불변식 | 위반 시 결과 |
|---|--------|-------------|
| 1 | 하나의 입찰에는 최대 하나의 주문만 생성된다 | 이중 체결 → 이중 포인트 차감 |
| 2 | 체결된 입찰은 취소할 수 없다 | 포인트 이전 후 취소 → 정합성 파괴 |
| 3 | 포인트 차감과 적립은 원자적이다 | 부분 실행 → 한쪽만 돈을 잃음 |
| 4 | 주문 상태 전이는 단방향이다 | 역방향 전이 → 배송 완료 후 검수 중으로 회귀 |
| 5 | 포인트는 음수가 될 수 없다 | 잔액 부족 체결 → 마이너스 포인트 |

---

## 2. 현재 보호된 영역: 주문 생성 (OrderCreateView)

**파일**: `orders/views.py:65-110`

```python
with transaction.atomic():
    # 1) 행 수준 잠금: 같은 입찰에 동시 접근 차단
    bidding = Bidding.objects.select_for_update().get(pk=bidding_id)

    # 2) 상태 검증: 이미 체결된 입찰 거부
    if bidding.status == Bidding.Status.CONTRACTED:
        raise ConflictError("Bidding already contracted.")

    # 3) DB 레벨 연산: Python 메모리가 아닌 SQL에서 직접 계산
    User.objects.filter(pk=buyer.pk).update(point=F("point") - bidding.price)
    User.objects.filter(pk=seller.pk).update(point=F("point") + bidding.price)

    # 4) 상태 변경 + 주문 생성
    bidding.status = Bidding.Status.CONTRACTED
    bidding.save(update_fields=["status"])
    Order.objects.create(...)
```

### 보호 메커니즘 분석

| 기법 | 역할 | 보호하는 불변식 |
|------|------|----------------|
| `transaction.atomic()` | 전체 블록을 하나의 트랜잭션으로 묶음. 실패 시 전체 롤백 | #3 (원자적 포인트 이전) |
| `select_for_update()` | 해당 입찰 행에 배타적 잠금(Exclusive Lock). 다른 트랜잭션은 대기 | #1 (이중 체결 방지) |
| `F("point")` | `UPDATE SET point = point - 300000` SQL 생성. read-then-write 없음 | #5 (race condition 방지) |
| `PositiveIntegerField` | DB 제약으로 음수 차단 → `IntegrityError` → 롤백 | #5 (음수 포인트 방지) |

### 동시 체결 시나리오

```
User A (체결 시도)                  User B (체결 시도)
─────────────────                  ─────────────────
BEGIN                              BEGIN
SELECT ... FOR UPDATE (잠금 획득)
  → status = ON_BIDDING ✓           SELECT ... FOR UPDATE (대기 ⏳)
  → 포인트 차감/적립
  → status = CONTRACTED
  → Order 생성
COMMIT (잠금 해제)
                                    → status = CONTRACTED ✗
                                    → ConflictError 반환
                                   ROLLBACK
```

---

## 3. 취약점: 보호되지 않은 영역

### 취약점 1: 입찰 취소 (BidCancelView)

**파일**: `orders/views.py:169-184`

```python
# 현재 코드: 잠금 없는 read-then-write
bidding = Bidding.objects.get(pk=bid_id, user=request.user)   # ① 읽기
if bidding.status != Bidding.Status.ON_BIDDING:               # ② 판단
    raise ConflictError(...)
bidding.status = Bidding.Status.CANCELLED                     # ③ 쓰기
bidding.save(update_fields=["status"])
```

**공격 시나리오: 체결과 취소의 경합**

```
사용자 A (체결)                     입찰자 B (취소)
────────────                       ──────────
                                   GET bidding → ON_BIDDING ①
BEGIN (atomic)
SELECT FOR UPDATE → ON_BIDDING
포인트 이전 완료
status = CONTRACTED
COMMIT
                                   status 확인 → ON_BIDDING ② (stale read!)
                                   status = CANCELLED ③
                                   SAVE → DB에 CANCELLED 저장
```

**결과**: 포인트가 이전된 주문이 존재하는데, 입찰은 CANCELLED 상태. 불변식 #2 위반.

### 취약점 2: 주문 상태 변경 (OrderStatusUpdateView)

**파일**: `orders/views.py:144-166`

```python
# 현재 코드: 잠금 없는 read-then-write
order = Order.objects.get(pk=order_id)                        # ① 읽기
if VALID_STATUS_TRANSITIONS.get(order.status) != new_status:  # ② 판단
    raise ValidationError(...)
order.status = new_status                                     # ③ 쓰기
order.save(update_fields=["status"])
```

**공격 시나리오: 동일 주문에 동시 상태 변경**

```
요청 A (INSPECTION→IN_TRANSIT)      요청 B (INSPECTION→IN_TRANSIT)
──────────────────────              ──────────────────────
GET order → INSPECTION ①            GET order → INSPECTION ①
전이 검증 통과 ②                      전이 검증 통과 ②
status = IN_TRANSIT ③               status = IN_TRANSIT ③
SAVE                                SAVE
```

**결과**: 이 경우 같은 값으로 덮어쓰므로 실질적 피해는 적지만, INSPECTION → DELIVERED 직접 전이처럼 전이 규칙을 우회하는 시나리오가 가능하다. 불변식 #4 위반.

---

## 4. 개선 방안

### 입찰 취소 — atomic + select_for_update 적용

```python
# 개선안
def delete(self, request, bid_id):
    with transaction.atomic():
        try:
            bidding = (
                Bidding.objects
                .select_for_update()
                .get(pk=bid_id, user=request.user)
            )
        except Bidding.DoesNotExist:
            raise NotFound("Bidding not found.")

        if bidding.status != Bidding.Status.ON_BIDDING:
            raise ConflictError("Only active bids can be cancelled.")

        bidding.status = Bidding.Status.CANCELLED
        bidding.save(update_fields=["status"])

    return success_response(message="Bid cancelled.")
```

체결 트랜잭션이 `select_for_update()`로 잠금을 잡고 있으면, 취소 요청은 대기 후 CONTRACTED 상태를 읽어 ConflictError를 반환한다.

### 주문 상태 변경 — 동일 패턴 적용

```python
# 개선안
def patch(self, request, order_id):
    with transaction.atomic():
        try:
            order = (
                Order.objects
                .select_for_update()
                .get(pk=order_id)
            )
        except Order.DoesNotExist:
            raise NotFound("Order not found.")

        if order.seller != request.user:
            raise ForbiddenError("Only the seller can update order status.")

        serializer = OrderStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]

        if VALID_STATUS_TRANSITIONS.get(order.status) != new_status:
            raise ValidationError("Invalid status transition.")

        order.status = new_status
        order.save(update_fields=["status"])

    return success_response(...)
```

---

## 5. 동시성 보호 요약

| 영역 | 현재 상태 | 위험도 | 보호 기법 |
|------|----------|--------|----------|
| 주문 생성 (체결) | ✅ 보호됨 | — | atomic + select_for_update + F() |
| 포인트 이전 | ✅ 보호됨 | — | F() + PositiveIntegerField 제약 |
| 입찰 취소 | ❌ 미보호 | **높음** | → atomic + select_for_update 필요 |
| 주문 상태 변경 | ❌ 미보호 | 중간 | → atomic + select_for_update 필요 |
| 상품 삭제 시 입찰 취소 | ✅ 보호됨 | — | bulk update (signal, 단일 SQL) |

---

## 6. 테스트 전략

동시성 버그는 단위 테스트로 잡기 어렵다. 다음 전략을 조합한다:

### 단위 테스트 (현재 존재)
- 상태 전이 규칙 검증 (순방향/역방향)
- 이미 체결된 입찰 거부
- 포인트 부족 거부

### 동시성 테스트 (추가 필요)
```python
# threading을 이용한 동시 요청 시뮬레이션
from concurrent.futures import ThreadPoolExecutor

def test_동시체결_하나만_성공한다():
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(client_a.post, order_url, data),
            pool.submit(client_b.post, order_url, data),
        ]
    results = [f.result() for f in futures]
    success = [r for r in results if r.status_code == 201]
    assert len(success) == 1  # 정확히 하나만 성공
```

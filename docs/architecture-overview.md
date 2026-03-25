# 아키텍처 개요

## 목적

SUNKREAM API는 스니커즈 마켓플레이스를 위한 Django REST Framework 백엔드입니다. 코드베이스는 다음 세 가지 핵심 기능을 중심으로 구성됩니다.

- 카카오 소셜 로그인과 JWT 발급
- 상품 조회와 위시리스트 관리
- 입찰, 주문 체결, 주문 상태 추적

이 문서는 현재 시스템 구조를 설명하는 기준 문서입니다. 요청 단위의 상세 동작은 `docs/project-flow.md`를 보면 됩니다.

## 기술 스택

- Python 3.13
- Django 5.2
- Django REST Framework
- SimpleJWT
- drf-spectacular
- pytest + pytest-django + factory-boy
- Docker 및 CI 환경의 PostgreSQL

## 앱 경계

### `users`

- `KakaoLoginView`가 카카오 토큰 검증과 서비스 JWT 발급을 담당합니다.
- `CustomUser`가 사용자 인증 모델이며 프로필 필드와 포인트를 저장합니다.

### `products`

- 상품, 브랜드, 사이즈, 이미지, 위시리스트 도메인 모델
- 공개 상품 목록/상세 API
- 관리자 전용 상품 생성, 수정, 삭제 API

### `orders`

- 입찰 생성 및 조회
- 입찰 기반 주문 생성
- 주문 상태 변경
- 입찰 취소
- 시세 히스토리 및 마이페이지 주문/입찰 조회

### `core`

- 공통 타임스탬프 베이스 모델
- 성공 응답 헬퍼
- 공통 목록 응답 믹스인
- 예외 코드 매핑

## 실행 규칙

### 인증과 권한

- 기본 인증: `rest_framework_simplejwt.authentication.JWTAuthentication`
- 기본 권한: `IsAuthenticatedOrReadOnly`
- 공개 엔드포인트는 `AllowAny`로 재정의
- 관리자 상품 변경 API는 `IsAdminUser` 사용

### 응답 형식

성공 응답은 다음 형식을 사용합니다.

```json
{"code": "OK", "message": "success", "data": {...}}
```

에러 응답은 `core.exceptions.custom_exception_handler`에서 공통 형식으로 정규화됩니다.

```json
{"code": "NOT_FOUND", "message": "Product not found."}
```

### 페이지네이션

- 기본 paginator: `LimitOffsetPagination`
- 기본 페이지 크기: `20`
- `SuccessResponseListMixin`이 페이지네이션 응답을 공통 성공 형식으로 감쌉니다.

## 도메인 모델 요약

### 사용자

- `CustomUser(email, kakao_id, name, phone_number, address, point, is_active, is_staff)`
- `point`에는 음수 값을 막는 DB 체크 제약이 있습니다.

### 상품 도메인

- `Brand 1:N Product`
- `Product 1:N ProductImage`
- `Product 1:N ProductSize`
- `Size 1:N ProductSize`
- `Wishlist`는 `User`와 `Product` 사이의 유일한 관계입니다.

### 거래 도메인

- `Bidding(user, product_size, status, position, price)`
- 입찰 상태: `ON_BIDDING`, `CONTRACTED`, `CANCELLED`
- 입찰 방향: `BUY`, `SELL`
- `Order`는 `Bidding`과 `OneToOne` 관계입니다.
- 주문 상태: `INSPECTION`, `IN_TRANSIT`, `DELIVERED`

## API 구성 요약

### 인증

- `POST /api/v1/auth/kakao/`
- `POST /api/v1/auth/token/refresh/`

### 상품

- `GET /api/v1/products/`
- `POST /api/v1/products/` 관리자 전용
- `GET /api/v1/products/brands/`
- `GET /api/v1/products/<id>/`
- `PATCH /api/v1/products/<id>/` 관리자 전용
- `DELETE /api/v1/products/<id>/` 관리자 전용
- `POST /api/v1/products/<id>/wishlist/`
- `DELETE /api/v1/products/<id>/wishlist/`

### 주문과 입찰

- `GET /api/v1/bids/`
- `POST /api/v1/bids/`
- `DELETE /api/v1/bids/<id>/`
- `POST /api/v1/orders/`
- `PATCH /api/v1/orders/<id>/status/`
- `GET /api/v1/me/orders/`
- `GET /api/v1/products/<id>/price-history/`

## 데이터 무결성과 동시성

가장 민감한 로직은 포인트 이동과 입찰 소진이 함께 일어나는 주문 생성입니다.

- `transaction.atomic()`으로 포인트 이동, 입찰 상태 변경, 주문 생성을 하나의 트랜잭션으로 묶습니다.
- `select_for_update()`로 체결 대상 입찰 행을 잠급니다.
- `F()` expression으로 구매자/판매자 포인트를 DB에서 직접 갱신해 read-modify-write 경쟁 상태를 피합니다.
- 사용자 포인트 체크 제약이 음수 잔액을 막습니다.
- 입찰 취소와 주문 상태 변경도 `transaction.atomic()`과 `select_for_update()`를 사용해 stale write를 방지합니다.

## 인프라와 운영

### Docker

- 멀티 스테이지 이미지 빌드
- 런타임은 Gunicorn으로 Django를 실행
- `docker-compose.yml`로 앱과 PostgreSQL을 함께 구성
- 환경 변수는 로컬 `.env`와 Docker용 `.env.docker`로 분리

### CI

- GitHub Actions가 PostgreSQL 기반으로 테스트를 수행
- 의존성 설치는 `uv sync --frozen` 사용
- Docker 빌드 검증은 테스트 job 이후 실행

## 테스트 전략

- API 동작은 pytest와 DRF `APIClient`로 검증합니다.
- 팩토리로 사용자, 상품, 사이즈, 입찰, 주문 데이터를 생성합니다.
- 테스트는 인증, 상품, 입찰, 주문, 공통 응답 형식을 다룹니다.
- 현재 테스트 스위트는 `uv run pytest -q` 기준 통과 상태입니다.

## 남아 있는 리스크와 후속 작업

- `OrderCreateView`는 `CONTRACTED`만 아니라 `ON_BIDDING`이 아닌 모든 입찰을 거부해야 취소된 입찰 체결을 막을 수 있습니다.
- `KakaoLoginView`는 카카오의 `200` 응답 본문을 너무 신뢰하고 있어 잘못된 JSON이나 누락된 `id`에서 서버 에러가 날 수 있습니다.
- `ProductDetailView`는 `RetrieveAPIView`를 상속하면서 `patch()`와 `delete()`를 직접 구현하고 있어, `RetrieveUpdateDestroyAPIView`가 더 적절합니다.

## 권장 읽기 순서

1. 이 문서에서 정적 구조와 규칙을 확인합니다.
2. `docs/project-flow.md`에서 요청 흐름과 엔드포인트 동작을 확인합니다.
3. 세부 구현은 `users/`, `products/`, `orders/` 코드를 확인합니다.

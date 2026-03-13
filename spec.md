# Sunkream API - 기능 명세

## Feature 1: 카카오 OAuth 인증

### 요구사항
1. 카카오 access token으로 로그인/회원가입
2. JWT 토큰 발급 (access 2h, refresh 7d)
3. 토큰 갱신 엔드포인트

### API 명세
- `POST /api/v1/auth/kakao/` — 카카오 로그인
- `POST /api/v1/auth/token/refresh/` — 토큰 갱신

### 데이터 모델
- `CustomUser`: email, kakao_id, name, phone_number, address, point(기본 1,000,000)

---

## Feature 2: 상품 조회

### 요구사항
1. 상품 목록 조회 (브랜드/사이즈/검색 필터, 페이지네이션)
2. 상품 상세 조회 (이미지, 위시리스트 수 포함)
3. 브랜드 전체 목록 조회
4. 위시리스트 추가/삭제

### API 명세
- `GET /api/v1/products/` — 상품 목록
- `GET /api/v1/products/<id>/` — 상품 상세
- `GET /api/v1/products/brands/` — 브랜드 목록
- `POST/DELETE /api/v1/products/<id>/wishlist/` — 위시리스트

### 데이터 모델
- `Brand`, `Product`, `ProductImage`, `Size`, `ProductSize`, `Wishlist`

---

## Feature 3: 입찰 & 주문

### 요구사항
1. BUY/SELL 입찰 등록
2. 상대방 입찰 매칭으로 주문 생성 (atomic 포인트 이전)
3. 내 주문/입찰 내역 조회
4. 상품별 가격 히스토리 조회

### API 명세
- `GET/POST /api/v1/bids/` — 입찰 조회/생성
- `POST /api/v1/orders/` — 주문 생성
- `GET /api/v1/me/orders/` — 내 거래내역
- `GET /api/v1/products/<id>/price-history/` — 가격 히스토리

### 비즈니스 로직
- 자기 입찰 매칭 불가
- 포인트 부족 시 주문 실패
- 입찰 row lock → 포인트 F() expression 이전

---

## Feature 4: 입찰 취소 (미구현)

### 요구사항
1. ON_BIDDING 상태 입찰만 취소 가능
2. CONTRACTED 입찰은 취소 불가
3. 본인 입찰만 취소 가능

### API 명세
- `DELETE /api/v1/bids/<id>/` — 입찰 취소

---

## Feature 5: 주문 상태 변경 (미구현)

### 요구사항
1. 판매자만 상태 변경 가능
2. 순방향 전이만 허용: INSPECTION → IN_TRANSIT → DELIVERED
3. 역방향 전이 불가

### API 명세
- `PATCH /api/v1/orders/<id>/status/` — 주문 상태 변경

---

## Feature 6: 상품 관리 Admin CRUD (미구현)

### 요구사항
1. 관리자(is_staff)만 상품 생성/수정/삭제 가능
2. 상품 생성 시 사이즈 목록 함께 등록
3. 활성 입찰 있는 상품은 삭제 불가

### API 명세
- `POST /api/v1/admin/products/` — 상품 생성
- `PATCH /api/v1/admin/products/<id>/` — 상품 수정
- `DELETE /api/v1/admin/products/<id>/` — 상품 삭제

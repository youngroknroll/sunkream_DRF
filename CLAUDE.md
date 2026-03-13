# Sunkream API

## 개요

KREAM(스니커즈 리셀 플랫폼) 클론 백엔드 API. 카카오 OAuth 인증, 상품 조회, 입찰/주문 거래 기능을 제공한다.

## 기술 스택

- Python 3.13+
- Django 5.2 + Django REST Framework
- SimpleJWT (인증)
- drf-spectacular (OpenAPI 문서)
- PostgreSQL 14 (psycopg3)
- pytest + factory-boy (테스트)

## 패키지 관리

- 패키지 매니저: **uv**
- 의존성 추가: `uv add <package>`
- 개발 의존성 추가: `uv add --dev <package>`
- Lock 파일: `uv.lock`

## 빌드 & 테스트

- 서버 실행: `uv run python manage.py runserver`
- 테스트: `uv run pytest`
- 마이그레이션: `uv run python manage.py makemigrations && uv run python manage.py migrate`
- API 문서: `http://localhost:8000/api/docs/` (Swagger UI)

## 디렉토리 구조

```
sunkream_api/   Django 프로젝트 설정 (settings, urls, wsgi)
core/           공통 유틸 (TimeStampModel, 예외처리, 응답포맷, 믹스인)
users/          카카오 OAuth 인증 + CustomUser 모델
products/       상품, 브랜드, 사이즈, 위시리스트
orders/         입찰(Bidding), 주문(Order), 가격 히스토리
tests/          테스트 (conftest, factories, test_*.py)
docs/           API 설계 문서, 코드 리뷰, 구현 계획
```

## 코딩 컨벤션

- 응답 포맷: `{"code": "OK", "message": "...", "data": {...}}` (성공) / `{"code": "ERROR_CODE", "message": "..."}` (실패)
- 커스텀 예외는 `core/exceptions.py`에 정의, `custom_exception_handler`로 일괄 처리
- DB 최적화: `select_related` (FK), `prefetch_related` (역참조), `annotate` (집계)
- Atomic 트랜잭션: 포인트 이전 등 동시성 이슈가 있는 로직에 `transaction.atomic()` + `select_for_update()` 사용
- 테스트: 행위 중심 한글 네이밍, factory-boy 기반 fixture

## 환경 변수

- `SECRET_KEY` - Django secret key
- `DEBUG` - 디버그 모드 (True/False)
- `KAKAO_REST_API_KEY` - 카카오 REST API 키

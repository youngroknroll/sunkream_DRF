# Docker & CI/CD 인프라 설계

## 1. Docker

### 아키텍처: 멀티스테이지 빌드

```
┌─────────────────────────────────────┐
│  Stage 1: builder                   │
│  python:3.13-slim + uv              │
│  ┌───────────────────────────────┐  │
│  │ 1. pyproject.toml, uv.lock   │  │  ← 의존성 레이어 캐싱
│  │ 2. uv sync (의존성 설치)      │  │
│  │ 3. COPY . . (소스 복사)       │  │
│  │ 4. uv sync (프로젝트 설치)    │  │
│  └───────────────────────────────┘  │
└──────────────┬──────────────────────┘
               │ COPY --from=builder
┌──────────────▼──────────────────────┐
│  Stage 2: runtime                   │
│  python:3.13-slim (uv 없음)         │
│  ┌───────────────────────────────┐  │
│  │ .venv + 소스코드만 포함       │  │  ← 최종 이미지 경량화
│  │ gunicorn으로 실행             │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

### 설계 결정

| 결정 | 선택 | 이유 |
|------|------|------|
| 베이스 이미지 | `python:3.13-slim` | alpine은 psycopg 빌드 이슈 있음, slim이 호환성 우수 |
| 패키지 매니저 | `uv` (COPY from ghcr) | 프로젝트 기존 도구 유지, pip 대비 10-100x 빠름 |
| 멀티스테이지 | 2단계 (builder → runtime) | 빌드 도구(uv) 제외로 이미지 크기 절감 |
| WSGI 서버 | `gunicorn` (workers=3) | Django 프로덕션 표준, worker 수는 (2×CPU)+1 공식 기반 |
| 의존성 캐싱 | pyproject.toml 먼저 COPY | 소스 변경 시 의존성 레이어 재빌드 방지 |

### 레이어 캐싱 전략

```dockerfile
# 1단계: 의존성만 먼저 설치 (변경 드묾 → 캐시 히트율 높음)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 2단계: 소스 복사 후 프로젝트 설치 (변경 잦음 → 여기서만 재빌드)
COPY . .
RUN uv sync --frozen --no-dev
```

소스코드만 변경되면 1단계는 캐시에서 가져오고 2단계만 재실행된다.

### docker-compose 구성

```
┌─────────────┐     ┌─────────────┐
│     app      │────▶│     db      │
│  Django API  │     │ PostgreSQL  │
│  :8000       │     │  14-alpine  │
└─────────────┘     └──────┬──────┘
                           │
                    pgdata volume
```

- **healthcheck**: `pg_isready`로 DB 준비 상태 확인 후 app 시작
- **depends_on + condition**: DB가 healthy일 때만 app 실행
- **command**: migrate → gunicorn 순차 실행 (매 컨테이너 시작 시 마이그레이션 적용)

### 환경변수 분리

| 파일 | 용도 | Git 추적 |
|------|------|----------|
| `.env` | 로컬 개발 (uv run) | ✗ |
| `.env.docker` | Docker Compose | ✗ |

DB 호스트가 다르기 때문에 분리: 로컬은 `localhost`, Docker는 서비스명 `db`.

---

## 2. CI/CD (GitHub Actions)

### 파이프라인 흐름

```
PR/push to main
       │
       ▼
┌──────────────┐    성공    ┌──────────────┐
│   test job   │──────────▶│  docker job  │
│              │           │              │
│ ┌──────────┐ │           │ docker build │
│ │ uv sync  │ │           │ (빌드 검증)   │
│ │ migrate  │ │           └──────────────┘
│ │ pytest   │ │
│ └──────────┘ │
│   PostgreSQL │
│   (service)  │
└──────────────┘
```

### test job 상세

```yaml
services:
  postgres:           # GitHub Actions 서비스 컨테이너
    image: postgres:14-alpine
    health-cmd: pg_isready   # 준비 상태 확인

steps:
  1. checkout         # 소스 체크아웃
  2. setup-uv         # uv 설치 (astral-sh/setup-uv)
  3. setup-python     # Python 3.13
  4. uv sync          # 의존성 설치 (dev 포함)
  5. migrate          # DB 스키마 적용
  6. pytest -v        # 테스트 실행
```

### 설계 결정

| 결정 | 선택 | 이유 |
|------|------|------|
| 트리거 | push + PR to main | main 브랜치 보호, PR 머지 전 검증 |
| DB | 서비스 컨테이너 (postgres:14) | 실제 DB로 테스트, mock 사용 안 함 |
| 의존성 설치 | `uv sync --frozen` | lock 파일 기반 재현 가능한 설치 |
| docker job 의존성 | `needs: test` | 테스트 실패 시 이미지 빌드 생략 (비용 절감) |
| 시크릿 관리 | 환경변수로 주입 | CI 전용 test 값 사용, 실제 시크릿 노출 없음 |

### 확장 가능 구조

현재는 빌드 검증까지만 수행한다. 배포 대상이 정해지면 docker job 뒤에 deploy job을 추가:

```
test → docker build → docker push (ECR/GHCR) → deploy (ECS/Railway/Fly.io)
```

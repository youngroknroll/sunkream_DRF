# 문서 통합 실행 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**목표:** 분산된 프로젝트 문서를 아키텍처 문서와 흐름 문서, 두 개의 기준 문서로 통합한다.

**아키텍처:** 하나는 정적 구조를 설명하는 개요 문서로 두고, 다른 하나는 요청 흐름 문서로 분리한다. 현재 코드와 맞는 정보만 옮기고, 대체된 메모와 이력 문서는 제거한다.

**기술 스택:** Markdown, Django, DRF, SimpleJWT, pytest

---

### Task 1: 기준 아키텍처 문서 작성

**Files:**
- Create: `docs/architecture-overview.md`
- Read: `docs/code-review.md`
- Read: `docs/concurrency-analysis.md`
- Read: `docs/infra-docker-cicd.md`
- Read: `docs/legacy-backend-api-design.md`
- Read: `.docs/code-review-v2.md`
- Read: `.docs/improvement-plan.md`

**Step 1: 문서 뼈대 작성**

목적, 스택, 앱 경계, 실행 규칙, 도메인 모델, 인프라, 테스트, 리스크 섹션을 만든다.

**Step 2: 현재 상태 기준으로 내용 통합**

현재 코드와 맞는 정보만 옮기고, 과거 리뷰 메모는 짧은 "남은 리스크 / 후속 작업" 섹션으로 정리한다.

**Step 3: 중복 제거 검토**

엔드포인트 세부 흐름처럼 `docs/project-flow.md`에 있어야 할 내용은 제거한다.

### Task 2: 기준 흐름 문서 작성

**Files:**
- Create: `docs/project-flow.md`
- Read: `.docs/flow-diagram.md`
- Read: `.docs/simplification.md`
- Read: `orders/views.py`
- Read: `products/views.py`
- Read: `users/views.py`

**Step 1: 공통 요청 생명주기 작성**

미들웨어, 인증, 시리얼라이저 검증, 비즈니스 로직, DB 접근, 응답 포맷을 정리한다.

**Step 2: 엔드포인트 흐름 작성**

인증, 상품, 위시리스트, 입찰, 주문, 주문 상태 변경, 입찰 취소, 시세 히스토리 흐름을 문서화한다.

**Step 3: 일관성 검토**

흐름 설명이 현재 코드 경로와 응답 규칙에 맞는지 확인한다.

### Task 3: 대체된 문서 제거

**Files:**
- Delete: `.docs/code-review-v2.md`
- Delete: `.docs/flow-diagram.md`
- Delete: `.docs/improvement-plan.md`
- Delete: `.docs/simplification.md`
- Delete: `docs/code-review-2025-03-25.md`
- Delete: `docs/code-review.md`
- Delete: `docs/concurrency-analysis.md`
- Delete: `docs/infra-docker-cicd.md`
- Delete: `docs/legacy-backend-api-design.md`
- Delete: `docs/plan-crud-features.md`

**Step 1: 대체 범위 확인**

각 문서의 핵심 내용이 새 기준 문서 두 개에 반영됐는지 확인한다.

**Step 2: 문서 삭제**

기존 리뷰, 계획, 흐름 문서를 제거한다.

### Task 4: 최종 문서 구조 검증

**Files:**
- Read: `docs/`
- Read: `.docs/`

**Step 1: 최종 문서 목록 확인**

파일 목록을 확인해 기준 문서 구조가 한눈에 보이는지 점검한다.

**Step 2: 내용 최종 점검**

새 문서의 제목과 섹션 구성이 올바른지 확인한다.

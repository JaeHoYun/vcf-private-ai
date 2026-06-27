# 04 — 개발 시나리오 및 AI 앱 개발

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.

이 문서는 ① 조직 상황에 맞는 **PAIF/PAIS 사용 패턴** 선택과 ② **AI 앱 개발의 구조·연동·배포**를 다룹니다.

---

## 4.1 구성요소와 라이프사이클 — DLVM · PAIS · VKS

PAIF를 구축하면 PAIS(관리형 AI 서비스)는 **포함되어 항상 가용**합니다. DLVM과 PAIS는 같은 라이프사이클의 **서로 다른 단계**를 맡습니다 — DLVM은 개발·실험, PAIS는 프로덕션 서빙입니다.

| 구성요소 | 위치 | 역할 | 주 사용자 |
|---------|------|------|----------|
| **DLVM** | 개발·실험 단계 | 모델 평가·프로토타이핑·검증(GPU 워크스테이션) | Data Scientist, MLOps |
| **PAIS Model Endpoint** | 프로덕션 서빙 | 검증된 모델을 관리형 API로 서빙 | MLOps |
| **PAIS Agent Builder / KB** | 프로덕션 RAG/앱 | 모델+지식베이스로 RAG·에이전트 구성 | Data Scientist |
| **VKS** | 앱 실행 | 완성된 앱(Frontend/Backend) 배포 | App Dev, DevOps |

```
라이프사이클 (Broadcom 공식: 순차 파이프라인 단계)

  [실험·개발]              [프로덕션 서빙·RAG]            [앱 실행]
   DLVM   ──검증된 모델──▶   PAIS                  ──API──▶  VKS
   • 모델 평가   Harbor에     • Model Endpoint(서빙)          • Frontend/Backend Pod
   • 프롬프트     Push        • Knowledge Base / Agent        • PAIS Agent API 호출
   • RAG 실험                • 관측성 · MCP · 자동 스케일링
```

> 그래서 핵심 결정은 **프로덕션 RAG/앱을 만들 때 PAIS 관리형 서비스를 어디까지 쓸 것인가**입니다(§4.2). DLVM은 어느 패턴에서든 Data Scientist의 **개발 단계**에서 쓰입니다.

---

## 4.2 프로덕션 패턴 — PAIS를 어디까지 쓸 것인가

프로덕션 패턴의 선택지는 **PAIS 관리형 서비스를 RAG/앱에서 어디까지 소비하느냐의 깊이**입니다. 깊이에 따라 아래와 같이 스펙트럼으로 나뉩니다.

| | 패턴 1: 관리형 엔드투엔드 (권장) | 패턴 2: 관리형 서빙 + 커스텀 RAG | (예외) 자체 추론 운영 |
|---|---|---|---|
| 한 줄 | Agent Builder로 RAG/에이전트까지 관리형 | 서빙만 PAIS, RAG는 코드로 직접 | 추론 엔진까지 직접 운영 |
| 모델 서빙 | PAIS Model Endpoint | PAIS Model Endpoint | 직접(vLLM 등) |
| RAG/오케스트레이션 | Agent Builder + Knowledge Base | 직접(LangChain/LlamaIndex 등) | 직접 |
| 벡터 DB | Knowledge Base(pgvector 자동) | 직접(pgvector·Milvus·Qdrant 등) | 직접 |
| 코드량 | 최소(앱 연동만) | 중간(RAG 로직) | 많음(전 스택) |
| 적합 | 표준 RAG·에이전트 (대다수) | 고급 검색·기존 RAG 코드·특수 벡터DB | 미지원 엔진/프레임워크·기존 MLOps |
| 구축 속도 | 수 시간 | 수 일 | 수 주 |
| 운영 부담 | 낮음 | 중간 | 높음 |

### 패턴 1 — 관리형 엔드투엔드 (기본 권장)

Model Endpoint + Knowledge Base + Agent Builder로 **코드 거의 없이** RAG/에이전트를 구성합니다. Agent 생성 시점에 이미 프로덕션 준비 완료(관측성·MCP·자동 스케일링 기본). 표준 문서 Q&A·에이전트의 대다수가 여기 해당합니다.

구성: ① Model Endpoint → ② Data Source → ③ Knowledge Base → ④ Agent(+MCP) → ⑤ Playground → ⑥ 앱 연동. (상세 [문서 03](03-workflows.md))

### 패턴 2 — 관리형 서빙 + 커스텀 RAG

서빙(vLLM/Infinity/llama.cpp)은 PAIS Model Endpoint에 맡기고, **RAG/오케스트레이션만 코드로** 직접 구현합니다. 멀티홉·리랭킹·Self-RAG 같은 고급 검색, 기존 LangChain 자산 재사용, 특수 벡터 DB(Milvus/Qdrant/Chroma)가 필요할 때 선택합니다.

```python
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
llm = ChatOpenAI(openai_api_base="https://pais.company.com/v1",
                 openai_api_key="<PAIS_TOKEN>", model_name="llama-3-1-8b-instruct")
embeddings = OpenAIEmbeddings(openai_api_base="https://pais.company.com/v1",
                 openai_api_key="<PAIS_TOKEN>", model="bge-small-en")
# PAIS Endpoint는 OpenAI 호환 → Base URL·Model 이름만 바꾸면 기존 코드 재사용
```

### (예외) 자체 추론 운영 — 주류 아님

PAIS Model Endpoint가 지원하지 않는 추론 엔진·프레임워크·모델이 필요하거나, 이미 성숙한 외부 MLOps 플랫폼이 있을 때만 선택하는 엣지 케이스입니다. 추론 엔진(vLLM 등)·서빙·스케일링·인증을 **전부 직접 운영**해야 하므로 부담이 큽니다.

> PAIF를 구축한 환경에서 **PAIS 서빙을 통째로 우회하는 것은 일반적으로 권장하지 않습니다.** 특수 요구가 없다면 패턴 1·2를 사용하세요. (DLVM은 이때도 어디까지나 개발·실험용이며, 프로덕션 상시 서빙 대상이 아닙니다.)

---

## 4.3 조직 상황별 선택 요인 (직교 축)

§4.2의 패턴(소비 깊이)이 "메인 축"이라면, 아래 3가지는 그 위에 **독립적으로 겹쳐 선택하는 별개의 축**입니다. 세 축은 서로 독립적입니다.

> **"직교"가 무슨 뜻인가요?** 한 축의 선택이 다른 축의 선택을 강제하지 않는다는 뜻입니다. 예컨대 *패턴 1(관리형 엔드투엔드)* 을 고르면서 동시에 *에어갭* 이고 *추론·RAG 워크로드* 이며 *부서 규모* 일 수 있습니다. 패턴과 무관하게 각 축을 독립적으로 정하므로, 조합의 수만큼 현실 구성이 나옵니다. 그래서 "패턴 1–예외"와 아래 축들을 한 줄에 세워 비교하면 안 됩니다.

### 축 ① 연결성 — 연결망 vs 에어갭

| | 연결망(Connected) | 에어갭(Air-gapped) |
|---|---|---|
| 모델/컨테이너 반입 | NGC·HuggingFace 직접 | **Artifact Mirroring Tool로 미러링 후 오프라인 반입** (9.1) |
| 외부 데이터/도구 | SaaS·외부 MCP 연동 가능 | **내부 시스템만** (외부 SaaS·MCP 차단) |
| 대상 | 일반 기업 | 방산·금융·공공·일부 제조 |

→ 에어갭이어도 패턴(§4.2)은 그대로 고르되, 반입·연동을 내부로 제한하고 Artifact Mirroring Tool로 구성합니다([문서 06 §6.9](06-production.md#69-에어갭air-gapped-환경--artifact-mirroring-tool-91-신규)).

### 축 ② 워크로드 유형 — 추론/RAG vs 파인튜닝 vs 에이전트

| 유형 | 내용 | 핵심 구성요소 |
|------|------|--------------|
| **추론·RAG** (대다수) | 문서 Q&A·챗봇 | Model Endpoint + KB/Agent |
| **파인튜닝·학습** | 도메인 특화 모델 제작 | DLVM·VKS GPU + NeMo(NVAIE), 대규모 GPU |
| **에이전트(도구 사용)** | 사내 시스템 연동 자동화 | Agent + **MCP**(거버넌스 필수, [문서 05](05-agents-mcp.md)) |

→ 한 조직이 셋을 동시에 가질 수 있습니다(예: RAG 챗봇 + 분기별 파인튜닝 + 업무 자동화 에이전트).

→ 세 워크로드를 **언제** 고르는지(프롬프트 vs RAG vs 파인튜닝)의 의사결정과 LoRA/QLoRA 개념은 [문서 01 §1.9](01-concepts.md#19-프롬프트-vs-rag-vs-파인튜닝-선택)를 보십시오.

### 축 ③ 성숙도·규모 — PoC → 부서 → 그룹 플랫폼

| 단계 | 특징 | 구성 |
|------|------|------|
| **단일팀 PoC** | 빠른 검증 | 패턴 1, 단일 네임스페이스, CPU 추론으로 비용 최소 가능 |
| **부서 확장** | 여러 팀 사용 | 멀티 네임스페이스·리소스 쿼터, MCP 사내 연동(읽기 우선) |
| **그룹 멀티테넌트 플랫폼** | 전사/계열사 | 멀티테넌트 격리, HA/DR, 관측성·거버넌스, 그룹 GPU 풀 |

→ 같은 패턴이라도 규모가 커질수록 [문서 06](06-production.md)의 프로덕션 요소(HA/DR·멀티테넌트·관측성)가 더 중요해집니다.

> **GPU를 자원 서비스로 제공하려면** — 위 "그룹 GPU 풀"처럼 GPU 자체를 사내·계열사에 셀프서비스로 빌려주는 GPUaaS 관점(책임 경계 2티어·분할 매트릭스·쇼백/차지백·공유 풀 시나리오)은 [문서 07](07-gpuaas.md)에서 전용으로 다룹니다.

---

## 4.4 의사결정 가이드

> 전제: PAIS는 VCF에 포함되어 항상 가용합니다. 그러므로 결정은 **"어느 패턴으로, 어떤 상황 축 위에서 쓰냐"** 입니다.

```
[메인 축] 프로덕션 RAG/앱을 어떻게 만들 것인가?
   표준 RAG·에이전트인가?
     ├── 예 ───────────────────────────────▶ 패턴 1 (관리형 엔드투엔드) (권장)
     └── 아니오: 고급 RAG·기존 코드·특수 벡터DB 필요?
            ├── 예 ──▶ 서빙은 PAIS에 맡길 수 있나?
            │           ├── 예 ────▶ 패턴 2 (관리형 서빙 + 커스텀 RAG)
            │           └── 아니오(미지원 엔진/프레임워크) ─▶ (예외) 자체 추론 운영
            └── 아니오 ─▶ 패턴 1

[직교 축] 위 패턴에 겹쳐서 각각 독립 선택 (§4.3)
   • 연결성 : 연결망 / 에어갭(Artifact Mirroring Tool)
   • 워크로드: 추론·RAG / 파인튜닝(NeMo) / 에이전트(MCP)
   • 규모   : PoC / 부서 / 그룹 플랫폼
```

> 대부분의 엔터프라이즈는 **패턴 1로 시작**해, 고급 검색이 필요한 일부 앱만 패턴 2로 분기하는 전략이 현실적입니다. 자체 추론 운영(예외)은 특수 요구가 분명할 때만 선택하세요.

---

## 4.5 일반 웹앱 vs AI 앱 구조

전통적 웹 애플리케이션 (3-Tier):

```
전통적인 웹 애플리케이션 구조

  [사용자] → HTTP Request
  ┌──────────┐   ┌───────────┐   ┌──────────┐
  │ Frontend │ → │  Backend  │ → │ Database │
  │ React/Vue│   │Spring Boot│   │PostgreSQL│
  └──────────┘   └───────────┘   └──────────┘
  (Presentation)  (Business)       (Data)

  • HTML/CSS/JS · Node.js · MySQL · MongoDB · CRUD · 정형 데이터

특징: 요청-응답이 결정적(Deterministic), 동일 입력→동일 출력,
      비즈니스 로직을 명시적으로 코딩, 응답이 빠르고 예측 가능(ms 단위)
```

AI 애플리케이션 (AI 서비스 계층 추가):

```
AI 애플리케이션 구조

  [사용자] → HTTP Request
  ┌──────────┐   ┌──────────┐   ┌──────────┐
  │ Frontend │ → │  Backend │ → │ Database │
  │ React/Vue│   │ FastAPI  │   │PostgreSQL│
  └──────────┘   └────┬─────┘   └──────────┘
  (Presentation)  (BFF/Business)  (Data)
  • 채팅 UI       • 파일 업로드    • 사용자 정보·세션
  • 대화 이력          │
                  AI API 호출
                       ▼
  ┌──────────────── AI Services (PAIS) ───────────────┐
  │  Agent API → (RAG 파이프라인)                      │
  │  ┌──────────┐ ┌───────────────┐ ┌──────────────┐  │
  │  │ 질문 이해│ │ 답변 생성(LLM) │ │ 스트리밍 응답│  │
  │  │ 문서검색 │ │   출처 제공    │ │  인증/인가   │  │
  │  │  (KB)    │ │               │ │              │  │
  │  └──────────┘ └───────────────┘ └──────────────┘  │
  └────────────────────────────────────────────────────┘

특징: 요청-응답이 확률적(Probabilistic), 동일 입력→유사하지만 다른 출력 가능,
      AI 모델이 "추론"으로 응답 생성, 응답 시간이 상대적으로 길고 가변적(초 단위)
```

### 핵심 차이점

| 관점 | 전통적 웹앱 | AI 앱 |
|------|-----------|-------|
| 응답 특성 | 결정적 | 확률적 |
| 로직 | 코드로 명시 | 모델 추론 |
| 응답 시간 | 빠름 (ms) | 가변 (초) |
| 리소스 | CPU 중심 | GPU 필수(대규모 추론) |
| 데이터 흐름 | 정형 CRUD | 비정형 → 벡터 → 추론 |
| 에러 처리 | 명확한 예외 | 환각(Hallucination) 관리 |
| 테스트 | 단위/통합 | 품질 평가(정확도·관련성) |

> AI 앱은 응답이 초 단위로 길어지므로 타임아웃·비동기·스트리밍(SSE) 처리를 반드시 갖춰야 합니다.

---

## 4.6 AI 앱의 계층별 역할 (4-Tier)

```
AI 앱 4-Tier (위 → 아래, 호출 흐름)

  Tier 1: Presentation (Frontend)   기술: React/Vue/Next, Mobile
          담당: App Developer(Frontend)
                       ▼
  Tier 2: Business Logic (Backend/BFF)  기술: FastAPI/Node/Spring
          AI API 호출 전후 처리(로깅·필터링·비용추적), 담당: App Developer(Backend)
                       ▼
  Tier 3: AI Service (PAIS)         기술: Model Endpoint(vLLM)/Agent(RAG)/KB
          PAIF 포함 관리형 서비스·OpenAI 호환, 담당: Data Scientist·MLOps
                       ▼
  Tier 4: Infrastructure (PAIF 코어 기능 계층 · VCF)  기술: VCF/Supervisor/VKS/vGPU/Harbor/DSM
          엔터프라이즈 인프라·멀티테넌시·보안, 담당: VI Admin·Platform Engineer
```

> **PAIF의 범위 주의:** Tier 3(PAIS)와 Tier 4의 PAIF 코어 기능 계층은 **둘 다 PAIF(솔루션)에 속합니다** — PAIF는 한 티어가 아니라 서비스 계층(Tier 3)과 코어 기능 계층(Tier 4)을 함께 감쌉니다([문서 02 §2.1](02-architecture.md#21-전체-계층-구조)). 고객 앱(Tier 1·2)만 PAIF 밖입니다.

| 계층 | 책임 | PAIS 담당 | 개발팀 담당 |
|------|------|:---:|------|
| Frontend | UI/UX | 미지원 | 지원 전체 |
| Backend | 비즈니스 로직, 인증 | 미지원 | 지원 전체 |
| AI Service | LLM 추론, RAG | 지원 Agent/Endpoint | 프롬프트·KB 구성 |
| Infrastructure | GPU, 컴퓨팅 | 지원 자동 프로비저닝 | 미지원 |

"PAIS Agent = AI 두뇌" — 제공 경계:

```
PAIS Agent vs 앱 개발 영역

  PAIS가 제공 (AI 두뇌)             개발팀이 구현 (앱 몸체)
  O LLM 추론 (Completion EP)        O 사용자 인증/인가
  O 벡터 검색 (Knowledge Base)      O 사용자 인터페이스
  O RAG 파이프라인 (Agent)          O 비즈니스 로직
  O 세션 관리 (대화 히스토리)       O 대화 이력 저장 (DB)
  O OpenAI 호환 API                 O 사용량 추적/과금
  O 출처 정보 반환                  O 에러 처리
  O 자동 스케일링                   O 로깅/모니터링 확장
  X 사용자 관리                     O CI/CD 파이프라인
  X 비즈니스 규칙
  X 커스텀 UI

비유: PAIS Agent = "AI 전문가 직원", 앱 = "회사 시스템"(출입·업무규칙·보고체계).
      회사는 AI 전문가에게 질문하고 답을 받지만, 누가 질문할 수 있는지·답을
      어떻게 활용할지는 회사가 결정합니다.
```

---

## 4.7 PAIS API 연동

PAIS API 유형:

```
PAIS API 비교  (경로는 예시 — §4.7 상단 주의 참조)

  Model Endpoint API                Agent API
  POST /v1/chat/completions         POST /v1/agents/{name}/chat
  ── 입력 ──                        ── 입력 ──
   • messages (대화 이력)            • message (사용자 질문)
   • model (모델명)                  • session_id (세션 식별자)
   • temperature, max_tokens
  ── 출력 ──                        ── 출력 ──
   • 생성된 텍스트                   • 생성된 답변 / 참조 문서(출처) / session_id
  ── 특징 ──                        ── 특징 ──
   • OpenAI API 완전 호환            • RAG 자동 처리
   • 대화 이력 직접 관리 필요        • 세션/대화 이력 자동 관리
   • RAG 없음(직접 구현)             • Knowledge Base 연결됨
  ── 용도 ──                        ── 용도 ──
   • 커스텀 RAG 구현                 • 일반적인 RAG 앱 (권장)
   • 단순 챗봇(KB 불필요)            • 문서 기반 Q&A
   • 패턴 2 (관리형 서빙+커스텀RAG)  • 패턴 1 (관리형 엔드투엔드)

권장: 대부분의 경우 Agent API — RAG 로직을 직접 구현할 필요 없이 즉시 문서 기반 Q&A 가능
```

| API 유형 | 용도 | 엔드포인트 |
|---------|------|-----------|
| Model Endpoint API | 단순 LLM 추론 | `/v1/chat/completions` |
| Agent API | RAG 통합 추론(권장) | `/v1/agents/{name}/chat` |

> 위 엔드포인트 경로는 **예시**입니다(9.0.x 문서에서 이어받음, PAIS 2.1에서 미검증). 실제 경로·인증 파라미터는 PAIS UI의 Sample Code/공식 문서로 확인하세요. 아래 curl·응답 JSON도 동일하게 예시입니다.

인증 흐름 (VCF OIDC 기반):

```
PAIS API 인증 흐름  (경로는 예시)

  앱(Backend) ──① Token 요청(Client Credentials)──▶ VCF Automation
              POST /oauth/token                        (OIDC Provider)
              {client_id, client_secret, grant_type}
  앱(Backend) ◀──② Access Token 반환──────────────── VCF Automation
              {access_token, expires_in, token_type}    (OIDC Provider)
  ·························· Token 획득 완료 ··························
  앱(Backend) ──③ PAIS API 호출(Bearer Token)──────▶ PAIS
              POST /v1/agents/{name}/chat               (ML API Gateway)
              Authorization: Bearer {access_token}
  앱(Backend) ◀──④ 응답 반환───────────────────────── PAIS
              {response, references, session_id}         (ML API Gateway)

토큰 관리 팁: Access Token은 만료 시간 있음(보통 1시간), 만료 전 갱신 로직 구현,
            Backend에서 토큰 관리·Frontend에 노출 금지
```

```bash
curl -X POST 'https://pais.company.com/v1/agents/hr-assistant/chat' \
  -H 'Authorization: Bearer <access_token>' -H 'Content-Type: application/json' \
  -d '{"message":"연차 휴가는 며칠인가요?","session_id":"user-123-session-456"}'
```

```json
{ "response":"…연간 15일…",
  "references":[{"source":"HR_Policy_2026.pdf","page":12,"content":"…"}],
  "session_id":"user-123-session-456" }
```

---

## 4.8 배포 아키텍처

AI 앱은 **VKS 클러스터**에 배포하는 것이 권장됩니다.

```
AI 앱 배포 아키텍처

┌─ AI 플레이그라운드 (PAIF/PAIS) ─────────────────────────┐
│  [외부 사용자] ─HTTPS─▼                                  │
│  ┌─ VKS Cluster (프로젝트) ────────────────────────────┐ │
│  │  Ingress Controller (L7 로드밸런싱, TLS 종료)        │ │
│  │             ▼                                        │ │
│  │  ┌ Frontend Pod(s) ┐  →  ┌ Backend Pod(s) ┐         │ │
│  │  │ • React         │     │ • FastAPI       │         │ │
│  │  │ • Nginx         │     │ • 인증 처리     │         │ │
│  │  └─────────────────┘     │ • AI API 중계   │         │ │
│  │                          └─────────────────┘         │ │
│  └──────────────── PAIS API 호출 ▼ ────────────────────┘ │
│  ┌─ PAIS Services ─────────────────────────────────────┐ │
│  │  Agent API · Model Endpoints · Knowledge Base        │ │
│  └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
  공유 서비스: Harbor(컨테이너 이미지 저장소),
              DSM(PostgreSQL — 앱 데이터·사용자 정보)
```

| 배포 방식 | 장점 | 단점 | 권장 |
|----------|------|------|------|
| VKS 배포 | 스케일링·롤링업데이트·HA | 초기 설정 복잡 | 프로덕션 |
| DLVM 직접 실행 | 빠른 테스트 | 스케일 어려움·단일 장애점 | 개발/PoC |
| 외부 배포 | 기존 인프라 활용 | 네트워크 복잡 | 특수 |

컨테이너화:

```
컨테이너화 및 배포 흐름

  [개발자 PC / CI 서버]
   ① 코드 작성 및 Dockerfile 준비
   ② docker build (이미지 빌드)
        ▼
  Container Image (로컬)
        ▼  ③ docker push (Harbor에 이미지 업로드)
  Harbor Registry (이미지 저장소)
   • Frontend 이미지 · Backend 이미지 · 버전 태그 관리
        ▼  ④ kubectl apply / helm install (VKS에 배포)
  VKS Cluster
   • Pod 생성 및 실행 · 서비스 노출

CI/CD 자동화: Git Push → 자동 빌드 → 자동 배포 파이프라인 구성 가능
            (GitLab CI, Jenkins, GitHub Actions 등 활용)
```

VKS 배포 리소스: Deployment · Service · Ingress(L7/TLS) · ConfigMap · Secret · PVC.

---

## 4.9 운영 고려사항

모니터링 핵심 지표:

```
AI 앱 모니터링 영역 (3계층)

  앱 레벨 (개발팀 담당)
   • 요청 수 / 응답 시간(P50·P95·P99) · 에러율(5xx·4xx)
   • 동시 사용자 수 · API 호출 패턴(시간대별)
  AI 서비스 레벨 (PAIS 제공)
   • Model Endpoint 응답 시간 · 토큰 사용량(Input/Output)
   • Agent 호출 수 · Knowledge Base 검색 품질(Similarity Score 분포)
  인프라 레벨 (플랫폼팀 담당)
   • GPU 사용률(DCGM Exporter) · GPU 메모리 사용량
   • VKS 클러스터 리소스(CPU/Memory) · Pod 상태·재시작 횟수

도구: VCF Operations(인프라 모니터링), Prometheus+Grafana(커스텀 메트릭),
     앱 로그(ELK Stack, Loki 등). ※ 9.1은 모델·GPU 메트릭이 PAIS에 기본 제공 → 문서 06
```

> **9.1:** 모델·GPU 메트릭과 LLM 트레이싱이 PAIS에 기본 제공됩니다 → [문서 06 관측성](06-production.md).

### 보안 고려사항

| 영역 | 권장 방안 |
|------|----------|
| 인증/인가 | OIDC 토큰, RBAC |
| 데이터 보호 | 입출력 필터링, PII 마스킹 |
| 네트워크 | TLS 필수(내부 통신 포함) |
| 프롬프트 인젝션 | 입력 검증·샌드박싱 |
| 모델 보안 | Harbor 접근 제어, 네트워크 격리 |
| 감사 로깅 | 모든 API 호출 로깅·보관 |

> **MCP 도입 시(9.1):** 에이전트가 외부 도구·DB에 접근하므로 도구 권한·범위 거버넌스가 추가로 중요합니다 → [문서 05](05-agents-mcp.md).

비용 고려사항:

```
AI 앱 비용 구성 요소

  GPU 리소스 비용 (가장 큰 비중)
   • Model Endpoint 실행에 GPU 필수 · Replicas 수에 비례 증가 · 유휴 할당 시에도 비용
   최적화: 적정 모델 크기(8B vs 70B), 자동 스케일링(최소 Replicas), 개발/테스트는 작은 모델,
          Embedding은 CPU 전용 가능(Infinity)  ※ 9.1은 소규모 Completion도 CPU 가능(llama.cpp)
  스토리지 비용
   • Harbor: 모델 이미지(수십 GB/모델) · pgvector: 벡터 데이터(문서 규모 비례)
   • 앱 데이터: 대화 이력·사용자 데이터
  컴퓨팅 비용 (앱 레벨)
   • VKS 클러스터 노드(CPU/Memory) · 상대적으로 작은 비중

비용 최적화 핵심: GPU 사용률 모니터링 후 적정 Replicas 조정, 개발/테스트는 소형 모델,
               KB 갱신 주기 최적화(과도한 재임베딩 방지)
```

성능 최적화:

| 영역 | 최적화 |
|------|--------|
| 응답 시간 | 스트리밍(SSE), 진행 상태 표시 |
| 동시 처리 | Endpoint Replicas 증가, 자동 스케일링 |
| 검색 품질 | Chunk·Similarity Cutoff 튜닝 |
| 대화 맥락 | Chat History Length 조정, 요약 기법 |
| 첫 응답(Cold Start) | Min Replicas ≥ 1 유지 (상세: [문서 06 §스케일링](06-production.md)) |

---

## 4.10 개발 vs 프로덕션 환경

| 항목 | 개발/테스트 | 프로덕션 |
|------|------------|----------|
| 배포 위치 | DLVM 직접 | VKS |
| Replicas | 1 | 2+ (HA) |
| 스케일링 | 수동 | 자동 |
| 모니터링 | 기본 로그 | 전체 스택 + 알림 |
| 보안 | 내부망 | TLS, 인증 강화, 감사 |
| 데이터 | 테스트 | 실데이터 + 백업 |

환경 전환 체크리스트:

```
개발 → 프로덕션 전환 체크리스트

  - 컨테이너 이미지: Dockerfile 최적화(멀티스테이지), 이미지 크기 최소화, Harbor Push
  - Kubernetes 매니페스트: Deployment/Service/Ingress, Resource Limits/Requests,
     Health Check(Liveness/Readiness)
  - 설정 관리: ConfigMap(환경별 설정 분리), Secret(민감 정보), 환경 변수 정리
  - 보안: TLS 인증서, 인증/인가 테스트, 네트워크 정책 검토
  - 모니터링/로깅: 로그 수집, 메트릭 대시보드, 알림 규칙
  - 성능/부하 테스트: 예상 트래픽 부하, 응답 SLA 확인, 스케일링 동작 검증
  - 백업/복구: 데이터 백업 정책, 복구 절차 문서화·테스트 (상세 HA/DR은 문서 06)
```

AI 앱 개발 핵심:

```
AI 앱 개발 핵심 요약

  1. PAIS 활용이 기본 — PAIS는 PAIF에 포함된 모듈, Agent API로 RAG 즉시 사용,
     개발팀은 AI 로직 구현 없이 API 호출에 집중
  2. 역할 분담 명확화 — PAIS: AI 두뇌(LLM·RAG·세션), 개발팀: 앱 몸체(UI·인증·비즈니스),
     인프라팀: 플레이그라운드 환경 제공
  3. 계층 구조 이해 — Frontend → Backend → PAIS → Infrastructure, 각 계층 책임·담당 명확히
  4. 개발-프로덕션 경로 — 개발: DLVM+PAIS Playground 반복 실험, 프로덕션: VKS 컨테이너 배포,
     PAIS Agent는 이미 프로덕션 준비 상태
  5. 운영 고려사항 — 모니터링 3계층, 보안(인증·프롬프트 인젝션·감사),
     비용(GPU 핵심·적정 크기), HA/DR 프로덕션 필수 (상세는 문서 06)
```

---

[← 이전: 03 역할별 워크플로우](03-workflows.md) · [목차](../README.md) · [다음: 05 에이전트·MCP·거버넌스 →](05-agents-mcp.md)

# 01 — 핵심 개념 및 페르소나

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.
> 처음이라면 [문서 00 What's New](00-whats-new.md)로 9.1 변경점을 먼저 훑어보시길 권합니다.

이 문서는 PAIF/PAIS/DLVM이 **무엇이고 서로 어떤 관계인지**, **누가 무엇을 하는지**(페르소나)를 정리합니다. 이후 모든 문서의 공통 토대입니다.

---

## 1.1 용어 정의

| 용어 | 정식 명칭 | 역할 | 비유 |
|------|----------|------|------|
| **PAIF** | VMware Private AI Foundation with NVIDIA | GPU 인프라 + AI 서비스 플랫폼 전체 | 건물 + 모든 시설 |
| **PAIS** | Private AI Services | 관리형 AI 서비스 레이어 (추론, RAG, Agent, MCP) | 건물 내 비즈니스 서비스 |
| **DLVM** | Deep Learning VM | GPU 장착 개발자 워크스테이션 VM | 개발자 책상 + 장비 |
| **VKS** | vSphere Kubernetes Service | 프로덕션용 GPU 가속 K8s 클러스터 | 프로덕션 서버팜 |
| **DSM** | VMware Data Services Manager | 데이터베이스 서비스 (pgvector 포함) | 데이터베이스 관리 시스템 |

> **PAIS는 별도 제품이 아니라 PAIF에 포함된 서비스 레이어입니다.** 그리고 "PAIF"는 두 가지로 쓰입니다 — 수식어 없이 **PAIF**라 하면 VCF가 제공하는 Private AI Foundation **솔루션 전체**(GPU 인프라부터 서비스까지)를 가리키고, 큰 구성요소를 가를 때의 GPU·지원 인프라 부분(공식 용어 **PAIF core functionality**)은 **"PAIF 코어 기능 계층"**(GPU·지원 인프라를 묶는 PAIF의 인프라·관리 계층)으로 구분해 적습니다. 한 줄로: **PAIF(솔루션) = PAIF 코어 기능 계층 + PAIS 서비스 계층**. PAIS는 공식 문서상 *"a Supervisor service ... installed as a package, separately from the VMware Private AI Foundation with NVIDIA core functionality"* 로 코어 기능과 **별도 설치**됩니다. 둘 다 VCF 코어 구독에 포함됩니다(§1.2). 계층 그림은 [문서 02 §2.1](02-architecture.md#21-전체-계층-구조).

---

## 1.2 라이선스 구조 (정확히)

9.0.x 가이드 일부에서 "PAIF는 VCF의 Add-on"으로 기술했으나, 이는 **부정확**합니다. 정확한 구조는 다음과 같습니다.

```
VMware Cloud Foundation 9.1 (코어 구독)
   │
   ├── vSphere · vSAN · NSX · VCF Operations · VCF Automation · VKS/VKSM
   │
   └── PAIF (Private AI Foundation) * 코어 구독에 포함 — 별도 구매 불필요
            │
            ├── PAIS (Private AI Services)  ← 포함
            └── DLVM 이미지                  ← 포함

별도 구매가 필요한 것:
   • NVIDIA AI Enterprise (NVAIE) — NVIDIA에서 별도 구매
        (vGPU 호스트 드라이버, NGC 컨테이너, NIM, NeMo, Triton 등)
   • GPU 하드웨어 (H100/H200/L40S/Blackwell 등) — BCG/HCL 확인 필수
```

| 항목 | 포함 여부 | 비고 |
|------|----------|------|
| PAIF (cores) | 지원 VCF 코어 구독 포함 | 별도 구매 불필요 |
| PAIS, DLVM 이미지 | 지원 PAIF에 포함 | — |
| 벡터 DB(pgvector) via DSM | 지원 PAIS 사용분 한정 포함 | DSM은 본래 별도 라이선스 Advanced Service이나, **PAIS가 벡터 DB용 DSM 사용 권한(entitlement)을 포함** |
| **NVIDIA AI Enterprise (NVAIE)** | 미지원 별도 (NVIDIA 구매) | vGPU 드라이버·NIM·NeMo 등 |
| GPU 하드웨어 | 미지원 별도 | BCG/HCL 확인 |
| DSM 일반 DBaaS 확장 사용 | 미지원 별도 | 벡터 DB 외 용도로 DSM 확장 시 Advanced Service 라이선스 |

> **자주 틀리는 부분 1:** "PAIF는 Add-on이다" → 틀립니다. PAIF는 VCF 코어 포함입니다.
> **자주 틀리는 부분 2:** "NVAIE도 VCF에 포함된다" → 틀립니다. NVAIE는 NVIDIA에서 별도 구매합니다. 도입 비용 산정 시 NVAIE 누락이 가장 흔한 실수입니다.
> **자주 틀리는 부분 3 (DSM):** PAIS 벡터 DB는 **DSM(Data Services Manager)** 기반입니다. DSM은 원래 VCF 코어와 별도로 라이선스되는 Advanced Service이지만, **PAIS가 벡터 DB(pgvector) 용도의 DSM 사용 권한을 포함**하므로 RAG용 벡터 DB를 위해 DSM을 따로 구매할 필요는 없습니다. 단, DSM을 일반 DBaaS(다른 DB 운영 등)로 확장 사용하려면 별도 라이선스가 필요합니다.

> **Enhanced DirectPath I/O 예외:** 9.1에서는 GPU를 VM/VKS 노드에 **전용 패스스루**로 줄 때 **NVAIE 라이선스 없이** 사용할 수 있고 vMotion 이점도 유지됩니다 ([문서 02](02-architecture.md#23-gpu-할당-방식-주의-91-변경)). 단, vGPU 분할 공유나 NIM/NeMo 사용 시에는 NVAIE가 필요합니다.

---

## 1.3 DLVM과 PAIS의 관계

```
미지원 잘못된 이해:
   PAIS = 개발 플레이그라운드 → 그 안에서 DLVM 배포

지원 올바른 이해:
   DLVM = 개발자 개인용 GPU VM (워크스테이션) — 모델 검증/실험용
   PAIS = 모델을 프로덕션 API로 서빙하는 관리형 플랫폼
   둘 다 "AI 플레이그라운드"라는 개념적 영역 안에서 함께 동작
```

**핵심:**
- DLVM은 PAIS와 **독립적**으로 배포 가능 (vSphere 하이퍼바이저 위에 직접)
- DLVM은 **모든 개발자가 쓰는 것이 아님** — 주로 Data Scientist·MLOps Engineer가 사용
- **App Developer는 DLVM 없이** PAIS API URL만으로 앱 개발 가능

---

## 1.4 용어 혼동 주의: "AI 플레이그라운드" vs "PAIS Playground"

| 용어 | 의미 | 범위 | 해당 제품/기능 |
|------|------|------|----------------|
| **AI 플레이그라운드** | PAIF/PAIS 기반 AI 개발/운영 전체 공간 | 개념적 영역 (DEV/QA/STAGING/PROD 포함) | 없음 (개념) |
| **PAIS Playground** | Agent Builder 내 대화형 테스트 UI | PAIS UI의 특정 기능 | PAIS Agent Builder |
| **LLM Playground** | 프롬프트 테스트 환경 (업계 일반 용어) | PAIF 용어 아님 | 업계 일반 |

> 본 문서의 "AI 플레이그라운드"는 특정 UI 화면이 아니라, 인프라팀이 PAIF/PAIS 환경을 구축하면 자동으로 형성되는 **개념적 영역**입니다. 개발자들이 DLVM·Model Endpoint·Agent 등을 자유롭게 실험·배포하는 공간을 가리킵니다.

---

## 1.5 PAIS가 제공하는 서비스 (2.1 기준)

| 모듈 | 역할 | 대상 사용자 | 9.1 / PAIS 2.1 정보 |
|------|------|------------|---------------------|
| **Model Gallery** | Harbor 기반 ML 모델 저장소 (OCI 아티팩트) | MLOps Engineer | Harbor Registry, `pais` CLI 또는 UI |
| **Model Runtime** | LLM/Embedding 모델을 API Endpoint로 자동 배포 | MLOps Engineer | **vLLM 0.11.2 / Infinity 0.0.76 / llama.cpp b7739(CPU)** |
| **Data Indexing & Retrieval** | Knowledge Base 관리, 벡터 인덱싱 자동화 | Data Scientist | pgvector 0.8.0 (PostgreSQL 16.8), **+ Google Workspace 소스**, **MCP 도구로 통합 → agentic retrieval (2.1)** |
| **Agent Builder** | RAG/에이전트 GUI 구성 + Playground | Data Scientist, MLOps | **+ MCP 도구 연동, Tool-calling** |
| **MCP 통합** | 외부 데이터·도구 표준 연동 (거버넌스), **Tool Gallery로 MCP 서버 중앙 등록·관리**, **KB를 MCP 도구로 노출** | MLOps, Platform | **PAIS 2.1 신규** ([문서 05](05-agents-mcp.md)) |
| **관측성** | 모델·GPU 메트릭 + LLM 트레이싱 | Platform, MLOps | **모델/GPU 대시보드 + OpenTelemetry** ([문서 06](06-production.md)) |

> **PAIS 2.1 MCP 강화:** 외부 도구 연동에 더해, **Tool Gallery**(MCP 서버 중앙 등록·관리 UI), **Knowledge Base의 MCP 노출**(KB-as-MCP-tool), **Data Indexing & Retrieval의 MCP 도구 통합**(에이전트가 검색 여부·검색어를 스스로 결정하는 *agentic retrieval*)이 추가됐습니다 ([Broadcom TechDocs — PAIS 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-release-notes/vmware-private-ai-services-release-notes.html)). 상세는 [문서 05 §5.3](05-agents-mcp.md#53-mcpmodel-context-protocol란).

### 추론 엔진 비교 (9.1)

| 엔진 | 버전 | 용도 | GPU 필요 |
|------|------|------|:---:|
| **vLLM** | 0.11.2 | Completion(+Embedding) 고성능 추론 | 지원 |
| **Infinity** | 0.0.76 | Embedding 전용 | CPU 가능 |
| **llama.cpp** | b7739 | Completion·Embedding **CPU 추론** | 미지원 (CPU) |

> 9.1부터는 소규모/테스트/비용 민감 워크로드의 **Completion 추론도 CPU(llama.cpp)** 로 가능합니다. 대규모·실시간 추론은 여전히 GPU(vLLM)가 정석입니다.

> 왜 추론에 GPU가 필요한지, vLLM이 어떻게 동시 요청을 처리하는지(연속 배칭·PagedAttention) 같은 동작 원리는 [③ 서빙 가이드 §0.6](../../03-serving-api/docs/00-serving-primer.md)에서, GPU·동시성 사이징 수치는 [⑥ 사이징 가이드](../../06-sizing-cost/docs/02-gpu-sizing.md)에서 다룹니다.

---

## 1.6 페르소나 및 역할 정의

### 1.6.1 AI 프로젝트 핵심 역할

| 역할 | 실제 하는 일 | 사용 도구 | 결과물 |
|------|-------------|----------|--------|
| **Data Scientist** | 모델 선택/평가, 프롬프트 엔지니어링, RAG/에이전트 설계 | DLVM JupyterLab, PAIS UI | "최적 모델 + 설정 + 프롬프트" 가이드 |
| **MLOps Engineer** | 모델 배포, 버전 관리, Endpoint 생성, MCP/운영 | DLVM CLI, PAIS UI, Harbor | API Endpoint URL + 인증 정보 |
| **App Developer** | API 호출 코드, 비즈니스 로직, UI/UX | **로컬 PC** (VS Code 등) | 실제 서비스 앱 |
| **Platform Engineer** | VCF/PAIF 인프라 구축·운영, 관측성·거버넌스 | vSphere Client, VCF Automation/Operations | AI 플레이그라운드 환경 |
| **VI Admin** | GPU 호스트 관리, vGPU/DirectPath, 네트워킹 | ESXi, vCenter | PAIF Workload Domain |

### 1.6.2 역할별 DLVM 필요 여부

| 역할 | DLVM 필요 | 이유 |
|------|:---:|------|
| **Data Scientist** | 지원 필수 | GPU로 모델 테스트, 프롬프트 튜닝 |
| **MLOps Engineer** | 지원 필요 | 모델 Push용 CLI, PAIS UI는 브라우저 |
| **App Developer** | 미지원 불필요 | API URL만 있으면 로컬 PC에서 개발 |
| **Platform Engineer** | 미지원 불필요 | vSphere/VCF 관리 도구 사용 |

### 1.6.3 협업 흐름

```
Data Scientist  → "이 모델 + 이 프롬프트 + 이 RAG 설정이 최적입니다"
       ↓
MLOps Engineer  → Harbor Push → Model Endpoint/Agent 생성 → (필요 시 MCP 연동) → API URL 전달
       ↓
App Developer   → 전달받은 API URL + 인증으로 로컬 PC에서 앱 개발
       ↓
Platform/DevOps → VKS 배포, 관측성·스케일링·거버넌스 운영
```

---

## 1.7 Data Scientist가 결정하는 것 vs PAIS가 제공하는 것

PAIS는 도구·인프라를 제공하고, **품질을 좌우하는 설계 결정은 Data Scientist의 몫**입니다.

| 구분 | PAIS가 제공 (인프라/도구) | Data Scientist가 결정 (설계/최적화) |
|------|--------------------------|-----------------------------------|
| 문서 청킹 | 청킹 기능 | chunk_size 500/1000? overlap 50/100? |
| 임베딩 | 임베딩 엔진 (Infinity) | bge-small/large/m3? multilingual? |
| 벡터 검색 | pgvector, 검색 기능 | top_k 3/5/10? similarity 0.7/0.8? |
| LLM 추론 | vLLM / llama.cpp 엔진 | Llama3? Mistral? Qwen? temperature? |
| 프롬프트 | Agent Builder GUI | 시스템 프롬프트 내용 (품질 영향 최대!) |
| 도구 연동 | MCP 통합 | 어떤 도구/데이터를 어떤 권한으로 붙일지 |

```
PAIS = 주방 (오븐, 냄비, 재료)
Data Scientist = 요리사 (레시피, 온도, 조리 시간 결정)
→ 주방이 있다고 요리가 자동으로 되지는 않습니다.
```

---

## 1.8 App Developer의 핵심 이해

> **App Developer는 AI 전문가가 아닙니다. REST API를 호출하는 일반 개발자입니다.**

| 구분 | Data Scientist | App Developer |
|------|----------------|---------------|
| 주 업무 | 모델 선택, 프롬프트, RAG/에이전트 설계 | UI/UX, 비즈니스 로직 |
| 사용 도구 | JupyterLab, Python, ML 프레임워크 | VS Code, React/Vue, FastAPI |
| 필요 지식 | ML/DL, NLP, 통계 | 웹 개발, REST API, 소프트웨어 공학 |
| 산출물 | "최적 모델+설정" 가이드 | 실제 서비스 앱 |
| DLVM 필요 | 지원 필수 | 미지원 불필요 |

App Developer가 MLOps/Data Scientist로부터 받는 것: **① PAIS Base URL ② Agent/Endpoint 이름 ③ 인증 정보(Token/OAuth) ④ 사용 가이드(세션·타임아웃)**. 이것만 있으면 로컬 PC에서 일반 REST API처럼 개발합니다. 상세는 [문서 04](04-dev-scenarios.md).

---

## 1.9 프롬프트 vs RAG vs 파인튜닝 선택

우리 모델을 사내 도메인·데이터에 맞추는 길은 셋이고, 이것이 **Private AI 설계의 첫 분기**입니다. 무엇을 고르느냐가 인프라 요구(학습용 GPU 여부)·일정·비용을 좌우하므로, 구현 패턴([문서 04](04-dev-scenarios.md))을 정하기 전에 먼저 정리해야 합니다.

- **프롬프트 엔지니어링** — 모델·지식은 그대로 두고 **지시문(프롬프트)만** 다듬어 출력을 개선합니다. 가장 싸고 빠릅니다. 시스템 프롬프트로 역할·규칙·형식을 박고, 필요하면 예시 몇 개를 프롬프트에 넣습니다(예시를 주면 **few-shot**, 안 주고 바로 시키면 **zero-shot**). 추가 학습 없이 프롬프트 안에서만 유도하는 이 방식을 **인컨텍스트 러닝(in-context learning)** 이라 합니다.
- **RAG** — 지식을 모델 밖(벡터 DB)에 두고 질문 시 검색해 프롬프트에 끼워 넣습니다. **자주 바뀌는 사내 지식·출처 표기·접근통제**가 중요할 때 적합합니다(상세 [④ RAG 레퍼런스](../../04-rag/README.md)).
- **파인튜닝(fine-tuning)** — 모델 **가중치 자체를 사내 데이터로 추가 학습**해 도메인 능력을 심습니다. 문체·특수 형식·고정된 전문 도메인이 필요하고 지식이 자주 안 바뀔 때입니다. 비용·시간이 가장 큽니다.
  - **LoRA · QLoRA · 풀 파인튜닝** — 풀 파인튜닝은 전체 가중치를 갱신해 메모리·비용이 최대입니다(다중 GPU). **LoRA**는 기존 가중치를 얼리고 작은 '어댑터'만 학습해 비용을 크게 줄이고, **QLoRA**는 거기에 양자화를 더해 단일 GPU로도 가능합니다. 대부분의 도메인 적응은 LoRA로 충분합니다.

| 신호 | 우선 선택 |
|------|-----------|
| 지식이 자주 바뀜 · 출처 필요 | RAG |
| 일반적 · 간단 · 빨리 시작 | 프롬프트(+ few-shot) |
| 문체 · 형식 · 전문 도메인 고정, 지식 안정 | 파인튜닝(RAG 병행 가능) |

셋은 배타적이지 않습니다 — 흔히 **프롬프트 + RAG**를 기본으로 하고, 그래도 부족할 때만 파인튜닝을 더합니다. 파인튜닝 학습은 PAIS 밖(DLVM·NeMo)에서 수행해 Model Gallery로 반입하며(워크로드 위치는 [문서 04 §4.3](04-dev-scenarios.md)), 학습 GPU·노드 비용은 [⑥ 사이징](../../06-sizing-cost/docs/02-gpu-sizing.md)을 참조합니다.

---

[← 이전: 00 What's New (9.1)](00-whats-new.md) · [목차](../README.md) · [다음: 02 아키텍처 및 구축 순서 →](02-architecture.md)

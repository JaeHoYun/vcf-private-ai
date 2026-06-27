# VCF 9.1 Private AI 모델 서빙 API 가이드

> **이 가이드를 읽기 전에** — 임베딩·벡터·토큰·RAG·쿠버네티스(VKS) 같은 용어가 낯설다면, 먼저 [VCF Private AI 입문 (Primer)](../00-foundations/README.md)에서 기초 어휘를 잡으시길 권합니다. 이 가이드는 그 개념들을 이미 아는 것으로 전제합니다.

> Private AI Foundation(PAIF) 위에서 모델을 **API로 서빙하고 사내 앱이 소비**하는 방법을 다루는 실무 레퍼런스

VCF에서 Private AI Foundation을 구축하고(인프라), 그 위에 엔터프라이즈 벡터 DB를 올렸다면(데이터), 마지막 단계는 **"그 모델을 어떻게 API로 노출하고, 앱이 어떻게 소비하는가"** 입니다. 이 가이드는 PAIS(Private AI Services)가 제공하는 **OpenAI 호환 API**를 중심으로, 추론 엔드포인트·에이전트(RAG) API·인증·MCP 도구·관측성·레퍼런스 구현을 생애주기 순서로 정리합니다.

핵심 메시지는 하나입니다. **기존 OpenAI 코드의 `base_url`만 사내 PAIS로 바꾸면, 데이터가 외부로 나가지 않는 사내 추론으로 그대로 전환됩니다.**

> **VCF Private AI 가이드 시리즈 — ③ 서빙 API** · 7부작 중 한 편입니다. [전체 7개 보기 — 시리즈 허브](../README.md) · 상위 전략 [AX 방법론](https://github.com/JaeHoYun/enterprise-ax-methodology)

---

## 기반 버전 (Source of Truth)

> 모든 수치·버전은 작성 시점(2026-06) Broadcom 공식 문서 기준이며, 적용 전 [참고 자료](#참고-자료)의 공식 문서로 재확인하시기 바랍니다.

| 구분 | 버전 | 비고 |
|------|------|------|
| **VMware Cloud Foundation** | **9.1** | GA 2026년 5월 |
| **Private AI Foundation with NVIDIA (PAIF)** | **9.1** | VCF 코어 구독 포함 (NVAIE만 별도) |
| **Private AI Services (PAIS)** | **2.1** | UI 셀프서비스, MCP, Artifact Mirroring Tool(아티팩트 미러링 도구, 에어갭 아티팩트 반입) 추가 |
| Private AI Services API | OpenAI 호환 (`/compatibility/openai/v1`) | [공식 API 레퍼런스](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/) |

> **추론 엔진 버전(vLLM·Infinity·llama.cpp 등)** 은 형제 가이드의 버전 단일 기준 문서를 따릅니다 → [① README 버전표](../01-infra/README.md#기반-버전-source-of-truth). 본 가이드는 **API 계층**에 집중하며, 엔진 버전은 별도로 단정하지 않고 그 표를 기준선으로 삼습니다. 엔진 버전은 릴리스마다 변동되므로 적용 직전 공식 릴리스 노트로 확인하시기 바랍니다.

---

## 문서 구성

기초 동작 원리(00)를 먼저 짚고, 추론을 노출하고(서빙) → 호출하고(소비) → 통제하는(인증·도구·운영) 생애주기 순서입니다.

| 순서 | 문서 | 내용 |
|---|---|---|
| 00 | [추론 서빙은 어떻게 동작하나 (기초)](docs/00-serving-primer.md) | 왜 GPU·양자화·추론 엔진·동시성(연속 배칭·PagedAttention)·같은 API로 CPU↔GPU |
| 01 | [왜 사내 추론 API인가](docs/01-why-serving-api.md) | 데이터 주권·비용·레이턴시, OpenAI 호환의 의미 |
| 02 | [서빙 API 아키텍처](docs/02-serving-api-architecture.md) | 서빙 계층의 토대·4대 모듈·제어/데이터 평면, 모델 생애주기(반입→배포→노출→호출), Model Runtime·Gateway, Endpoint vs Agent |
| 03 | [OpenAI 호환 엔드포인트](docs/03-openai-compatible-endpoints.md) | models·embeddings·chat/completions, 요청/응답 스키마, 스트리밍, 함수 호출, 구조화 출력(JSON 모드), 에러 처리 |
| 04 | [에이전트·RAG API](docs/04-agent-rag-api.md) | agents CRUD, agent chat, data-sources·knowledge-bases·indexes·search |
| 05 | [인증·게이트웨이](docs/05-auth-and-gateway.md) | OIDC Bearer 토큰, mTLS, API Gateway, 레이트리밋·쿼터·로드밸런싱, 에러/재시도 |
| 06 | [MCP 도구 API](docs/06-mcp-tools-api.md) | mcp-servers 등록·도구 승인, 거버넌스(읽기 우선) |
| 07 | [관측성·운영](docs/07-observability-ops.md) | 토큰 usage, OTel 트레이싱, Grafana 관측성(health·quality·behavior), 모델 버전 관리, 알려진 이슈 |
| 08 | [레퍼런스 구현](docs/08-reference-implementation.md) | curl·OpenAI SDK·LangChain 최소 동작 예제, 엔드투엔드 |

---

## 빠른 시작

- **"GPU·양자화·동시성 같은 기초부터 알고 싶어요"** → [00](docs/00-serving-primer.md)
- **"왜 외부 LLM API 대신 사내 API인가요?"** → [01](docs/01-why-serving-api.md)
- **"서빙 아키텍처가 어떻게 생겼나요? / 모델이 API가 되기까지 절차는?"** → [02](docs/02-serving-api-architecture.md)
- **"기존 OpenAI 코드를 그대로 쓸 수 있나요?"** → [03](docs/03-openai-compatible-endpoints.md) + [08](docs/08-reference-implementation.md)
- **"RAG를 직접 짜지 않고 API로 받고 싶어요"** → [04](docs/04-agent-rag-api.md)
- **"토큰은 어떻게 받나요?"** → [05](docs/05-auth-and-gateway.md)
- **"에이전트에 사내 DB·도구를 붙이고 싶어요"** → [06](docs/06-mcp-tools-api.md)
- **"운영하면서 무엇을 봐야 하나요?"** → [07](docs/07-observability-ops.md)

---

## 주요 용어

| 용어 | 설명 |
|------|------|
| **PAIF** | Private AI Foundation with NVIDIA — VCF 코어 구독에 포함된 AI 인프라 |
| **PAIS** | Private AI Services — Model Runtime·RAG·Agent Builder 등 관리형 AI 서비스 레이어 |
| **Model Endpoint** | 단일 모델을 OpenAI 호환 API로 노출하는 서빙 단위 (상태 비저장) |
| **Agent** | Model Endpoint + Knowledge Base(+MCP 도구)를 묶어 RAG·세션까지 캡슐화한 API |
| **API Gateway** | Model Runtime의 진입점 — 인증·인가·로드밸런싱 담당 |
| **OpenAI 호환** | `/compatibility/openai/v1` 경로로 OpenAI SDK·클라이언트를 그대로 사용 가능 |
| **MCP** | Model Context Protocol — 에이전트가 외부 데이터·도구를 표준으로 연동 (PAIS 2.1) |

---

## 관련 가이드 (시리즈)

이 가이드는 다음 가이드들과 **인프라 → 데이터 → 서빙(API) → 통합(RAG)** 흐름을 이룹니다. ([시리즈 허브](../README.md)에서 전체 보기)

1. **① 인프라** — [VCF Private AI Foundation 실무 가이드](../01-infra/README.md) — PAIF/PAIS/DLVM(Deep Learning VM, 딥러닝 가상머신) 구축·운영
2. **② 데이터** — [Private AI를 위한 엔터프라이즈 vectorDB 가이드](../02-vectordb/README.md) — PostgreSQL + pgvector
3. **③ 서빙(API)** — 본 가이드
4. **④ 통합(RAG)** — [엔드투엔드 RAG 레퍼런스 아키텍처](../04-rag/README.md) — ①②③을 묶는 RAG 레퍼런스
5. **⑤ 보안·거버넌스** — [Private AI 보안·거버넌스 통합 가이드](../05-security/README.md) — 전 계층 보안·거버넌스·감사
6. **⑥ 사이징·용량·비용** — [사이징·용량·비용(TCO) 가이드](../06-sizing-cost/README.md) — 워크로드·GPU·VKS 사이징·TCO
7. **⑦ 통합 설계** — [VCF Private AI 통합 설계 가이드](../07-design/README.md) — ①~⑥의 설계 결정을 하나의 플랫폼 설계로 종합

---

## 라이선스

이 문서는 자유롭게 활용하실 수 있습니다. **출처 표기**를 부탁드립니다.

```
출처: https://github.com/JaeHoYun/vcf-private-ai/tree/main/03-serving-api
```

## 업데이트 이력

- **v0.1 (2026-06):** 초안 작성. VCF 9.1 / PAIF 9.1 / PAIS 2.1 기준. 공식 PAIS API 레퍼런스(developer.broadcom.com) 기반으로 OpenAI 호환 엔드포인트·에이전트·인증·MCP·관측성·레퍼런스 구현 정리.
- **v0.2 (2026-06):** 문서 00 "추론 서빙은 어떻게 동작하나 (기초)" 신설 — 왜 GPU·양자화·추론 엔진·OpenAI 호환 추상화·동시성 메커니즘(연속 배칭·PagedAttention)·개발(CPU)/운영(GPU) 패턴을 개념 수준으로 정리. 정량은 ⑥, 인프라는 ①로 딥링크.
- **v0.3 (2026-06):** 문서 00에 §0.8 토큰·컨텍스트 윈도우, §0.9 모델 타입·포맷·샘플링 추가 — 토큰·컨텍스트 한계가 청크·top-k·모델 선택을 어떻게 묶는지, 베이스 vs Instruct·오픈웨이트·모델 포맷·샘플링 파라미터 기초.
- **v0.4 (2026-06):** 문서 03에 §3.7 구조화 출력(JSON 모드) 신설 — `response_format`(json_object·json_schema)·vLLM `guided_*` 제약 디코딩으로 응답 본문을 스키마로 강제하는 방법, 분류·추출·라우팅 활용과 함정. 기존 §3.7 치트시트→§3.8, §3.8 에러 처리→§3.9로 이동.
- **v0.5 (2026-06):** 문서 03 §3.8 치트시트 보강 — 엔드포인트 3종에 더해 `chat/completions` 옵션(스트리밍·함수 호출·구조화 출력·에러) 한눈 표 추가. 용어 정비 — API를 가리키는 '표면'(번역투)을 인터페이스·API·방식·경로로 교체(보안/공격 표면은 표준어로 유지). 00·02·03·04·08 적용.

## 피드백

오류 발견, 개선 제안, 질문은 [Issues](https://github.com/JaeHoYun/vcf-private-ai/issues)에 남겨주세요.

---

## 면책 조항 (Disclaimer)

**작성자 관점** — VCF + PAIF + PAIS 조합으로 모델을 서빙하는 방향을 권장하는 관점으로 쓰여 있습니다. 다만 PAIS 관리형 서빙이 맞지 않는 경우(미지원 엔진·기존 MLOps 자산 등)도 솔직하게 다룹니다.

**비공식 문서** — 공개된 공식 기술 문서·API 레퍼런스·릴리스 노트를 기반으로 작성한 비공식 실무 레퍼런스입니다. Broadcom, VMware, NVIDIA 또는 기타 벤더의 공식 입장을 대변하지 않습니다.

**정확성 및 최신성** — 본 문서의 내용은 작성 시점(2026년 6월) 기준이며, 제품 업데이트에 따라 달라질 수 있습니다. 특히 **API 엔드포인트 경로·요청/응답 스키마·인증 방식**은 PAIS 버전에 따라 변경될 수 있으므로, 적용 전 반드시 [공식 API 레퍼런스](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/)와 제품 내 Sample Code로 확인하시기 바랍니다. 또한 본문에 언급된 **성능·비용 관련 서술**(예: 단위 비용·레이턴시 이점)은 일반론이며 실제 효과는 워크로드·환경별 검증이 필요합니다.

**책임 한계** — 본 문서를 참고하여 발생한 직접적·간접적 손해에 대해 작성자는 책임을 지지 않습니다. 실제 구축·운영은 각 조직의 요구사항과 환경에 맞게 검토 후 진행하시고, 기술 지원이 필요한 경우 Broadcom 공식 지원 채널을 이용하시기 바랍니다.

**상표권 고지** — VMware, VMware Cloud Foundation, vSphere, vSAN, NSX, VCF Automation, VCF Operations, Private AI Foundation, Private AI Services 등은 Broadcom의 등록 상표입니다. NVIDIA, CUDA, NIM, NeMo 등은 NVIDIA Corporation의 등록 상표입니다. OpenAI는 OpenAI의 상표이며, 본 문서의 "OpenAI 호환"은 API 인터페이스 호환성을 의미할 뿐 OpenAI와의 제휴·보증을 뜻하지 않습니다. 기타 언급된 제품명 및 회사명은 각 소유자의 상표 또는 등록 상표입니다.

---

## 참고 자료

- [VMware Private AI Service API Reference (Broadcom Developer Portal)](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/)
- [Private AI Services — Detailed Design (VCF 9.1, Broadcom TechDocs)](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/design/design-library/private-ai-platform-detailed-design/private-ai-services.html)
- [VMware Private AI Foundation with NVIDIA 9.1 (Broadcom TechDocs)](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1.html)
- [Streamline, Simplify and Protect all your AI workloads with VCF 9.1 (VCF Blog, 2026-05)](https://blogs.vmware.com/cloud-foundation/2026/05/05/streamline-simplify-and-protect-all-your-ai-workloads-with-vcf-9-1/) — llama.cpp CPU 추론·멀티 액셀러레이터·Grafana AI 메트릭 근거
- [Broadcom Announces VMware Cloud Foundation 9.1 (Broadcom, 2026-05)](https://www.broadcom.com/company/news/product-releases/64326) — AMD·NVIDIA 멀티 액셀러레이터, AMD·Intel·NVIDIA 혼합 컴퓨트 근거
- [VMware Private AI Services Release Notes (Broadcom TechDocs)](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-release-notes/vmware-private-ai-services-release-notes.html) — PAIS 2.1(llama.cpp b7739, 관측성, MCP tool calling) 근거. *URL 경로는 `/9-0/`이나 PAIS 릴리스 노트는 2.1(=9.1 동반) 내용을 동일 경로에 누적 게시하므로 9.1 기준선으로 인용.*
- [Running Completion or Embedding Models by Using Model Endpoints (Broadcom TechDocs)](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/what-is-private-ai-services/deploying-model-endpoints.html) — *9.1 전용 딥링크가 아직 공개되지 않아 9.0 문서를 9.1 기준선으로 인용(엔드포인트 개념은 버전 간 동일). 적용 직전 9.1 문서 세트에서 재확인 권장.*
- [How to Connect your VMware Private AI Services Agents to OpenWeb UI (VCF Blog)](https://blogs.vmware.com/cloud-foundation/2025/08/15/how-to-connect-your-vmware-private-ai-services-agents-to-openweb-ui/)

# 02 — 서빙 API 아키텍처

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.

앞 문서(01)에서 "왜 사내 추론 API인가"를 봤다면, 이 문서는 **그 API가 실제로 어떻게 만들어지고 노출되는가** — 모델 하나가 들어와서 앱이 호출 가능한 엔드포인트가 되기까지의 구조와 절차 — 를 다룹니다. PAIS의 어느 모듈이 무엇을 수행하고, 무엇에 의존하며, 서로 어떻게 연결되는지를 따라가면, 이후 문서(엔드포인트·인증·운영)에서 마주칠 설계가 왜 그렇게 생겼는지 자연히 풀립니다.

> **이 문서의 고도(altitude)와 경계** — 이 가이드는 **API 서빙 계층**을 다룹니다. 그 아래의 플랫폼 토대(VCF·Supervisor·VKS·GPU 할당·DLVM·구축 순서)는 **[① 인프라 가이드 §2 아키텍처](../../01-infra/docs/02-architecture.md)** 가 기준이고, 토폴로지·노드풀 같은 설계 결정은 **[⑦ 통합 설계 가이드](../../07-design/README.md)**, 용량·비용 산정은 **[⑥ 사이징](../../06-sizing-cost/README.md)** 이 맡습니다. 이 문서는 그 토대를 **다시 쓰지 않고**, 그 위에 얹히는 서빙 계층의 그림과 흐름에 집중합니다. 본 문서에서 다루지 않는 것은 §2.9에 명시했습니다.

---

## 2.1 무엇 위에 얹히나 — 서빙 계층의 토대

서빙은 허공에 뜨지 않습니다. PAIS의 모든 추론 API는 아래 토대 위에서 동작하며, **이 귀속 관계가 GPU·격리·스케일링이 어디서 결정되는지를 정합니다.**

```
VCF 9.1 — PAIF Workload Domain (GPU 가속 워크로드 도메인)
  └── Supervisor                              ← vSphere 위의 Kubernetes 제어면
        └── vSphere Namespace                 ← 격리 단위 (DEV/QA/STAGING/PROD)
              └── VKS (vSphere Kubernetes Service)
                    └── PAIS 2.1              ← 여기서부터가 본 가이드의 범위
                          ├── Model Gallery (Harbor)
                          ├── Model Runtime (추론 엔진 + ML API Gateway)
                          ├── Data Indexing & Retrieval
                          └── Agent Builder (+ MCP)
  └── GPU 호스트(ESXi + vGPU / Enhanced DirectPath I/O)  ← Supervisor 직속 인프라
```

핵심만 짚으면:

- **GPU는 호스트(ESXi)에 물려 있고**, Model Endpoint 파드는 VKS 워커 노드(VM) 위에서 그 물리 GPU에 연결됩니다(§2.3). 즉 "모델에 GPU를 붙인다"는 곧 *Endpoint 파드를 GPU 호스트가 받치는 워커 노드에 스케줄한다*는 뜻입니다.
- **격리·쿼터는 vSphere Namespace 단위**입니다(§2.8). 어느 모델·에이전트가 누구에게 보이고, 복제본을 몇 개까지 띄울 수 있는지가 여기서 걸립니다.
- **공유 인프라**(Harbor·DSM의 pgvector·VCF Automation·관측성)는 네임스페이스들이 함께 씁니다.

> GPU 할당 방식(vGPU vs Enhanced DirectPath I/O), 구축 Phase, 의존성 다이어그램의 상세는 **[① §2.1·§2.3·§2.8](../../01-infra/docs/02-architecture.md)** 에 있습니다. 본 문서는 "서빙이 이 위에 얹힌다"는 연결만 세웁니다.

---

## 2.2 PAIS 4대 모듈 — 무엇이 무엇을 하는가

공식 설계 문서(PAIS Detailed Design, VCF 9.1) 기준으로 PAIS는 4개 모듈로 구성됩니다. 단순 나열이 아니라 **각자 무엇을 수행·유지·노출하며 무엇에 의존하는지**가 아키텍처의 본체입니다.

```
                 ┌──────────────── Model Gallery (Harbor / OCI) ───────────────┐
                 │  모델 아티팩트 저장 · RBAC 접근통제 · 버전관리 · 메타데이터    │
                 └───────────────────────────┬────────────────────────────────┘
                                             │ ① 모델 리비전을 가져와 배포
                                             ▼
   ┌──────────────────────────────  Model Runtime  ──────────────────────────────┐
   │                                                                              │
   │   [ ML API Gateway ]  인증 · 인가 · 로드밸런싱 · OpenAI 호환 경로 · SSE       │ ◀── 모든 호출의 진입점
   │          │                          │                          │             │
   │          ▼                          ▼                          ▼             │
   │   Completion Endpoint        Embedding Endpoint          (복제본 N개)         │
   │   · vLLM (GPU)               · Infinity (CPU/GPU)        VKS 워커 노드 파드    │
   │   · llama.cpp (CPU)          · vLLM / llama.cpp          → ESXi 물리 GPU 연결  │
   │          │ stateless                │                                         │
   └──────────┼──────────────────────────┼─────────────────────────────────────-─┘
              │ 모델 호출(내부)           │ 임베딩 생성
              ▼                          ▼
   ┌─ Agent Builder ─────────┐   ┌─ Data Indexing & Retrieval ─┐
   │  RAG + 세션 + MCP 도구   │◀─▶│  Data Source → 파싱 → 청킹    │
   │  를 묶어 오케스트레이션   │   │  → 임베딩 → pgvector 저장     │
   │  → Agent API            │   │  (Knowledge Base / Index)    │
   └─────────────────────────┘   └──────────────────────────────┘
```

### 모듈별 책임표 — 수행 / 유지 / 요구(의존) / 노출

| 모듈 | 무엇을 수행하나 | 무엇을 유지하나(상태) | 무엇을 요구하나(의존) | 무엇을 노출하나 |
|------|----------------|---------------------|---------------------|----------------|
| **Model Gallery** | 모델 아티팩트 보관·반입·버전관리·접근통제 | 모델 리비전·메타데이터(상태 보관소) | Harbor(OCI), Supervisor 서비스, 스토리지 | Runtime이 가져갈 **모델 리비전** (§2.4) |
| **Model Runtime** | Gallery의 모델을 추론 엔진으로 실행, OpenAI 호환 API로 노출 | **stateless** — 요청 간 상태 없음 | Gallery(모델), VKS 워커 노드, **GPU**(completion), ML API Gateway | **Model Endpoint** = OpenAI 호환 추론 API (§2.5·[03](03-openai-compatible-endpoints.md)) |
| **Data Indexing & Retrieval** | 데이터 소스 파싱·청킹·임베딩·의미 검색 | Knowledge Base / 인덱스(pgvector에 영속) | **임베딩 Endpoint**(Runtime), DSM의 pgvector, 데이터 소스 커넥터 | **검색 API** / KB (§[04](04-agent-rag-api.md)) |
| **Agent Builder** | 모델+KB+도구를 묶어 RAG·세션·도구호출 오케스트레이션 | **stateful** — `session_id` 기반 대화·세션 | Model Endpoint(LLM), KB(검색), MCP 도구 | **Agent API** (§2.6·[04](04-agent-rag-api.md)·[06](06-mcp-tools-api.md)) |

읽는 법: **위에서 아래로 의존이 흐릅니다.** Gallery가 모델을 대고 → Runtime이 그걸 Endpoint로 띄우고 → Indexing이 그 임베딩 Endpoint를 써서 KB를 만들고 → Agent가 그 Endpoint와 KB와 도구를 묶습니다. 그래서 한 모듈이 막히면 그 아래가 함께 막힙니다(예: 임베딩 Endpoint가 없으면 KB 인덱싱이 안 됩니다).

### 제어 평면(control plane)과 데이터 평면(data plane)

같은 모듈을 두 가지 시선으로 봐야 그림이 또렷해집니다.

| 평면 | 무엇이 흐르나 | 누가 다루나 | 경로 |
|------|-------------|-----------|------|
| **제어 평면** | 모델 반입·Endpoint 생성/삭제·복제본 조정·KB 구성 | 관리자/MLOps (UI·`vcf pais` CLI·REST) | VCF Automation UI / PAIS UI / kubectl |
| **데이터 평면** | 실제 추론 요청·응답(토큰) | 앱(런타임 트래픽) | ML API Gateway → Endpoint 파드 |

이 분리가 중요한 이유: **앱이 쓰는 것은 데이터 평면 하나**(Gateway 단일 URL)뿐입니다. 모델을 새로 올리거나(제어 평면) 복제본을 늘려도, 앱 코드는 데이터 평면 경로를 그대로 두면 됩니다(§2.7의 스케일아웃 흡수가 여기서 나옵니다).

> 추론 엔진의 정확한 버전(vLLM·Infinity·llama.cpp)은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)의 안내대로 형제 가이드 표를 기준선으로 삼고, 적용 직전 공식 릴리스 노트로 확인하시기 바랍니다.

---

## 2.3 모델 한 개의 생애주기 — 반입에서 호출까지

아키텍처를 "정지 화면"이 아니라 "절차"로 보면 가장 빨리 이해됩니다. 모델 하나가 사내 추론 API가 되기까지는 다음 다섯 단계를 거칩니다.

```
 [준비]            [반입]              [배포]                    [노출]         [소비]
 PAIS 밖           Model Gallery       Model Runtime             ML API Gateway  앱/에이전트
┌────────┐       ┌──────────┐        ┌────────────────────┐    ┌──────────┐   ┌────────┐
│외부 모델│──①──▶│ Harbor   │──②──▶ │ 추론 엔진 컨테이너로 │─③▶│ 단일 URL │─④▶│  앱     │
│NGC/HF  │       │ (OCI)    │        │ VKS 워커 노드에      │    │ 인증·인가 │   │ base_url│
│또는    │       │ 리비전·  │        │ 파드로 스케줄        │    │ 로드밸런싱│   │ 만 교체 │
│DLVM/학습│      │ 메타데이터│        │ → ESXi 물리 GPU 연결 │    └──────────┘   └────────┘
└────────┘       └──────────┘        │ (복제본 ≥2)         │
                                     └────────────────────┘
```

1. **준비 (PAIS 밖)** — 모델은 외부 출처(NVIDIA NGC, Hugging Face 등)에서 받거나, 사내에서 파인튜닝·학습한 산출물입니다. **파인튜닝·학습 자체는 PAIS 범위 밖**이며 DLVM이나 별도 학습 파이프라인(NeMo 등)에서 수행합니다(§2.9 경계 참조).
2. **반입 (Model Gallery)** — 검증된 모델을 Harbor(OCI 레지스트리)에 올립니다. NIM은 JupyterLab 노트북으로 Harbor에 내려받고, 자체 모델은 `vcf pais models push`로 리비전을 등록합니다. Gallery는 이때 **버전·접근권한(RBAC)·메타데이터**를 함께 관리합니다(§2.4).
3. **배포 (Model Runtime)** — 관리자가 Gallery의 특정 모델 리비전을 골라 **Model Endpoint**를 만듭니다. Runtime은 그 모델을 적합한 추론 엔진(생성=vLLM/llama.cpp, 임베딩=Infinity 등) 컨테이너로 감싸 **VKS 워커 노드에 파드로 스케줄**하고, 그 파드가 **ESXi 호스트의 물리 GPU에 연결**됩니다. 가용성을 위해 서로 다른 워커 노드에 **복제본을 2개 이상** 둡니다.
4. **노출 (ML API Gateway)** — 배포된 Endpoint는 개별 파드 IP가 아니라 **Gateway의 단일 진입 URL**로 노출됩니다. Gateway가 인증·인가·로드밸런싱을 그 뒤에서 처리합니다(§2.7).
5. **소비 (앱/에이전트)** — 앱은 기존 OpenAI 코드의 `base_url`만 사내 PAIS로 바꿔 호출합니다([03](03-openai-compatible-endpoints.md)·[08](08-reference-implementation.md)). Agent를 쓰면 그 위에 RAG·세션·도구가 얹힙니다(§2.6).

> **여기서 "GPU는 어디에 연결되나"의 답** — 프로덕션 추론에서 GPU는 개발용 DLVM이 아니라 **Endpoint 파드(VKS 워커 VM)가 ESXi 호스트의 물리 GPU에 직접 연결**되는 방식으로 쓰입니다. ([근거: VCF Blog — VKS 워커 VM 파드의 물리 GPU 연결](https://blogs.vmware.com/cloud-foundation/2025/12/17/deploy-vmware-private-ai-services-in-minimal-vmware-cloud-foundation-environments/)) DLVM의 역할은 §2.9에서 분리해 설명합니다.

---

## 2.4 Model Gallery — 무엇을 저장하고 무엇을 하는가

Model Gallery는 단순 파일 창고가 아니라 **"무엇을 서빙해도 되는가"의 출처·거버넌스 관문**입니다. **Harbor**(OCI 호환 컨테이너 레지스트리)를 기반으로 Supervisor 서비스로 배포되며, 모델을 프로젝트·리포지토리 단위로 보관하고 리포지토리별 쓰기 권한을 관리합니다. (CLI·일부 인자에서는 내부적으로 `model-store`라는 용어도 함께 쓰입니다.)

**무엇을 저장하나** — OCI 레지스트리이므로 단일 형식에 묶이지 않습니다.

| 저장 대상 | 설명 |
|----------|------|
| **모델 가중치** | safetensors·GGUF 등. NIM은 추론 컨테이너 형태로 보관 |
| **메타데이터(annotation)** | 모델 아키텍처·파라미터 수·포맷 등 구조화 정보 → 검색·표시에 사용 |
| (그 밖의 OCI 아티팩트) | OCI 레지스트리 특성상 Helm 차트·서명(signature)·SBOM 등도 담길 수 있음 |

**무엇을 하나** — 저장에 더해 세 가지를 수행합니다: ① **접근통제(RBAC)** — 리포지토리 단위 권한, ② **버전관리** — 허용 모델의 리비전 관리, ③ **반입 경로 제공** — NIM(JupyterLab), 자체 모델(`vcf pais models push`), 에어갭 미러링(Artifact Mirroring Tool, §2.8).

> **경계 — Gallery는 학습하지 않습니다.** Model Gallery는 모델을 **보관·반입·버전관리**할 뿐, 파인튜닝·학습은 하지 않습니다. 도메인 적응 학습은 PAIS 밖(DLVM·전용 학습 파이프라인)에서 수행한 뒤 산출 모델을 Gallery로 반입합니다. 학습용 GPU·노드 사이징은 [⑥ GPU 사이징](../../06-sizing-cost/docs/02-gpu-sizing.md)·[①](../../01-infra/README.md)에 위임합니다. 에이전트 관점의 모델 선택·CLI는 [⑧ §5](https://github.com/JaeHoYun/vcf-private-ai-agents/blob/main/docs/05-models-serving.md)에서 다룹니다.

([근거: Broadcom Blog — Harbor as an AI Model Registry](https://blogs.vmware.com/cloud-foundation/2026/03/03/using-harbor-as-an-ai-model-registry/), [Model Gallery — JupyterLab Notebooks](https://blogs.vmware.com/cloud-foundation/2026/02/26/model-gallery-how-to-use-jupyterlab-notebooks-to-simplify-model-deployment-and-management/), [TechDocs — Storing ML Models](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/what-is-private-ai-services/storing-ml-models-in-vmware-private-ai-foundation.html). 메타데이터 항목·세부 스키마는 릴리스마다 달라질 수 있으니 적용 직전 공식 문서로 재확인하시기 바랍니다.)

---

## 2.5 Model Runtime — 추론 엔진과 멀티 액셀러레이터 (9.1)

Model Runtime은 Gallery의 모델을 실제로 실행해 API로 노출하는 모듈입니다. 단일 엔진에 고정되지 않고, 워크로드·하드웨어에 따라 여러 추론 엔진을 선택합니다.

| 엔진 | 주 용도 | 가속기 | API 관점 함의 |
|------|--------|--------|--------------|
| **vLLM** | Completion(생성형 LLM) | GPU | 고처리량 생성. `GET /models`의 `model_engine`로 식별 |
| **Infinity** | Embedding | CPU/GPU | 임베딩 전용. GPU 없이도 운영 가능 |
| **llama.cpp** | Completion·Embedding | **CPU** | **GPU 없이 CPU만으로** 추론. GGUF(llama.cpp 계열이 쓰는 단일 파일 모델 형식) 사용 |

- **CPU Completion 추론(llama.cpp)** — VCF 9.1에서 Model Runtime이 llama.cpp 엔진을 통합해 **CPU 기반 추론**을 지원합니다. GPU가 필요 없는 테스트·PoC·경량 워크로드를 GPU 없이 돌려 총소유비용(TCO)을 낮출 수 있습니다. 모델은 GGUF 형식으로 제공됩니다. ([VCF 9.1 블로그](https://blogs.vmware.com/cloud-foundation/2026/05/05/streamline-simplify-and-protect-all-your-ai-workloads-with-vcf-9-1/), [PAIS 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-release-notes/vmware-private-ai-services-release-notes.html))
- **멀티 액셀러레이터(AMD/NVIDIA)** — VCF 9.1은 **AMD·NVIDIA 양쪽 GPU 선택지**와 AMD·Intel CPU 플랫폼을 아우르는 혼합 컴퓨트를 지원합니다. 즉 같은 OpenAI 호환 API를 유지한 채, 그 뒤의 가속기를 조직 사정에 맞게 고를 수 있습니다. ([Broadcom 9.1 발표](https://www.broadcom.com/company/news/product-releases/64326))

> **API 관점의 결론** — 앱 코드는 엔진·가속기 종류를 구분하지 않아도 됩니다. 어느 엔진(vLLM/Infinity/llama.cpp)이 어느 가속기(GPU/CPU, AMD/NVIDIA)에서 떠 있든, 호출은 동일한 `…/compatibility/openai/v1/...` 경로로 이루어집니다. 실제 엔진·버전·가속기 매핑은 `GET /models`의 `model_engine`과 적용 직전 공식 릴리스 노트로 확인하시기 바랍니다(엔진 버전은 릴리스마다 변동).

> 엔진을 **언제 무엇을** 고르는지의 직관과, vLLM이 동시 요청을 처리하는 메커니즘(연속 배칭·PagedAttention)은 [00 §0.4·§0.6](00-serving-primer.md)에서, GGUF 양자화의 절감·품질 정량은 [⑥ GPU 사이징 §2.4](../../06-sizing-cost/docs/02-gpu-sizing.md)에서 다룹니다.

---

## 2.6 ML API Gateway — 모든 호출의 진입점

Model Runtime의 **ML API Gateway**는 사내 추론 API의 정문입니다. 공식 문서 기준 다음을 담당합니다.

| 책임 | 의미 |
|------|------|
| **인증(Authentication)** | 들어오는 요청이 누구인지 검증 (OIDC Bearer 토큰 / mTLS → [05](05-auth-and-gateway.md)) |
| **인가(Authorization)** | 그 사용자가 이 모델·에이전트를 호출할 권한이 있는지 |
| **로드밸런싱** | 같은 모델의 여러 복제본(Replicas)에 요청 분산 |

> 따라서 앱은 개별 추론 파드의 IP를 알 필요가 없습니다. **Gateway의 단일 진입 URL**(`https://{fqdn}/api/v1/...`)로 호출하면 인증·분산이 그 뒤에서 처리됩니다. 스케일아웃(복제본 증가)도 앱 코드 변경 없이 흡수됩니다(§2.2 데이터 평면). 복제본 수의 네임스페이스 한도는 §2.8을, 레이트리밋·쿼터·재시도는 [05](05-auth-and-gateway.md)를 보십시오.

---

## 2.7 Model Endpoint vs Agent — 무엇이 무엇을 호출하나

[01.3](01-why-serving-api.md#13-두-종류의-api--endpoint와-agent)에서 소비 관점으로 둘을 비교했습니다. 여기서는 **무엇이 무엇을 호출하는지**(아키텍처 관점)를 봅니다.

```
앱 → Model Endpoint API           앱 → Agent API
     POST .../chat/completions          POST .../agents/{id}/chat/completions
        │                                   │
        ▼                                   ▼
     추론 엔진(LLM) 1회 호출            Agent Builder 오케스트레이션:
        │                              ① KB에서 관련 청크 검색(의미 검색)
        ▼                              ② (필요 시) MCP 도구 호출
     텍스트 응답                        ③ 검색·도구 결과를 컨텍스트로 주입
                                       ④ Model Endpoint(LLM) 호출
                                       ⑤ 응답 + 출처 + session_id 반환
```

즉 **Agent는 Model Endpoint를 내부적으로 호출하는 상위 계층**입니다. 그래서 같은 OpenAI 호환 `chat/completions` 형태이면서도, Agent는 RAG·세션·도구를 추가로 끼워 넣습니다. 이 둘의 상태(state) 차이가 핵심입니다 — **Model Endpoint는 stateless**(요청 간 기억 없음), **Agent는 stateful**(`session_id`로 대화 유지).

| 관점 | Model Endpoint | Agent |
|------|---------------|-------|
| 추상화 수준 | 낮음(모델 그대로) | 높음(RAG·세션·도구 포함) |
| 상태 | stateless | stateful(`session_id`) |
| 내부 호출 | 자기 자신(LLM) | KB + (MCP) + Model Endpoint |
| 앱이 직접 짜야 할 것 | 대화 이력·RAG·출처 | (거의 없음) 호출만 |
| 응답에 추가되는 것 | — | `session_id`, `index_context_info`(출처) |

---

## 2.8 멀티테넌시·네임스페이스 경계

PAIS는 VCF Automation의 **조직(Organization)·네임스페이스**(§2.1 토대) 위에서 동작합니다. API 관점에서 중요한 함의는 다음과 같습니다.

- **격리** — 한 네임스페이스의 Model Endpoint·Agent·KB는 그 경계 안에서 관리됩니다. 토큰의 권한도 그 경계를 따릅니다.
- **거버넌스 경계** — DEV/PROD를 네임스페이스로 분리하면, 민감한 도구(MCP)·데이터 소스를 PROD에만 허용하는 식의 통제가 가능합니다 → [06 MCP 거버넌스](06-mcp-tools-api.md).
- **리소스 쿼터** — GPU·복제본 한도가 네임스페이스 단위로 걸리므로, API 스케일링도 그 한도 안에서 일어납니다. 구체적으로 **네임스페이스당 Model Endpoint 복제본은 최대 15개**이고, **각 복제본이 /24 CIDR 블록을 소비**합니다(더 늘리려면 Supervisor 서비스의 `vks.candidatePodCIDRs`로 대역을 키웁니다) → [07 운영](07-observability-ops.md). ([근거: VCF Blog — Minimal VCF 환경의 PAIS 배포](https://blogs.vmware.com/cloud-foundation/2025/12/17/deploy-vmware-private-ai-services-in-minimal-vmware-cloud-foundation-environments/). 한도 수치는 릴리스마다 달라질 수 있으니 적용 직전 공식 문서로 재확인하시기 바랍니다.)

> **에어갭 반입 — Artifact Mirroring Tool(아티팩트 미러링 도구, PAIS 2.1 신규)** — 외부 반출이 불가한 폐쇄망(에어갭)에서는 PAIS 패키지·NVIDIA GPU Operator 구성요소·NGC 컨테이너 등 **아티팩트를 로컬 Harbor 레지스트리로 미러링**하는 도구입니다. 이를 통해 GPU 모델 엔드포인트·에이전트를 포함한 풀 Private AI를 격리망에서 설치·운영하고, 외부 SaaS·외부 MCP는 차단합니다. API 자체는 동일하되 **연동 대상이 내부로 제한**됩니다. 미러링은 pais CLI 플러그인의 **`vcf pais amt pull/push`** 명령으로 수행합니다(이 명령은 VCF CLI 명령 레퍼런스에는 누락돼 있고 Disconnected Environment 배포 문서에 명시). ([근거: PAIS 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-release-notes/vmware-private-ai-services-release-notes.html), [Disconnected 환경 구성요소 업로드](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/deploying-private-ai-foundation-with-nvidia/installing-and-configuring-private-ai-services/upload-the-private-ai-services-components-to-a-disconnected-environment.html). 상세 런북은 형제 가이드 [① §6.9](../../01-infra/docs/06-production.md), [⑧ §5.4](https://github.com/JaeHoYun/vcf-private-ai-agents/blob/main/docs/05-models-serving.md))

---

## 2.9 이 문서에서 다루지 않는 것 (경계)

서빙 API 아키텍처를 또렷이 하려면 **무엇이 여기 속하지 않는지**도 분명히 해야 합니다. 아래는 인접하지만 다른 문서가 기준인 주제들입니다.

| 주제 | 왜 여기가 아닌가 | 기준 문서 |
|------|----------------|----------|
| **DLVM (Deep Learning VM)** | 서빙 평면이 아니라 **개발·실험 평면**. 데이터 과학자·MLOps의 개인 GPU 워크스테이션 VM으로 모델 평가·프로토타이핑·검증에 쓰며, 프로덕션 상시 서빙 대상이 아님. App Developer는 DLVM 없이 PAIS API URL만으로 개발 | [① §2.7·§1.3](../../01-infra/docs/01-concepts.md), 라이프사이클 [① §4.1](../../01-infra/docs/04-dev-scenarios.md) |
| **GPU 할당 방식 / 구축 순서** | 플랫폼 토대(vGPU vs DirectPath I/O, Phase별 구축) | [① §2.3·§2.6](../../01-infra/docs/02-architecture.md) |
| **컴퓨트·GPU·VKS 토폴로지 설계** | 노드풀·배치 같은 설계 결정 | [⑦ §3](../../07-design/docs/03-compute-gpu-topology.md) |
| **용량·복제본·GPU 사이징(정량)** | 수식·산정은 본 가이드 범위 밖 | [⑥ §2](../../06-sizing-cost/docs/02-gpu-sizing.md) |
| **벡터 DB(pgvector) 내부** | Data Indexing이 의존하는 데이터 계층 | [② VectorDB 가이드](../../02-vectordb/README.md) |

> **DLVM의 자리를 한 줄로** — *DLVM(개발·검증) → Model Gallery(반입) → Model Endpoint(프로덕션 서빙, VKS+GPU) → 앱*. DLVM은 이 사슬의 **맨 앞(개발)** 에만 있고, 본 가이드가 다루는 서빙은 **Gallery 이후**입니다.

---

[← 이전: 01 왜 사내 추론 API인가](01-why-serving-api.md) · [목차](../README.md) · [다음: 03 OpenAI 호환 엔드포인트 →](03-openai-compatible-endpoints.md)

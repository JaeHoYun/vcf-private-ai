# 02 — 아키텍처 및 구축 순서

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.

이 문서는 PAIF의 **계층 구조**, **GPU 할당 방식(9.1 변경 반영)**, **구축 Phase와 의존성**을 다룹니다.

---

## 2.1 전체 계층 구조

"PAIF"는 두 가지로 쓰입니다 — 수식어 없이 **PAIF**라 하면 VCF가 제공하는 Private AI Foundation **솔루션 전체**를 가리키고, 큰 구성요소 관점의 인프라·관리 부분(공식 용어 **PAIF core functionality**)은 본 문서에서 **PAIF 코어 기능 계층**으로 적습니다. 한 줄로:

**PAIF(솔루션) = PAIF 코어 기능 계층 + PAIS 서비스 계층**

이 둘은 한 솔루션의 두 부분이며, PAIS는 공식 문서상 *"a Supervisor service ... installed as a package, separately from the VMware Private AI Foundation with NVIDIA core functionality"* 로 코어 기능과 **별도 설치**됩니다 ([System Architecture of PAIF](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/deploying-private-ai-foundation-with-nvidia/system-architecture-of-vmware-private-ai-foundation-with-nvidia.html)). 아래는 무엇이 무엇 위에서 동작하는지의 **논리 계층**입니다.

```
[ 고객 AI 앱 ]  PAIF 밖 — PAIS API(OpenAI 호환) 소비
      │  Frontend(React/Vue) · Backend(FastAPI 등)
══════╪════════════════════ PAIF (솔루션) ═════════════════════════
 PAIS │ 서비스 계층 — Supervisor 서비스 패키지(코어와 별도 설치)
      │   ML API Gateway · Model Runtime / Model Gallery
      │   · Data Indexing & Retrieval · Agent Builder · MCP
      │   · 관측성(모델·GPU 메트릭, OTel 트레이싱)
──────┼──────────────────────────────────────────────────────────
 PAIF │ 코어 기능 계층 (PAIF core functionality)
 코어 │   GPU enablement : vGPU 드라이버 / GPU Operator / MIG · EDPIO
      │                    / DLS 라이선싱 / DRA
      │   공유 서비스(필수): Harbor(Supervisor Service · 모델/컨테이너
      │                    저장) · DSM(pgvector 벡터 DB)
      │   관리·오케스트레이션: VCF Automation(셀프서비스 카탈로그)
      │                    · VCF Operations(GPU 관측·쇼백/차지백)
      │   DLVM 이미지(개발 평면)
══════╪══════════════════════════════════════════════════════════
 VCF  │ 9.1 기반 플랫폼
      │   GPU 가속 워크로드 도메인: GPU-enabled ESXi 호스트
      │   · Supervisor · NSX Edge/VPC · vSAN · VKS(Kubernetes)
```

> **GPUaaS(문서 07)는 별도 계층이 아니라 운영 모델입니다.** 공식 문서에 "GPUaaS / GPU as a Service" 컴포넌트는 없으며, GPUaaS는 위 **PAIF 코어 기능 계층의 GPU 자원**(GPU enablement · VM Class · VCF Automation 카탈로그 · VCF Operations 쇼백/차지백)을 사내·계열사에 셀프서비스로 노출하는 *운영 관점*입니다. PAIS 서비스 계층의 형제 계층도, 코어의 하위 컴포넌트도 아닙니다.

> **공유 서비스 주의:** Harbor·DSM은 본래 범용 Supervisor Service·VCF 데이터 서비스지만, PAIF가 정상 동작하려면 **반드시 있어야 하는 필수 구성요소**입니다. 각 서비스의 역할·필수성·근거는 아래 [PAIF 코어 공유 서비스 상세](#paif-코어-공유-서비스-상세)에서, 설치 순서는 [§2.6 구축 Phase 2](#26-구축-phase-개요)에서 다룹니다.

> **용어 주의:** Broadcom 공식 문서(TechDocs)는 PAIS를 설치하는 GPU 워크로드 도메인을 **GPU-Accelerated Workload Domain**으로 표기합니다("Install Private AI Services on the Supervisor of the GPU-Accelerated Workload Domain") ([Broadcom TechDocs — PAIS 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-release-notes/vmware-private-ai-services-release-notes.html), [PAIS 상세 설계](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/design/design-library/private-ai-platform-detailed-design/private-ai-services.html)). 본 문서는 가독성을 위해 이를 **PAIF Workload Domain**으로 약칭하며, "GPU Workload Domain", "AI Domain", "GPU Domain" 등 그 밖의 표현은 비공식 약식으로 봅니다.

### 계층 귀속과 격리 단위

위가 **논리 계층**(무엇이 무엇 위에서 동작하나)이라면, 아래는 **귀속·격리 단위**(자원이 어디에 담기나)입니다. 환경 분리(DEV/QA/STAGING/PROD)는 vSphere Namespace 단위로 이뤄집니다.

```
VCF (PAIF Workload Domain)        ← 최외곽
  └── Supervisor                  ← 중간
        └── vSphere Namespace     ← 환경 격리 단위 (DEV/QA/STAGING/PROD)
              └── VKS             ← Kubernetes 클러스터
  └── GPU Host-01, GPU Host-02 …  ← Supervisor 직속 GPU 인프라
```

### PAIF 코어 공유 서비스 상세

PAIF 코어 기능 계층의 **공유 서비스 4종**(Harbor·DSM·VCF Automation·VCF Operations)은 본래 범용 VCF/Supervisor 서비스지만, Model Gallery·RAG·셀프서비스·관측을 갖춘 실운영 PAIF에는 빠질 수 없는 구성요소입니다. 공식 시스템 아키텍처도 이들을 PAIF의 "AI Workload Infrastructure / Data & Services / Management" 그룹에 포함합니다 ([System Architecture of PAIF](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/deploying-private-ai-foundation-with-nvidia/system-architecture-of-vmware-private-ai-foundation-with-nvidia.html)).

| 서비스 | 본질(무엇인가) | PAIF에서의 역할 | PAIS 연계 |
|--------|----------------|-----------------|-----------|
| **Harbor** | Supervisor Service(OCI 레지스트리) | 컨테이너 이미지 + **Model Gallery**(검증 모델·NIM을 OCI 아티팩트로) 저장, HTTPS 필수 | Model Runtime이 여기서 모델을 pull — Model Gallery의 백엔드 |
| **DSM**(Data Services Manager) | VCF 데이터 서비스(Advanced Service) | **PostgreSQL 16.8 + pgvector 0.8.0** 벡터 DB 프로비저닝·HA·백업 | Data Indexing & Retrieval의 벡터 저장소(Knowledge Base) |
| **VCF Automation** | VCF 셀프서비스(관리) 평면 | DLVM/VKS/RAG **카탈로그** 블루프린트, OIDC IdP 연동, 9.1 네임스페이스 단위 PAIS 활성화 UI | 카탈로그로 PAIS·GPU 자원을 셀프서비스 신청 |
| **VCF Operations** | VCF 관측·과금 평면 | 모델·GPU 메트릭 대시보드, GPU 소비 관측, 쇼백/차지백 | 관측성([문서 06 §6.8](06-production.md))·GPUaaS 과금([문서 07 §7.6](07-gpuaas.md)) |

**필수성의 정확한 의미(과장 금지):** 공식 배포 요구사항 문서 기준으로는 위 4종 모두 "최소 GPU 워크로드 배포 자체"에는 강제가 아닙니다. 그러나 **Model Gallery(Harbor)·RAG 벡터 DB(DSM)** 는 모델 서빙·RAG를 하는 순간 사실상 전제가 되고, **VCF Automation·VCF Operations** 는 셀프서비스·관측·거버넌스의 핵심입니다. 즉 "되는 최소 구성"이 아니라 "실제로 운영하는 PAIF"를 그리면 이 4종은 빠지지 않습니다. Automation·Operations는 없으면 각각 kubectl 직접 배포·기본 vCenter 관측으로 대체할 수 있습니다.

**서비스별 주의:**
- **Harbor** — Supervisor Service로 활성화하며 설치 시 인터넷 연결이 필요합니다. 에어갭에서는 외부 레지스트리 대신 **내부 Harbor로 아티팩트를 미러링**해 사용합니다(Artifact Mirroring Tool, [문서 06 §6.9](06-production.md)).
- **DSM** — DSM은 원래 VCF 코어와 별도 라이선스되는 Advanced Service지만, **PAIS가 벡터 DB(pgvector) 용도의 DSM 사용 권한(entitlement)을 포함**하므로 RAG용 벡터 DB엔 별도 구매가 불필요합니다. 일반 DBaaS로 확장 사용 시에만 별도 라이선스입니다([문서 01](01-concepts.md) §1.2).
- **VCF Automation / Operations** — 9.1에서 Automation은 네임스페이스 단위 PAIS 셀프서비스 UI를, Operations는 모델·GPU 메트릭을 나머지 인프라와 같은 화면으로 제공합니다(9.0.x의 kubectl·자체 모니터링 부담을 줄임).

---

## 2.2 PAIS 서비스 아키텍처

PAIS(Private AI Services 2.1)는 구성요소를 나열한 평면 박스가 아니라 **세 개의 평면**으로 보면 "무엇이 무엇을 호출하는가"가 드러납니다. 제어 평면이 입구를 지키고, 추론 평면이 요청을 모델까지 나르며, 인입 평면이 검색에 쓰일 지식을 미리 채워 둡니다. 관측성은 제어·추론 평면을 가로지릅니다.

```
                        클라이언트(고객 AI 앱)
                               │  OpenAI 호환 요청
═══════════════════════════════╪═══════════════ PAIS 2.1 ═══════════════
                               ▼
  ┌─ 제어 평면 ────────────────────────────────────────────────────┐
  │  ML API Gateway : 인증/인가 · 라우팅 · 로드밸런싱 · OpenAI 호환  │
  └───────────────────────────────┬─────────────────────────────────┘
                                  │  라우팅
  ┌─ 추론(데이터) 평면 ───────────▼─────────────────────────────────┐
  │   Completion Endpoint     Embedding Endpoint      Agent          │
  │   • vLLM 0.11.2           • Infinity 0.0.76       • RAG          │
  │   • llama.cpp(CPU)        • (CPU 가능)            • Tool-calling │
  │   • GPU                                           • MCP(외부도구) │
  │        │                       │                      │          │
  │        ▼                       ▼                      ▼          │
  │     모델 런타임            모델 런타임          Knowledge Base    │
  │                                                  (검색) + 모델   │
  └─────────────────────────────────────────────────────────────────┘
  ┌─ 인입(인덱싱) 평면 ──────────────────────────────────────────────┐
  │   Data Source → 파싱 → 청킹 → 임베딩 → pgvector 적재 → 자동 갱신  │
  └─────────────────────────────────────────────────────────────────┘
       └─── 관측성(두 평면 횡단) : 모델 메트릭(캐시·토큰·지연) ·
                                   GPU 메트릭 · OTel 트레이싱 ───┘
```

- **제어 평면 — ML API Gateway.** 모든 요청의 단일 입구입니다. 인증/인가, 엔드포인트·에이전트로의 라우팅, 로드밸런싱을 담당하고 OpenAI 호환 인터페이스를 노출합니다.
- **추론(데이터) 평면 — 요청 경로.** 클라이언트 → Gateway → **Completion/Embedding Endpoint** 또는 **Agent**(RAG·Tool-calling)로 흐르고, 끝단에서 모델 런타임(vLLM 0.11.2 / Infinity 0.0.76 / llama.cpp) 또는 Knowledge Base를 호출합니다. Agent는 검색(Knowledge Base)과 외부 도구(MCP)를 묶어 답을 만듭니다.
- **인입(인덱싱) 평면 — 지식 적재 경로.** Data Source에서 가져온 문서를 파싱 → 청킹 → 임베딩한 뒤 pgvector(DSM)에 적재하고, 소스 변경을 자동 갱신합니다. 추론 평면의 RAG가 여기서 채운 Knowledge Base를 읽습니다.
- **관측성 — 횡단 관심사.** 모델 메트릭(캐시·토큰·지연)·GPU 메트릭·OTel 트레이싱이 제어·추론 두 평면을 가로질러 수집됩니다.

> 서빙 런타임의 깊은 동작 원리(연속 배칭 등)는 ③ 서빙 가이드로 위임합니다. Agent Builder의 MCP·Tool-calling은 [문서 05](05-agents-mcp.md), 관측성은 [문서 06](06-production.md)에서 상세히 다룹니다. 인입 평면의 소스 연결 절차는 [문서 03 §3.4](03-workflows.md), 소비 패턴은 [문서 04](04-dev-scenarios.md)를 참조하세요.

---

## 2.3 GPU 할당 방식 (주의 9.1 변경)

PAIF에서 GPU를 워크로드에 붙이는 방식은 **세 축**으로 나뉩니다 — 시간 분할 공유(vGPU), 하드웨어 분할 격리(MIG), 전용 패스스루(Enhanced DirectPath I/O). 어느 것을 쓰느냐로 격리 수준·라이선스·성능이 갈립니다. **9.1에서 DirectPath I/O 관련 서술이 바뀌었습니다.**

| 방식 | 설명 | NVAIE 라이선스 | vMotion | 비고 |
|------|------|:---:|:---:|------|
| **vGPU** | GPU를 여러 VM에 시간 분할로 공유 | 필요 | 지원 | 유연한 리소스 할당, GPU 활용률↑ |
| **MIG** | GPU를 하드웨어 단위로 분할해 인스턴스별 격리 | vGPU 경유 시 필요 | 프로파일 의존 | 테넌트 간 강한 격리, A100/H100 등 지원 GPU 한정 |
| **패스스루 (Enhanced DirectPath I/O)** | GPU를 단일 VM/VKS 노드에 전용 할당 | **불필요** | **지원 유지** | ConnectX-7/BlueField-3와 결합 시 GPUDirect RDMA·Storage, 멀티호스트 학습 |

> **9.1 정정:** 9.0.x 가이드의 "DirectPath I/O는 vMotion 제한, VM당 1GPU" 서술은 **폐기**됩니다. 9.1의 Enhanced DirectPath I/O는 **NVAIE(NVIDIA AI Enterprise) 라이선스 없이 전용 GPU**를 제공하면서 **vMotion 이점을 유지**합니다.
>
> **선택 가이드(개념 수준):** 다중 사용자 추론·GPU 활용률 극대화 → **vGPU**(NVAIE 필요). 테넌트 간 강한 격리로 한 GPU를 나눠 줄 때 → **MIG**(지원 GPU 한정). 대규모 학습·단일 워크로드 최대 성능·라이선스 절감 → **패스스루(Enhanced DirectPath I/O)**.
>
> **세부 분류·enablement는 기준 문서로 위임:** 위는 결정에 필요한 개념 수준입니다. 할당 모드의 세부 분류와 실제 활성화 절차(BIOS·드라이버·GPU Operator·PAISConfiguration까지)는 [문서 11 §11.5](11-gpu-enablement.md)가 기준이며, 문서 07과의 정합은 [문서 07 §7.4](07-gpuaas.md)를 참조하세요. 02는 개념·결정 수준만 둡니다(중복 금지).

> **멀티호스트 RDMA 결정·구성 노트:**
> - **언제 필요한가:** ConnectX-7/BlueField-3 기반 GPUDirect RDMA·멀티호스트 패브릭은 *대규모 분산 학습*과 *단일 서버 용량을 초과하는 초대형 모델의 분산 추론*에만 필요합니다. 단일노드 추론·RAG·일반 챗봇에는 불필요하므로 표준 구성으로 시작하세요([VCF 블로그 — GPUDirect RDMA 분산 추론](https://blogs.vmware.com/cloud-foundation/2025/09/16/deploy-distributed-llm-inference-with-gpudirect-rdma-over-infiniband-in-private-ai/)).
> - **VCF 구성 체크포인트:** GPUDirect RDMA 활성화에는 **ESXi의 ACS(Access Control Services) 활성화**와 **ConnectX-7 NIC의 ATS(Address Translation Services) 활성화**가 필요합니다(ATS는 PCIe 장치 간 직접 DMA로 가상화 오버헤드를 낮춥니다) ([VCF 블로그 — GPUDirect RDMA 분산 추론](https://blogs.vmware.com/cloud-foundation/2025/09/16/deploy-distributed-llm-inference-with-gpudirect-rdma-over-infiniband-in-private-ai/)).
> - **본 문서 범위 밖:** 무손실(lossless) 물리 패브릭 설계(RoCE/InfiniBand 스위치 PFC·ECN 설정 등)는 **네트워크팀 선결요건**이며 본 가이드 범위 밖입니다. 정확한 스위치·패브릭 구성은 네트워크팀 및 공식 문서로 확인하시기 바랍니다(공식 문서 확인 필요).

### Kubernetes AI Conformance (DRA)

9.1의 VKS는 **Dynamic Resource Allocation(DRA)** 기반 개방형 GPU 스케줄링을 지원합니다. 타 클라우드와 동일한 오픈 표준(Kubernetes AI Conformance)으로 GPU 워크로드를 선언·할당할 수 있어, 이식성과 멀티클러스터 운영 일관성이 높아집니다.

---

## 2.4 지원 데이터 소스 및 파일 형식

인입 평면([§2.2](#22-pais-서비스-아키텍처))이 받아들이는 소스와 파일 형식의 종류만 정리합니다. 인증·연결 절차의 상세는 [문서 03 §3.4](03-workflows.md), 앱에서의 소비 패턴은 [문서 04](04-dev-scenarios.md)가 기준입니다.

| 데이터 소스 | 지원 파일 형식 |
|------------|---------------|
| Confluence · SharePoint · Google Drive · Amazon S3(S3 호환 포함) · 로컬 업로드 | PDF · Word(.docx) · PowerPoint(.pptx) · 텍스트/CSV/HTML/Markdown |
| **Google Workspace (Docs/Sheets/Slides)** — 9.1 신규 | **Google Docs/Sheets/Slides** — 9.1 신규 |

> PDF는 텍스트 기반이 전제이며 스캔 문서는 별도 OCR이 필요합니다. 소스별 인증 방식(API Token · OAuth 2.0 · Access Key 등)과 단계별 연결 절차는 [문서 03 §3.4](03-workflows.md)를 참조하세요.

---

## 2.5 OpenAI 호환 API

PAIS의 ML API Gateway는 OpenAI 호환 인터페이스를 노출하므로 기존 OpenAI SDK로 Base URL·모델 이름만 바꿔 연동할 수 있습니다. 실제 베이스 경로·엔드포인트 표·curl 예시는 [문서 04 §4.7](04-dev-scenarios.md)이 기준입니다(경로는 버전에 따라 달라질 수 있으므로 PAIS 2.1 UI의 "Sample Code"로 확인).

---

## 2.6 구축 Phase 개요

```
Phase 1            Phase 2           Phase 3            Phase 4
VCF 인프라         지원 서비스        PAIS 설치          개발/운영
┌─────────┐       ┌─────────┐       ┌─────────┐        ┌─────────┐
│ VCF 9.1 │──────▶│ Harbor  │──────▶│  PAIS   │───────▶│  DLVM   │
│ PAIF WD │       │ DSM     │       │ 2.1     │        │  VKS    │
│Supervisor│      │         │       │ (UI/CLI)│        │  Apps   │
└─────────┘       └─────────┘       └─────────┘        └─────────┘
담당: VI Admin    VI Admin          Cloud/Org Admin    DevOps/DS
기간: 2-3일       1일               1일                지속
```

### Phase 1: VCF 기반 인프라 (VI Admin, 2-3일)

```
[1.1] VCF 9.1 배포
[1.2] PAIF Workload Domain 생성 (최소 3개 GPU 호스트)
[1.3] NVIDIA vGPU 호스트 드라이버 설치 (또는 Enhanced DirectPath I/O 구성)
[1.4] Supervisor 활성화 + NSX VPC 네트워킹
[1.5] vGPU VM Class 생성 (또는 DirectPath I/O VM Class)
```

**GPU 지원 하드웨어 (9.1)**

| GPU 모델 | vGPU | Enhanced DirectPath I/O | 권장 용도 |
|----------|:---:|:---:|----------|
| NVIDIA A100 40/80GB | 지원 | 지원 | 대규모 LLM 추론 |
| NVIDIA H100 / H200 | 지원 | 지원 | 고성능 추론, 대용량 HBM |
| **NVIDIA HGX B200 (Blackwell)** | BCG(Broadcom Compatibility Guide) 확인 | 지원 | **차세대 대규모 학습/추론 (9.1 GA)** |
| **NVIDIA RTX PRO 4500 / 6000 Blackwell** | BCG 확인 | 지원 | **워크스테이션/추론 (9.1 GA)** |
| NVIDIA HGX B300 | 예정 | 예정 | 향후 |
| NVIDIA L40S | 지원 | 지원 | 비용 효율적 추론 |

> GPU 모델별 세부 호환성·드라이버(v580.x) 매트릭스는 반드시 [Broadcom Compatibility Guide](https://www.broadcom.com/support/vmware/product-compatibility)에서 최신 정보를 확인하시기 바랍니다. ConnectX-7 NIC / BlueField-3 DPU는 GPUDirect RDMA·Storage 및 멀티호스트 AI 학습에 활용됩니다.

### Phase 2: 지원 서비스 (VI Admin, 1일)

```
[2.1] Harbor Registry 설치 (Supervisor Service) — 컨테이너 이미지 + Model Gallery, HTTPS 필수
[2.2] VMware Data Services Manager(DSM) 설치 — pgvector PostgreSQL(PAIS 벡터 DB), S3 호환 스토리지 필요
      ※ DSM은 별도 라이선스 Advanced Service이나, PAIS가 벡터 DB용 DSM 사용 권한을 포함 (문서 01 §1.2)
[2.3] VCF Automation 배포 (권장) — 셀프서비스 카탈로그, OIDC IdP 연동
```

```yaml
# Harbor 프로젝트 구조 예시
harbor.company.com/
├── models/        # Model Gallery (llama3/, mistral/, bge-embeddings/ …)
├── paif-images/   # PAIS 컨테이너 이미지
└── app-images/    # 앱 컨테이너 이미지
```

### Phase 3: PAIS 2.1 설치·활성화 (Cloud/Org Admin, 1일)

```
[3.1] PAIS Supervisor Service 설치 (Broadcom Support Portal YAML, OCI Registry 인증)
[3.2] Trust Bundle 구성 (OIDC · Harbor · DSM 인증서)
[3.3] PAISConfiguration CRD 적용 (GPU Operator 25.10.1 오버라이드 가능)
[3.4-A] VCF Automation 사용: 조직 설정 → Private AI Quickstart → 카탈로그 자동 생성
[3.4-B] kubectl 직접 배포: PAIS 독립 UI 접근
        ───────────────────────────────────
              "AI 플레이그라운드" 완성
```

> **9.1 UI 셀프서비스:** 조직 관리자가 **VCF Automation UI**에서 네임스페이스 단위로 PAIS를 활성화·관리할 수 있습니다. Model Endpoint·KB·Agent의 생성·배포·라이프사이클을 UI에서 처리하므로, 9.0.x의 kubectl 중심 절차 부담이 크게 줄었습니다. 에어갭 환경은 **Artifact Mirroring Tool** 기반으로 설치합니다 ([문서 06](06-production.md)).

```bash
# (참고) VCF Automation 없이 kubectl 직접 배포
vcf context use <namespace_context_name>
kubectl apply -f harbor-trust-bundle.yaml
kubectl apply -f oidc-trust-bundle.yaml
kubectl apply -f dsm-trust-bundle.yaml
kubectl apply -f paisconfiguration.yaml
kubectl get paisconfiguration            # READY=True 확인
kubectl get services | grep pais-ingress # PAIS UI 접근 IP
```

### Phase 4: 카탈로그 항목 (VCF Automation 사용 시)

| 카탈로그 항목 | 설명 | 대상 |
|--------------|------|------|
| AI Workstation | DLVM + PyTorch/CUDA | Data Scientist |
| AI Workstation (Triton) | DLVM + Triton | MLOps |
| AI RAG Workstation | DLVM + RAG | Data Scientist |
| AI Kubernetes Cluster | VKS + GPU Operator | DevOps |
| AI Kubernetes RAG Cluster | VKS + RAG | DevOps |

---

## 2.7 DLVM 이미지 (9.1)

VCF 9.1 호환 DLVM(Deep Learning VM, 딥러닝용 가상머신 이미지)은 신규 Ubuntu OS와 ML 라이브러리/프레임워크/툴킷으로 갱신됐고, 임베디드 Conda가 **Miniconda 24.3.0 → Miniforge3 24.3.0** 으로 변경됐습니다.

```
DLVM 기본 구성 (VCF 9.1)
├── OS: 갱신된 Ubuntu LTS
├── GPU Driver: NVIDIA vGPU Guest Driver (v580.x 계열)
├── Container Runtime: Docker + NVIDIA Container Toolkit
├── Dev: JupyterLab · Python · CUDA Toolkit · Miniforge3 24.3.0
├── CLI: pais CLI · Docker CLI
└── Libraries(번들별): PyTorch · Transformers · LangChain 등
```

> NGC 기반 vGPU 드라이버 다운로드 방식(Personal/Service API Key)은 9.0.1부터 유지됩니다. 정확한 DLVM 이미지 버전 문자열은 [DLVM 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1.html)에서 확인하시기 바랍니다.

---

## 2.8 의존성 다이어그램

```
VCF 9.1
  └── PAIF Workload Domain + Supervisor
        ├── vGPU VM Class / Enhanced DirectPath I/O VM Class
        ├── Harbor Registry ──▶ Model Gallery
        ├── DSM (PostgreSQL 16.8 + pgvector 0.8.0)
        └── VCF Automation (선택)
              └── PAIS 2.1 Supervisor Service
                    ├── Model Runtime (vLLM 0.11.2 / Infinity 0.0.76 / llama.cpp)
                    ├── Agent Builder (+ MCP)
                    ├── Data Indexing & Retrieval
                    ├── 관측성 (모델·GPU 메트릭, OTel)
                    └── 카탈로그 (DLVM / VKS / RAG)
```

---

## 2.9 알려진 이슈 및 Workaround

알려진 이슈의 운영 기준 문서는 [문서 10 §10.2 트러블슈팅 런북](10-operations.md)입니다(증상 → 진단 → 조치). PoC에서 가장 흔한 막힘 지점의 핸즈온은 [문서 11 §11.11](11-gpu-enablement.md)을 참조하세요.

- **운영 런북(증상→진단→조치)** — [문서 10 §10.2](10-operations.md): ModelRuntime GPU Pod 시작 실패, 업그레이드 후 Endpoint 재배포 실패, LLM 트레이스 미표시, 업그레이드 다운타임 등.
- **PoC 핸즈온 함정** — [문서 11 §11.11](11-gpu-enablement.md): GPU enablement 단계에서 가장 자주 막히는 지점.

> GPU Operator가 24.9.0 → **25.10.1**(드라이버 v580.x)로 올라갔으므로, 9.0.x에서 적용했던 드라이버 고정·MIG 관련 Workaround는 **재검증**이 필요합니다. 정확한 증상·Workaround·해결 여부는 [공식 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1.html)로 재확인하시기 바랍니다.

---

[← 이전: 01 핵심 개념 및 페르소나](01-concepts.md) · [목차](../README.md) · [다음: 03 역할별 워크플로우 →](03-workflows.md)

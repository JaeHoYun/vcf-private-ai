# 00 — What's New (VCF 9.1.x / PAIF 9.1.x / PAIS 2.1과 3.0)

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.
> 이 문서는 **9.0.x에서 9.1로 올라오는 분**, **9.1 / PAIS 2.1을 운영하다가 9.1.1 / PAIS 3.0으로 올라오는 분**, **9.1.x를 처음 접하는 분** 모두를 위한 변경 요약입니다. 0.1절부터 0.6절까지는 9.0.x 대비 9.1의 변경, 0.7절부터 0.9절까지는 9.1 대비 9.1.1 / PAIS 3.0의 변경입니다. 어느 기능이 어느 버전에서 들어왔는지 한 표로 보려면 0.8절로 바로 가시면 됩니다.

VCF 9.1은 2026년 5월 GA되었으며, "프로덕션 AI를 위한 안전하고 비용 효율적인 프라이빗 클라우드"를 표방했습니다. AI 관점에서는 PAIF 9.1 / **Private AI Services(PAIS) 2.1**이 함께 출시되며 **에이전트, 외부 도구 연동(MCP), 에어갭, 관측성**이 크게 보강됐습니다. 이어 2026년 9월 3일 VCF 9.1.1이 유지보수 릴리스로 GA됐고, 같은 날 PAIF 9.1.1과 **PAIS 3.0**이 나오면서 공유 모델 호스팅, 원격 클라우드 모델 연결, API 토큰이 추가됐습니다(0.7절).

---

## 0.1 변경 요약

| 영역 | 9.0.x | 9.1 |
|------|-------|-----|
| 추론 엔진 | vLLM 0.6.5 / Infinity 0.0.43 | **vLLM 0.11.2 / Infinity 0.0.76 / llama.cpp b7739 (CPU)** |
| CPU 전용 추론 | Embedding(Infinity)만 | **Completion도 CPU 가능 (llama.cpp)** |
| 외부 도구 연동 | 커스텀 코드 필요 | **MCP 표준 연동 (Oracle, MS SQL, ServiceNow, GitHub, Slack, PostgreSQL 등)** |
| 에어갭 | Harbor 수동 구성 | **Artifact Mirroring Tool로 풀 AI 기능 구동** |
| 관측성 | 모호/수동 | **모델과 GPU 메트릭 대시보드 + OpenTelemetry LLM 트레이싱** |
| GPU 전용 패스스루 | DirectPath I/O = vMotion 제한 | **Enhanced DirectPath I/O = vMotion 유지, NVAIE(NVIDIA AI Enterprise) 불필요** |
| 최신 GPU | B200 "테스트 중" | **Blackwell GA (HGX B200, RTX PRO 4500/6000)** |
| K8s GPU 스케줄링 | 정적 할당 중심 | **Kubernetes AI Conformance (DRA 기반)** |
| 데이터 소스 | MS Office, PDF 등 | **+ Google Workspace (Docs/Sheets/Slides)** |
| PAIS 활성화 | kubectl 중심 | **VCF Automation UI 셀프서비스 (네임스페이스 단위)** |
| VKS 스케일 | — | **Supervisor당 최대 500 K8s 클러스터** |

---

## 0.2 VCF 9.1 플랫폼 변화 (AI 인프라에 영향)

PAIF는 VCF 위에서 동작하므로, 플랫폼 레벨 변화가 AI 운영에 직접 영향을 줍니다.

| 변화 | 내용 | AI 워크로드 관점 |
|------|------|----------------|
| **API-first 통합 모델** | SDDC Manager, vCenter, NSX, vSAN을 단일 API 계약으로 통합 | AI 인프라 프로비저닝/IaC 자동화 일관성 ↑ |
| **vCenter Quick Patch** | 변경된 바이너리만 패치 → 다운타임 초 단위/제로 | GPU 호스트 유지보수 창 최소화 |
| **Enhanced NVMe Memory Tiering** | DRAM+NVMe 통합 메모리 모델, 콜드 페이지를 NVMe로 오프로드 | 메모리 바운드 AI/벡터 DB 워크로드 직접 대응 |
| **VKS 스케일 확장** | Supervisor당 최대 500 클러스터, 배포 70%↑, 업그레이드 창 75%↓ | 대규모 AI 클러스터 운영 비용 절감 |
| **Topology Aware Scheduling** | NUMA, 가속기 로컬리티 고려 배치 | GPU/메모리 인접성 기반 추론 성능 ↑ |
| **Native S3 Object Storage** | S3 호환 오브젝트 스토리지 (**9.1.x Tech Preview**) | 데이터 레이크/학습셋 저장 용도로 활용 전망 — **프로덕션 비적용** |
| **CrowdStrike EDR 연동 복구** | 클린룸에서 복구 워크로드 스캔 후 운영 복귀 | AI 데이터/모델 자산 랜섬웨어 복구 강화 |

> **Broadcom 발표 수치 (보수적 해석 필요):** 인텔리전트 메모리 티어링으로 서버비용 최대 약 40%↓, vSAN ESA 압축과 중복제거로 스토리지 TCO 약 39%↓, 대규모 AI K8s 운영비 최대 약 46%↓. 모두 "up to"(최대) 값이며 **Broadcom 내부 추정과 테스트(2026년 4월) 기준으로 변경될 수 있습니다.** **실제 효과는 워크로드, 사용률, 환경에 따라 달라지며 고객 실측 검증이 필요합니다.**

---

## 0.3 PAIF 9.1 / PAIS 2.1 — AI 핵심 변화

### (1) MCP(Model Context Protocol) 통합 — 가장 큰 변화
에이전트를 **외부 데이터 소스와 도구**에 표준 인터페이스를 통해 연결합니다. Oracle, Microsoft SQL Server, ServiceNow, GitHub, Slack, PostgreSQL 등을 **커스텀 커넥터 없이** 거버넌스 하에 연동합니다.
→ 상세: [문서 05](05-agents-mcp.md)

### (2) Artifact Mirroring Tool — 에어갭 풀스택
PAIS 2.1에 도입. VI 관리자가 **폐쇄망(air-gapped)** 환경에서 NVIDIA GPU 기반 Model Endpoint와 에이전트를 포함한 **완전한 Private AI 기능**을 설치하고 운영할 수 있습니다. 방산, 금융, 공공처럼 외부 반출이 불가한 환경의 핵심 기능입니다.
→ 상세: [문서 06](06-production.md) | 산업 적용: [문서 08](08-industry.md)

### (3) CPU 추론 (llama.cpp)
기존에는 Embedding만 CPU로 가능했으나, **llama.cpp(b7739)** 엔진 통합으로 **Completion 추론도 CPU 전용** 배포가 가능해졌습니다. 비용 절감, 테스트, 소규모 추론에 활용합니다.

### (4) 통합 관측성
- **모델과 GPU 메트릭 대시보드**: 캐시 활용률, 토큰 처리량, 지연시간, GPU 사용률, 온도, 전력을 VCF Operations 콘솔에서 통합 조회.
- **OpenTelemetry 기반 LLM 트레이싱**: OTel Collector로 LLM 호출 추적.
→ 상세: [문서 06](06-production.md)

### (5) Enhanced DirectPath I/O (주의 기존 서술 정정)
9.0.x 가이드의 "DirectPath I/O는 vMotion 제한" 서술은 **9.1에서 폐기**됩니다. 9.1의 Enhanced DirectPath I/O는:
- **NVAIE(NVIDIA AI Enterprise) 라이선스 없이** 전용(exclusive) GPU 액세스
- **vSphere vMotion 이점 유지**
- NVIDIA **ConnectX-7 / BlueField-3**와 결합해 GPUDirect RDMA, GPUDirect Storage, **멀티호스트 AI 학습** 지원

### (6) Blackwell GPU 지원
NVIDIA **HGX B200**, **RTX PRO 4500 Blackwell Server Edition**, **RTX PRO 6000 Blackwell** 지원. HGX B300은 향후 예정. (세부 호환성은 [Broadcom Compatibility Guide](https://www.broadcom.com/support/vmware/product-compatibility)에서 매번 확인 필요.)

### (7) Kubernetes AI Conformance (DRA)
VKS가 **Dynamic Resource Allocation(DRA)** 기반의 개방형 GPU 스케줄링을 지원해, 타 클라우드와 동일한 오픈 표준으로 ML/생성형 AI 워크로드를 실행할 수 있습니다.

### (8) 데이터 소스 확장
기존 MS Office, PDF, Confluence, SharePoint, S3 등에 더해 **Google Workspace(Docs/Sheets/Slides)** 가 추가됐습니다.

### (9) PAIS UI 셀프서비스
조직 관리자가 **VCF Automation UI**에서 네임스페이스 단위로 PAIS를 활성화하고 관리하고, 사용자는 Model Endpoint, 지식 베이스(KB), Agent의 전체 라이프사이클을 UI에서 처리합니다.

---

## 0.4 버전 매트릭스 변경 (9.0.x → 9.1)

| 컴포넌트 | 9.0.x (PAIS 2.0.89) | 9.1 (PAIS 2.1) | **9.1.1 (PAIS 3.0)** | 변경(2.1 대비) |
|----------|---------------------|----------------|----------------------|:---:|
| vLLM | 0.6.5 (completion) | 0.11.2 (completion+embedding) | **0.20.0** (CUDA 13.0 기본, 드라이버 580 이상 필요) | 상향 |
| Infinity | 0.0.43 (embedding) | 0.0.76 (embedding) | 0.0.76 | = |
| llama.cpp | 없음 | b7739 (CPU completion+embedding) | **b9309** | 상향 |
| VKr | 1.32 | 1.33 | **1.34** (Ubuntu 24.04 노드 이미지) | 상향 |
| VKS | — | 3.5.0+ 권장 | **3.7.x** (VKr 1.33–1.36 지원, 1.32 종료) | 상향 |
| ClusterClass | builtin-generic-v3.2.0 | builtin-generic-v3.2.0 | **builtin-generic-v3.5.0** | 상향 |
| GPU Operator | 24.9.0 | 25.10.1 (driver v580.x) | **25.10.1 기본 또는 26.3.1** (DC 드라이버 580.105.8 / 580.126.20, vGPU 580.105.8) | 선택지 추가 |
| PostgreSQL (PAIS 검증) | 16.8 | 16.8 | 16.8 | = |
| pgvector (PAIS 검증) | 0.8.0 | 0.8.0 | 0.8.0 | = |
| DSM PostgreSQL 지원 범위 | 9.0.x | 9.1: 17.7 ~ 12.22 | **9.1.1: 18.4, 17.10, 16.14, 15.18, 14.23** (12, 13 제거) | 상향 |
| DLVM 기본 OS | Ubuntu 22.04 | 9.1: Ubuntu 24.04 | **9.1.1: Ubuntu 26.04** | 상향 |
| DLVM Conda | Miniconda 24.3.0 | Miniforge 24.11.3 (9.1 RN 기준) | Miniforge 26.1.1 (deprecated 예고) | 상향 |
| DLVM NVIDIA 드라이버 | — | 580.95.05 | **595.71.05** | 상향 |
| DLVM 동봉 CLI | standalone `pais` CLI | VCF CLI 9.0.1 + pais 플러그인 2.0.89, standalone `pais` CLI 제거 | VCF CLI 9.1.0, Helm 4.2.0, kubectl vSphere 플러그인 | 확장 |

> 9.1 열의 DLVM Conda 값은 초판에서 "Miniforge3 24.3.0"으로 적었으나, DLVM 9.1 릴리스 노트 기준 24.11.3이 맞습니다(24.3.0은 DLVM 9.0.2 값). 이번 판에서 정정했습니다.

---

## 0.5 Deprecated / 주의 사항

| 항목 | 상태 | 권고 |
|------|------|------|
| **standalone `pais` CLI** | DLVM 9.1 릴리스 노트에서 **이미지에서 제거** 확정. 대체는 VCF Consumption CLI의 `vcf pais` 플러그인 | 초판의 "상태 불명" 단서는 해소. 명령은 `vcf pais models ...` 형태로 통일 ([문서 03](03-workflows.md)). 모델 저장은 **VCF Automation UI** 우선, CLI는 보조 |
| **TensorFlow 카탈로그 번들** | 축소/비권장 흐름 유지 | PyTorch 기반 권장 |
| **DirectPath I/O "vMotion 제한" 서술** | 폐기 | Enhanced DirectPath I/O는 vMotion 유지 ([0.3-(5)](#5-enhanced-directpath-io-주의-기존-서술-정정)) |
| **Native S3 Object Storage** | **Tech Preview (9.1.x, 9.1.1에서도 유지)** | 프로덕션 비적용. 기존 오브젝트 스토리지 유지, GA 시 재검토 |
| **DLVM 콘솔, Miniforge** | DLVM 9.1에서 deprecated 예고 | 개발 환경은 DLVM 9.1.1의 Deep Learning Container 이미지 등 컨테이너 기반으로 옮기는 흐름을 전제로 계획 |
| **레거시 non-chat completions API** | PAIS 3.0에서 deprecated (OpenAI 호환 API와 Agent Builder API 양쪽) | 신규 코드는 chat completions만 사용. 기존 호출부 점검 ([③ 03](../../03-serving-api/docs/03-openai-compatible-endpoints.md)) |
| **에이전트 API `completion_role` 필드** | PAIS 3.0에서 제거. 응답 role은 항상 assistant | 해당 필드를 읽는 클라이언트 코드 수정 |
| **boolean 필드 느슨한 값** | PAIS 3.0에서 엄격 검증 | "true" / "false" 문자열 등 비정규 값을 보내는 클라이언트 점검 |
| **PostgreSQL 12, 13 (DSM)** | DSM 9.1.1에서 지원 제거 | DSM 9.1.1 배포 전에 14 이상으로 업그레이드 ([② 01](../../02-vectordb/docs/01-version-compatibility.md)) |
| **TanzuKubernetesCluster(TKC) API** | VKS 3.7에서 종료(VKr 1.32가 마지막) | 브라운필드 환경의 TKC 기반 클러스터는 ClusterClass 기반으로 전환 후 VKS 3.7 업그레이드 |
| **VCF Automation 퍼블릭 클라우드 리소스 관리** | VCF Automation 9.1.1에서 deprecated, 기본 비활성 | AI 인프라 범위 밖이나 같은 VCF Automation을 쓰는 조직은 영향 확인 |

> 위 deprecated 항목의 정확한 상태는 적용 직전 [PAIF 9.1 / PAIS 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1.html)로 재확인하시기 바랍니다.

---

## 0.6 9.0.x → 9.1 마이그레이션 체크리스트

```
- [계획] PAIF/PAIS/DLVM/VCF 9.1 릴리스 노트 검토 + 변경 영향 분석
- [호환성] GPU 하드웨어 호환성 목록(BCG: Broadcom Compatibility Guide, HCL: Hardware Compatibility List) 재확인 (특히 Blackwell, ConnectX-7/BlueField-3)
- [인프라] VCF 9.1 업그레이드 (vCenter Quick Patch 활용, 단계적 도메인 업그레이드)
- [GPU Operator] 24.9.0 → 25.10.1, 드라이버 v580.x 검증 (기존 MIG 이슈 회귀 테스트)
- [VKr/VKS] VKr 1.32 → 1.33, VKS 3.5.0+ 확인, DRA 기반 GPU 스케줄링 검토
- [추론 엔진] 기존 Model Endpoint를 vLLM 0.11.2 / Infinity 0.0.76으로 재배포 검증
- [CPU 추론] llama.cpp 활용 가능 워크로드(소규모/테스트) 식별
- [데이터] Google Workspace 등 신규 소스 연동 여부 검토
- [에이전트] MCP로 대체 가능한 기존 커스텀 커넥터 식별 → 거버넌스 정책 수립
- [관측성] 모델, GPU 메트릭 대시보드 + OTel 트레이싱 활성화
- [에어갭] 폐쇄망 대상이면 Artifact Mirroring Tool 기반 재설계 검토
- [검증] 기능/부하/장애/보안 테스트 후 프로덕션 전환
```

---

## 0.7 9.1.1 / PAIS 3.0 변경 (2026-09-03 GA)

VCF 9.1.1.0은 BOM(Bill of Materials, 구성 컴포넌트 버전 목록)을 갱신한 유지보수 릴리스이며, 공식 릴리스 노트 스스로 "지원성 개선 중심"이라고 밝힙니다. AI 관점의 실질 변경은 같은 날 나온 PAIS 3.0과 DLVM 9.1.1 이미지에 있습니다. PAIF 9.1.1 릴리스 노트의 변경 항목도 이 두 가지뿐입니다.

### 0.7.1 PAIS 3.0 변경 요약

| 영역 | 9.1 (PAIS 2.1) | 9.1.1 (PAIS 3.0) |
|------|----------------|------------------|
| 모델 위치 | 네임스페이스마다 자기 모델 엔드포인트를 배포 | **공유 모델 호스팅**: 중앙(provider) 인스턴스의 completion / embedding 엔드포인트를 다른 인스턴스와 네임스페이스에서 참조 |
| 모델 출처 | 사내 Model Gallery의 모델만 | **원격 클라우드 모델**: Google Gemini 네이티브 API, Gemini Enterprise Agent Platform(구 Vertex AI), Google OpenAI 호환 계층, 서드파티 OpenAI 호환 서비스. 토큰 사용량 추적 포함 |
| 인증 수단 | OIDC Bearer 토큰, mTLS | **API 토큰** 추가(VCF Automation 계정 `vcfa-<org>-...`, 로컬 PAIS 계정 `pais-<provider>-...`). PAIS API 인증, 인스턴스 간 공유 모델 접근, VCF Consumption CLI 실행에 사용 |
| 관측성 | 메트릭 대시보드(Grafana 직접 배포 전제), OTel 트레이싱 | 모델과 에이전트 실시간 대시보드, **Grafana 예시 구성 제공**, 백엔드 헬스 실시간, LLM 상호작용 전체 트레이싱. Prometheus 수집은 VKS 클러스터 가용 후 시작 |
| 데이터 평면 | 고정 구성 | Ingress 독립 스케일링, 커스텀 모델 게이트웨이 주입, Agent Builder와 Data Indexing 개별 on/off |
| 배포 경로 | VCF Automation UI 셀프서비스 | vSphere Local Consumption Interface 경유 배포 추가, 복수 인증 공급자(VCF Automation 또는 로컬 계정) |
| TLS | 플랫폼 발급 | Ingress 종단 인증서 BYO, OIDC 연결 TLS 검증 설정 |
| CLI | `vcf pais models`, `vcf pais amt` | kubeconfig 조회 단순화, 지원 번들 수집 개선 |
| OpenAI 호환 API | 기본 호환 | 모델 status 필드, embedding encoding_format 설정, 비표준 속성 전달, 스트리밍 처리량 개선. non-chat completions deprecated, `completion_role` 제거 |
| Data Indexing | 지식베이스 인덱싱과 검색 | 인용 노드 ID, TLS 검증 설정, 지식베이스와 인덱스 복제(clone), 임베딩 메트릭 개선 |
| 실행 기반 | VKr 1.33, ClusterClass v3.2.0, GPU Operator 25.10.1 | VKr 1.34, ClusterClass v3.5.0, GPU Operator 25.10.1 또는 26.3.1, vLLM 0.20.0(CUDA 13.0) |

각 항목의 설계 함의는 해당 편에서 다룹니다. 공유 모델 호스팅은 [문서 06 멀티테넌트](06-production.md)와 [③ 02 서빙 아키텍처](../../03-serving-api/docs/02-serving-api-architecture.md), [⑦ 05 테넌시](../../07-design/docs/05-tenancy-security.md)에, 원격 클라우드 모델과 API 토큰은 [③ 05 인증](../../03-serving-api/docs/05-auth-and-gateway.md)과 [⑤ 03 Identity](../../05-security/docs/03-identity-access.md)에, 관측성은 [문서 06 6.8절](06-production.md)과 [③ 07](../../03-serving-api/docs/07-observability-ops.md)에 있습니다.

### 0.7.2 PAIS 2.1.2 (2026-08-17) 수정 사항

3.0 이전에 2.1 라인의 수정 릴리스가 한 번 있었습니다. 2.1을 유지하는 환경이라면 최소 2.1.2로 올리는 것이 좋습니다. 수정된 문제는 패키지 다운로드 URL 오류, 로컬 레지스트리 미러와 5000 포트 충돌, 중간 CA 인증서 갱신 요구, CPU 추론에서 MCP 도구 사용 시 reasoning 모델 타임아웃, Photon OS 패키지 갱신, 지원 번들 로그 수집 개선입니다.

### 0.7.3 VCF 9.1.1 플랫폼 변경 중 AI 인프라에 닿는 것

| 컴포넌트 | 변경 | AI 인프라 관점 |
|----------|------|----------------|
| VCF Operations | AI Assistant(백엔드로 PAIS 모델 엔드포인트 또는 사설 Google Gemini 인스턴스 선택), VKS 메트릭 OpenTelemetry 2초 간격 스트리밍과 멀티클러스터 모니터링, Grafana 대시보드 임포트 | 플랫폼이 자기 모델로 자기를 진단하는 구성이 가능. VKS 관측이 PAIS 관측과 같은 표준(OTel)으로 맞춰짐 ([문서 10](10-operations.md)) |
| VCF Operations | AD / LDAP 로그인 시 온디맨드 조회, 비밀번호 정책과 인증서 관리 범위 확장(vSphere Supervisor, NSX Edge, 라이선스 서버 포함), Salt 기반 구성 API, 컴팩트 폼팩터(CPU / 메모리 최대 40% 절감), 라이선스 서버 IPv6 | 인증서 회전 런북에 Supervisor 인증서가 편입됨 ([문서 10](10-operations.md)) |
| vCenter | 컴퓨트 정책으로 VM-VM affinity / anti-affinity 규칙, 메모리 티어링 환경에서 HA admission control이 DRAM을 별도 추적, Secure Boot PK 자동 교정 | 모델 레플리카 VM을 호스트 분산하는 근거가 공식 기능이 됨 ([⑦ 04](../../07-design/docs/04-network-storage-availability.md)) |
| VCF Automation | VLAN-backed VPC, 퍼블릭 클라우드 리소스 관리 deprecated, BYO Velero deprecated | VKS 백업은 Broadcom 제공 Velero 패키지로 |
| DSM 9.1.1 | PostgreSQL 18 지원, 읽기 복제, set_user 확장, SQL Server 2025, VKS 3.7 연동, Supervisor 크로스클러스터 HA. Avi와 NSX를 함께 쓰는 클러스터는 VCF 9.1.0 이상으로 올리기 전에 DSM을 9.1.1로 먼저 올려야 DB 다운타임을 피함 | 벡터 DB 운영 ([② 06](../../02-vectordb/docs/06-operations.md)) |
| VKS 3.7 | VKr 1.33–1.36, ClusterClass v3.7.0, 워커 노드 최대 250, 5노드 컨트롤 플레인, 네이티브 OIDC, Workload Identity Federation, 애드온 관리 프레임워크(지원 4단계), TKC API 종료 | 클러스터 사이징 상한과 ID 연동 ([⑥ 04](../../06-sizing-cost/docs/04-vks-cluster-sizing.md)) |
| Tech Preview | GitOps Service(Argo CD 내장), vSAN Object Storage(S3 호환) | 프로덕션 비적용 |
| 인증 | vSphere 9.1이 NVIDIA-Certified Hypervisor 인증 획득 | GPU 워크로드 성능 근거 자료로 활용 가능 |

### 0.7.4 발표됐으나 GA가 아닌 것

2026년 8월 말 VMware Explore에서 발표된 항목 중 아래는 아직 릴리스 노트에 없습니다. 이 시리즈는 GA 문서로 확인된 것만 본문에 반영하므로, 아래는 이 절에서만 언급합니다.

| 항목 | 상태 | 비고 |
|------|------|------|
| AI Gateway(프롬프트 라우팅, 사용자 단위 토큰 제한, OIDC 기반 앱 인가) | 향후 릴리스 | 지금은 레이트리밋과 쿼터를 앱 또는 게이트웨이 계층에서 구현 ([③ 05](../../03-serving-api/docs/05-auth-and-gateway.md)) |
| Secure Agent Framework(에이전트 코드 샌드박스, Agent Harness) | 향후 릴리스 | 콘텐츠 가드레일과 도구 권한은 앱 계층 책임 유지 |
| Model Autoscaling(지연과 세션 임계 기반 자동 스케일) | 향후 릴리스 | 레플리카 수는 수동 설정 |
| AgentMinder | 별도 제품, 2026-08-31 GA | 에이전트를 기업 신원으로 다루고, 도구 호출을 게이트웨이에서 인증과 정책 평가 후 승인된 백엔드로만 보내며, OpenTelemetry로 감사하는 런타임 통제 제품. PAIS 구성요소가 아니며 VKS 등 Kubernetes에 배포 ([Broadcom 보도자료](https://www.globenewswire.com/news-release/2026/08/31/3353342/19933/en/broadcom-unveils-agentminder-an-enterprise-solution-for-ai-agent-governance-and-runtime-control.html)) |
| vDefend와 Avi Load Balancer의 에이전틱 보안(MCP 서버와 LLM과 데이터스토어 자동 탐지, 섀도 AI 탐지, 미승인 MCP 도구 접근 차단, 자격증명과 PII 유출 방지) | 향후 릴리스(시점 미공개) | 보도자료가 전부 미래형으로 기술하며 버전과 시점이 없음 ([Broadcom 보도자료](https://www.globenewswire.com/news-release/2026/08/31/3353355/19933/en/broadcom-delivers-end-to-end-security-identity-and-observability-for-agentic-ai.html)). 지금은 [⑤ 02](../../05-security/docs/02-network-tenant-isolation.md)의 NSX와 vDefend 통제로 설계 |
| VMware AI Factory, VMware Private AI Cloud | 프로그램과 브랜드 | AMD Instinct MI350 + ROCm, OEM AI ReadyNode, 베어메탈 자동화. 라이선스 패키징 미공개 |

---

## 0.8 버전별 기능 이력 (PAIS 2.0.89 / 2.1 / 3.0)

"우리 환경은 2.1인데 이 기능을 쓸 수 있나"를 답하는 표입니다. 본문에서 "PAIS 3.0부터"로 표기한 대목은 이 표의 3.0 열에 해당합니다. 모든 버전을 반드시 최신으로 올려야 하는 것은 아니므로, 운영 중인 버전의 열만 보고 해당 절을 골라 읽으시면 됩니다.

| 기능 | 2.0.89 (VCF 9.0.x, 2025-09) | 2.1 (VCF 9.1, 2026-05) | 3.0 (VCF 9.1.1, 2026-09) | 본문 위치 |
|------|:---:|:---:|:---:|-----------|
| Model Gallery(Harbor), Model Runtime, Data Indexing, Agent Builder | 있음 | 있음 | 있음 | [01](01-concepts.md) |
| vLLM completion, Infinity embedding | 있음 | 있음 | 있음 | [③](../../03-serving-api/README.md) |
| vLLM embedding | 없음 | 있음 | 있음 | [③ 02](../../03-serving-api/docs/02-serving-api-architecture.md) |
| CPU completion 추론(llama.cpp) | 없음 | 있음 | 있음 | [③ 02](../../03-serving-api/docs/02-serving-api-architecture.md) |
| MCP 서버 연동, Tool Gallery | 없음 | 있음 | 있음 | [05](05-agents-mcp.md) |
| 지식베이스를 MCP로 노출 | 없음 | 있음 | 있음 | [05](05-agents-mcp.md) |
| Artifact Mirroring Tool(에어갭) | 없음 | 있음 | 있음 | [06 6.9절](06-production.md) |
| VCF Automation UI 셀프서비스 활성화 | 없음 | 있음 | 있음 | [03](03-workflows.md) |
| 모델 엔드포인트 확장 설정 UI | 없음 | 있음 | 있음 | [03](03-workflows.md) |
| 통합 관측성(메트릭 대시보드), OTel LLM 트레이싱 | 없음 | 있음 | 확장 | [06 6.8절](06-production.md) |
| Google Workspace 데이터 소스 | 없음 | 있음 | 있음 | [03](03-workflows.md) |
| Broadcom 인증서 서명, 지원 번들 | 있음 | 있음 | 있음 | [10](10-operations.md) |
| 공유 모델 호스팅(인스턴스 간, 네임스페이스 간) | 없음 | 없음 | 있음 | [06 6.4절](06-production.md) |
| 원격 클라우드 모델(Gemini, Vertex, OpenAI 호환) | 없음 | 없음 | 있음 | [③ 02](../../03-serving-api/docs/02-serving-api-architecture.md) |
| API 토큰(VCF Automation 계정, 로컬 계정) | 없음 | 없음 | 있음 | [③ 05](../../03-serving-api/docs/05-auth-and-gateway.md) |
| Grafana 예시 대시보드, 백엔드 헬스 | 없음 | 없음 | 있음 | [③ 07](../../03-serving-api/docs/07-observability-ops.md) |
| Ingress 독립 스케일링, 커스텀 게이트웨이 주입, 모듈 on/off | 없음 | 없음 | 있음 | [06 6.5절](06-production.md) |
| vSphere Local Consumption Interface 배포, 복수 인증 공급자 | 없음 | 없음 | 있음 | [03](03-workflows.md) |
| BYO Ingress TLS 인증서 | 없음 | 없음 | 있음 | [10](10-operations.md) |
| 지식베이스와 인덱스 복제, 인용 노드 ID | 없음 | 없음 | 있음 | [④ 03](../../04-rag/docs/03-retrieval-context.md) |
| embedding encoding_format, 모델 status 필드 | 없음 | 없음 | 있음 | [③ 03](../../03-serving-api/docs/03-openai-compatible-endpoints.md) |
| non-chat completions | 있음 | 있음 | deprecated | [③ 03](../../03-serving-api/docs/03-openai-compatible-endpoints.md) |
| 에이전트 API `completion_role` | 있음 | 있음 | 제거 | 에이전트 가이드 03 |

인프라 쪽 이력은 PAIS 버전과 별개로 VCF 라인을 따릅니다. Enhanced DirectPath I/O, Blackwell GPU, DRA, NVMe 메모리 티어링은 9.1부터이고, VM-VM anti-affinity 컴퓨트 정책, VCF Operations AI Assistant, VKS OTel 스트리밍은 9.1.1부터입니다(0.7.3절).

---

## 0.9 9.1 → 9.1.1 / PAIS 2.1 → 3.0 체크리스트

0.6절의 9.0.x → 9.1 체크리스트를 이미 마친 환경이 9.1.1로 올라갈 때의 추가 항목입니다.

```
- [계획] VCF 9.1.1.0, PAIF 9.1.1, PAIS 3.0, DLVM 9.1.1, DSM 9.1.1 릴리스 노트 검토
- [순서] VCF 관리 서비스(fleet lifecycle)를 9.1.1.0으로 먼저 패치한 뒤 나머지 컴포넌트
- [DSM] Avi + NSX 조합 클러스터는 VCF 9.1.0 이상으로 올리기 전에 DSM 9.1.1 선적용, PostgreSQL 12/13 인스턴스는 14 이상으로 사전 업그레이드
- [VKS] VKr 1.32 클러스터가 남아 있으면 1.33 이상으로 먼저, TKC API 기반 클러스터는 ClusterClass 기반으로 전환
- [PAIS] 2.1 → 3.0 업그레이드 창 확보. 단일 레플리카 모델 엔드포인트는 다운타임 발생, 중요 엔드포인트는 사전에 레플리카 2 이상
- [GPU] vLLM 0.20.0은 CUDA 13.0 기본이므로 게스트 드라이버 580 이상 확인. GPU Operator 26.3.1로 갈지 25.10.1을 유지할지 결정하고 문서 11의 인터락 규칙으로 검증
- [API] non-chat completions 호출부와 completion_role 필드를 읽는 코드 식별, boolean 값 정규화
- [인증] API 토큰 활성화 여부 확인(UI 활성화 시 기본으로 켜지지 않는 알려진 이슈), 로컬 계정 기본 base URL 설정
- [관측] Prometheus 수집이 VKS 클러스터 가용 이후 시작되는 동작 변화를 알람 규칙에 반영
- [설계] 공유 모델 호스팅 도입 여부(테넌트별 중복 엔드포인트 정리)와 원격 클라우드 모델 허용 정책 결정
- [DLVM] 9.1.1 이미지(Ubuntu 26.04) 전환 계획, Miniforge와 DLVM 콘솔 deprecated 대응
- [검증] 업그레이드 후 모델 엔드포인트, 에이전트, 지식베이스, MCP 연결 정상 복구 확인
```

---

## 출처

- [Announcing VCF 9.1 (VMware Cloud Foundation Blog, 2026-05)](https://blogs.vmware.com/cloud-foundation/2026/05/05/announcing-vcf-9-1-modern-private-cloud-built-for-efficiency-and-resilience/)
- [Streamline, Simplify and Protect all your AI workloads with VCF 9.1](https://blogs.vmware.com/cloud-foundation/2026/05/05/streamline-simplify-and-protect-all-your-ai-workloads-with-vcf-9-1/)
- [VMware Private AI Foundation with NVIDIA 9.1 (Broadcom TechDocs)](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1.html)
- [Broadcom Announces VCF 9.1 — Production AI (Broadcom News)](https://news.broadcom.com/releases/broadcom-announces-vmware-cloud-foundation-9-1)
- [VMware Cloud Foundation 9.1.1.0 Release Notes (Broadcom TechDocs)](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/release-notes/vmware-cloud-foundation-9-1-1-0-release-notes.html)
- [VMware Private AI Foundation with NVIDIA 9.1 / 9.1.1 Release Notes](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1/private-ai-release-notes/vmware-private-ai-foundation-with-nvidia-91-release-notes.html)
- [VMware Private AI Services Release Notes (3.0, 2.1.2, 2.1)](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1/private-ai-release-notes/vmware-private-ai-services-release-notes.html)
- [VMware Deep Learning VM Image Release Notes](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1/private-ai-release-notes/vmware-deep-learning-vm-image-release-notes.html)
- [VMware Data Services Manager 9.1.1 Release Notes](https://techdocs.broadcom.com/us/en/vmware-cis/dsm/data-services-manager/9-1/release-notes/vmware-data-services-manager-911-release-notes.html)
- [VMware vSphere Kubernetes Service 3.7 Release Notes](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-service-administration-and-development/9-1/release-notes/vks-release-notes/vmware-tanzu-kubernetes-grid-service-37-release-notes.html)
- [Announcing General Availability of VCF 9.1.1 (VMware Cloud Foundation Blog, 2026-09-03)](https://blogs.vmware.com/cloud-foundation/2026/09/03/announcing-general-availability-of-vmware-cloud-foundation-9-1-1/)
- [New AI and Kubernetes Private Cloud Operations Capabilities in VCF 9.1.1 (VMware Cloud Foundation Blog, 2026-09-03)](https://blogs.vmware.com/cloud-foundation/2026/09/03/new-ai-and-kubernetes-private-cloud-operations-capabilities-in-vmware-cloud-foundation-9-1-1/)
- [Explore 2026: VMware AI Factory and other new AI innovations in VCF (VMware Cloud Foundation Blog, 2026-09-03)](https://blogs.vmware.com/cloud-foundation/2026/09/03/explore-2026-vmware-ai-factory-and-other-new-ai-innovations-in-vcf/)

---

[목차](../README.md) | [다음: 01 핵심 개념 및 페르소나 →](01-concepts.md)

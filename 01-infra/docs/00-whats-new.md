# 00 — What's New (VCF 9.1 / PAIF 9.1 / PAIS 2.1)

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.
> 이 문서는 **9.0.x에서 9.1로 올라오는 분**과 **9.1을 처음 접하는 분** 모두를 위한 변경 요약입니다.

VCF 9.1은 2026년 5월 GA되었으며, "프로덕션 AI를 위한 안전하고 비용 효율적인 프라이빗 클라우드"를 표방했습니다. AI 관점에서는 PAIF 9.1 / **Private AI Services(PAIS) 2.1**이 함께 출시되며 **에이전트·외부 도구 연동(MCP)·에어갭·관측성**이 크게 보강됐습니다.

---

## 0.1 변경 요약

| 영역 | 9.0.x | 9.1 |
|------|-------|-----|
| 추론 엔진 | vLLM 0.6.5 / Infinity 0.0.43 | **vLLM 0.11.2 / Infinity 0.0.76 / llama.cpp b7739 (CPU)** |
| CPU 전용 추론 | Embedding(Infinity)만 | **Completion도 CPU 가능 (llama.cpp)** |
| 외부 도구 연동 | 커스텀 코드 필요 | **MCP 표준 연동 (Oracle·MS SQL·ServiceNow·GitHub·Slack·PostgreSQL 등)** |
| 에어갭 | Harbor 수동 구성 | **Artifact Mirroring Tool로 풀 AI 기능 구동** |
| 관측성 | 모호/수동 | **모델·GPU 메트릭 대시보드 + OpenTelemetry LLM 트레이싱** |
| GPU 전용 패스스루 | DirectPath I/O = vMotion 제한 | **Enhanced DirectPath I/O = vMotion 유지, NVAIE(NVIDIA AI Enterprise) 불필요** |
| 최신 GPU | B200 "테스트 중" | **Blackwell GA (HGX B200, RTX PRO 4500/6000)** |
| K8s GPU 스케줄링 | 정적 할당 중심 | **Kubernetes AI Conformance (DRA 기반)** |
| 데이터 소스 | MS Office·PDF 등 | **+ Google Workspace (Docs/Sheets/Slides)** |
| PAIS 활성화 | kubectl 중심 | **VCF Automation UI 셀프서비스 (네임스페이스 단위)** |
| VKS 스케일 | — | **Supervisor당 최대 500 K8s 클러스터** |

---

## 0.2 VCF 9.1 플랫폼 변화 (AI 인프라에 영향)

PAIF는 VCF 위에서 동작하므로, 플랫폼 레벨 변화가 AI 운영에 직접 영향을 줍니다.

| 변화 | 내용 | AI 워크로드 관점 |
|------|------|----------------|
| **API-first 통합 모델** | SDDC Manager·vCenter·NSX·vSAN을 단일 API 계약으로 통합 | AI 인프라 프로비저닝/IaC 자동화 일관성 ↑ |
| **vCenter Quick Patch** | 변경된 바이너리만 패치 → 다운타임 초 단위/제로 | GPU 호스트 유지보수 창 최소화 |
| **Enhanced NVMe Memory Tiering** | DRAM+NVMe 통합 메모리 모델, 콜드 페이지를 NVMe로 오프로드 | 메모리 바운드 AI/벡터 DB 워크로드 직접 대응 |
| **VKS 스케일 확장** | Supervisor당 최대 500 클러스터, 배포 70%↑, 업그레이드 창 75%↓ | 대규모 AI 클러스터 운영 비용 절감 |
| **Topology Aware Scheduling** | NUMA·가속기 로컬리티 고려 배치 | GPU/메모리 인접성 기반 추론 성능 ↑ |
| **Native S3 Object Storage** | S3 호환 오브젝트 스토리지 (**9.1.x Tech Preview**) | 데이터 레이크/학습셋 저장 용도로 활용 전망 — **프로덕션 비적용** |
| **CrowdStrike EDR 연동 복구** | 클린룸에서 복구 워크로드 스캔 후 운영 복귀 | AI 데이터/모델 자산 랜섬웨어 복구 강화 |

> **Broadcom 발표 수치 (보수적 해석 필요):** 인텔리전트 메모리 티어링으로 서버비용 최대 약 40%↓, vSAN ESA 압축·중복제거로 스토리지 TCO 약 39%↓, 대규모 AI K8s 운영비 최대 약 46%↓. 모두 "up to"(최대) 값이며 **Broadcom 내부 추정·테스트(2026년 4월) 기준으로 변경될 수 있습니다.** **실제 효과는 워크로드·사용률·환경에 따라 달라지며 고객 실측 검증이 필요합니다.**

---

## 0.3 PAIF 9.1 / PAIS 2.1 — AI 핵심 변화

### (1) MCP(Model Context Protocol) 통합 — 가장 큰 변화
에이전트를 **외부 데이터 소스·도구**에 표준 인터페이스를 통해 연결합니다. Oracle, Microsoft SQL Server, ServiceNow, GitHub, Slack, PostgreSQL 등을 **커스텀 커넥터 없이** 거버넌스 하에 연동합니다.
→ 상세: [문서 05](05-agents-mcp.md)

### (2) Artifact Mirroring Tool — 에어갭 풀스택
PAIS 2.1에 도입. VI 관리자가 **폐쇄망(air-gapped)** 환경에서 NVIDIA GPU 기반 Model Endpoint와 에이전트를 포함한 **완전한 Private AI 기능**을 설치·운영할 수 있습니다. 방산·금융·공공처럼 외부 반출이 불가한 환경의 핵심 기능입니다.
→ 상세: [문서 06](06-production.md) · 산업 적용: [문서 08](08-industry.md)

### (3) CPU 추론 (llama.cpp)
기존에는 Embedding만 CPU로 가능했으나, **llama.cpp(b7739)** 엔진 통합으로 **Completion 추론도 CPU 전용** 배포가 가능해졌습니다. 비용 절감·테스트·소규모 추론에 활용합니다.

### (4) 통합 관측성
- **모델·GPU 메트릭 대시보드**: 캐시 활용률, 토큰 처리량, 지연시간, GPU 사용률·온도·전력을 VCF Operations 콘솔에서 통합 조회.
- **OpenTelemetry 기반 LLM 트레이싱**: OTel Collector로 LLM 호출 추적.
→ 상세: [문서 06](06-production.md)

### (5) Enhanced DirectPath I/O (주의 기존 서술 정정)
9.0.x 가이드의 "DirectPath I/O는 vMotion 제한" 서술은 **9.1에서 폐기**됩니다. 9.1의 Enhanced DirectPath I/O는:
- **NVAIE(NVIDIA AI Enterprise) 라이선스 없이** 전용(exclusive) GPU 액세스
- **vSphere vMotion 이점 유지**
- NVIDIA **ConnectX-7 / BlueField-3**와 결합해 GPUDirect RDMA·GPUDirect Storage, **멀티호스트 AI 학습** 지원

### (6) Blackwell GPU 지원
NVIDIA **HGX B200**, **RTX PRO 4500 Blackwell Server Edition**, **RTX PRO 6000 Blackwell** 지원. HGX B300은 향후 예정. (세부 호환성은 [Broadcom Compatibility Guide](https://www.broadcom.com/support/vmware/product-compatibility)에서 매번 확인 필요.)

### (7) Kubernetes AI Conformance (DRA)
VKS가 **Dynamic Resource Allocation(DRA)** 기반의 개방형 GPU 스케줄링을 지원해, 타 클라우드와 동일한 오픈 표준으로 ML/생성형 AI 워크로드를 실행할 수 있습니다.

### (8) 데이터 소스 확장
기존 MS Office·PDF·Confluence·SharePoint·S3 등에 더해 **Google Workspace(Docs/Sheets/Slides)** 가 추가됐습니다.

### (9) PAIS UI 셀프서비스
조직 관리자가 **VCF Automation UI**에서 네임스페이스 단위로 PAIS를 활성화·관리하고, 사용자는 Model Endpoint·지식 베이스(KB)·Agent의 전체 라이프사이클을 UI에서 처리합니다.

---

## 0.4 버전 매트릭스 변경 (9.0.x → 9.1)

| 컴포넌트 | 9.0.x (PAIS 2.0.89) | **9.1 (PAIS 2.1)** | 변경 |
|----------|---------------------|--------------------|:---:|
| vLLM | 0.6.5 (completion) | **0.11.2** (completion+embedding) | 상향 |
| Infinity | 0.0.43 (embedding) | **0.0.76** (embedding) | 상향 |
| llama.cpp | 없음 | **b7739** (CPU completion+embedding) | 신규 |
| VKr | 1.32 | **1.33** | 상향 |
| VKS | — | **3.5.0+** 권장 | 신규 |
| GPU Operator | 24.9.0 | **25.10.1** (driver v580.x) | 상향 |
| PostgreSQL | 16.8 | 16.8 | = |
| pgvector | 0.8.0 | 0.8.0 | = |
| ClusterClass | builtin-generic-v3.2.0 | builtin-generic-v3.2.0 | = |
| DLVM Conda | Miniconda 24.3.0 | **Miniforge3 24.3.0** | 대체 |

---

## 0.5 Deprecated / 주의 사항

| 항목 | 상태 | 권고 |
|------|------|------|
| **`pais` CLI** | PAIF 9.1(NVIDIA) RN에는 "pais CLI 1.0.0 제공"으로 표기되나 **PAIS 2.1 RN에는 언급 없음** → 상태·명령 구문은 공식 CLI 문서로 확인 필요 | 9.0.x 가이드의 "제거 예정" 단정은 과함. 모델 저장은 **VCF Automation UI** 우선, CLI는 보조 ([문서 03](03-workflows.md)) |
| **TensorFlow 카탈로그 번들** | 축소/비권장 흐름 유지 | PyTorch 기반 권장 |
| **DirectPath I/O "vMotion 제한" 서술** | 폐기 | Enhanced DirectPath I/O는 vMotion 유지 ([0.3-(5)](#5-enhanced-directpath-io-주의-기존-서술-정정)) |
| **Native S3 Object Storage** | **Tech Preview (9.1.x)** | 프로덕션 비적용. 기존 오브젝트 스토리지 유지, GA 시 재검토 |

> 위 deprecated 항목과 `pais` CLI 정확한 상태는 적용 직전 [PAIF 9.1 / PAIS 2.1 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1.html)로 재확인하시기 바랍니다.

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
- [관측성] 모델·GPU 메트릭 대시보드 + OTel 트레이싱 활성화
- [에어갭] 폐쇄망 대상이면 Artifact Mirroring Tool 기반 재설계 검토
- [검증] 기능/부하/장애/보안 테스트 후 프로덕션 전환
```

---

## 출처

- [Announcing VCF 9.1 (VMware Cloud Foundation Blog, 2026-05)](https://blogs.vmware.com/cloud-foundation/2026/05/05/announcing-vcf-9-1-modern-private-cloud-built-for-efficiency-and-resilience/)
- [Streamline, Simplify and Protect all your AI workloads with VCF 9.1](https://blogs.vmware.com/cloud-foundation/2026/05/05/streamline-simplify-and-protect-all-your-ai-workloads-with-vcf-9-1/)
- [VMware Private AI Foundation with NVIDIA 9.1 (Broadcom TechDocs)](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1.html)
- [Broadcom Announces VCF 9.1 — Production AI (Broadcom News)](https://news.broadcom.com/releases/broadcom-announces-vmware-cloud-foundation-9-1)

---

[목차](../README.md) · [다음: 01 핵심 개념 및 페르소나 →](01-concepts.md)

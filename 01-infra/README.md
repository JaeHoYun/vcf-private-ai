# VCF 9.1 Private AI Foundation 가이드

> **이 가이드를 읽기 전에** — 임베딩, 벡터, 토큰, RAG, 쿠버네티스(VKS) 같은 용어가 낯설다면, 먼저 [VCF Private AI 입문 (Primer)](../00-foundations/README.md)에서 기초 어휘를 익히시길 권합니다. 이 가이드는 그 개념들을 이미 아는 것으로 전제합니다.

VMware Cloud Foundation(VCF) 9.1 기반 Private AI 인프라의 **구축, 개발, 운영**을 위한 실무 참조 가이드입니다.
인프라팀이 AI 플랫폼을 구축하고, 데이터 사이언티스트와 MLOps가 모델과 RAG를 배포하고, 앱 개발자가 API로 서비스를 만드는 전체 여정을 한 권으로 다룹니다.

> **VCF Private AI 가이드 시리즈 — ① 인프라와 운영**, 7부작 중 한 편입니다. [전체 7개 보기 — 시리즈 허브](../README.md), 상위 전략 [AX 방법론](https://github.com/JaeHoYun/enterprise-ax-methodology)

---

## 목차

| 구분 | 번호 | 문서 | 주요 내용 |
|------|------|------|-----------|
| 본문 | 00 | [What's New (9.1 / 9.1.1)](docs/00-whats-new.md) | VCF/PAIF 9.1 신규 기능, 9.1.1 / PAIS 3.0 변경, 버전별 기능 이력, 버전 매트릭스, 9.0.x→9.1→9.1.1 마이그레이션 |
| | 01 | [핵심 개념 및 페르소나](docs/01-concepts.md) | PAIF/PAIS/DLVM 개념, 라이선스 구조, 역할 정의 |
| | 02 | [아키텍처 및 구축 순서](docs/02-architecture.md) | 계층 구조, GPU(DirectPath/vGPU/Blackwell/DRA), Phase별 구축 |
| | 03 | [역할별 워크플로우](docs/03-workflows.md) | AI 플레이그라운드, 모델 준비, RAG 구성, PAIS UI, 데이터 소스 |
| | 04 | [개발 시나리오 및 AI 앱 개발](docs/04-dev-scenarios.md) | PAIS 사용 패턴(라이프사이클, 소비 깊이, 상황 축), AI 앱 4-Tier, API 연동, 배포 |
| | 05 | [에이전트, MCP, 거버넌스](docs/05-agents-mcp.md) | Agent Builder, Model Context Protocol, Tool-calling, LLM 트레이싱 |
| | 06 | [프로덕션 아키텍처](docs/06-production.md) | HA/DR, 멀티테넌트, 스케일링, 워크로드 사이징, 모델 라이프사이클, 보안, AI 관측성, 에어갭(Artifact Mirroring Tool) |
| | 07 | [GPUaaS (PAIF GPU 자원 서비스)](docs/07-gpuaas.md) | 책임 경계 2티어, VM+K8s 셀프서비스, GPU 분할 매트릭스, 쇼백과 차지백, 셀프서비스/공유풀 시나리오 |
| | 08 | [한국 산업군 적용 시나리오](docs/08-industry.md) | 제조, 방산, 유통, 콘텐츠 PAIF 시나리오, 에어갭, Blackwell, MCP 연계 |
| | 09 | [구축 시나리오](docs/09-deployment-scenarios.md) | 신규(그린필드), 기존 환경에 추가 구축(브라운필드)와 전환(마이그레이션) 구축 출발 상황별 절차 골격, 선결요건, 리스크 |
| | 10 | [Day-2 운영](docs/10-operations.md) | 구축 이후 운영. 업그레이드(LCM), 트러블슈팅, 백업복구, 인증서 회전, SLO/알람, 온콜, 네트워크, 스토리지 Day-2 런북 + 운영자 독자 트랙(상황별 라우터) |
| | 11 | [GPU Enablement 핸즈온 (딥다이브)](docs/11-gpu-enablement.md) | 시리즈 표준보다 깊은 핸즈온 트랙. BIOS 전제→하이퍼바이저 인식→할당 모드 4종→버전 인터락→GPU Operator→PAIS 소비 수직 경로, known-good 스냅샷, PoC 검증 경로, 흔한 함정(CDI, vGPU 라이선스) |
| 부록 | A1 | [FAQ, 버전 매트릭스, 용어집](appendix/A1-appendix.md) | 자주 묻는 질문, 호환성, 용어, 참고 링크 |
| | 워크시트 | [채워넣기 워크시트](worksheet/README.md) | 09 구축 시나리오 결정, 현황 파악, SoW 정의, 10 Day-2 점검, 업그레이드, 복구, SLO 기록용 채워넣기 양식(계산용 xlsx 아님) |

---

## 기반 버전

| 구분 | 버전 | 비고 |
|------|------|------|
| VMware Cloud Foundation (VCF) | 9.1.1 | 9.1 GA 2026-05, 9.1.1 GA 2026-09(유지보수 릴리스, BOM 갱신) |
| Private AI Foundation with NVIDIA (PAIF) | 9.1.1 | VCF 코어 구독 포함(NVAIE만 별도). 9.1.1 변경은 PAIS 3.0 제공과 DLVM 이미지 갱신 |
| Private AI Services (PAIS) | 3.0 | VCF 9.1.x 호환. 공유 모델 호스팅, 원격 클라우드 모델, API 토큰, 관측성 확장 추가. 2.1의 UI 셀프서비스, MCP, Artifact Mirroring Tool(에어갭)은 그대로 유지 |
| Deep Learning VM(DLVM) 이미지 | 9.1.1 | Ubuntu 26.04 LTS, NVIDIA 데이터센터 드라이버 595.71.05, Miniforge 26.1.1(deprecated 예고), VCF CLI 9.1.0 동봉. 9.1 이미지는 Ubuntu 24.04, 드라이버 580.95.05, Miniforge 24.11.3 |
| vLLM (Completion/Embedding) | 0.20.0 | completions + embeddings 지원. CUDA 13.0 기본이라 GPU 드라이버 580 이상 필요 |
| Infinity (Embedding) | 0.0.76 | embeddings 전용 (2.1과 동일) |
| llama.cpp (CPU 추론) | b9309 | completions + embeddings, CPU 추론 |
| VKr (vSphere Kubernetes release) | 1.34 | ClusterClass `builtin-generic-v3.5.0`, Ubuntu 24.04 노드 이미지. 컨트롤 플레인 VM 클래스는 best-effort-large 이상 |
| VKS (vSphere Kubernetes Service) | 3.7.x | VKS 3.7.1(2026-08)이 VKr 1.33에서 1.36까지 지원. PAIS가 고정한 VKr과 ClusterClass 값을 우선 따릅니다 |
| NVIDIA GPU Operator | 25.10.1(기본값) 또는 26.3.1 | 데이터센터 드라이버 580.105.8 또는 580.126.20, vGPU(NVAIE) 드라이버 580.105.8 |
| Data Services Manager (DSM) | 9.1.1 | PostgreSQL 18.4, 17.10, 16.14, 15.18, 14.23 지원. PostgreSQL 12와 13은 9.1.1에서 제거 |
| PostgreSQL / pgvector (PAIS 검증 조합) | 16.8 / 0.8.0 | PAIS Data Indexing이 검증한 조합. 2.1과 동일 |

> **이 표가 문서 전체 버전 기준의 단일 출처입니다.** 각 문서는 개별 버전을 반복 표기하지 않고 이 표를 참조합니다. 모든 수치와 버전은 작성 시점(2026-06) Broadcom 공식 릴리스 노트 기준이고, 2026-09에 VCF 9.1.1 / PAIF 9.1.1 / PAIS 3.0 GA(2026-09-03) 내용을 반영했습니다. 적용 전 [공식 문서](#참고-자료)로 재확인하시기 바랍니다.
>
> **9.0.x에서 업그레이드하시는 경우.** 엔진과 운영 컴포넌트 버전이 대폭 상향됐습니다. 변경 요약과 마이그레이션 체크리스트는 [00](docs/00-whats-new.md)을 먼저 보시기 바랍니다.
>
> **9.1 / PAIS 2.1을 운영 중이라면.** 9.1.1 / PAIS 3.0에서 무엇이 바뀌었는지는 [00의 0.7절](docs/00-whats-new.md#07-911--pais-30-변경-2026-09-03-ga)에, 기능이 어느 버전에서 추가됐는지는 [00의 0.8절 버전별 기능 이력](docs/00-whats-new.md#08-버전별-기능-이력-pais-2089--21--30)에 정리했습니다. 2.1 기준으로 작성된 2026-06 시점 문서 전체는 태그 [`baseline-pais-2.1`](https://github.com/JaeHoYun/vcf-private-ai/tree/baseline-pais-2.1)에서 읽을 수 있습니다.

## 주요 용어

| 용어 | 설명 |
|------|------|
| **VCF** | VMware Cloud Foundation — 통합 프라이빗 클라우드 플랫폼 |
| **PAIF** | Private AI Foundation with NVIDIA — VCF가 제공하는 AI 플랫폼(솔루션). **PAIF 코어 기능 계층 + PAIS 서비스 계층**으로 구성되며 VCF 코어 구독에 포함(NVAIE만 별도) |
| **PAIS** | Private AI Services — Model Runtime, RAG, Agent Builder 등 관리형 AI 서비스 레이어 |
| **DLVM** | Deep Learning VM — GPU 장착 개발/실험용 VM |
| **(GPU-Accelerated) Workload Domain** | PAIS를 설치하는 GPU 가속 VCF 워크로드 도메인. Broadcom 공식 표기는 **GPU-Accelerated Workload Domain**이며, 본 문서는 가독성을 위해 **PAIF Workload Domain**으로 약칭합니다 ([TechDocs](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/design/design-library/private-ai-platform-detailed-design/private-ai-services.html)) |
| **VKS** | vSphere Kubernetes Service — vSphere 네이티브 K8s |
| **MCP** | Model Context Protocol — 에이전트가 외부 데이터와 도구를 표준 인터페이스로 연동하는 프로토콜 (PAIS 2.1 신규) |
| **Artifact Mirroring Tool** | 에어갭 환경 구동용 아티팩트 미러링 도구 (PAIS 2.1 신규) |
| **NVAIE** | NVIDIA AI Enterprise — vGPU 드라이버, NIM, NeMo 등을 포함하며 **NVIDIA에서 별도 구매** |

## 라이선스

이 문서는 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)으로 제공됩니다. 자유롭게 활용하시되 아래와 같이 출처를 표기해 주세요. 라이선스 전문은 [LICENSE](../LICENSE) 파일에 있습니다.

출처: https://github.com/JaeHoYun/vcf-private-ai/tree/main/01-infra

## 피드백

오류 발견, 개선 제안, 질문은 [Issues](https://github.com/JaeHoYun/vcf-private-ai/issues)에 남겨주세요.

---

## 면책 조항

**비공식 문서.** 작성자가 공개 자료를 바탕으로 정리한 비공식 문서이며, Broadcom, NVIDIA 등 특정 벤더의 공식 입장을 대변하지 않습니다.

**정확성과 최신성.** 본문의 버전, 수치, 구성값, 절차는 작성 시점 기준의 예시이며 제품 릴리스와 조직 환경에 따라 달라집니다. 성능과 비용 수치는 출처의 발표 조건을 따른 값입니다. 적용 전 공식 문서와 자체 환경에서 검증하시기 바랍니다.

**책임 한계.** 이 문서를 참고해 발생한 직접, 간접 손해는 작성자가 책임지지 않습니다. 기술 지원이 필요하면 각 벤더의 공식 지원 채널을 이용하시기 바랍니다.

**상표권 고지.** VMware, VMware Cloud Foundation 등은 Broadcom의 상표이고 NVIDIA, CUDA 등은 NVIDIA Corporation의 상표입니다. 기타 언급된 제품명과 회사명은 각 소유자의 상표입니다.

**이 가이드의 유의사항.** 본문에 인용한 서버 비용과 TCO 절감률은 Broadcom 발표 기준이며, 실제 효과는 워크로드와 환경별 검증이 필요합니다.

## 참고 자료

- [VMware Cloud Foundation 9.1 Release Notes (Broadcom TechDocs)](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/release-notes/vmware-cloud-foundation-9-1-0-0-release-notes.html)
- [VMware Cloud Foundation 9.1.1.0 Release Notes (Broadcom TechDocs)](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/release-notes/vmware-cloud-foundation-9-1-1-0-release-notes.html)
- [VMware Private AI Foundation with NVIDIA 9.1 (Broadcom TechDocs)](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1.html)
- [VMware Private AI Foundation with NVIDIA 9.1 / 9.1.1 Release Notes](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1/private-ai-release-notes/vmware-private-ai-foundation-with-nvidia-91-release-notes.html)
- [VMware Private AI Services Release Notes (3.0, 2.1.2, 2.1)](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1/private-ai-release-notes/vmware-private-ai-services-release-notes.html)
- [VMware Deep Learning VM Image Release Notes (9.1, 9.1.1)](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1/private-ai-release-notes/vmware-deep-learning-vm-image-release-notes.html)
- [Announcing VCF 9.1 (VMware Cloud Foundation Blog)](https://blogs.vmware.com/cloud-foundation/2026/05/05/announcing-vcf-9-1-modern-private-cloud-built-for-efficiency-and-resilience/)
- [Broadcom Announces VCF 9.1 — Production AI (Broadcom News)](https://news.broadcom.com/releases/broadcom-announces-vmware-cloud-foundation-9-1)

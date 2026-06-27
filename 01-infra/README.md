# VCF 9.1 Private AI Foundation 가이드

> **이 가이드를 읽기 전에** — 임베딩·벡터·토큰·RAG·쿠버네티스(VKS) 같은 용어가 낯설다면, 먼저 [VCF Private AI 입문 (Primer)](../00-foundations/README.md)에서 기초 어휘를 잡으시길 권합니다. 이 가이드는 그 개념들을 이미 아는 것으로 전제합니다.

VMware Cloud Foundation(VCF) 9.1 기반 Private AI 인프라의 **구축·개발·운영**을 위한 실무 참조 가이드입니다.
인프라팀이 AI 플랫폼을 깔고, 데이터 사이언티스트·MLOps가 모델과 RAG를 올리고, 앱 개발자가 API로 서비스를 만드는 전체 여정을 한 권으로 다룹니다.

> **VCF Private AI 가이드 시리즈 — ① 인프라·운영** · 7부작 중 한 편입니다. [전체 7개 보기 — 시리즈 허브](../README.md) · 상위 전략 [AX 방법론](https://github.com/JaeHoYun/enterprise-ax-methodology)

---

## 기반 버전 (Source of Truth)

> **이 표가 문서 전체의 버전 기준이 되는 단일 출처입니다.** 각 문서는 개별 버전을 반복 표기하지 않고 이 표를 참조합니다.
> 모든 수치·버전은 작성 시점(2026-06) Broadcom 공식 릴리스 노트 기준이며, 적용 전 [공식 문서](#참고-자료)로 재확인하시기 바랍니다.

| 구분 | 버전 | 비고 |
|------|------|------|
| **VMware Cloud Foundation** | **9.1** | GA 2026년 5월 |
| **Private AI Foundation with NVIDIA (PAIF)** | **9.1** | VCF 코어 구독 포함 (NVAIE만 별도) |
| **Private AI Services (PAIS)** | **2.1** | UI 셀프서비스, MCP, Artifact Mirroring Tool(에어갭) 추가 |
| Deep Learning VM(DLVM) 이미지 | VCF 9.1 호환 이미지 | Miniforge3 24.3.0, 신규 Ubuntu/ML 스택 |
| vLLM (Completion/Embedding) | **0.11.2** | completions + embeddings 지원 |
| Infinity (Embedding) | **0.0.76** | embeddings 전용 |
| llama.cpp (CPU 추론) | **b7739** | completions + embeddings, CPU 추론 |
| VKr (vSphere Kubernetes release) | **1.33** | ClusterClass `builtin-generic-v3.2.0` |
| VKS (vSphere Kubernetes Service) | **3.5.0+** 권장 | — |
| NVIDIA GPU Operator | **25.10.1** (기본값) | GPU 드라이버 v580.x 계열 |
| PostgreSQL / pgvector | 16.8 / 0.8.0 | DSM(Data Services Manager) 제공 벡터 DB |

> **9.0.x에서 올라오신 경우**: 엔진·운영 컴포넌트 버전이 대폭 상향됐습니다. 변경 요약과 마이그레이션 체크리스트는 [00](docs/00-whats-new.md)을 먼저 보시기 바랍니다.

---

## 목차

| 문서 | 제목 | 주요 내용 |
|------|------|----------|
| 00 | **[What's New (9.1)](docs/00-whats-new.md)** | VCF/PAIF 9.1 신규 기능, 버전 매트릭스 변경, 9.0.x→9.1 마이그레이션 |
| 01 | [핵심 개념 및 페르소나](docs/01-concepts.md) | PAIF/PAIS/DLVM 개념, 라이선스 구조, 역할 정의 |
| 02 | [아키텍처 및 구축 순서](docs/02-architecture.md) | 계층 구조, GPU(DirectPath/vGPU/Blackwell/DRA), Phase별 구축 |
| 03 | [역할별 워크플로우](docs/03-workflows.md) | AI 플레이그라운드, 모델 준비, RAG 구성, PAIS UI, 데이터 소스 |
| 04 | [개발 시나리오 및 AI 앱 개발](docs/04-dev-scenarios.md) | PAIS 사용 패턴(라이프사이클·소비 깊이·상황 축), AI 앱 4-Tier, API 연동, 배포 |
| 05 | **[에이전트·MCP·거버넌스](docs/05-agents-mcp.md)** | Agent Builder, Model Context Protocol, Tool-calling, LLM 트레이싱 |
| 06 | [프로덕션 아키텍처](docs/06-production.md) | HA/DR, 멀티테넌트, 스케일링, 워크로드 사이징, 모델 라이프사이클, 보안, AI 관측성, 에어갭(Artifact Mirroring Tool) |
| 07 | **[GPUaaS (PAIF GPU 자원 서비스)](docs/07-gpuaas.md)** | 책임 경계 2티어, VM+K8s 셀프서비스, GPU 분할 매트릭스, 쇼백·차지백, 셀프서비스/공유풀 시나리오 |
| 08 | **[한국 산업군 적용 시나리오](docs/08-industry.md)** | 제조·방산·유통·콘텐츠 PAIF 시나리오, 에어갭·Blackwell·MCP 연계 |
| 09 | **[구축 시나리오](docs/09-deployment-scenarios.md)** | 신규(그린필드)·기존 환경에 얹기(브라운필드)·전환(마이그레이션) 구축 출발 상황별 절차 골격·선결요건·리스크 |
| 10 | **[Day-2 운영](docs/10-operations.md)** | 구축 이후 운영 — 업그레이드(LCM)·트러블슈팅·백업복구·인증서 회전·SLO/알람·온콜·네트워크·스토리지 Day-2 런북 + 운영자 독자 트랙(상황별 라우터) |
| 11 | **[GPU Enablement 핸즈온](docs/11-gpu-enablement.md)** (딥다이브) | 시리즈 표준보다 깊은 핸즈온 트랙 — BIOS 전제→하이퍼바이저 인식→할당 모드 4종→버전 인터락→GPU Operator→PAIS 소비 수직 경로, known-good 스냅샷, PoC 검증 경로, 자주 막히는 함정(CDI·vGPU 라이선스) |
| A1 | [FAQ·버전 매트릭스·용어집](appendix/A1-appendix.md) | 자주 묻는 질문, 호환성, 용어, 참고 링크, CHANGELOG |
| 워크시트 | [채워넣기 워크시트](worksheet/README.md) | 09 구축 시나리오 결정·현황 파악·SoW 정의, 10 Day-2 점검·업그레이드·복구·SLO 기록용 채워넣기 양식(계산용 xlsx 아님) |

## 빠른 시작

- **"9.0에서 뭐가 바뀌었나요?"** → [00](docs/00-whats-new.md)
- **"PAIF가 뭔가요?"** → [01](docs/01-concepts.md)
- **"아키텍처/구축 순서가 궁금해요"** → [02](docs/02-architecture.md)
- **"개발자로서 뭘 할 수 있나요?"** → [03](docs/03-workflows.md) + [04](docs/04-dev-scenarios.md)
- **"에이전트/MCP로 외부 도구를 붙이고 싶어요"** → [05](docs/05-agents-mcp.md)
- **"프로덕션 운영/에어갭은?"** → [06](docs/06-production.md)
- **"GPU를 사내·계열사에 서비스로 제공하고 싶어요(GPUaaS)"** → [07](docs/07-gpuaas.md)
- **"우리 산업(제조/방산/유통/콘텐츠)에는?"** → [08](docs/08-industry.md)
- **"새로 / 기존 환경에 / 경쟁사에서 옮기며 구축하려면?"** → [09](docs/09-deployment-scenarios.md)
- **"알람·백업·업그레이드·트러블슈팅을 맡았어요(운영자)"** → [10 §10.6 운영자 독자 트랙](docs/10-operations.md#106-운영자-독자-트랙)
- **"구축한 다음 운영·업그레이드는?"** → [10](docs/10-operations.md)
- **"GPU를 실제로 물려보는데 자꾸 막혀요(PoC 엔지니어)"** → [11 GPU Enablement 핸즈온](docs/11-gpu-enablement.md) (딥다이브)
- **"특정 질문이 있어요"** → [A1](appendix/A1-appendix.md) FAQ
- **"채워넣을 워크시트가 필요해요(구축 결정·SoW·운영 점검)"** → [worksheet/](worksheet/README.md)

## 주요 용어

| 용어 | 설명 |
|------|------|
| **VCF** | VMware Cloud Foundation — 통합 프라이빗 클라우드 플랫폼 |
| **PAIF** | Private AI Foundation with NVIDIA — VCF가 제공하는 AI 플랫폼(솔루션). **PAIF 코어 기능 계층 + PAIS 서비스 계층**으로 구성되며 VCF 코어 구독에 포함(NVAIE만 별도) |
| **PAIS** | Private AI Services — Model Runtime, RAG, Agent Builder 등 관리형 AI 서비스 레이어 |
| **DLVM** | Deep Learning VM — GPU 장착 개발/실험용 VM |
| **(GPU-Accelerated) Workload Domain** | PAIS를 설치하는 GPU 가속 VCF 워크로드 도메인. Broadcom 공식 표기는 **GPU-Accelerated Workload Domain**이며, 본 문서는 가독성을 위해 **PAIF Workload Domain**으로 약칭합니다 ([TechDocs](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/design/design-library/private-ai-platform-detailed-design/private-ai-services.html)) |
| **VKS** | vSphere Kubernetes Service — vSphere 네이티브 K8s |
| **MCP** | Model Context Protocol — 에이전트가 외부 데이터·도구를 표준 인터페이스로 연동하는 프로토콜 (PAIS 2.1 신규) |
| **Artifact Mirroring Tool** | 에어갭 환경 구동용 아티팩트 미러링 도구 (PAIS 2.1 신규) |
| **NVAIE** | NVIDIA AI Enterprise — vGPU 드라이버·NIM·NeMo 등을 포함하며 **NVIDIA에서 별도 구매** |

## 라이선스

이 문서는 자유롭게 활용하실 수 있습니다. **출처 표기**를 부탁드립니다.

```
출처: https://github.com/JaeHoYun/vcf-private-ai/tree/main/01-infra
```

## 업데이트 이력

- **v4.10 (2026-06):** 워크시트 09 전면 개편 — 문서 09의 그대로 옮겨 쓰는 체크리스트에서 **현황 파악 → 갭·선결요건 → SoW(작업기술서) 정의** 도구로 재설계. 시나리오별 자기완결 블록(G 그린필드·B 브라운필드·M 마이그레이션) 각각에 풀 SoW 골격(범위 In/Out·산출물·WBS·전제/의존성·RACI·마일스톤·인수기준·리스크/롤백) 수록, WBS를 시나리오별 절차 골격(02 §2.6 / 편입 Convert·Import / 09 §9.4 5단계)에 매핑. 관련 상위 README·worksheet README·docs 09 명칭·설명을 일치시킴.
- **v4.9 (2026-06):** 자립성 패턴 이식 — 문서 09·10 도입부에 선수지식 표 추가, 채워넣기 워크시트 신설(worksheet/: 09 구축 시나리오 결정·선결요건, 10 Day-2 점검·업그레이드·복구·SLO 기록), A1.3 용어집에 구축·운영 용어(그린필드·브라운필드·마이그레이션·Workload Mobility·LCM·SDDC Manager·SLI/SLO·TTFT·Trust Bundle·vSAN Effective Capacity·Adaptive Resync 등) 추가, 빠른 시작에 운영자 진입로(§10.6)·워크시트 노출.
- **v4.8 (2026-06):** 문서 10에 §10.5 네트워크·스토리지 Day-2 운영 추가 — NSX Edge·로드밸런서·Network Policy·GPU 패브릭 네트워크 운영과 vSAN(Effective Capacity·Automatic Rebalance·resync)·AI 자산 store(Harbor·pgvector/DSM) 스토리지 운영. 기존 운영자 독자 트랙은 §10.5 → §10.6으로 이동. 구성·설계는 문서 02·09, 용량 산정은 ⑥로 경계를 명시.
- **v4.7 (2026-06):** 문서 10에 §10.5 운영자 독자 트랙 추가 — 상황별 라우터(무슨 일이 생기면 어디로), 운영자 정기 점검 리듬(일·주·월·분기), 운영 책임 경계. 문서 10 Day-2 운영 1차 범위 마감(09 구축 시나리오 + 10 Day-2 운영으로 ① 인프라 운영 라이프사이클 골격 완비).
- **v4.6 (2026-06):** 문서 10에 §10.4 SLO·알람·온콜 추가 — 06.8 관측 대시보드를 운영 액션으로 연결(SLI/SLO 정의, VCF Operations Alert/Symptom/Notification 기반 알람, 온콜·에스컬레이션). AI 지표(TTFT·토큰 처리량·GPU 사용률) 기반.
- **v4.5 (2026-06):** 문서 10에 §10.3 백업·복구와 인증서·시크릿 회전 추가 — 플랫폼 구성(SDDC Manager·vCenter·NSX) 파일 기반 백업, 복구 훈련, VCF 9 자동 인증서 갱신(Fleet Management CA)·수동 교체·PAIS Trust Bundle/시크릿 회전.
- **v4.4 (2026-06):** 문서 10에 §10.2 트러블슈팅 런북 추가 — 02.9 알려진 이슈를 증상→진단→조치로 승격(GPU/ModelRuntime의 `CDI device injection failed`·vGPU Unlicensed, 모델 엔드포인트, 관측성, DLVM). 진단 기본 흐름·계층별 1차 확인 포함.
- **v4.3 (2026-06):** 문서 10 Day-2 운영 신설 — 플랫폼 업그레이드·패치(LCM) 런북: VCF 코어(SDDC Manager → NSX → vCenter → ESX → vSAN) → 관리 서비스 → Kubernetes → GPU → PAIS 업그레이드 순서, 사전 점검, 다운타임(PAIS 2.0→2.1 VKS 재생성)·롤백·검증. 트러블슈팅·백업복구·인증서·SLO·운영자 트랙은 후속 보강 예정.
- **v4.2 (2026-06):** 문서 09 구축 시나리오 신설 — 신규(그린필드)·기존 환경에 얹기(브라운필드: VCF Import/Convert + GPU 워크로드 도메인 추가)·전환(마이그레이션: VCF Operations Workload Mobility) 3가지 구축 출발 상황별 절차 골격·선결요건·리스크. 업그레이드는 Day-2 운영 영역으로 분리하고 본 문서에선 선결요건으로 참조만.
- **v4.1 (2026-06):** 문서 07 GPUaaS(PAIF GPU 자원 서비스) 신설 — 책임 경계 2티어, VM+K8s 셀프서비스, GPU 분할 매트릭스, 쇼백·차지백, 사내 셀프서비스/계열사 공유 풀 시나리오. 기존 산업(→문서 08)·부록(→문서 09) 리넘버링.
- **v4.0 (2026-06):** VCF 9.1 / PAIF 9.1 / PAIS 2.1 전면 반영. 문서 구조 재설계(문서 00 What's New, 문서 05 에이전트·MCP, 문서 08 산업 시나리오 신설), 버전 기준 단일 출처 표 도입, 라이선스·용어 정정, 엔진 버전 매트릭스 갱신.
- 이전 이력(v3.x, 9.0.1 기반)은 [A1 CHANGELOG](appendix/A1-appendix.md) 참조.

## 피드백

오류 발견, 개선 제안, 질문은 [Issues](https://github.com/JaeHoYun/vcf-private-ai/issues)에 남겨주세요.

---

## 면책 조항 (Disclaimer)

**비공식 문서** — 이 가이드는 VCF/PAIF 공식 기술 문서를 기반으로 작성된 비공식 실무 가이드입니다. Broadcom, NVIDIA 또는 기타 벤더의 공식 입장을 대변하지 않습니다.

**정확성 및 최신성** — 본 문서의 내용은 작성 시점(2026년 6월) 기준이며, 제품 업데이트에 따라 달라질 수 있습니다. 정확성을 위해 노력하였으나 오류나 누락이 있을 수 있습니다. 프로덕션 적용 전 반드시 공식 문서를 확인하시기 바랍니다. 특히 본문에 인용된 성능·비용 수치(예: 서버비용·TCO 절감률)는 Broadcom 발표 기준이며 실제 효과는 워크로드·환경별 검증이 필요합니다.

**책임 한계** — 본 문서를 참고하여 발생한 직접적·간접적 손해에 대해 작성자는 책임을 지지 않습니다. 실제 구축·운영은 각 조직의 요구사항과 환경에 맞게 검토 후 진행하시기 바랍니다. 기술 지원이 필요한 경우 Broadcom 공식 지원 채널을 이용하시기 바랍니다.

**상표권 고지** — VMware, VMware Cloud Foundation, vSphere, vSAN, NSX, VCF Automation, VCF Operations, Private AI Foundation 등은 Broadcom의 등록 상표입니다. NVIDIA, CUDA, NIM, NeMo, Blackwell 등은 NVIDIA Corporation의 등록 상표입니다. 기타 언급된 제품명 및 회사명은 각 소유자의 상표 또는 등록 상표입니다.

## 참고 자료

- [VMware Cloud Foundation 9.1 Release Notes (Broadcom TechDocs)](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/release-notes/vmware-cloud-foundation-9-1-0-0-release-notes.html)
- [VMware Private AI Foundation with NVIDIA 9.1 (Broadcom TechDocs)](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1.html)
- [Announcing VCF 9.1 (VMware Cloud Foundation Blog)](https://blogs.vmware.com/cloud-foundation/2026/05/05/announcing-vcf-9-1-modern-private-cloud-built-for-efficiency-and-resilience/)
- [Broadcom Announces VCF 9.1 — Production AI (Broadcom News)](https://news.broadcom.com/releases/broadcom-announces-vmware-cloud-foundation-9-1)

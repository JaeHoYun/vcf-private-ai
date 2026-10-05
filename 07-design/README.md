# VCF 9.1 Private AI 통합 설계 가이드

> **이 가이드를 읽기 전에** — 임베딩, 벡터, 토큰, RAG, 쿠버네티스(VKS) 같은 용어가 낯설다면, 먼저 [VCF Private AI 입문 (Primer)](../00-foundations/README.md)에서 기초 어휘를 익히시길 권합니다. 이 가이드는 그 개념들을 이미 아는 것으로 전제합니다.

> VMware Cloud Foundation(VCF) 9.1 기반 Private AI 플랫폼을 **요구사항에서 출발해 하나의 일관된 설계로 종합**하는 통합 설계편 — 설계 프로세스, 레퍼런스 블루프린트, 설계 결정 기록

[① 인프라](../01-infra/README.md), [② VectorDB](../02-vectordb/README.md), [③ 서빙 API](../03-serving-api/README.md), [④ RAG](../04-rag/README.md), [⑤ 보안과 거버넌스](../05-security/README.md), [⑥ 사이징과 비용](../06-sizing-cost/README.md)은 각 계층의 설계를 **부분적으로** 제시합니다. 여섯 편을 다 읽고 나면 마지막 질문이 남습니다 — **"그래서 이 결정들을 어떻게 하나의 플랫폼 설계로 종합하나?"** 이 가이드가 그 답입니다.

본 문서는 새 컴포넌트를 소개하지 않습니다. ①–⑥에 흩어진 설계 결정을 **요구사항 → 블루프린트 → 트레이드오프** 관점에서 한곳에 모으고, 누락된 연결을 채우며, 세부 스펙은 각 가이드로 링크합니다.

> **VCF Private AI 가이드 시리즈 — ⑦ 통합 설계**, 7부작 중 한 편입니다. [전체 7개 보기 — 시리즈 허브](../README.md), 상위 전략 [AX 방법론](https://github.com/JaeHoYun/enterprise-ax-methodology)

---

## 목차

| 구분 | 번호 | 문서 | 주요 내용 |
|------|------|------|-----------|
| 본문 | 01 | [설계 프로세스와 요구사항 수집](docs/01-design-process.md) | 요구사항과 제약 입력(워크로드, SLO, 규제, 예산), 설계 결정 순서 |
| | 02 | [레퍼런스 설계 블루프린트](docs/02-reference-blueprints.md) | 소/중/대 규모별(T-shirt sizing) 레퍼런스 설계, 각 구성과 선택 근거 |
| | 03 | [설계 결정: 컴퓨트, GPU, VKS 토폴로지](docs/03-compute-gpu-topology.md) | GPU 배치, VKS/Supervisor 토폴로지, 노드 풀 설계 |
| | 04 | [설계 결정: 네트워크, 스토리지, 가용성](docs/04-network-storage-availability.md) | NSX 설계, vSAN 스토리지 정책, 가용성과 DR |
| | 05 | [설계 결정: 멀티테넌시와 보안 설계](docs/05-tenancy-security.md) | 테넌트 격리 모델, security by design (⑤ 위임) |
| | 06 | [설계 결정 카탈로그](docs/06-decision-forks.md) | 16개 설계 결정 색인, 요구와 제약→설계 결정 매핑, 설계 결정 기록 템플릿 |
| | 07 | [설계 리뷰 체크리스트와 검증 관문](docs/07-design-review.md) | 설계 리뷰 항목, 단계별 검증 관문 |
| | 08 | [브라운필드 통합 설계](docs/08-brownfield-integration.md) | 기존 온프렘 AI, MLOps의 PAIF 점진 통합, 퍼블릭 클라우드 처리 |
| | 09 | [역할과 책임 (RACI)](docs/09-roles-raci.md) | AI 플랫폼 수명주기 단계별 역할표(인프라/플랫폼/앱/보안/데이터) |
| 부록 | A1 | [부록](appendix/A1-reference.md) | 용어집, 참조 링크 |
| | 워크시트 | [채워넣기 워크시트](worksheet/README.md) | 결정 요인 시트 + 설계 결정 기록(D1–D16) + 브라운필드용 AI 자산 인벤토리와 6R 처분 매트릭스 채워넣기 양식 |

## 이 가이드의 관점 — 조립이 아니라 설계

④가 "한 워크로드(사내 Q&A RAG)를 어떻게 **조립**하나"를 다룬다면, 이 가이드는 그보다 넓은 범위 — **플랫폼 전체를 어떤 요구사항으로, 어떤 결정과 트레이드오프로 설계하나**를 다룹니다.

- **요구사항이 먼저다** — 워크로드 프로파일, SLO, 규제, 예산을 입력으로 설계 결정의 순서를 정합니다.
- **블루프린트로 빠르게** — 소/중/대 레퍼런스 설계를 출발점으로 제시하고, 각 선택의 근거를 함께 제시합니다.
- **결정을 추적한다** — ①–⑥에 흩어진 설계 결정을 대안과 트레이드오프와 함께 설계 결정 기록으로 한곳에 모읍니다.

## 기반 버전

| 구분 | 버전 | 비고 |
|------|------|------|
| VMware Cloud Foundation (VCF) | 9.1.1 | 9.1 GA 2026-05, 9.1.1 GA 2026-09 |
| Private AI Foundation with NVIDIA (PAIF) | 9.1.1 | VCF 코어 구독 포함(NVAIE만 별도) |
| Private AI Services (PAIS) | 3.0 | Agent Builder, Model Runtime, MCP, Artifact Mirroring Tool. 3.0에서 공유 모델 호스팅과 원격 클라우드 모델이 설계 선택지로 추가 |
| PostgreSQL / pgvector (PAIS 검증 조합) | 16.8 / 0.8.0 | DSM 9.1.1 기준(②) |

> 본 가이드는 **설계 의사결정**에 집중하며, 엔진과 컴포넌트 버전은 단정하지 않고 형제 가이드의 버전 단일 기준 문서를 기준선으로 삼습니다 → [① README 버전표](../01-infra/README.md#기반-버전). 모든 수치는 작성 시점(2026-06) 기준이고 2026-09에 VCF 9.1.1 / PAIS 3.0을 반영했으며, 적용 전 공식 문서로 재확인하시기 바랍니다.

## 라이선스

이 문서는 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)으로 제공됩니다. 자유롭게 활용하시되 아래와 같이 출처를 표기해 주세요. 라이선스 전문은 [LICENSE](../LICENSE) 파일에 있습니다.

출처: https://github.com/JaeHoYun/vcf-private-ai/tree/main/07-design

## 면책 조항

**비공식 문서.** 작성자가 공개 자료를 바탕으로 정리한 비공식 문서이며, Broadcom, NVIDIA 등 특정 벤더의 공식 입장을 대변하지 않습니다.

**정확성과 최신성.** 본문의 버전, 수치, 구성값, 절차는 작성 시점 기준의 예시이며 제품 릴리스와 조직 환경에 따라 달라집니다. 성능과 비용 수치는 출처의 발표 조건을 따른 값입니다. 적용 전 공식 문서와 자체 환경에서 검증하시기 바랍니다.

**책임 한계.** 이 문서를 참고해 발생한 직접, 간접 손해는 작성자가 책임지지 않습니다. 기술 지원이 필요하면 각 벤더의 공식 지원 채널을 이용하시기 바랍니다.

**상표권 고지.** VMware, VMware Cloud Foundation 등은 Broadcom의 상표이고 NVIDIA, CUDA 등은 NVIDIA Corporation의 상표입니다. 기타 언급된 제품명과 회사명은 각 소유자의 상표입니다.

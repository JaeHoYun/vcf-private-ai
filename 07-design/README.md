# VCF 9.1 Private AI 통합 설계 가이드

> **이 가이드를 읽기 전에** — 임베딩·벡터·토큰·RAG·쿠버네티스(VKS) 같은 용어가 낯설다면, 먼저 [VCF Private AI 입문 (Primer)](../00-foundations/README.md)에서 기초 어휘를 잡으시길 권합니다. 이 가이드는 그 개념들을 이미 아는 것으로 전제합니다.

> VMware Cloud Foundation(VCF) 9.1 기반 Private AI 플랫폼을 **요구사항에서 출발해 하나의 일관된 설계로 종합**하는 통합 설계편 — 설계 프로세스 · 레퍼런스 블루프린트 · 설계 결정 기록

[① 인프라](../01-infra/README.md) · [② VectorDB](../02-vectordb/README.md) · [③ 서빙 API](../03-serving-api/README.md) · [④ RAG](../04-rag/README.md) · [⑤ 보안·거버넌스](../05-security/README.md) · [⑥ 사이징·비용](../06-sizing-cost/README.md)은 각 계층의 설계를 **부분적으로** 제시합니다. 여섯 편을 다 읽고 나면 마지막 질문이 남습니다 — **"그래서 이 결정들을 어떻게 하나의 플랫폼 설계로 종합하나?"** 이 가이드가 그 답입니다.

본 문서는 새 컴포넌트를 소개하지 않습니다. ①~⑥에 흩어진 설계 결정을 **요구사항 → 블루프린트 → 트레이드오프** 관점에서 한곳에 모으고, 빠진 연결을 채우며, 세부 스펙은 각 가이드로 링크합니다.

> **VCF Private AI 가이드 시리즈 — ⑦ 통합 설계** · 7부작 중 한 편입니다. [전체 7개 보기 — 시리즈 허브](../README.md) · 상위 전략 [AX 방법론](https://github.com/JaeHoYun/enterprise-ax-methodology)

---

## 기반 버전 (Source of Truth)

> 본 가이드는 **설계 의사결정**에 집중하며, 엔진·컴포넌트 버전은 단정하지 않고 형제 가이드의 버전 단일 기준 문서를 기준선으로 삼습니다 → [① README 버전표](../01-infra/README.md#기반-버전-source-of-truth). 모든 수치는 작성 시점(2026-06) 기준이며 적용 전 공식 문서로 재확인하시기 바랍니다.

| 구분 | 버전 | 비고 |
|------|------|------|
| VMware Cloud Foundation / PAIF | 9.1 | GA 2026-05 |
| Private AI Services (PAIS) | 2.1 | Agent Builder, Model Runtime, MCP, Artifact Mirroring Tool |
| PostgreSQL / pgvector (DSM 9.1) | 16.8 / 0.8.0 | PAIS 검증 조합 (②) |

## 이 가이드의 관점 — 조립이 아니라 설계

④가 "한 워크로드(사내 Q&A RAG)를 어떻게 **조립**하나"를 다룬다면, 이 가이드는 한 단계 위 — **플랫폼 전체를 어떤 요구사항으로, 어떤 결정과 트레이드오프로 설계하나**를 다룹니다.

- **요구사항이 먼저다** — 워크로드 프로파일·SLO·규제·예산을 입력으로 설계 결정의 순서를 정합니다.
- **블루프린트로 빠르게** — 소/중/대 레퍼런스 설계를 출발점으로 제시하고, 각 선택의 근거를 답니다.
- **결정을 추적한다** — ①~⑥에 흩어진 설계 결정을 대안·트레이드오프와 함께 설계 결정 기록(아키텍처 의사결정 기록, ADR)으로 한곳에 모읍니다.

## 문서 구성

| 순서 | 문서 | 내용 |
|------|------|------|
| 01 | [설계 프로세스와 요구사항 수집](docs/01-design-process.md) | 요구사항·제약 입력(워크로드·SLO·규제·예산), 설계 결정 순서 |
| 02 | [레퍼런스 설계 블루프린트](docs/02-reference-blueprints.md) | 소/중/대 규모별(T-shirt sizing) 레퍼런스 설계, 각 구성과 선택 근거 |
| 03 | [설계 결정: 컴퓨트·GPU·VKS 토폴로지](docs/03-compute-gpu-topology.md) | GPU 배치, VKS/Supervisor 토폴로지, 노드 풀 설계 |
| 04 | [설계 결정: 네트워크·스토리지·가용성](docs/04-network-storage-availability.md) | NSX 설계, vSAN 스토리지 정책, 가용성·DR |
| 05 | [설계 결정: 멀티테넌시·보안 설계](docs/05-tenancy-security.md) | 테넌트 격리 모델, security by design (⑤ 위임) |
| 06 | [설계 결정 카탈로그](docs/06-decision-forks.md) | 12개 설계 결정 색인, 결정 요인→설계 결정 매핑, 설계 결정 기록(ADR) 템플릿 |
| 07 | [설계 리뷰 체크리스트와 검증 관문](docs/07-design-review.md) | 설계 리뷰 항목, 단계별 검증 관문 |
| 08 | [브라운필드 통합 설계](docs/08-brownfield-integration.md) | 기존 온프렘 AI·MLOps의 PAIF 점진 통합, 퍼블릭 클라우드 처리 |
| 09 | [역할과 책임 (RACI)](docs/09-roles-raci.md) | AI 플랫폼 수명주기 단계별 역할표(인프라/플랫폼/앱/보안/데이터) |
| A1 | [부록](appendix/A1-reference.md) | 용어집, 참조 링크, 변경 이력 |
| 워크시트 | [채워넣기 워크시트](worksheet/README.md) | 결정 요인 시트 + 설계 결정 기록(D1–D12) 채워넣기 양식 |

## 빠른 시작

- **"어디서 시작하나"** → [01 설계 프로세스](docs/01-design-process.md)
- **"빠른 출발점이 필요하다"** → [02 레퍼런스 블루프린트](docs/02-reference-blueprints.md)
- **"설계 결정을 한자리에서 보고 결정·기록한다"** → [06 설계 결정 카탈로그](docs/06-decision-forks.md) + [07 설계 리뷰](docs/07-design-review.md)
- **"이미 온프렘 AI·MLOps가 있고 점진적으로 옮긴다"** → [08 브라운필드 통합 설계](docs/08-brownfield-integration.md)
- **"전사 확장(멀티테넌트) 설계를 본다"** → [02 §2.5 전사 확장 블루프린트](docs/02-reference-blueprints.md) · [05 §5.1.1 멀티테넌트 기반 설계](docs/05-tenancy-security.md)
- **"누가 무엇을 책임지나"** → [09 역할과 책임 (RACI)](docs/09-roles-raci.md)
- **"설계 결정을 직접 적는다"** → [채워넣기 워크시트](worksheet/README.md) (결정 요인 시트 → 설계 결정 기록)

## 라이선스

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). 자유롭게 활용하시되 출처를 표기해 주세요. `출처: https://github.com/JaeHoYun/vcf-private-ai/tree/main/07-design`

## 면책

**비공식 문서** — Broadcom·NVIDIA 등 벤더의 공식 입장을 대변하지 않습니다. 본문의 설계 수치·구성값은 **예시**이며 워크로드·환경별 검증이 필요합니다. 적용 전 반드시 공식 문서로 확인하시기 바랍니다. 언급된 제품명·상표는 각 소유자의 자산입니다.

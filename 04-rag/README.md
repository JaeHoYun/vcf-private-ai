# VCF 9.1 Private AI 엔드투엔드 RAG 레퍼런스 아키텍처

> **이 가이드를 읽기 전에** — 임베딩·벡터·토큰·RAG·쿠버네티스(VKS) 같은 용어가 낯설다면, 먼저 [VCF Private AI 입문 (Primer)](../00-foundations/README.md)에서 기초 어휘를 잡으시길 권합니다. 이 가이드는 그 개념들을 이미 아는 것으로 전제합니다.

> VMware Cloud Foundation(VCF) 9.1 위에서 **사내 문서 Q&A RAG 시스템**을 인입·인덱싱부터 검색·추론·앱 통합·운영까지 하나로 꿰는 통합 레퍼런스

[① 인프라](../01-infra/README.md)는 플랫폼을 깔고, [② VectorDB](../02-vectordb/README.md)는 데이터 계층을 올리고, [③ 서빙 API](../03-serving-api/README.md)는 모델을 API로 제공합니다. 세 가이드를 다 읽고 나면 마지막 질문이 남습니다 — **"그래서 이 조각들을 어떻게 하나의 동작하는 RAG로 조립하나?"** 이 가이드가 그 답입니다.

본 문서는 새 컴포넌트를 소개하지 않습니다. ②③에서 만든 것을 **조립·흐름·의사결정** 관점에서 연결하며, 세부 스펙은 해당 가이드로 링크합니다.

> **VCF Private AI 가이드 시리즈 — ④ 통합(RAG)** · 7부작 중 한 편입니다. [전체 7개 보기 — 시리즈 허브](../README.md) · 상위 전략 [AX 방법론](https://github.com/JaeHoYun/enterprise-ax-methodology)

---

## 기반 버전 (기준 문서)

> 본 가이드는 **통합 흐름**에 집중하며, 엔진·컴포넌트 버전은 단정하지 않고 형제 가이드의 버전 기준 문서를 기준선으로 삼습니다 → [① README 버전표](../01-infra/README.md#기반-버전-source-of-truth). 모든 수치는 작성 시점(2026-06) 기준이며 적용 전 공식 문서로 재확인하시기 바랍니다.

| 구분 | 버전 | 비고 |
|------|------|------|
| VMware Cloud Foundation / PAIF | 9.1 | GA 2026-05 |
| Private AI Services (PAIS) | 2.1 | Agent Builder, Data Indexing(RAG), MCP Tools Registry |
| PostgreSQL / pgvector (DSM 9.1, Data Services Manager) | 16.8 / 0.8.0 | PAIS 검증 조합 (②) |

## 레퍼런스 시나리오

본 가이드는 하나의 관통 예제를 사용합니다.

> **"사내 정책·기술 문서 수천 건을 학습한 Q&A 봇"** — 직원이 자연어로 질문하면, 사내 문서에서 근거를 찾아 출처와 함께 답한다. 데이터는 사내를 벗어나지 않는다.

이 시나리오를 ②(pgvector)와 ③(서빙 API)으로 조립하는 과정을 문서 01–07이 단계별로 따라갑니다. (※ 시나리오는 가상의 일반 엔터프라이즈를 가정하며 특정 기업과 무관합니다.)

## 문서 구성

**준비(인덱싱) → 검색(검색·조립) → 생성(추론) → 소비(앱) → 검증(평가) → 운영**으로 이어지는 RAG 생애주기 순서입니다.

| 순서 | 문서 | 내용 |
|------|------|------|
| 01 | [레퍼런스 아키텍처 전경](docs/01-reference-architecture.md) | 전체 데이터 흐름, 컴포넌트 매핑, 직접 구축 vs 구매(Agent Builder) 결정 |
| 02 | [데이터 인입·인덱싱](docs/02-ingestion-indexing.md) | 문서 로딩, 청킹 전략, 임베딩, pgvector 적재 |
| 03 | [검색·컨텍스트 조립](docs/03-retrieval-context.md) | 유사도/하이브리드 검색, 리랭킹, 컨텍스트 윈도우 관리 |
| 04 | [추론 통합](docs/04-inference-integration.md) | Agent vs Model Endpoint, RAG 호출 흐름, 스트리밍, 인용 |
| 05 | [앱 통합 패턴](docs/05-app-integration.md) | 4-Tier 구조, base_url 스위치, 인증, 멀티턴 세션 |
| 06 | [평가·품질](docs/06-evaluation-quality.md) | RAG 평가 지표, 환각·근거율, 회귀 테스트, 관측성 |
| 07 | [프로덕션 운영](docs/07-production-operations.md) | 스케일링, 멀티테넌트, 캐시, 사이징, 에어갭(폐쇄망) 환경 배포(Artifact Mirroring Tool, Artifact Mirroring Tool) |
| A1 | [부록](appendix/A1-reference.md) | FAQ, 용어, 체크리스트, 참고 링크 |

## 빠른 시작

- **"전체 그림부터"** → [01 레퍼런스 아키텍처](docs/01-reference-architecture.md)
- **"노코드로 빨리"** → [01의 Agent Builder 결정](docs/01-reference-architecture.md#14-빌드-vs-바이--두-가지-조립-방식) (직접 구축 vs 구매) + [04](docs/04-inference-integration.md)
- **"검색 품질이 안 나온다"** → [03 검색·조립](docs/03-retrieval-context.md) + [06 평가](docs/06-evaluation-quality.md)

## 라이선스

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). 자유롭게 활용하시되 출처를 표기해 주세요. `출처: https://github.com/JaeHoYun/vcf-private-ai/tree/main/04-rag`

## 면책

**비공식 문서** — Broadcom·NVIDIA 등 벤더의 공식 입장을 대변하지 않습니다. 본문의 API 경로·파라미터·인덱스 설정값은 **예시**이며 릴리스마다 변동되므로, 적용 직전 [PAIS 공식 API 레퍼런스](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/)와 공식 문서로 확인하시기 바랍니다. 언급된 제품명·상표는 각 소유자의 자산입니다.

# VCF 9.1 Private AI 엔드투엔드 RAG 레퍼런스 아키텍처

> **이 가이드를 읽기 전에** — 임베딩, 벡터, 토큰, RAG, 쿠버네티스(VKS) 같은 용어가 낯설다면, 먼저 [VCF Private AI 입문 (Primer)](../00-foundations/README.md)에서 기초 어휘를 익히시길 권합니다. 이 가이드는 그 개념들을 이미 아는 것으로 전제합니다.

> VMware Cloud Foundation(VCF) 9.1에서 **사내 문서 Q&A RAG 시스템**을 인입, 인덱싱부터 검색, 추론, 앱 통합, 운영까지 하나로 연결하는 통합 레퍼런스

[① 인프라](../01-infra/README.md)는 플랫폼을 구축하고, [② VectorDB](../02-vectordb/README.md)는 데이터 계층을 배포하고, [③ 서빙 API](../03-serving-api/README.md)는 모델을 API로 제공합니다. 세 가이드를 다 읽고 나면 마지막 질문이 남습니다 — **"그래서 이 조각들을 어떻게 하나의 동작하는 RAG로 조립하나?"** 이 가이드가 그 답입니다.

본 문서는 새 컴포넌트를 소개하지 않습니다. ②③에서 만든 것을 **조립, 흐름, 의사결정** 관점에서 연결하며, 세부 스펙은 해당 가이드로 링크합니다.

> **VCF Private AI 가이드 시리즈 — ④ 통합(RAG)**, 7부작 중 한 편입니다. [전체 7개 보기 — 시리즈 허브](../README.md), 상위 전략 [AX 방법론](https://github.com/JaeHoYun/enterprise-ax-methodology)

---

## 목차

| 구분 | 번호 | 문서 | 주요 내용 |
|------|------|------|-----------|
| 본문 | 01 | [레퍼런스 아키텍처 전경](docs/01-reference-architecture.md) | 전체 데이터 흐름, 컴포넌트 매핑, 직접 구축 vs 구매(Agent Builder) 결정 |
| | 02 | [데이터 인입과 인덱싱](docs/02-ingestion-indexing.md) | 문서 로딩, 청킹 전략, 임베딩, pgvector 적재 |
| | 03 | [검색과 컨텍스트 조립](docs/03-retrieval-context.md) | 유사도/하이브리드 검색, 리랭킹, 컨텍스트 윈도우 관리 |
| | 04 | [추론 통합](docs/04-inference-integration.md) | Agent vs Model Endpoint, RAG 호출 흐름, 스트리밍, 인용 |
| | 05 | [앱 통합 패턴](docs/05-app-integration.md) | 4-Tier 구조, base_url 스위치, 인증, 멀티턴 세션 |
| | 06 | [평가와 품질](docs/06-evaluation-quality.md) | RAG 평가 지표, 환각과 근거율, 회귀 테스트, 관측성 |
| | 07 | [프로덕션 운영](docs/07-production-operations.md) | 스케일링, 멀티테넌트, 캐시, 사이징, 에어갭(폐쇄망) 환경 배포(Artifact Mirroring Tool, 아티팩트 미러링 도구) |
| 부록 | A1 | [부록](appendix/A1-reference.md) | FAQ, 용어, 체크리스트, 참고 링크 |

> **준비(인덱싱) → 검색(검색과 조립) → 생성(추론) → 소비(앱) → 검증(평가) → 운영**으로 이어지는 RAG 생애주기 순서입니다.

## 기반 버전

| 구분 | 버전 | 비고 |
|------|------|------|
| VMware Cloud Foundation (VCF) | 9.1.1 | 9.1 GA 2026-05, 9.1.1 GA 2026-09 |
| Private AI Foundation with NVIDIA (PAIF) | 9.1.1 | VCF 코어 구독 포함(NVAIE만 별도) |
| Private AI Services (PAIS) | 3.0 | Agent Builder, Data Indexing(RAG), MCP Tools Registry. 3.0에서 지식베이스 복제, 인용 노드 ID, 원격 임베딩 모델 추가 |
| PostgreSQL / pgvector (PAIS 검증 조합) | 16.8 / 0.8.0 | DSM 9.1.1 기준(②) |

> 본 가이드는 **통합 흐름**에 집중하며, 엔진과 컴포넌트 버전은 단정하지 않고 형제 가이드의 버전 단일 기준 문서를 기준선으로 삼습니다 → [① README 버전표](../01-infra/README.md#기반-버전). 모든 수치는 작성 시점(2026-06) 기준이고 2026-09에 VCF 9.1.1 / PAIS 3.0을 반영했으며, 적용 전 공식 문서로 재확인하시기 바랍니다.

## 레퍼런스 시나리오

본 가이드는 하나의 관통 예제를 사용합니다.

> **"사내 정책과 기술 문서 수천 건을 학습한 Q&A 봇"** — 직원이 자연어로 질문하면, 사내 문서에서 근거를 찾아 출처와 함께 답한다. 데이터는 사내 밖으로 반출되지 않는다.

이 시나리오를 ②(pgvector)와 ③(서빙 API)으로 조립하는 과정을 문서 01–07이 단계별로 따라갑니다. (※ 시나리오는 가상의 일반 엔터프라이즈를 가정하며 특정 기업과 무관합니다.)

## 라이선스

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). 자유롭게 활용하시되 출처를 표기해 주세요. `출처: https://github.com/JaeHoYun/vcf-private-ai/tree/main/04-rag`

## 면책 조항

**비공식 문서.** 작성자가 공개 자료를 바탕으로 정리한 비공식 문서이며, Broadcom, NVIDIA 등 특정 벤더의 공식 입장을 대변하지 않습니다.

**정확성과 최신성.** 본문의 버전, 수치, 구성값, 절차는 작성 시점 기준의 예시이며 제품 릴리스와 조직 환경에 따라 달라집니다. 성능과 비용 수치는 출처의 발표 조건을 따른 값입니다. 적용 전 공식 문서와 자체 환경에서 검증하시기 바랍니다.

**책임 한계.** 이 문서를 참고해 발생한 직접, 간접 손해는 작성자가 책임지지 않습니다. 기술 지원이 필요하면 각 벤더의 공식 지원 채널을 이용하시기 바랍니다.

**상표권 고지.** VMware, VMware Cloud Foundation 등은 Broadcom의 상표이고 NVIDIA, CUDA 등은 NVIDIA Corporation의 상표입니다. 기타 언급된 제품명과 회사명은 각 소유자의 상표입니다.

**이 가이드의 유의사항.** 본문의 API 경로, 파라미터, 인덱스 설정값은 예시이며 릴리스마다 바뀝니다. 적용 직전 [PAIS 공식 API 레퍼런스](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/)로 확인하시기 바랍니다.

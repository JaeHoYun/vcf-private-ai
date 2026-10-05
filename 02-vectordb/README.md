# Private AI를 위한 엔터프라이즈 vectorDB 가이드

> **이 가이드를 읽기 전에** — 임베딩, 벡터, 토큰, RAG, 쿠버네티스(VKS) 같은 용어가 낯설다면, 먼저 [VCF Private AI 입문 (Primer)](../00-foundations/README.md)에서 기초 어휘를 익히시길 권합니다. 이 가이드는 그 개념들을 이미 아는 것으로 전제합니다.

> PostgreSQL + pgvector. 상용 벡터 DB 추가 도입 없이 VCF 인프라에서 AI 워크로드를 배포, 사용, 관리하기 위한 실무 가이드

VCF에서 Private AI Foundation을 운영 중이라면 DSM(Data Services Manager)에 기본 포함된 PostgreSQL + pgvector를 즉시 활용할 수 있습니다. Pinecone, Milvus 같은 전용 벡터 DB를 별도로 도입하지 않아도 RAG, 의미 검색, 추천 시스템을 바로 구현할 수 있습니다.

이 가이드는 Vector DB 기초 개념부터 VCF DSM 아키텍처, 실제 배포 절차, 운영(Day-2) 런북, 도입 시나리오까지 생애주기 순서로 정리한 기술 레퍼런스입니다.

기준 버전: VCF 9.1.1 / DSM 9.1.1 / PAIF 9.1.1 / PAIS 3.0 (2026-09 반영, 상세는 [01 버전 호환 매트릭스](docs/01-version-compatibility.md))

> **VCF Private AI 가이드 시리즈 — ② 데이터(VectorDB)**, 7부작 중 한 편입니다. [전체 7개 보기 — 시리즈 허브](../README.md), 상위 전략 [AX 방법론](https://github.com/JaeHoYun/enterprise-ax-methodology)

---

## 목차

| 구분 | 번호 | 문서 | 주요 내용 |
|------|------|------|-----------|
| 본문 | 01 | [버전 호환 매트릭스](docs/01-version-compatibility.md) | VCF / DSM / PAIS / PostgreSQL / pgvector 버전 호환 기준 |
| | 02 | [Vector Database & pgvector 기초](docs/02-vectordb-pgvector-basics.md) | Vector DB 기초 개념, pgvector 심층 분석(아키텍처, 인덱스, 성능, 튜닝) |
| | 03 | [VCF DSM 아키텍처](docs/03-vcf-dsm-architecture.md) | 왜 VCF DSM인가, DSM 아키텍처, Private AI Services(PAIS) 통합 |
| | 04 | [배포 (Day-0 / Day-1)](docs/04-deployment.md) | Day-0/1 배포. 선행조건, DSM 프로비저닝, HA 구성, PAIS 연결, 사이징 |
| | 05 | [사용 및 RAG 구성 (Day-1 / Day-2)](docs/05-usage-rag.md) | Day-1/2 사용. pgvector 사용법, RAG 파이프라인 구성 |
| | 06 | [운영 (Day-2)](docs/06-operations.md) | Day-2 운영. 모니터링, 백업, 스케일, 트러블슈팅, 유지보수, 보안 |
| | 07 | [산업 도입 시나리오](docs/07-scenarios.md) | 금융/유통/제조 산업 도입 시나리오 |
| | 08 | [PoC 가이드](docs/08-poc-guide.md) | 4주 PoC 가이드 및 성공 기준 |
| 부록 | A1 | [Vector Database 경쟁 비교](appendix/A1-vectordb-comparison.md) | 전용/확장형 벡터 DB 10종 경쟁 비교 |

> 버전 기준을 먼저 확인한 뒤 배포-사용-관리 생애주기 순서로 구성됩니다. 경쟁 비교는 부록에 있습니다.

---

## 주요 내용

- Vector Embedding, 근사 최근접 이웃(ANN, Approximate Nearest Neighbor) 검색, HNSW/IVFFlat 인덱스의 동작 원리
- pgvector 0.8.x 핵심 기능: Iterative Index Scan, halfvec, sparsevec
- VCF DSM 9.1.x 기반 PostgreSQL + pgvector HA 클러스터 아키텍처
- DSM 프로비저닝부터 HA, 백업/PITR, 스케일까지 Day-0/1/2 절차
- VMware Private AI Services(PAIS)와 pgvector의 RAG 파이프라인 통합
- 모니터링, 트러블슈팅, 재임베딩, 보안 하드닝, 폐쇄망(Artifact Mirroring Tool) 운영
- 금융 규정 검색, 유통 상품 추천, 제조 기술 문서 검색 시나리오
- 4주 PoC 로드맵 및 성공 기준

---

## 관련 가이드

- [VCF Private AI Foundation 실무 가이드](../01-infra/README.md). VCF 9.1 기반 Private AI Foundation with NVIDIA 구축 가이드

---

## 기반 버전

| 구분 | 버전 | 비고 |
|------|------|------|
| VMware Cloud Foundation (VCF) | 9.1.1 | 9.1 GA 2026-05, 9.1.1 GA 2026-09 |
| Private AI Foundation with NVIDIA (PAIF) | 9.1.1 | VCF 코어 구독 포함(NVAIE만 별도) |
| Private AI Services (PAIS) | 3.0 | 2026-09 GA. 2.1은 2026-05 GA |
| Data Services Manager (DSM) | 9.1.1 | 2026-09 GA. 9.1은 2026-05 GA |
| PostgreSQL (DSM 9.1.1) | 18.4, 17.10, 16.14, 15.18, 14.23 | 12와 13은 9.1.1에서 제거 |
| pgvector | 0.8.0 (DSM 9.1 번들, 9.1.1 번들은 릴리스 노트 미기재) / 0.8.2 커뮤니티 | 0.8.2는 CVE-2026-3172 수정 |
| PostgreSQL / pgvector (PAIS 검증 조합) | 16.8 / 0.8.0 | 공식 문서 기준 조합이며 도입 환경에서 검증 권장 |

> 도입 전 반드시 확인하는 정보입니다. 상세는 [01 버전 호환 매트릭스](docs/01-version-compatibility.md)를 참조하시기 바랍니다.

## 라이선스

이 문서는 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)으로 제공됩니다. 자유롭게 활용하시되 아래와 같이 출처를 표기해 주세요. 라이선스 전문은 [LICENSE](../LICENSE) 파일에 있습니다.

출처: https://github.com/JaeHoYun/vcf-private-ai/tree/main/02-vectordb

## 피드백

오류 발견, 개선 제안, 질문은 [Issues](https://github.com/JaeHoYun/vcf-private-ai/issues)에 남겨주세요.

---

## 면책 조항

**비공식 문서.** 작성자가 공개 자료를 바탕으로 정리한 비공식 문서이며, Broadcom, NVIDIA 등 특정 벤더의 공식 입장을 대변하지 않습니다.

**정확성과 최신성.** 본문의 버전, 수치, 구성값, 절차는 작성 시점 기준의 예시이며 제품 릴리스와 조직 환경에 따라 달라집니다. 성능과 비용 수치는 출처의 발표 조건을 따른 값입니다. 적용 전 공식 문서와 자체 환경에서 검증하시기 바랍니다.

**책임 한계.** 이 문서를 참고해 발생한 직접, 간접 손해는 작성자가 책임지지 않습니다. 기술 지원이 필요하면 각 벤더의 공식 지원 채널을 이용하시기 바랍니다.

**상표권 고지.** VMware, VMware Cloud Foundation 등은 Broadcom의 상표이고 NVIDIA, CUDA 등은 NVIDIA Corporation의 상표입니다. 기타 언급된 제품명과 회사명은 각 소유자의 상표입니다.

**이 가이드의 유의사항.** 인용한 벤치마크는 각 출처의 테스트 환경과 조건에서 측정한 결과입니다. 프로덕션 도입 전 자체 워크로드로 테스트하시기 바랍니다. PostgreSQL은 PostgreSQL Global Development Group의 상표입니다.

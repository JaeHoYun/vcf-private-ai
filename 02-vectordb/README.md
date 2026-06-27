# Private AI를 위한 엔터프라이즈 vectorDB 가이드

> **이 가이드를 읽기 전에** — 임베딩·벡터·토큰·RAG·쿠버네티스(VKS) 같은 용어가 낯설다면, 먼저 [VCF Private AI 입문 (Primer)](../00-foundations/README.md)에서 기초 어휘를 잡으시길 권합니다. 이 가이드는 그 개념들을 이미 아는 것으로 전제합니다.

> PostgreSQL + pgvector. 상용 벡터 DB 추가 도입 없이 VCF 인프라에서 AI 워크로드를 배포·사용·관리하기 위한 실무 가이드

VCF에서 Private AI Foundation을 운영 중이라면 DSM(Data Services Manager)에 기본 포함된 PostgreSQL + pgvector를 즉시 활용할 수 있습니다. Pinecone, Milvus 같은 전용 벡터 DB를 별도로 도입하지 않아도 RAG, 의미 검색, 추천 시스템을 바로 구현할 수 있습니다.

이 가이드는 Vector DB 기초 개념부터 VCF DSM 아키텍처, 실제 배포 절차, 운영(Day-2) 런북, 도입 시나리오까지 생애주기 순서로 정리한 기술 레퍼런스입니다.

기준 버전: VCF 9.1 / DSM 9.1 / PAIF 9.1 / PAIS 2.1

> **VCF Private AI 가이드 시리즈 — ② 데이터(VectorDB)** · 7부작 중 한 편입니다. [전체 7개 보기 — 시리즈 허브](../README.md) · 상위 전략 [AX 방법론](https://github.com/JaeHoYun/enterprise-ax-methodology)

### 핵심 버전 호환 요약

도입 전 반드시 확인하는 정보입니다. 상세는 [docs/01-version-compatibility.md](docs/01-version-compatibility.md) 참조.

| 컴포넌트 | 기준 | 비고 |
|---|---|---|
| VCF / DSM / PAIF / PAIS | 9.1 / 9.1 / 9.1 / 2.1 | 2026-05 GA |
| PostgreSQL (DSM 9.1) | 17.7 – 12.22 | 12/13은 9.1.0이 지원 마지막 |
| pgvector | 0.8.0 번들 / 0.8.2 커뮤니티 | 0.8.2는 CVE-2026-3172 수정 |
| PAIS 연동 검증 | PostgreSQL 16.8 + pgvector 0.8.0 | 공식 문서 기준 조합이며 도입 환경에서 검증 권장 |

---

## 문서 구성

버전 기준을 먼저 확인한 뒤 배포-사용-관리 생애주기 순서로 구성됩니다. 경쟁 비교는 부록에 있습니다.

| 순서 | 문서 | 내용 |
|---|---|---|
| 01 | [버전 호환 매트릭스](docs/01-version-compatibility.md) | VCF / DSM / PAIS / PostgreSQL / pgvector 버전 호환 기준 |
| 02 | [Vector Database & pgvector 기초](docs/02-vectordb-pgvector-basics.md) | Vector DB 기초 개념, pgvector 심층 분석(아키텍처, 인덱스, 성능, 튜닝) |
| 03 | [VCF DSM 아키텍처](docs/03-vcf-dsm-architecture.md) | 왜 VCF DSM인가, DSM 아키텍처, Private AI Services(PAIS) 통합 |
| 04 | [배포 (Day-0 / Day-1)](docs/04-deployment.md) | Day-0/1 배포. 선행조건, DSM 프로비저닝, HA 구성, PAIS 연결, 사이징 |
| 05 | [사용 및 RAG 구성 (Day-1 / Day-2)](docs/05-usage-rag.md) | Day-1/2 사용. pgvector 사용법, RAG 파이프라인 구성 |
| 06 | [운영 (Day-2)](docs/06-operations.md) | Day-2 운영. 모니터링, 백업, 스케일, 트러블슈팅, 유지보수, 보안 |
| 07 | [산업 도입 시나리오](docs/07-scenarios.md) | 금융/유통/제조 산업 도입 시나리오 |
| 08 | [PoC 가이드](docs/08-poc-guide.md) | 4주 PoC 가이드 및 성공 기준 |

부록

| 문서 | 내용 |
|---|---|
| [Vector Database 경쟁 비교](appendix/A1-vectordb-comparison.md) | 전용/확장형 벡터 DB 10종 경쟁 비교 |

---

## 독자별 권장 경로

역할에 따라 읽는 순서를 다르게 잡으면 효율적입니다.

- VI Admin(인프라 관리자): 01 호환 to 03 아키텍처 to 04 배포 to 06 운영
- DBA(데이터베이스 관리자): 01 호환 to 02 기초 to 04 배포 to 06 운영 to 05 사용
- 개발자/데이터 사이언티스트: 02 기초 to 05 사용 to 08 PoC
- 의사결정자(CxO): 03 아키텍처 to 07 시나리오 to 08 PoC

---

## 주요 내용

- Vector Embedding, 근사 최근접 이웃(ANN, Approximate Nearest Neighbor) 검색, HNSW/IVFFlat 인덱스의 동작 원리
- pgvector 0.8.x 핵심 기능: Iterative Index Scan, halfvec, sparsevec
- VCF DSM 9.1 기반 PostgreSQL + pgvector HA 클러스터 아키텍처
- DSM 프로비저닝부터 HA, 백업/PITR, 스케일까지 Day-0/1/2 절차
- VMware Private AI Services(PAIS) 2.1과 pgvector의 RAG 파이프라인 통합
- 모니터링, 트러블슈팅, 재임베딩, 보안 하드닝, 폐쇄망(Artifact Mirroring Tool) 운영
- 금융 규정 검색, 유통 상품 추천, 제조 기술 문서 검색 시나리오
- 4주 PoC 로드맵 및 성공 기준

---

## 관련 가이드

- [VCF Private AI Foundation 실무 가이드](../01-infra/README.md). VCF 9.1 기반 Private AI Foundation with NVIDIA 구축 가이드

---

## 라이선스

이 문서는 자유롭게 활용하실 수 있습니다. 출처 표기를 부탁드립니다.

```
출처: https://github.com/JaeHoYun/vcf-private-ai/tree/main/02-vectordb
```

## 피드백

오류 발견, 개선 제안, 질문은 [Issues](https://github.com/JaeHoYun/vcf-private-ai/issues)에 남겨주세요.

---

## 면책 조항 (Disclaimer)

개인적으로 작성한 비공식 문서이며 특정 벤더의 공식 입장을 대변하지 않습니다. 모든 사양/라이선스는 공식 자료로 확인하시기 바랍니다.

비공식 문서: 공개된 기술 문서, 블로그, 릴리스 노트를 기반으로 작성한 비공식 기술 레퍼런스입니다. Broadcom, VMware, NVIDIA 또는 기타 벤더의 공식 입장을 대변하지 않습니다.

정확성 및 최신성: 작성 시점(2026년 6월) 기준이며, 제품 업데이트에 따라 내용이 달라질 수 있습니다. 가격, 기능, 성능 수치는 시점에 따라 변동되므로 공식 문서를 함께 확인하시기 바랍니다.

벤치마크: 인용된 벤치마크는 각 출처의 테스트 환경과 조건에 따른 결과이며, 실제 워크로드에서의 성능은 다를 수 있습니다. 프로덕션 도입 전 자체 워크로드 기반 테스트를 권장합니다.

상표권 고지: VMware, VMware Cloud Foundation, vSphere, vSAN, NSX, VCF Automation, VCF Operations, Data Services Manager, Private AI Services 등은 Broadcom의 등록 상표입니다. NVIDIA, CUDA, NIM 등은 NVIDIA Corporation의 등록 상표입니다. PostgreSQL은 PostgreSQL Global Development Group의 상표입니다. 기타 언급된 제품명 및 회사명은 각 소유자의 상표 또는 등록 상표입니다.

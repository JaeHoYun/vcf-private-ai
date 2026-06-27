# 01 — 버전 호환 매트릭스

> VCF / DSM / PAIS / PostgreSQL / pgvector 조합 기준표

기준 시점: 2026년 6월. 버전 정보는 변동되므로 도입 전 공식 릴리스 노트를 반드시 재확인하시기 바랍니다.

---

## 1.1 스택 버전 기준선

| 컴포넌트 | 기준 버전 | GA 시점 | 비고 |
|---|---|---|---|
| VMware Cloud Foundation (VCF) | 9.1 | 2026-05 | API-First 통합, vCenter Quick Patch, VCF Management Services |
| Data Services Manager (DSM) | 9.1 | 2026-05 | SQL Server 정식 GA, Brownfield Onboarding, 전 엔진 셀프서비스 |
| Private AI Foundation (PAIF) | 9.1 | 2026-05 | Blackwell GPU 지원, DirectPath GPU |
| Private AI Services (PAIS) | 2.1 | 2026-05 | UI 셀프서비스, 폐쇄망(Artifact Mirroring Tool) 지원 |

---

## 1.2 DSM 9.1 지원 데이터베이스 엔진

| 엔진 | 지원 버전 | 비고 |
|---|---|---|
| PostgreSQL | 17.7, 16.11, 15.15, 14.20, 13.23, 12.22 | pgvector 확장 내장. **9.1.0은 PostgreSQL 12/13 지원 마지막 릴리스**(다음 maintenance 릴리스에서 제거 예정) |
| MySQL | 8.4.6, 8.0.43, 8.0.42, 8.0.41, 8.0.40 | Fast Cloning(vSAN ESA 필요) |
| Microsoft SQL Server | 2022.CU22 | **9.1에서 정식 GA**. Always On Availability Groups, 자동 백업/PITR(Point-In-Time Recovery, 특정 시점 복구), AD(Active Directory) 통합 |

출처: VMware Data Services Manager 9.1 Release Notes.

---

## 1.3 pgvector 버전 기준

| 구분 | 버전 | 비고 |
|---|---|---|
| DSM 9.1 번들 | 0.8.0 | VMware Postgres 17.7 기준. Iterative Index Scan 등 0.8.0 핵심 기능 사용 가능 |
| 커뮤니티 최신 | 0.8.2 | **CVE-2026-3172 수정**(병렬 HNSW 인덱스 빌드 buffer overflow, 데이터 유출/크래시 가능). 가능 시 업그레이드 권장 |

병렬 인덱스 빌드(`max_parallel_maintenance_workers` 사용)를 적용하는 환경은 CVE-2026-3172 영향 경로에 해당합니다. DSM 번들 pgvector의 패치 적용 시점을 확인하시기 바랍니다.

출처: pgvector CHANGELOG, PostgreSQL.org pgvector 0.8.2 릴리스 공지.

---

## 1.4 PAIS 연동 시 핵심 주의 (버전 불일치 가능성)

PAIS의 Data Indexing & Retrieval 모듈은 pgvector 확장이 설치된 외부 PostgreSQL에 연결하여 임베딩을 저장·검색합니다. 이때 DSM이 프로비저닝하는 PostgreSQL 버전과 PAIS가 검증한 조합이 다를 수 있으므로 분리해서 확인해야 합니다.

| 사용 경로 | 권장 조합 | 비고 |
|---|---|---|
| DSM 단독 프로비저닝(벡터 검색만) | PostgreSQL 17.7 + pgvector 0.8.0 | DSM 9.1 최신 번들 |
| PAIS Data Indexing & Retrieval 연동 | PostgreSQL 16.8 + pgvector 0.8.0 | PAIS 검증 조합으로 알려짐. 연동 전 PAIS 릴리스 노트로 재확인 필수 |

PAIS 검증 조합 수치는 공개 자료 기반이며, 실제 연동 전 PAIF 9.1 / PAIS 2.1 릴리스 노트의 지원 매트릭스를 직접 확인하시기 바랍니다.

---

## 1.5 외부 라이선스 의존

| 항목 | 포함 관계 | 확보 방법 |
|---|---|---|
| DSM (벡터 DB 프로비저닝) | VCF 구독에 Add-on 구독 | Broadcom |
| PAIS 소프트웨어 컴포넌트 | VCF 9.x 구독 포함 | 추가 비용 없음 |
| NVIDIA AI Enterprise | VCF 외부 의존 | NVIDIA에서 별도 구매(GPU 모델 추론/임베딩 시) |
| GPU 하드웨어 | 별도 확보 | NVIDIA Blackwell(B200, RTX PRO 6000/4500) 등 |

DSM의 포함 관계는 환경에 따라 다를 수 있어 공식 자료와 구독/라이선스 조건으로 재확인하시기 바랍니다.

---

## 출처

| 자료 | URL |
|---|---|
| VCF 9.1 Release Notes | https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/release-notes/vmware-cloud-foundation-9-1-0-0-release-notes.html |
| DSM 9.1 Release Notes | https://techdocs.broadcom.com/us/en/vmware-cis/dsm/data-services-manager/9-1/release-notes/vmware-data-services-manager-91-release-notes.html |
| DSM 9.1 소개 (VCF Blog) | https://blogs.vmware.com/cloud-foundation/2026/05/05/vmware-data-services-manager-9-1-automating-the-modern-databases-that-drive-ai-and-private-cloud/ |
| VCF 9.1 AI 워크로드 (VCF Blog) | https://blogs.vmware.com/cloud-foundation/2026/05/05/streamline-simplify-and-protect-all-your-ai-workloads-with-vcf-9-1/ |
| pgvector 0.8.2 릴리스 (CVE-2026-3172) | https://www.postgresql.org/about/news/pgvector-082-released-3245/ |
| pgvector CHANGELOG | https://github.com/pgvector/pgvector/blob/master/CHANGELOG.md |

---
[목차](../README.md) · [다음: 02 Vector Database & pgvector 기초 →](02-vectordb-pgvector-basics.md)

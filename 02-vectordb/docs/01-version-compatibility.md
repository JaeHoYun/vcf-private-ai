# 01 — 버전 호환 매트릭스

> VCF / DSM / PAIS / PostgreSQL / pgvector 조합 기준표

기준 시점: 2026년 6월, VCF 9.1.1 / DSM 9.1.1 / PAIS 3.0 반영 2026년 9월. 버전 정보는 변동되므로 도입 전 공식 릴리스 노트를 반드시 재확인하시기 바랍니다.

---

## 1.1 스택 버전 기준선

| 컴포넌트 | 기준 버전 | GA 시점 | 비고 |
|---|---|---|---|
| VMware Cloud Foundation (VCF) | 9.1.1 | 2026-09 (9.1은 2026-05) | 9.1.1은 BOM 갱신 중심의 유지보수 릴리스. 9.1 라인의 API-First 통합, vCenter Quick Patch, VCF Management Services 유지 |
| Data Services Manager (DSM) | 9.1.1 | 2026-09 (9.1은 2026-05) | PostgreSQL 18 지원, 읽기 복제, set_user 확장, SQL Server 2025, VKS 3.7 연동. PostgreSQL 12와 13 제거 |
| Private AI Foundation (PAIF) | 9.1.1 | 2026-09 (9.1은 2026-05) | 9.1.1 변경은 PAIS 3.0 제공과 DLVM 이미지 갱신 |
| Private AI Services (PAIS) | 3.0 | 2026-09 (2.1은 2026-05) | 공유 모델 호스팅, 원격 클라우드 모델, API 토큰, 지식베이스 복제 추가. 2.1의 UI 셀프서비스와 폐쇄망(Artifact Mirroring Tool) 지원 유지 |

9.1 / PAIS 2.1 기준으로 쓰인 2026-06 시점 문서 전체는 태그 [`baseline-pais-2.1`](https://github.com/JaeHoYun/vcf-private-ai/tree/baseline-pais-2.1)에서 읽을 수 있습니다.

---

## 1.2 DSM 9.1.x 지원 데이터베이스 엔진

| 엔진 | 9.1 (2026-05) | 9.1.1 (2026-09) | 비고 |
|---|---|---|---|
| PostgreSQL | 17.7, 16.11, 15.15, 14.20, 13.23, 12.22 | **18.4, 17.10, 16.14, 15.18, 14.23** | pgvector 확장 내장. **9.1.1에서 PostgreSQL 12와 13 제거**. 해당 버전 인스턴스는 DSM 9.1.1 배포 전에 14 이상으로 업그레이드해야 합니다. 9.1.1은 읽기 복제(read replication)와 set_user 확장(안전한 역할 전환)을 추가 |
| MySQL | 8.4.6, 8.0.43, 8.0.42, 8.0.41, 8.0.40 | 8.4.10, 8.4.8, 8.4.6, 8.0.46, 8.0.45, 8.0.43, 8.0.42 | Fast Cloning(vSAN ESA 필요). 9.1.1에서 메이저 버전 업그레이드와 마이너 자동 업그레이드 지원 |
| Microsoft SQL Server | 2022.CU22 | 2022.CU25, 2025.CU6 | **9.1에서 정식 GA**. Always On Availability Groups, 자동 백업/PITR(Point-In-Time Recovery, 특정 시점 복구), AD(Active Directory) 통합. 9.1.1에서 TDE(투명한 데이터 암호화) 활성화 |

DSM 9.1.1 업그레이드 순서 주의: Avi Load Balancer와 NSX 네트워킹을 함께 쓰는 클러스터는 VCF를 9.1.0 이상으로 올리기 전에 DSM을 9.1.1로 먼저 올려야 데이터베이스 다운타임을 피할 수 있습니다(DSM 9.1.1 릴리스 노트 업그레이드 주의 사항). 운영 절차는 [06 운영](06-operations.md)에서 다룹니다.

출처: VMware Data Services Manager 9.1 및 9.1.1 Release Notes.

---

## 1.3 pgvector 버전 기준

| 구분 | 버전 | 비고 |
|---|---|---|
| DSM 9.1 번들 | 0.8.0 | VMware Postgres 17.7 기준. Iterative Index Scan 등 0.8.0 핵심 기능 사용 가능 |
| DSM 9.1.1 번들 | 릴리스 노트 미기재 | 9.1.1 릴리스 노트는 pgvector 버전을 따로 밝히지 않습니다. 배포 후 `SELECT extversion FROM pg_extension WHERE extname = 'vector';`로 직접 확인하십시오 |
| 커뮤니티 최신 | 0.8.2 | **CVE-2026-3172 수정**(병렬 HNSW 인덱스 빌드 buffer overflow, 데이터 유출/크래시 가능). 가능 시 업그레이드 권장 |

병렬 인덱스 빌드(`max_parallel_maintenance_workers` 사용)를 적용하는 환경은 CVE-2026-3172 영향 경로에 해당합니다. DSM 번들 pgvector의 패치 적용 시점을 확인하시기 바랍니다.

출처: pgvector CHANGELOG, PostgreSQL.org pgvector 0.8.2 릴리스 공지.

---

## 1.4 PAIS 연동 시 핵심 주의 (버전 불일치 가능성)

PAIS의 Data Indexing & Retrieval 모듈은 pgvector 확장이 설치된 외부 PostgreSQL에 연결하여 임베딩을 저장하고 검색합니다. 이때 DSM이 프로비저닝하는 PostgreSQL 버전과 PAIS가 검증한 조합이 다를 수 있으므로 분리해서 확인해야 합니다.

| 사용 경로 | 권장 조합 | 비고 |
|---|---|---|
| DSM 단독 프로비저닝(벡터 검색만) | PostgreSQL 17.10 또는 18.4 + pgvector | DSM 9.1.1 번들. PostgreSQL 18은 9.1.1에서 처음 지원되므로 pgvector 호환과 확장 동작을 PoC로 확인한 뒤 채택 |
| PAIS Data Indexing & Retrieval 연동 | PostgreSQL 16.8 + pgvector 0.8.0 | PAIS 3.0 릴리스 노트 기준 검증 조합(2.0.x, 2.1, 3.0 모두 동일). 연동 전 PAIS 릴리스 노트로 재확인 필수 |

PAIS 검증 조합은 PAIS 3.0 릴리스 노트에 명시된 값이며, DSM이 지원하는 최신 PostgreSQL(18.4)과는 다릅니다. PAIS Data Indexing이 붙는 인스턴스는 검증 조합을 유지하고, 별도 벡터 검색 용도의 인스턴스에서만 상위 버전을 검토하시기 바랍니다.

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
| DSM 9.1.1 Release Notes | https://techdocs.broadcom.com/us/en/vmware-cis/dsm/data-services-manager/9-1/release-notes/vmware-data-services-manager-911-release-notes.html |
| VCF 9.1.1.0 Release Notes | https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/release-notes/vmware-cloud-foundation-9-1-1-0-release-notes.html |
| PAIS Release Notes (3.0) | https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1/private-ai-release-notes/vmware-private-ai-services-release-notes.html |
| DSM 9.1 소개 (VCF Blog) | https://blogs.vmware.com/cloud-foundation/2026/05/05/vmware-data-services-manager-9-1-automating-the-modern-databases-that-drive-ai-and-private-cloud/ |
| VCF 9.1 AI 워크로드 (VCF Blog) | https://blogs.vmware.com/cloud-foundation/2026/05/05/streamline-simplify-and-protect-all-your-ai-workloads-with-vcf-9-1/ |
| pgvector 0.8.2 릴리스 (CVE-2026-3172) | https://www.postgresql.org/about/news/pgvector-082-released-3245/ |
| pgvector CHANGELOG | https://github.com/pgvector/pgvector/blob/master/CHANGELOG.md |

---
[목차](../README.md) | [다음: 02 Vector Database & pgvector 기초 →](02-vectordb-pgvector-basics.md)

# 06 — 운영 (Day-2)

> 모니터링, 백업/복구, 스케일, 패치, pgvector 유지보수, 트러블슈팅, 보안

기준 버전: VCF 9.1 / DSM 9.1. DSM이 라이프사이클을 자동화하므로, 본 문서는 DSM 자동화 동작과 pgvector 워크로드 특화 운영을 함께 다룹니다.

---

## 6.1 모니터링

### 통합 모니터링 경로

DSM은 데이터베이스 메트릭을 VCF Operations로 전송하며, Prometheus 엔드포인트로도 메트릭을 내보낼 수 있습니다. 로그는 한 번에 DSM 어플라이언스와 모든 DB의 로그를 SYSLOG 엔드포인트로 전송할 수 있습니다. vSphere Client에서는 DB 인스턴스명, 엔진, 상태, 버전, 노드 수, 가용성, 정책, CPU/메모리/디스크 사용률을 확인합니다.

### 벡터 워크로드 특화 점검 지표

| 지표 | 의미 | 경고 기준(예시) |
|---|---|---|
| 인덱스 메모리 상주 여부 | HNSW 인덱스가 shared_buffers에 상주하는가 | 미상주 시 성능 급락 |
| 버퍼 히트율 | `pg_statio_user_tables` 기반 캐시 적중 | 99% 미만 지속 시 점검 |
| 검색 지연 시간(Latency, p95) | 벡터 쿼리 지연 | 목표 100ms 초과 시 점검 |
| 활성 커넥션 | `pg_stat_activity` 수 | max_connections 근접 시 풀링 점검 |
| Recall 저하 | 검색 품질 지표 | ef_search/인덱스 파라미터 재검토 |
| 인덱스 bloat | 대량 갱신 후 인덱스 팽창 | REINDEX 필요 판단 |

출처: Why choose DSM as your on-premises DBaaS(VCF Blog).

---

## 6.2 백업 및 복구

DSM은 배포 시 자동 백업을 구성합니다. PostgreSQL 기본값은 주 1회 전체 백업, 일 단위 백업, WAL(Write-Ahead Log, 쓰기 전 로그)은 5분 또는 16MB 중 먼저 도달하는 시점마다 전송하며, 모든 DB에 대해 PITR(Point-In-Time Restore)이 제공됩니다.

운영 항목

- PITR: DSM UI에서 특정 시점으로 복구
- Clone: 프로덕션 DB를 개발/테스트로 복제(라이브 데이터 검증)
- Delete Protection: 삭제된 DB는 기본 30일 보관(조정 가능), 복구 가능
- DR: 다른 vSphere 환경/다른 DSM 어플라이언스에 secondary 노드를 두고 replication, 장애 시 secondary를 primary로 승격

벡터 워크로드 주의: 임베딩과 메타데이터가 동일 DB에 있으므로 PITR 복구 시 벡터·관계형 데이터가 동일 시점으로 일관되게 복원됩니다. 별도 벡터 DB 동기화 문제가 없습니다.

출처: Why choose DSM as your on-premises DBaaS(VCF Blog).

---

## 6.3 스케일 및 패치

### 스케일

| 작업 | 방식 |
|---|---|
| Scale Out/In | Standalone(1노드) ↔ Clustered(3노드) 전환 |
| Scale Up/Down | VM Class 변경으로 노드 CPU/메모리 증감 |
| 읽기 분산 | Read Replica 추가(벡터 검색은 읽기 워크로드) |
| 스토리지 확장 | 온라인 디스크 확장 |

피크 대응(명절·세일)에는 일시적으로 Scale Up 후 종료 시 원복하는 방식이 유효합니다.

### 패치/업그레이드

DSM이 어플라이언스, 게스트 OS, Kubernetes, DB 엔진 업데이트를 통합 번들로 제공합니다. DBA는 다운로드·스테이징만 하면 유지보수 윈도(통상 토요일 밤-일요일 아침)에 롤링 적용됩니다. 메이저/마이너 버전 업그레이드 모두 지원되며, 메이저 업그레이드 시 확장(extension) 호환성을 사전 확인합니다.

pgvector 주의: 메이저 업그레이드 전 pgvector 확장 호환성과 인덱스 재구축 필요 여부를 점검합니다.

출처: Why choose DSM as your on-premises DBaaS(VCF Blog).

---

## 6.4 pgvector Day-2 유지보수

### 인덱스 유지보수

- 대량 적재 후: HNSW 인덱스는 실시간 삽입을 지원하나, 대규모 일괄 적재 후에는 빌드 파라미터를 재검토하고 필요 시 재구축
- bloat 관리: 잦은 갱신/삭제 후 인덱스 팽창 시 `REINDEX` 검토. `VACUUM`이 HNSW에 미치는 영향 모니터링
- 빌드 가속: `maintenance_work_mem` 상향, 병렬 빌드 활용(보안 주의 아래 참조)

#### 무중단 재인덱싱: REINDEX vs REINDEX CONCURRENTLY

HNSW 인덱스의 bloat 누적이나 파라미터 변경으로 재구축이 필요할 때, 일반 `REINDEX`는 PostgreSQL이 기본적으로 ACCESS EXCLUSIVE 락을 잡아 재구축이 끝날 때까지 해당 테이블에 대한 쓰기(읽기는 가능)를 차단합니다. 24/7 운영 중인 RAG/검색 서비스에서는 이 쓰기 중단이 그대로 장애로 이어질 수 있습니다. 가용성이 중요한 환경에서는 `REINDEX INDEX CONCURRENTLY idx_docs_embedding;`처럼 `CONCURRENTLY` 옵션을 사용합니다. 이 옵션은 SHARE UPDATE EXCLUSIVE 락만 잡아 재구축 중에도 INSERT/UPDATE/DELETE가 계속됩니다. 다만 비용이 있습니다. 공식 문서에 따르면 `CONCURRENTLY`는 각 인덱스에 대해 테이블을 두 번 스캔하고 해당 인덱스를 사용할 수 있는 기존 트랜잭션의 종료를 기다려야 하므로, 일반 재구축보다 총 작업량이 많고 완료까지 현저히 오래 걸리며, 추가 CPU·메모리·I/O 부하가 다른 작업을 느리게 만들 수 있습니다. 또한 대용량 HNSW 인덱스는 재구축 동안 기존 인덱스와 신규 인덱스가 함께 존재하므로 일시적으로 추가 디스크·메모리 여유가 필요합니다. 따라서 가능하면 유지보수 윈도에 수행하되, 온라인 가용성이 필수면 `CONCURRENTLY`를 선택합니다. 실패 시 INVALID 상태의 인덱스가 남을 수 있으므로 재시도 전 상태를 점검합니다.

출처: [PostgreSQL: REINDEX 문서](https://www.postgresql.org/docs/current/sql-reindex.html)

### 재임베딩 전략 (임베딩 모델 교체 시)

임베딩 모델을 교체하면 기존 벡터와 새 벡터가 동일 공간에 있지 않으므로 전체 재임베딩이 필요합니다.

- 신규 컬럼/테이블에 새 모델로 재임베딩 후 인덱스 생성, 검증 완료 시 전환(블루-그린)
- 차원이 바뀌면 새 `vector(D)` 컬럼 정의 필요
- 재인덱싱은 PAIS(Private AI Services)의 Data Indexing & Retrieval 갱신 정책으로 스케줄링 가능

### 보안 주의: 병렬 HNSW 빌드 취약점

pgvector 0.8.2 미만에서 병렬 HNSW 인덱스 빌드에 buffer overflow 취약점(CVE-2026-3172)이 있어 타 릴레이션 데이터 유출 또는 크래시가 가능합니다. `max_parallel_maintenance_workers`로 병렬 빌드를 사용하는 환경은 DSM 번들 pgvector의 패치 적용 시점을 확인하고, 가능하면 0.8.2 이상을 적용합니다.

출처: pgvector 0.8.2 릴리스(CVE-2026-3172); pgvector CHANGELOG.

---

## 6.5 트러블슈팅 매트릭스

| 증상 | 추정 원인 | 조치 |
|---|---|---|
| 필터 결합 시 결과 수 부족 | 과도한 필터링(overfiltering) | `hnsw.iterative_scan = relaxed_order`, `max_scan_tuples` 상향 |
| recall 저하 | ef_search/m 부족 | `hnsw.ef_search` 상향, 인덱스 m·ef_construction 재검토 |
| 쿼리 지연 급증 | 인덱스 메모리 미상주 | shared_buffers를 인덱스의 110% 이상으로, 노드 Scale Up |
| 인덱스 빌드 지연 | maintenance_work_mem/병렬 부족 | `maintenance_work_mem` 상향, 병렬 워커 증가(CVE 패치 확인) |
| 접속 실패/지연 | 커넥션 고갈 | PgBouncer `pool_mode=transaction`, max_connections 점검 |
| 배포 실패 | Storage Policy 이름 공백 | 공백 없는 정책명 사용 |
| 갱신 후 성능 저하 | 인덱스 bloat | REINDEX, VACUUM 영향 점검 |

---

## 6.6 보안 하드닝

| 영역 | 조치 |
|---|---|
| 접근 제어(네트워크) | NSX 마이크로세그멘테이션으로 RAG to pgvector 트래픽 격리 |
| 접근 제어(DB) | pg_hba.conf를 프로비저닝 시점에 사전 구성, Row-Level Security |
| 인증 | LDAPS 연동(DSM UI 및 DB 접근), GRANT 기반 LDAP 사용자 권한 |
| 암호화 | 저장 시 암호화(VM Crypt 선택 또는 데이터스토어 전체), 전송 SSL/TLS |
| 인증서 | DSM 자체 서명 또는 커스텀 인증서, 생성 시점/배포 후 적용 |
| 감사/알림 | 감사 로그 + 로그 수신기 전송, SMTP·webhook(ServiceNow/Slack) 알림 |

DSM은 pg_hba.conf와 고급 파라미터를 프로비저닝 시점에 설정하므로, DB가 일시적으로 무방비 상태로 노출되는 구간을 줄입니다.

출처: Why choose DSM as your on-premises DBaaS(VCF Blog).

---

## 6.7 폐쇄망(Air-gapped) 운영

PAIS 2.1은 Artifact Mirroring Tool을 통한 폐쇄망 환경을 지원합니다. VI Admin은 폐쇄망 내에서 NVIDIA GPU 기반 모델 엔드포인트와 에이전트를 포함한 Private AI 기능을 설치·운영할 수 있습니다. 방산·금융·공공 등 데이터 반출이 불가한 환경에서 RAG 전체 파이프라인을 외부 연결 없이 구성할 수 있습니다.

운영 시 모델·컨테이너 아티팩트를 Artifact Mirroring Tool로 미러링하고, 갱신 주기에 맞춰 미러를 동기화합니다.

출처: Streamline, Simplify and Protect all your AI workloads with VCF 9.1(VCF Blog).

---

## 출처

| 자료 | URL |
|---|---|
| Why choose DSM as your on-premises DBaaS | https://blogs.vmware.com/cloud-foundation/2025/07/07/why-choose-vmware-data-services-manager-as-your-on-premises-dbaas/ |
| DSM 9.1 Release Notes | https://techdocs.broadcom.com/us/en/vmware-cis/dsm/data-services-manager/9-1/release-notes/vmware-data-services-manager-91-release-notes.html |
| pgvector 0.8.2 릴리스(CVE-2026-3172) | https://www.postgresql.org/about/news/pgvector-082-released-3245/ |
| PostgreSQL REINDEX (CONCURRENTLY) 문서 | https://www.postgresql.org/docs/current/sql-reindex.html |
| Streamline, Simplify and Protect AI workloads with VCF 9.1 | https://blogs.vmware.com/cloud-foundation/2026/05/05/streamline-simplify-and-protect-all-your-ai-workloads-with-vcf-9-1/ |

---
[← 이전: 05 사용 및 RAG 구성 (Day-1 / Day-2)](05-usage-rag.md) · [목차](../README.md) · [다음: 07 산업 도입 시나리오 →](07-scenarios.md)

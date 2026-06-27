# 03 — VCF DSM 아키텍처

> 왜 PostgreSQL + pgvector인가, VCF DSM 아키텍처, Private AI Services(PAIS) 통합

기준 버전: VCF 9.1 / DSM 9.1 / PAIS 2.1. 대상 독자: Private AI Foundation으로 AI Agent 서비스를 제공하려는 인프라/플랫폼 팀. 경쟁 비교는 [부록](../appendix/A1-vectordb-comparison.md), 배포 절차는 [04 배포](04-deployment.md)를 참조하시기 바랍니다.

---

## 3.1 왜 PostgreSQL + pgvector인가 — 기술적 근거

부록의 경쟁 비교에서 10개의 Vector DB 솔루션을 비교했습니다. 이 섹션에서는 비교표 이면의 핵심 논리를 풀어서 설명합니다. 도입 검토팀이 "왜 새로운 전용 벡터 DB가 아니라 PostgreSQL 확장을 선택해야 하는가"라는 질문에 명확히 답할 수 있도록 구성했습니다.

### 3.1.1 전용 벡터 DB의 숨겨진 비용 — "빙산의 일각" 문제

벡터 검색이 필요하다고 해서 Pinecone이나 Milvus 같은 전용 벡터 DB를 도입하면, 눈에 보이는 것보다 훨씬 많은 인프라와 운영 비용이 발생합니다. 이를 "빙산의 일각" 문제라 합니다.

전용 벡터 DB를 도입할 때 실제로 필요한 것들을 살펴보면 다음과 같습니다.

**눈에 보이는 비용 (수면 위)**
- 벡터 DB 자체의 라이선스/구독료
- 벡터 DB가 실행될 컴퓨트/스토리지

**숨겨진 비용 (수면 아래)**
- 메타데이터 저장을 위한 별도 관계형 DB (PostgreSQL 또는 MySQL): 벡터 DB는 벡터만 저장합니다. "이 벡터가 어떤 문서의 것인지", "작성자가 누구인지", "언제 만들어졌는지" 같은 메타데이터는 별도 관계형 DB에 저장해야 합니다.
- 두 DB 간 데이터 동기화 인프라: 문서가 수정되면 관계형 DB의 메타데이터와 벡터 DB의 임베딩을 동시에 업데이트해야 합니다. 이 동기화가 실패하면 검색 결과가 틀어집니다.
- 두 시스템에 대한 각각의 백업/복구 체계
- 두 시스템에 대한 각각의 모니터링/알림 설정
- 두 시스템에 대한 각각의 보안 정책/접근 제어
- 벡터 DB 전문 인력 확보 또는 기존 인력 교육
- 장애 발생 시 두 시스템 간 데이터 일관성 복구

실제 사례 기반으로 비용을 비교하면, 전용 벡터 DB 구성의 경우 DB 서비스 비용에 더해 별도 PostgreSQL 인스턴스(메타데이터용), 데이터 동기화 인프라, 엔지니어링 오버헤드(월 20–40시간)가 추가됩니다. 반면 PostgreSQL + pgvector 단일 구성의 경우 단일 PostgreSQL 인스턴스에 pgvector 확장 비용 무료(오픈소스), 동기화 인프라 불필요, 엔지니어링 오버헤드도 월 5–10시간에 그칩니다. 실제 마이그레이션 사례에서 60–80%의 비용 절감이 보고되고 있습니다.

### 3.1.2 "하나의 쿼리로 모든 것을" — SQL 통합의 실질적 가치

pgvector의 핵심 차별점은 벡터 검색과 관계형 데이터 조회를 **하나의 SQL 문으로 처리**할 수 있다는 것입니다. 이것이 왜 중요한지 실제 시나리오로 설명합니다.

예를 들어 금융사에서 "고객 민원 중 투자 관련 내용을 의미 검색하되, 최근 30일 이내, VIP 등급 고객만"이라는 요구가 있다고 가정해 보겠습니다.

**전용 벡터 DB 방식 (3단계 프로세스)**

1단계에서 관계형 DB에 쿼리하여 최근 30일 + VIP 등급 고객의 민원 ID 목록을 가져옵니다. 2단계에서 해당 ID 목록을 벡터 DB에 전달하여 "투자" 관련 의미 검색을 실행합니다. 3단계에서 두 결과를 애플리케이션 코드에서 조합합니다. 이 과정에서 네트워크 왕복이 2회 이상 발생하고, 애플리케이션에 조합 로직이 필요하며, ID 목록이 크면 벡터 DB 쿼리 성능이 저하되고, 두 DB의 데이터 시점이 어긋날 수 있습니다.

**pgvector 방식 (단일 SQL)**

```sql
SELECT c.complaint_id, c.customer_name, c.created_at,
       c.content, c.embedding <=> $query_vector AS distance
FROM complaints c
JOIN customers cu ON c.customer_id = cu.id
WHERE cu.grade = 'VIP'
  AND c.created_at >= NOW() - INTERVAL '30 days'
ORDER BY c.embedding <=> $query_vector
LIMIT 10;
```

단일 쿼리로 벡터 유사도 검색, 메타데이터 필터링, 테이블 JOIN이 모두 수행됩니다. ACID 트랜잭션이 보장되어 데이터 일관성 문제가 원천적으로 없으며, pgvector 0.8.0의 Iterative Index Scan이 필터링과 벡터 검색을 효율적으로 결합합니다.

이 차이는 프로덕션 환경의 안정성, 성능, 유지보수성에 직결됩니다.

### 3.1.3 "80% 워크로드에 충분" — 현실적 규모 판단

벡터 DB 시장의 마케팅은 "수십억 벡터를 밀리초 단위로 검색"하는 극단적 시나리오를 강조합니다. 그러나 실제 엔터프라이즈 AI 워크로드의 규모는 다릅니다.

한국 대기업의 일반적인 AI/RAG 워크로드 규모를 살펴보면, 사내 문서 검색(규정, 매뉴얼, 기술 문서)의 경우 문서 수 1만–50만 건에 벡터 수(chunk 기준) 10만–500만 개 수준입니다. 고객 상담 이력 검색은 상담 건수 10만–300만 건에 벡터 수 50만–1,500만 개입니다. 상품 추천(유통)의 경우 SKU 수 10만–500만 개에 벡터 수 10만–500만 개입니다. 금융 이상거래 탐지는 일일 거래 수 100만–1,000만 건에 벡터 수 100만–1,000만 개입니다.

이 모든 시나리오가 1,000만 벡터 이하이며, pgvector가 단독으로도 100ms 미만 응답 시간을 달성하는 구간입니다. pgvectorscale을 추가하면 5,000만 벡터까지 커버할 수 있습니다. 수십억 벡터가 필요한 워크로드(대규모 이커머스 검색 엔진, 글로벌 소셜 미디어 추천 등)는 한국 엔터프라이즈 시장에서 극소수에 해당합니다.

정리하면, "나중에 규모가 커지면 전용 벡터 DB로 전환하면 된다"기보다 "대부분의 경우 전환이 필요 없을 만큼 pgvector가 충분하다"가 현실에 더 가깝습니다.

### 3.1.4 운영 전문성 — 30년 생태계의 힘

PostgreSQL은 1996년 첫 릴리스 이후 약 30년간 전 세계에서 가장 활발하게 운영되어 온 오픈소스 데이터베이스입니다. 이 기간 동안 축적된 운영 지식, 도구, 인력 풀은 다른 어떤 벡터 DB도 따라올 수 없는 자산입니다.

| 운영 영역 | PostgreSQL (pgvector 포함) | 전용 Vector DB (Milvus, Qdrant 등) |
|---|---|---|
| **DBA 인력 풀** | 전 세계 수십만 명, 국내 수천 명 | 극소수, 국내 거의 없음 |
| **백업/복구** | pg_dump, pg_basebackup, PITR — 30년간 검증 | 각 DB별 자체 도구, 성숙도 낮음 |
| **모니터링** | Prometheus, Grafana, Datadog, pganalyze 등 | 제한된 통합, 자체 도구 의존 |
| **HA/DR** | Streaming Replication, pg_auto_failover, Patroni | 각 DB별 자체 구현, 검증 사례 적음 |
| **보안** | LDAP/AD 연동, SSL/TLS, Row-Level Security, 감사 로그 | 기본적 인증/인가, 금융 규제 대응 미비 |
| **커뮤니티/지원** | Stack Overflow 100만+ 질문, 수천 개 블로그/도서 | 수천 개 질문, 도서 거의 없음 |

실질적 의미: 금요일 밤에 벡터 DB 장애가 발생했을 때, PostgreSQL이면 기존 DBA가 대응할 수 있습니다. Milvus나 Weaviate면 해외 커뮤니티에 영어로 질문을 올리고 답변을 기다려야 할 수 있습니다. 엔터프라이즈 환경에서는 이 차이가 장애 대응 속도를 좌우합니다.

### 3.1.5 실제 마이그레이션 트렌드 — 이미 전환이 진행 중이다

2023년 이후, 전용 벡터 DB에서 PostgreSQL + pgvector로 전환하는 사례가 빠르게 늘고 있으며, 2024–2025년에 이 트렌드가 가속화되고 있습니다. 대표적인 사례를 들면 다음과 같습니다.

**Instacart (2025년 5월)**: Elasticsearch 기반 검색 인프라를 PostgreSQL + pgvector 기반 하이브리드 검색으로 단계적 전환. 정규화된 데이터 모델 전환을 통해 write workload를 10배 감소시키고, 스토리지 및 인덱싱 비용 80% 절감을 달성했습니다. 또한 pgvector 기반 semantic search 도입으로 zero-result 검색률이 6% 감소하여 증분 매출 증가로 이어졌습니다.

**Firecrawl (2023년)**: Pinecone에서 Supabase 기반 pgvector로 전환. 동일 워크로드에서 비용이 대폭 절감되었으며, 벡터 데이터와 메타데이터의 통합 관리가 가능해졌습니다. Firecrawl 측은 "다른 벡터 DB(Faiss, Weaviate, Pinecone)는 비용이 높고 메타데이터 저장이 불편했다"고 밝혔습니다.

**Berri AI**: 별도 벡터 DB에서 PostgreSQL + pgvector로 통합. 데이터 동기화 문제가 해소되고 운영 부담이 감소했습니다.

이 트렌드의 배경은 명확합니다. 2022–2023년 ChatGPT 등장과 함께 벡터 DB 시장에 투자가 몰렸지만, 실제 프로덕션 운영을 경험한 기업들이 "별도 벡터 DB의 운영 복잡성 대비 실익이 크지 않다"는 결론을 내리고 있습니다.

---

## 3.2 VCF DSM 기반 아키텍처 — pgvector의 가치를 극대화하는 방법

앞 섹션에서 "왜 PostgreSQL + pgvector인가"를 설명했습니다. 이 섹션에서는 **왜 PostgreSQL을 직접 설치하지 않고 VCF DSM(Data Services Manager)을 통해 운영해야 하는가**를 설명합니다.

### 3.2.1 VCF Data Services Manager(DSM)란 무엇인가

VMware Data Services Manager(DSM)는 VMware Cloud Foundation(VCF)의 **Database-as-a-Service(DBaaS)** 솔루션입니다. 쉽게 말해, 프라이빗 클라우드 환경에서 AWS RDS나 Azure Database for PostgreSQL과 동등한 데이터베이스 관리형 서비스를 제공하는 것입니다.

DSM의 핵심 특징을 정리하면 다음과 같습니다.

| 항목 | 내용 |
|---|---|
| **포함 관계** | VCF Add-on 구독 (DB 엔진 자체는 오픈소스, DB 레벨 지원 모델 별도) |
| **지원 DB 엔진** | PostgreSQL, MySQL, Microsoft SQL Server (9.1에서 SQL Server 정식 GA) |
| **pgvector 지원** | PostgreSQL 프로비저닝 시 pgvector 확장 내장. `CREATE EXTENSION vector;`로 즉시 활성화 |
| **배포 방식** | OVA 기반 어플라이언스 배포 → vCenter 플러그인으로 통합 |
| **최신 버전** | DSM 9.1 (VCF 9.1 호환) |
| **관리 인터페이스** | DSM Admin UI, vSphere Client 통합, VCF Automation 통합, REST API |
| **인증된 아키텍처** | VMware Private AI Foundation with NVIDIA에서 pgvector 연동 공식 인증 |

SQL Server는 DSM 9.1에서 Tech Preview를 벗어나 정식 GA되었으며, Always On Availability Groups, 자동 백업/PITR, Active Directory 통합을 지원합니다. 또한 9.1에서 기존 비관리 PostgreSQL/MySQL을 DSM 관리로 편입하는 Brownfield Onboarding이 추가되었습니다.

핵심: **DSM은 VCF Add-on으로 확보하면 pgvector가 내장된 PostgreSQL을 프로비저닝할 수 있습니다.** 별도 벡터 DB를 추가 도입할 필요 없이, DSM에서 활성화하면 됩니다.

### 3.2.2 DSM이 해결하는 문제 — "PostgreSQL을 직접 설치하면 안 되나요?"

PostgreSQL을 VM에 직접 설치하여 pgvector를 사용하는 것은 기술적으로 가능합니다. 그러나 프로덕션 환경에서 이 접근은 많은 수동 작업과 리스크를 수반합니다. DSM이 이 문제를 어떻게 해결하는지 영역별로 살펴보겠습니다.

#### 프로비저닝

수동으로 PostgreSQL을 설치할 경우, VM 생성 → OS 설치 → PostgreSQL 패키지 설치 → 보안 설정 → 네트워크 설정 → pgvector 확장 컴파일/설치의 과정을 거쳐야 하며, 숙련된 엔지니어도 2–4시간이 소요됩니다. 환경마다 설정이 달라질 수 있어 일관성을 유지하기 어렵습니다.

DSM을 사용하면, DSM UI 또는 API에서 PostgreSQL 버전 선택 → 리소스 크기 지정 → "Create" 클릭의 3단계로 끝나며, 분 단위로 프로비저닝이 완료됩니다. VMware가 인증한 템플릿을 사용하므로 보안 하드닝, 네트워크 설정, pgvector 확장이 모두 사전 구성되어 있습니다.

#### 고가용성 (HA)

수동 구성 시, Streaming Replication 설정 → pg_auto_failover 또는 Patroni 설치 → Monitor 노드 구성 → Failover 테스트 → vSphere Anti-Affinity Rule 수동 설정이 필요하며, 초기 구성에 1–2일, 장애 테스트에 추가 시간이 소요됩니다.

DSM에서는 HA를 클릭 한 번으로 활성화합니다. DSM이 자동으로 수행하는 것은 다음과 같습니다.

- Primary + Monitor + Replica 3노드 클러스터 자동 배포
- pg_auto_failover 기반 자동 장애 감지 및 Failover (5분 주기 폴링)
- vSphere DRS Anti-Affinity Rule 자동 적용 (각 노드가 서로 다른 ESXi 호스트에 배치)
- Cross-Cluster HA 옵션을 통해 서로 다른 vSphere Cluster에 노드를 분산 배치하여 더 높은 수준의 가용성 확보
- Failover 발생 시 DSM 컨트롤 플레인이 자동으로 메타데이터 업데이트 및 DNS 매핑 갱신

#### 백업 및 복구

수동 구성 시, pg_basebackup + WAL 아카이빙 설정 → S3/NFS 백업 스토리지 구성 → cron 기반 스케줄 백업 → PITR(Point-In-Time Recovery) 테스트의 과정이 필요합니다.

DSM은 자동 백업 스케줄 설정, S3 호환 스토리지로 WAL 아카이빙, UI에서 특정 시점으로의 PITR 실행, 클론 기능을 통한 프로덕션 DB의 개발/테스트 환경 복제를 자동화합니다. PostgreSQL의 경우 기본 주 1회 전체 백업, 일 단위 백업, WAL은 5분 또는 16MB 중 먼저 도달하는 시점마다 전송합니다. DSM이 백업 및 WAL 아카이빙 정책에 따라 불필요한 WAL 파일을 정리하므로, 수동으로 디스크 공간을 모니터링할 필요가 줄어듭니다.

#### 라이프사이클 관리

수동 관리 시, PostgreSQL 마이너/메이저 버전 업그레이드를 직접 수행해야 하며, OS 패치와 DB 패치를 별도로 관리하고, 보안 취약점 대응도 자체적으로 해야 합니다.

DSM은 PostgreSQL 엔진 업데이트와 OS 패치를 통합된 번들로 제공합니다. 관리자가 스테이징하면 유지보수 윈도에 롤링 업데이트로 적용되며, Broadcom 지원 조직이 오픈소스 커뮤니티와 협력하여 보안 패치를 제공합니다. 커뮤니티 릴리스에 포함되지 않은 긴급 수정이 필요한 경우, Broadcom이 커스텀 빌드를 제작하여 제공할 수 있습니다. 메이저/마이너 버전 업그레이드 모두 지원하되, 메이저 업그레이드 시 확장(extension) 호환성을 사전 확인합니다.

#### 스케일링

수동 스케일링 시, VM 리소스 변경(CPU/RAM) → PostgreSQL 재시작 → shared_buffers 등 파라미터 재조정 → 디스크 확장 시 LVM/파일시스템 작업이 필요합니다.

DSM에서는 UI 또는 API로 리소스 크기를 변경하면 DSM이 자동으로 VM 리소스를 조정하고, PostgreSQL 파라미터(shared_buffers, max_connections 등)를 재설정합니다. Standalone(1노드)과 Clustered(3노드) 간 Scale Out/In, VM Class 변경을 통한 Scale Up/Down이 가능하며, 디스크 확장도 온라인으로 처리할 수 있습니다.

### 3.2.3 DSM의 아키텍처 구성 — 세 가지 페르소나

DSM은 세 가지 역할(페르소나)에 최적화된 인터페이스를 제공합니다.

**VI Admin (인프라 관리자)**

인프라 정책(Infrastructure Policy)을 통해 데이터베이스가 배포될 컴퓨트, 스토리지, 네트워크, VM 폴더를 정의합니다. 이를 통해 "데이터 스프롤(data sprawl)"을 방지하고, 라이선스 관리, 비용 예측, 청구가 용이해집니다. VCF 9.x에서는 vSphere Namespace 기반 인프라 정책을 통해 더욱 세밀한 리소스 제어가 가능합니다. CPU, 메모리, 스토리지의 한도를 Namespace 단위로 설정할 수 있으며, VCF Operations와 통합되어 데이터베이스 성능 메트릭을 기존 모니터링 체계에 통합합니다.

**DBA (데이터베이스 관리자)**

DSM UI에서 PostgreSQL 인스턴스 생성, HA 구성, 백업/복구, 파라미터 튜닝, 스케일링을 수행합니다. shared_buffers, max_connections 등 PostgreSQL 파라미터를 DB Options에서 직접 설정할 수 있으며, pgvector를 포함한 확장(Extension)을 SUPERUSER 권한으로 활성화/비활성화합니다. pg_hba.conf와 고급 파라미터를 프로비저닝 시점에 설정할 수 있어, DB가 일시적으로 무방비로 노출되는 구간을 줄입니다.

**개발자 / 데이터 사이언티스트**

VCF Automation의 셀프서비스 카탈로그에서 데이터베이스를 요청합니다. Jira 티켓을 만들고 DBA의 수동 작업을 기다리는 대신, 카탈로그에서 "PostgreSQL + pgvector"를 선택하면 수 분 내에 접속 정보(Connection String)를 받아 즉시 개발을 시작할 수 있습니다. REST API를 통한 프로그래밍 방식 프로비저닝도 지원되어 CI/CD 파이프라인에 통합 가능합니다. DSM 9.1에서는 PostgreSQL/MySQL/SQL Server 전 엔진의 셀프서비스 프로비저닝이 지원됩니다.

### 3.2.4 VCF 풀스택 통합 — DSM이 만드는 시너지

DSM은 단독으로 동작하는 것이 아니라, VCF의 전체 소프트웨어 스택과 긴밀하게 통합됩니다. 각 컴포넌트가 독립 동작할 때보다 통합 구성에서 운영 효율이 높아집니다.

#### vSAN — 스토리지 레이어

vSAN Express Storage Architecture(ESA)가 pgvector 워크로드의 스토리지 기반이 됩니다. FTT(Failures To Tolerate, 허용 가능 장애 수) 1(RAID-5) 또는 2(RAID-6)로 데이터 보호 수준을 선택할 수 있습니다. HNSW 인덱스는 읽기 집중 워크로드이므로 vSAN의 읽기 캐시 최적화가 직접적으로 벡터 검색 성능에 기여합니다. 별도의 SAN/NAS 스토리지를 구매하거나 관리할 필요가 없습니다. VCF 9.1에서는 vSAN ESA Global Deduplication과 향상된 압축이 GA되어 저장 시 암호화와 병행 가능하며, 대용량 벡터 테이블과 HNSW 인덱스의 스토리지 TCO 절감에 기여합니다.

#### NSX — 네트워크 레이어

마이크로세그멘테이션을 통해 벡터 DB 트래픽을 격리합니다. 예를 들어 "RAG 애플리케이션 → pgvector DB"와 "일반 업무 → ERP DB" 트래픽을 네트워크 레벨에서 분리할 수 있습니다. 로드밸런싱, 방화벽 규칙이 소프트웨어 정의 방식으로 관리되므로 물리 네트워크 변경 없이 보안 정책을 적용할 수 있습니다.

#### VCF Operations — 모니터링 레이어

DSM은 PostgreSQL 및 MySQL 전용 VCF Operations Management Pack을 제공합니다. 데이터베이스 성능 메트릭(쿼리 지연, 연결 수, 버퍼 히트율 등)이 기존 인프라 모니터링 대시보드에 통합됩니다. DSM 9.x에서는 모든 메트릭이 VCF Operations로 전송되며, Prometheus 엔드포인트로도 내보낼 수 있습니다. 로그는 한 번에 DSM 어플라이언스와 모든 DB의 로그를 SYSLOG 엔드포인트로 전송할 수 있습니다. 벡터 검색 쿼리의 성능 이상을 기존 운영 워크플로우 내에서 감지하고 대응할 수 있습니다.

#### VCF Automation — 자동화 레이어

DSM은 VCF Automation과 통합되어 셀프서비스 카탈로그, 블루프린트 기반 배포, 멀티테넌시를 지원합니다. Data Service Policy를 통해 특정 조직(Organization)이나 프로젝트에 할당되는 데이터 서비스 유형, 리소스 한도, 스토리지 정책을 정의할 수 있습니다. Terraform 등 IaC 도구와의 통합도 API를 통해 가능하여, 데이터베이스 라이프사이클을 코드로 관리하는 GitOps 워크플로우를 구현할 수 있습니다.

### 3.2.5 VCF 아키텍처 레퍼런스 — pgvector 워크로드 구성

VCF 환경에서 pgvector 워크로드를 위한 아키텍처는 다음과 같이 구성됩니다.

```
┌─────────────────────────────────────────────────────────────────┐
│                    VCF Management Domain                        │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────────┐    │
│  │ vCenter  │  │ SDDC Manager │  │ VCF Operations         │    │
│  │ Server   │  │              │  │ (DSM Management Pack)  │    │
│  └──────────┘  └──────────────┘  └────────────────────────┘    │
│  ┌──────────────────────┐  ┌──────────────────────────────┐    │
│  │ DSM Appliance        │  │ VCF Automation               │    │
│  │ (Control Plane)      │  │ (Self-Service Catalog)       │    │
│  └──────────────────────┘  └──────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                    Infrastructure Policy
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    VCF Workload Domain                          │
│                                                                 │
│  ┌─── vSphere Cluster A ─────────────────────────────────────┐  │
│  │                                                           │  │
│  │  ┌─────────────────┐  ┌─────────────────┐                │  │
│  │  │ ESXi Host 1     │  │ ESXi Host 2     │                │  │
│  │  │ ┌─────────────┐ │  │ ┌─────────────┐ │                │  │
│  │  │ │ PG Primary  │ │  │ │ PG Replica  │ │                │  │
│  │  │ │ + pgvector  │ │  │ │ + pgvector  │ │                │  │
│  │  │ │             │ │  │ │ (Read)      │ │                │  │
│  │  │ └─────────────┘ │  │ └─────────────┘ │                │  │
│  │  │ ┌─────────────┐ │  │ ┌─────────────┐ │                │  │
│  │  │ │ RAG App VM  │ │  │ │ PG Monitor  │ │                │  │
│  │  │ │ (LangChain) │ │  │ │ (HA Ctrl)   │ │                │  │
│  │  │ └─────────────┘ │  │ └─────────────┘ │                │  │
│  │  └─────────────────┘  └─────────────────┘                │  │
│  │                                                           │  │
│  │  ┌───────────────────────────────────────────────────┐    │  │
│  │  │ vSAN (ESA) — RAID-5/6, Read Cache Optimized      │    │  │
│  │  └───────────────────────────────────────────────────┘    │  │
│  │  ┌───────────────────────────────────────────────────┐    │  │
│  │  │ NSX — Micro-segmentation, Load Balancing          │    │  │
│  │  └───────────────────────────────────────────────────┘    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─── PAIF Workload Domain (Optional: Private AI) ───────────┐  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │  │
│  │  │ DLVM         │  │ Model Runtime│  │ Embedding    │    │  │
│  │  │ (Fine-tuning)│  │ (NVIDIA NIM) │  │ Service      │    │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

핵심 구성 요소별 역할은 다음과 같습니다.

- **DSM Appliance**: PostgreSQL 라이프사이클 전체를 관리하는 컨트롤 플레인. vCenter 플러그인으로 등록되어 vSphere Client에서 직접 접근 가능합니다.
- **Infrastructure Policy**: 데이터베이스가 배포될 컴퓨트/스토리지/네트워크를 정의. VCF 9.x에서는 vSphere Namespace 기반 정책도 지원합니다.
- **PG Primary + pgvector**: 벡터 데이터 저장 및 검색을 수행하는 주 데이터베이스. DSM이 pgvector 확장을 사전 포함하여 프로비저닝합니다.
- **PG Replica**: 읽기 분산 및 HA를 위한 복제본. 벡터 검색은 읽기 워크로드이므로 Replica로 분산하면 Primary의 부하를 줄일 수 있습니다.
- **PG Monitor**: pg_auto_failover 기반 장애 감지 및 자동 Failover를 수행하는 모니터링 노드.
- **vSAN ESA**: Anti-Affinity Rule에 의해 Primary, Replica, Monitor가 서로 다른 호스트에 배치되며, vSAN이 데이터 보호를 제공합니다.
- **PAIF Workload Domain**: Private AI Foundation 구성 시, 임베딩 모델과 LLM 추론을 위한 GPU 워크로드가 별도 도메인에서 실행됩니다.

---

## 3.3 Private AI Services — DSM + pgvector의 완성형

### 3.3.1 VMware Private AI Services(PAIS)와 pgvector의 관계

VMware Private AI Services(PAIS)는 프라이빗 클라우드에서 엔터프라이즈 AI를 구축하기 위한 통합 서비스 세트입니다. PAIS는 VCF 9.x 구독에 포함된 정식 서비스이며, 현재 PAIS 2.1 기준으로 UI 기반 셀프서비스 활성화와 폐쇄망(Air-gapped) 운영을 지원합니다. 추가 소프트웨어 구매 없이 활용할 수 있습니다.

PAIS의 핵심 구성 요소와 pgvector의 위치를 정리하면 다음과 같습니다.

| 서비스 | 역할 | pgvector 연관성 |
|---|---|---|
| **Model Gallery** | LLM 모델의 거버넌스. Harbor 레지스트리 기반으로 모델 버전을 관리 | — |
| **Model Runtime** | 모델 추론 서빙. vLLM(completion 모델), Infinity(embedding 모델) 등 추론 서버 기반으로 LLM과 임베딩 모델을 API로 제공. NVIDIA NIM과도 연동 가능 | 임베딩 모델이 텍스트를 벡터로 변환 → pgvector에 저장 |
| **Data Indexing & Retrieval** | 지식 기반(Knowledge Base) 구축. 데이터 소스 연결 → 청킹 → 임베딩 → 벡터 저장 → 주기적 갱신 | **pgvector가 벡터 저장소로 직접 사용됨** |
| **Agent Builder** | AI 에이전트 조합. 모델 + 지식 기반 + 도구를 결합하여 RAG 에이전트를 노코드로 구축 | 에이전트의 RAG 기능이 pgvector에서 컨텍스트를 검색 |
| **DSM (Vector Database)** | PostgreSQL + pgvector 프로비저닝 및 관리 | **pgvector를 관리형 서비스로 제공하는 핵심 인프라** |

PAIS에서 pgvector는 단순한 저장소에 그치지 않습니다. 사용자의 질문이 들어오면, Agent Builder의 에이전트가 질문을 임베딩 모델(Model Runtime에서 서빙)로 벡터화하고, 이 벡터를 pgvector(DSM에서 관리)에 조회하여 관련 문서를 찾고, 찾은 문서를 LLM(Model Runtime에서 서빙)에 컨텍스트로 전달하여 최종 답변을 생성합니다. pgvector는 이 파이프라인에서 검색 가능한 지식을 저장하는 핵심 저장소입니다.

**GPU 및 라이선스 참고**: PAIS의 소프트웨어 컴포넌트(Model Store, Model Runtime, Data Indexing & Retrieval, Agent Builder)는 VCF 9.x 구독에 포함되어 추가 소프트웨어 비용이 없습니다. 단, GPU 기반 모델 추론 및 임베딩 생성을 위한 **NVIDIA AI Enterprise 라이선스는 NVIDIA에서 별도 구매**해야 합니다. 또한 GPU 하드웨어(NVIDIA A100, H100, L40S, Blackwell B200, RTX PRO 6000/4500 등)도 별도 확보가 필요합니다. VCF 9.1/PAIF 9.1에서는 DirectPath GPU enablement와 GPUDirect RDMA/Storage를 지원합니다. DSM을 통한 PostgreSQL + pgvector 프로비저닝 자체는 GPU 없이도 가능하며, PoC 단계에서 임베딩 생성을 외부 API(OpenAI, Cohere 등)로 처리하면 GPU 인프라 없이 벡터 검색 기능을 검증할 수 있습니다.

### 3.3.2 PAIS RAG 워크플로우 상세

PAIS의 RAG 워크플로우를 단계별로 풀어 설명합니다.

**Phase 1: 지식 기반 구축 (오프라인, 주기적 실행)**

1단계 — 데이터 소스 연결: PAIS의 Data Indexing & Retrieval 서비스가 Google Drive, Confluence, SharePoint, S3 등 기업의 문서 저장소에 연결합니다.

2단계 — 문서 청킹: 연결된 문서를 의미 단위로 분할(chunking)합니다. 문서의 구조에 따라 문단, 문장, 테이블 등을 적절한 크기로 나눕니다.

3단계 — 임베딩 생성: Model Runtime에서 서빙되는 임베딩 모델(예: vLLM/Infinity 기반)이 각 chunk를 벡터로 변환합니다.

4단계 — 벡터 저장: 생성된 벡터가 DSM이 관리하는 PostgreSQL + pgvector 데이터베이스에 저장됩니다. 원본 텍스트, 메타데이터, 벡터가 모두 같은 DB에 위치합니다.

5단계 — 주기적 갱신: 데이터 소스의 변경을 감지하여 지식 기반을 자동으로 업데이트합니다. 스케줄 기반 또는 온디맨드 갱신이 가능합니다.

**Phase 2: 질의 응답 (실시간)**

사용자가 질문을 입력하면 → Agent Builder의 에이전트가 질문을 수신하고 → 임베딩 모델이 질문을 벡터로 변환하며 → pgvector에서 유사도 검색을 수행하여 관련 문서 chunk를 추출하고 → (선택적) Re-ranker가 검색 결과를 재정렬한 뒤 → LLM이 검색된 문서를 컨텍스트로 사용하여 답변을 생성하면 → 사용자에게 출처와 함께 답변이 전달됩니다.

### 3.3.3 PAIS + DSM 구성 시 얻는 것 — "풀 매니지드 Private RAG"

PAIS와 DSM을 결합하면 퍼블릭 클라우드의 RAG 서비스(AWS Bedrock Knowledge Base, Azure AI Search 등)와 동등한 기능을 프라이빗 클라우드에서 제공합니다.

| 역량 | 퍼블릭 클라우드 RAG | PAIS + DSM (프라이빗 클라우드) |
|---|---|---|
| 모델 서빙 | AWS Bedrock, Azure OpenAI | PAIS Model Runtime (vLLM/Infinity, NVIDIA NIM 연동 가능) |
| 벡터 DB | AWS Aurora pgvector, Azure Cosmos DB | DSM PostgreSQL + pgvector |
| 지식 기반 구축 | AWS Bedrock KB, Azure AI Search | PAIS Data Indexing & Retrieval |
| 에이전트 빌더 | AWS Bedrock Agent, Azure AI Agent | PAIS Agent Builder |
| 데이터 위치 | 퍼블릭 클라우드 (해외 리전) | **온프레미스 데이터센터 (국내)** |
| 데이터 주권 | 클라우드 사업자 약관에 의존 | **조직이 완전 통제** |
| 네트워크 지연 | 인터넷 경유 | **로컬 네트워크** |
| 비용 모델 | 종량제 (예측 어려움) | 고정 인프라 비용 (예측 가능) |

핵심 차별점: 데이터가 한 번도 조직의 네트워크 밖으로 나가지 않습니다. 문서 원본, 벡터 임베딩, LLM 추론 결과가 모두 온프레미스에서 처리됩니다. 이것은 금융감독원 규제, 개인정보보호법, 산업별 컴플라이언스를 준수해야 하는 한국 엔터프라이즈에 결정적인 요소입니다. PAIS 2.1의 폐쇄망(Air-gapped) 지원은 데이터 반출이 불가한 방산·금융·공공 환경에서도 RAG 전체 파이프라인을 외부 연결 없이 구성할 수 있게 합니다.

**성숙도 참고**: PAIS는 VCF 9.0(2025년 6월)에서 처음 도입된 서비스로, AWS Bedrock(2023년 GA)이나 Azure AI Search(2023년 GA) 대비 에코시스템과 서드파티 통합 측면에서 아직 확장 단계에 있습니다. 데이터 소스 커넥터 수, 지원되는 문서 포맷, 커뮤니티 사례 등이 분기별 업데이트로 확대되고 있습니다. 그러나 **데이터 주권, 네트워크 지연, 비용 예측 가능성** 측면에서의 구조적 우위는 퍼블릭 클라우드 대안이 따라올 수 없는 PAIS의 핵심 가치입니다.

---

## 3.4 Why VMware — pgvector 가치 극대화의 6가지 이유

기초 분석에서 pgvector의 기술적 우수성을, 부록에서 경쟁 대비 포지셔닝을, 이 문서에서 VCF DSM 아키텍처를 설명했습니다. 이를 종합하여 "왜 VMware VCF + DSM 환경에서 pgvector를 사용해야 하는가"에 대한 6가지 이유를 정리합니다.

### 3.4.1 "이미 가지고 있다" — 추가 도입 최소화

VCF에 DSM Add-on을 더하면 pgvector가 내장된 PostgreSQL을 프로비저닝할 수 있고, PAIS의 소프트웨어 서비스도 VCF 구독에 포함됩니다. 단, GPU 워크로드 실행을 위한 NVIDIA AI Enterprise 라이선스와 GPU 하드웨어는 별도로 확보해야 합니다. 별도의 전용 벡터 DB 라이선스, SaaS 구독, 오픈소스 벡터 DB 운영 인력을 추가로 확보할 필요가 없습니다. Pinecone, Zilliz Cloud 등 상용 벡터 DB는 별도 구독 비용이 발생하지만, DSM의 pgvector는 VCF + DSM 구성 내에서 추가 벡터 DB 없이 사용할 수 있습니다.

### 3.4.2 "Day-0부터 Day-2까지 자동화" — 운영 부담 최소화

DB를 직접 설치하면 프로비저닝, HA 구성, 백업 설정, 패치 적용, 스케일링을 모두 수동으로 해야 합니다. Milvus를 Kubernetes에 배포하면 etcd, MinIO, Pulsar 등의 의존성을 함께 관리해야 합니다. DSM은 이 모든 라이프사이클을 자동화합니다. 프로비저닝부터 패치, 백업, HA, 스케일링까지 UI 또는 API 한 번으로 처리됩니다. 인프라팀은 벡터 DB 운영 부담 대신 서비스 개선에 집중할 수 있습니다.

### 3.4.3 "인프라 통제권 유지" — VI Admin의 거버넌스

개발팀이 각자 Chroma, Qdrant, Pinecone을 도입하면 인프라팀 입장에서 "데이터 스프롤"이 발생합니다. 어디에 어떤 데이터가 있는지 파악이 어렵고, 보안 정책 적용이 일관되지 않으며, 비용 예측과 청구가 복잡해집니다. DSM의 Infrastructure Policy는 데이터베이스가 배포될 컴퓨트, 스토리지, 네트워크를 VI Admin이 중앙에서 정의합니다. 개발팀은 셀프서비스로 DB를 프로비저닝하되, 인프라팀이 설정한 가드레일 안에서만 동작합니다.

### 3.4.4 "Private AI 풀스택 통합" — 엔드투엔드 RAG 파이프라인

pgvector 단독이 아니라, PAIS의 Model Store → Model Runtime → Data Indexing & Retrieval → Agent Builder → DSM(pgvector)가 하나의 통합된 RAG 파이프라인을 구성합니다. 각 컴포넌트를 별도로 조합하는 DIY 방식 대비 구축 시간이 대폭 단축되고, 단일 벤더 지원을 받을 수 있습니다. VCF Automation을 통해 "PostgreSQL + pgvector 데이터베이스", "RAG 워크스테이션", "Kubernetes RAG 클러스터"를 카탈로그 아이템으로 원클릭 프로비저닝할 수 있습니다.

### 3.4.5 "금융 규제 대응" — 데이터 주권과 컴플라이언스

한국 금융권은 금융감독원의 클라우드 컴퓨팅 이용 가이드라인, 전자금융감독규정, 개인정보보호법에 의해 데이터 위치와 접근에 대한 엄격한 규제를 받습니다. VCF + DSM + pgvector 구성은 다음으로 대응합니다.

- 데이터 위치: 모든 데이터(원본 문서, 벡터 임베딩, 메타데이터)가 온프레미스 데이터센터에 위치
- ACID 트랜잭션: PostgreSQL의 완전한 ACID를 벡터 데이터에도 동일하게 적용
- 접근 제어: NSX 마이크로세그멘테이션 + PostgreSQL Row-Level Security
- 감사 추적: PostgreSQL 감사 로그 + VCF Operations 통합 모니터링
- 암호화: vSAN 저장 시 암호화(encryption at rest) + SSL/TLS 전송 암호화

Pinecone(SaaS)이나 Zilliz Cloud는 데이터가 해외 클라우드에 저장되므로 금융권 도입에 근본적인 장벽이 있습니다. Milvus나 Qdrant를 Self-hosted로 구성해도 HA, 백업, 보안, 모니터링을 자체 구현해야 하며, 금융감독원의 감사 요구에 대응하기 위한 증적 확보가 어렵습니다.

### 3.4.6 "점진적 확장 경로" — 시작은 작게, 필요하면 크게

DSM에서 pgvector로 시작하면 다음과 같은 점진적 확장 경로가 열립니다.

| 단계 | 규모 | 구성 |
|---|---|---|
| PoC/초기 서비스 | ~100만 벡터 | DSM 단일 PostgreSQL + pgvector |
| 프로덕션 확장 | 100만–1,000만 | DSM HA 클러스터 + Read Replica 분산 |
| 대규모 확장 | 1,000만–5,000만 | pgvectorscale 도입 + 파티셔닝 |
| 초대규모 | 5,000만 이상 | Citus 기반 분산 또는 전용 벡터 DB 검토 |

각 단계에서 이전 단계의 데이터와 스키마를 그대로 유지할 수 있습니다. PoC에서 만든 테이블 구조와 SQL 쿼리가 프로덕션에서도 동일하게 동작합니다. 전용 벡터 DB로 시작하면 규모가 작을 때도 해당 DB의 운영 복잡성을 감수해야 하지만, pgvector는 규모에 맞게 복잡성이 점진적으로 증가합니다.

---

## 참고 자료

| 자료 | URL |
|---|---|
| VMware DSM 공식 문서 | https://techdocs.broadcom.com/us/en/vmware-cis/dsm/data-services-manager/9-1.html |
| DSM 9.1 릴리스 노트 | https://techdocs.broadcom.com/us/en/vmware-cis/dsm/data-services-manager/9-1/release-notes/vmware-data-services-manager-91-release-notes.html |
| DSM을 온프레미스 DBaaS로 선택해야 하는 이유 | https://blogs.vmware.com/cloud-foundation/2025/07/07/why-choose-vmware-data-services-manager-as-your-on-premises-dbaas/ |
| DSM 9.1 소개 | https://blogs.vmware.com/cloud-foundation/2026/05/05/vmware-data-services-manager-9-1-automating-the-modern-databases-that-drive-ai-and-private-cloud/ |
| PAIS 기능 소개 (VCF 9.0) | https://blogs.vmware.com/cloud-foundation/2025/06/19/private-ai-services-new-in-vmware-private-ai-foundation-with-nvidia-in-vcf-9-0/ |
| VCF 9.1 AI 워크로드 / PAIS 2.1 | https://blogs.vmware.com/cloud-foundation/2026/05/05/streamline-simplify-and-protect-all-your-ai-workloads-with-vcf-9-1/ |
| Private AI Services Detailed Design | https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/design/design-library/private-ai-platform-detailed-design/private-ai-services.html |
| PAIS RAG 워크로드 배포 가이드 | https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1/private-ai-foundation-9-x/deploying-rag-workloads-in-private-ai-foundation-with-nvidia/deploy-a-vector-database-for-paif.html |

---
[← 이전: 02 Vector Database & pgvector 기초](02-vectordb-pgvector-basics.md) · [목차](../README.md) · [다음: 04 배포 (Day-0 / Day-1) →](04-deployment.md)

# 04 — 배포 (Day-0 / Day-1)

> VCF DSM 기반 PostgreSQL + pgvector를 프로비저닝하고 PAIS에 연결하기까지의 실행 절차

기준 버전: VCF 9.1 / DSM 9.1 / PAIS 2.1. 본 문서의 UI 경로·절차는 공식 문서와 공개 랩 가이드를 기반으로 하며, 릴리스에 따라 화면 명칭이 일부 달라질 수 있으므로 공식 문서를 함께 확인하시기 바랍니다.

---

## 4.1 선행조건 체크리스트

배포 시작 전 다음을 확인합니다.

| 구분 | 항목 | 확인 |
|---|---|---|
| 플랫폼 | VCF 9.1 Workload Domain 가용, vCenter 접근 권한 | |
| 라이선스 | DSM Add-on 구독 활성화 | |
| 컴퓨트 | DSM 어플라이언스 및 DB 노드용 리소스(클러스터 DB는 3노드) | |
| 스토리지 | vSAN ESA 데이터스토어, Storage Policy(FTT=1 또는 FTT=2). 정책 이름에 공백 없음 | |
| 네트워크 | DB 세그먼트, DSM과 vCenter/VCFA 간 통신 경로, DNS | |
| 자동화 | VCF Automation(VCFA) Organization 및 Namespace 생성 | |
| AI(선택) | PAIS 배포, GPU 호스트, NVIDIA AI Enterprise 라이선스 | |

스토리지 정책 이름에 공백이 있으면 Kubernetes 명명 규칙 위반으로 배포가 실패할 수 있으므로 공백 없는 이름을 사용합니다.

---

## 4.2 아키텍처 결정 사항

프로비저닝 전에 다음을 결정합니다.

- 토폴로지: Standalone(1노드, PoC) 또는 Clustered(3노드, 프로덕션 HA)
- 가용성 수준: 동일 vSphere Cluster 내 분산(기본) 또는 Cross-Cluster Infrastructure Policy(더 높은 가용성)
- 데이터 보호: vSAN FTT=1(RAID-5) 또는 FTT=2(RAID-6)
- 암호화: VM Crypt 기반 선택적 암호화 또는 데이터스토어 전체 암호화
- 소비 모델: DSM UI 직접 / VCFA 셀프서비스 카탈로그 / REST·K8s API
- 사이징: 4.6 사이징 워크시트 참조

---

## 4.3 DSM 배포 및 초기 구성

다음은 DSM을 배포하고 PostgreSQL 프로비저닝이 가능한 상태까지 만드는 절차입니다.

1. Broadcom Support Portal에서 최신 DSM OVA를 내려받아 vSphere UI로 배포합니다. OVA 속성(vCenter SHA256 Thumbprint 등)을 입력합니다.
2. 전원 인가 후 DSM이 vCenter 확장으로 자동 등록됩니다. 수 분 내 vSphere UI 플러그인 알림을 확인합니다.
   - 검증: vCenter 인벤토리 객체 → Configure → Data Services Manager 진입 가능
3. Configure → Data Services Manager에서 초기 설정 및 VCFA 연결에 사용할 로컬 사용자 계정을 생성합니다.
   - 주의: 비밀번호 확인 입력란이 없으므로 오타에 유의합니다.
4. Configure → Data Services Manager → Infrastructure Policies에서 DB가 배포될 VCFA Namespace를 선택합니다.
   - Infrastructure Policy는 컴퓨트·스토리지·네트워크·VM 폴더 배치를 정의합니다. 데이터 스프롤 방지와 라이선스·비용 통제의 기준점입니다.
5. DSM Admin UI(DSM FQDN)에 로컬 계정으로 로그인하여 Versions & Upgrades → Postgres에서 사용할 PostgreSQL 버전을 활성화합니다.
   - 검증: 활성화한 버전이 프로비저닝 옵션에 노출되는지 확인

출처: William Lam, MS-A2 VCF Lab(DSM for PAIS); DSM Getting Started 공식 문서.

---

## 4.4 VCF Automation 연동 및 셀프서비스 게시

DSM을 VCFA에 연결해 멀티테넌트 셀프서비스로 제공하는 절차입니다.

1. VCFA와 DSM 간 TLS 신뢰 설정을 확인합니다. (VCF 9.0 환경에서 VCFA Binding 관련 알려진 이슈가 있었으므로, 9.1 환경에서는 해당 Workaround 필요 여부를 공식 문서로 확인합니다.)
2. VCFA Provider Portal → VCF Services → Data Services에서 DSM 엔드포인트(https + FQDN), 로컬 자격증명, DSM PEM 인증서를 입력해 연결합니다.
   - 검증: Recent Tasks에서 연결 성공 확인
3. VCF Services → Data Services에서 Data Service Policy를 생성합니다. 데이터 서비스 유형(Postgres), 버전, Infrastructure Policy를 지정합니다.
4. Services → Overview → (DSM Service) → Action → Publish로 조직에 게시합니다.

VCFA 연동으로 개발자는 카탈로그에서 셀프서비스 프로비저닝을, VI Admin은 Infrastructure/Data Service Policy로 가드레일을 유지합니다. DSM 9.1에서는 전 엔진(PostgreSQL/MySQL/SQL Server) 셀프서비스 프로비저닝이 지원됩니다.

출처: William Lam, MS-A2 VCF Lab; DSM 9.1 Release Notes.

---

## 4.5 PostgreSQL + pgvector 프로비저닝

### UI 경로 (개발자 셀프서비스)

1. VCFA Tenant Portal 로그인 → Build & Deploy → (Namespace) → Services → Database
2. Create 클릭, PostgreSQL 버전·리소스·Infrastructure Policy 선택
3. 배포 완료 후 Connection String 확보
4. DB 접속 후 pgvector 활성화

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### API / kubectl 경로 (파이프라인 통합)

1. VCFA Tenant Portal → Account → API Tokens에서 API 토큰 생성
2. VCF CLI 설치 후 토큰 환경변수 설정 및 컨텍스트 생성

```bash
export VCF_CLI_VCFA_API_TOKEN=[YOURTOKEN]
vcf context create <name> --endpoint <vcfa-fqdn> --api-token $VCF_CLI_VCFA_API_TOKEN --type cci --tenant-name <tenant>
vcf context use <name>:<namespace>:<project>
```

3. Secret + PostgreSQL 인스턴스 매니페스트 적용

```bash
kubectl apply -f postgres-db-secret.yaml
kubectl apply -f postgres-db.yaml
```

VCFA UI는 배포 시 우측에 동적 YAML 매니페스트를 생성하므로, 이를 저장해 GitOps 소스 관리 및 CLI 재배포에 활용할 수 있습니다.

출처: William Lam, MS-A2 VCF Lab; DSM REST/K8s API(developer.broadcom.com).

---

## 4.6 프로덕션 사이징 워크시트

HNSW 인덱스가 메모리에 상주해야 최적 성능이 나오므로, 메모리를 기준으로 사이징합니다.

입력값

| 입력 | 예시 |
|---|---|
| 벡터 수(N) | 500만 |
| 차원(D) | 1,536 (OpenAI text-embedding-3-small) |
| 벡터 타입 | vector(float32) 또는 halfvec(float16) |

산정 가이드

| 항목 | 산정 방식 | 비고 |
|---|---|---|
| 테이블 크기 | N × (4×D + 8) bytes (vector 기준) | halfvec은 2×D + 8 |
| HNSW 인덱스 크기 | 데이터 적재 후 `pg_relation_size()`로 실측 | m, ef_construction에 좌우 |
| shared_buffers | 인덱스 크기의 110% 이상 | 인덱스 메모리 상주 필수 |
| maintenance_work_mem | 4-8 GB | 인덱스 빌드 가속 |
| effective_cache_size | 가용 메모리의 75% | |
| max_parallel_maintenance_workers | CPU 코어 - 1 | 병렬 빌드(05 운영 보안 주의 참조) |

인덱스가 메모리에 상주하지 못하면 성능이 10-100배 저하될 수 있으므로, 데이터 적재 후 실측 인덱스 크기로 사이징을 재검증합니다. 규모별 권장 구성은 03 아키텍처와 07 PoC를 참조합니다.

---

## 4.7 PAIS 연결 (RAG용 벡터 DB 등록)

PAIS의 Data Indexing & Retrieval은 pgvector가 설치된 외부 PostgreSQL에 연결해 임베딩을 저장·검색합니다.

1. 프로비저닝한 PostgreSQL의 CA 인증서를 확보합니다.
   - DSM Admin UI → Databases → Postgres → Summary → View CA(PEM 다운로드), 또는 kubectl로 시크릿에서 추출
2. PAIS UI에 접속합니다. PAIS 인스턴스의 외부 IP는 ingress 서비스로 확인합니다.

```bash
kubectl get services    # pais-ingress-default 의 External IP 확인
```

3. PAIS UI에서 Knowledge Base를 생성하고 외부 PostgreSQL(pgvector) 연결 정보(엔드포인트, 자격증명, CA 인증서)를 등록합니다.
4. 데이터 소스(Google Drive, Confluence, SharePoint, S3)를 연결하고 청킹 전략·임베딩 모델·top-k·유사도 임계값을 설정합니다.
5. 인덱싱을 실행하고 갱신 정책(스케줄/온디맨드)을 지정합니다.

버전 주의: PAIS Data Indexing & Retrieval이 검증한 PostgreSQL/pgvector 조합과 DSM 기본 번들 버전이 다를 수 있습니다. 연결 전 01 버전 호환표와 PAIS 릴리스 노트를 확인합니다.

출처: Private AI Services Detailed Design(Broadcom TechDocs); Building your GenAI Agents on VCF with Private AI Services(VCF Blog).

---

## 4.8 배포 완료 검증

- DB 상태가 Healthy이며 vSphere Client의 DSM 뷰에서 노드 배치(Anti-Affinity) 확인
- `CREATE EXTENSION vector;` 성공 및 `SELECT '[1,2,3]'::vector;` 동작
- HA 구성 시 Primary/Replica/Monitor 3노드가 서로 다른 호스트에 배치
- 자동 백업 활성화 및 첫 백업 생성 확인
- PAIS 연결 시 Knowledge Base 인덱싱 1건 성공

---

## 출처

| 자료 | URL |
|---|---|
| DSM for PAIS 구성 랩 (William Lam) | https://williamlam.com/2025/09/ms-a2-vcf-9-0-lab-configuring-data-services-manager-dsm-for-vmware-private-ai-services-pais.html |
| DSM Getting Started (공식) | https://techdocs.broadcom.com/us/en/vmware-cis/dsm/data-services-manager/9-1.html |
| DSM 9.1 Release Notes | https://techdocs.broadcom.com/us/en/vmware-cis/dsm/data-services-manager/9-1/release-notes/vmware-data-services-manager-91-release-notes.html |
| Private AI Services Detailed Design | https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/design/design-library/private-ai-platform-detailed-design/private-ai-services.html |
| DSM REST/K8s API | https://developer.broadcom.com/xapis/vmware-data-services-manager/latest/ |

---
[← 이전: 03 VCF DSM 아키텍처](03-vcf-dsm-architecture.md) · [목차](../README.md) · [다음: 05 사용 및 RAG 구성 (Day-1 / Day-2) →](05-usage-rag.md)

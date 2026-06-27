# 05 — 데이터 거버넌스·프라이버시

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)을 참조하세요.
> 시리즈 인덱스: [시리즈 허브](../../README.md)

이 문서는 사내 폐쇄망(프라이빗) 환경에서 운영하는 생성형 AI 플랫폼의 데이터 거버넌스와 프라이버시 통제를 다룹니다. 기반 스택은 VMware Cloud Foundation(VCF) 9.1과 그 위에서 동작하는 VMware Private AI Foundation with NVIDIA(PAIF) 9.1, VMware Private AI Services(PAIS) 2.1입니다. 검색·생성에 쓰이는 벡터 데이터 계층은 시리즈 ② 가이드에서 다룬 Data Services Manager(DSM) 기반 PostgreSQL + pgvector를 전제합니다. PAIF에서 벡터DB가 pgvector(PostgreSQL) 위에서 DSM으로 배포·관리된다는 점은 Broadcom TechDocs와 VCF 블로그에서 확인됩니다([Broadcom TechDocs: Deploy a Vector Database for PAIF](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/deploying-rag-workloads-in-private-ai-foundation-with-nvidia/deploy-a-vector-database-for-paif.html), [VCF Blog: Initial Availability of PAIF](https://blogs.vmware.com/cloud-foundation/2024/03/18/announcing-initial-availability-of-vmware-private-ai-foundation-with-nvidia/)).

데이터 거버넌스는 "어떤 데이터가, 누구에게, 언제까지, 어디에서" 노출·보존·이동되는지를 규율하는 영역입니다. 본 문서는 인프라 계층(VCF/PAIF)과 데이터 계층(② 벡터DB)을 잇는 통제에 집중하며, 프롬프트 인젝션 방어·출력 검열 같은 애플리케이션 런타임 가드레일은 06 문서의 범위로 명시적으로 분리합니다(아래 5.7 경계 정리 참조).

용어 풀이를 먼저 둡니다. PII(Personally Identifiable Information)는 개인을 식별할 수 있는 정보를 뜻합니다. ACL(Access Control List)은 특정 자원에 누가 접근 가능한지 적은 권한 목록입니다. RAG(Retrieval-Augmented Generation)는 외부 문서를 검색해 답변에 보태는 방식입니다. 임베딩(embedding)은 문서를 숫자 벡터로 바꾼 표현입니다. GPU-Accelerated Workload Domain(약칭 GPU WLD)은 VCF에서 GPU 가속 AI 워크로드를 격리해 담는 공식 도메인 단위입니다.

## 5.1 데이터 거버넌스 책임 모델과 데이터 분류

데이터 거버넌스는 누가 무엇을 책임지는지부터 정해야 통제가 끊기지 않습니다. 프라이빗 AI 플랫폼에서는 인프라 소유자(VCF/GPU WLD 운영), 데이터 소유자(원본 시스템·KB 관리), 플랫폼 운영자(파이프라인·벡터DB), 애플리케이션 소유자(앱 가드레일)의 책임이 명확히 분리되어야 합니다.

| 역할 | 책임 범위 | 본 문서 관련 통제 |
|---|---|---|
| 인프라 소유자 | GPU WLD, 격리, 데이터 상주(residency) 경계 | 5.6 |
| 데이터 소유자 | 원본 ACL, 접근등급 부여, 보존·삭제 정책 | 5.2, 5.5 |
| 플랫폼 운영자 | 인입 파이프라인, 임베딩, 권한 재동기화 | 5.2, 5.3, 5.4 |
| 앱 소유자 | 출력 가드레일, 사용자 인증 컨텍스트 전달 | 06 문서 |

모든 데이터는 인입 전에 분류(classification) 등급이 부여되어야 합니다. 데이터 최소화 원칙(data minimization)은 목적에 필요한 데이터만 수집·보관하라는 NIST Privacy Framework의 핵심 통제(CT.DM 계열)로, AI 파이프라인에도 동일하게 적용됩니다([NIST Privacy Framework v1.0 Core](https://www.nist.gov/document/nist-privacy-framework-version-1-core-pdf), [NIST: Data Minimization 가이드](https://www.strac.io/blog/nist-privacy-framework-data-minimization)). 즉 "수집 가능하니까 인입"이 아니라 "RAG 목적에 필요하니까 인입"이 되어야 하며, 분류 등급에 따라 이후의 권한 필터·마스킹·보존기간이 결정됩니다.

권장 분류 체계는 최소 4단계(공개 / 내부 / 기밀 / 제한)이며, 각 문서·청크 메타데이터에 등급을 기록합니다. PII 포함 여부는 분류와 독립된 별도 플래그로 관리하는 편이 마스킹 정책 적용에 유리합니다.

---

## 5.2 문서 권한 거버넌스: 접근등급 메타데이터와 권한 재동기화

RAG의 가장 흔한 데이터 사고는 "사용자가 봐서는 안 될 문서가 검색 결과로 노출"되는 것입니다. OWASP는 이를 LLM02(민감정보 노출)와 LLM08(벡터·임베딩 취약점)의 교차 지점으로 분류합니다. 검색 단계에서 권한 없는 문서가 반환되면 곧바로 민감정보 노출로 이어집니다([OWASP LLM08: Vector and Embedding Weaknesses](https://www.indusface.com/learning/owasp-llm-vector-and-embedding-weaknesses/), [OWASP Top 10 for LLM Applications 2025](https://www.indusface.com/learning/owasp-top-10-llm/)).

### 접근등급 메타데이터

② 벡터DB(pgvector) 가이드의 스키마를 전제로, 각 청크 레코드에 원본 ACL을 투영한 권한 메타데이터를 함께 저장합니다. 핵심은 임베딩과 권한 정보를 같은 레코드에 묶어 검색 시점에 함께 평가하는 것입니다.

| 메타데이터 필드 | 용도 | 예시 |
|---|---|---|
| `classification` | 분류 등급 | `confidential` |
| `acl_principals` | 접근 허용 주체(그룹/역할 ID 배열) | `["grp-finance","role-auditor"]` |
| `source_system` | 원본 시스템 식별 | `sharepoint-fin` |
| `source_doc_id` | 원본 문서 키(재동기화 추적용) | `doc-48213` |
| `pii_flag` | PII 포함 여부 | `true` |
| `acl_synced_at` | 마지막 권한 동기화 시각 | `2026-06-15T09:00Z` |

### 권한 재동기화(가장 중요)

원본 시스템에서 권한이 회수되거나 문서가 삭제되어도, 한 번 인입된 벡터DB 레코드는 그대로 남습니다. 이 "고아 권한(stale permission)" 상태가 권한 회수된 문서를 계속 노출시키는 주된 경로입니다. 업계 가이드들은 원본 ACL을 벡터 메타데이터로 동기화하고, 오래된 동기화(stale sync)를 권한 우회의 핵심 위험으로 지목합니다([Document-Level RBAC for RAG Pipelines (Truto)](https://truto.one/blog/how-to-maintain-document-level-rbac-in-enterprise-rag-pipelines/), [RAG with Access Control (Pinecone)](https://www.pinecone.io/learn/rag-access-control/)).

재동기화 설계 원칙은 다음과 같습니다.

- 이벤트 기반 우선: 원본 시스템의 권한 변경·삭제 이벤트를 구독해 즉시 메타데이터를 갱신하거나 레코드를 무효화합니다. 권한 회수는 지연 없이 반영되어야 합니다.
- 주기적 전수 대사(reconciliation) 병행: 이벤트 유실에 대비해 `source_doc_id` 기준으로 원본 ACL과 벡터DB 메타데이터를 주기 대조하고, 불일치 시 회수 우선 정책으로 처리합니다.
- 회수는 "차단 후 정리": 권한 회수 신호가 오면 먼저 검색 노출을 차단(soft-delete/tombstone)하고, 이후 임베딩 잔존까지 제거(5.5 참조)합니다.
- 삭제 전파: 원본 문서 삭제는 벡터DB 레코드 삭제 + 잊혀질 권리 처리(5.5)로 연결됩니다.

> 주의: 권한 재동기화는 "검색 결과의 정확성"이 아니라 "권한 회수의 즉시성"을 보장하는 통제입니다. 동기화 주기가 길수록 회수된 권한이 노출되는 시간 창이 길어집니다. 구체적인 SLA(예: 회수 반영 목표 시간)는 조직 정책에 따르며, 운영 도구별 이벤트 지원 여부는 확인 필요입니다.

---

## 5.3 검색단 권한 필터링(Retrieval-Time Authorization)

권한 메타데이터를 저장했더라도, 검색 시점에 실제로 필터링하지 않으면 의미가 없습니다. 검색단 권한 필터링은 사용자의 인증 컨텍스트(소속 그룹·역할)를 검색 쿼리의 필터 조건으로 적용해, 권한 있는 청크만 후보로 삼는 통제입니다.

업계 표준은 사전 필터(pre-filter)와 사후 필터(post-filter)를 모두 쓰는 하이브리드입니다. 사전 필터는 벡터 검색 쿼리에 `acl_principals` 조건을 결합해 권한 없는 청크가 애초에 후보에 들지 않게 하고, 사후 필터는 반환 직전에 최종 인가를 재확인합니다([The Right Approach to Authorization in RAG (Oso)](https://www.osohq.com/post/right-approach-to-authorization-in-rag), [Item-Level Permissions in RAG](https://kirkryan.co.uk/item-level-permissions-in-rag-why-your-vector-database-needs-access-control/), [ACL and Metadata Filtering (Databricks)](https://community.databricks.com/t5/technical-blog/mastering-rag-chatbot-security-acl-and-metadata-filtering-with/ba-p/101946)).

| 단계 | 위치 | 역할 | 실패 시 영향 |
|---|---|---|---|
| 사전 필터 | 벡터 검색 쿼리(pgvector WHERE 절) | 권한 없는 청크 후보 배제, 성능·정확도 확보 | 권한 외 문서가 후보에 진입 |
| 사후 필터 | 검색 결과 반환 직전 | 최종 인가 재확인(2차 방어) | 사전 필터 누락분 노출 |

설계 원칙입니다.

- 사용자 신원은 앱 계층에서 검증한 인증 컨텍스트를 그대로 전달받습니다. 검색 계층이 신원을 추측하지 않습니다.
- 기본값은 거부(deny-by-default): 권한 메타데이터가 없거나 매칭되지 않으면 노출하지 않습니다.
- 필터 조건 자체가 사용자 입력으로 조작되지 않도록 서버 측에서 주입합니다(클라이언트가 보낸 권한 값을 신뢰하지 않음).
- 검색 로그에 "누가, 어떤 필터로, 무엇을 받았는지"를 남겨 추적 가능성을 확보합니다(5.7 검증과 연계).

규제 산업용 RAG 통제 가이드도 데이터 프라이버시·접근통제·인젝션 방어를 핵심 축으로 제시하며, 검색단 인가를 필수 통제로 봅니다([Secure RAG for Regulated Industries](https://www.blockchain-council.org/ai/secure-rag-for-regulated-industries-data-privacy-access-control-prompt-injection-defense/)).

---

## 5.4 프라이버시: PII 식별·마스킹·익명화(인입/출력 양단)

프라이버시 통제는 데이터가 들어올 때와 나갈 때 양쪽에서 작동해야 합니다. 한쪽만 막으면 다른 경로로 새어 나갑니다.

### 인입 양단(데이터 적재 시)

원본 문서를 청크로 나눠 임베딩하기 전에 PII를 식별하고 처리합니다. NIST는 식별 가능성을 낮추는 기법으로 억제(suppression, 불필요 PII 삭제), 가명화(pseudonymization, 분석 용도용 토큰화), 일반화(generalization), 잡음 추가, 집계를 제시합니다([NIST SP 800-188 De-Identifying Datasets](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-188.3pd.pdf), [NIST SP 800-122 PII 가이드](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-122.pdf)).

| 기법 | 동작 | 적합한 경우 |
|---|---|---|
| 억제/삭제(suppression) | 활용 목적 없는 PII 제거 | RAG에 불필요한 식별자 |
| 마스킹/편집(redaction) | 비정형 텍스트의 PII를 토큰으로 치환 | 본문에 섞인 이름·연락처 |
| 가명화(pseudonymization) | 식별자를 가역 토큰으로 대체 | 추후 재식별 필요한 분석 |
| 익명화(anonymization) | 비가역적으로 식별 불가 처리 | 장기 보존·재식별 불요 |

핵심 주의점: 마스킹은 임베딩 생성 이전에 이루어져야 합니다. 원문을 임베딩한 뒤 마스킹하면, 임베딩 벡터에 PII 의미가 남아 역전 공격(5.5)으로 복원될 수 있습니다.

### 출력 양단(응답 생성 시)

검색 결과나 모델 생성 응답에 PII가 섞여 나가는 것을 막는 출력 측 필터입니다. 인입 단에서 놓친 PII, 또는 여러 청크 조합으로 재구성되는 식별 정보를 마지막에 거릅니다. 다만 출력 가드레일의 런타임 구현(응답 검열·차단 로직)은 06 문서가 다루며, 본 문서는 "출력 단에서도 PII 통제가 필요하다"는 정책 경계까지를 규정합니다.

> 민감정보 분류와 PII 플래그(5.1, 5.2의 `pii_flag`)에 따라 마스킹 정책이 결정됩니다. 분류가 정확할수록 양단 필터의 오탐·미탐이 줄어듭니다.

---

## 5.5 데이터 수명주기: 보존·삭제·잊혀질 권리·임베딩 잔존

데이터는 인입으로 끝나지 않습니다. 보존 기간, 삭제, 잊혀질 권리(right to be forgotten), 그리고 임베딩에 남는 원문 잔존까지가 수명주기 통제 범위입니다.

### 임베딩 잔존 위험(반드시 인지)

임베딩 벡터는 단순한 숫자 배열로 보이지만, 원문의 의미를 충분히 담고 있어 역전(embedding inversion) 공격으로 원문을 상당 부분 복원할 수 있습니다. 연구에 따르면 인코더 모델 접근 없이도 텍스트 임베딩만으로 이름·진단명·이메일 등 정확한 토큰 시퀀스를 높은 정확도로 복원한 사례가 보고되었습니다. 또한 멤버십 추론(membership inference)으로 특정 문서가 색인에 포함됐는지 탐지할 수 있습니다([OWASP LLM08](https://www.indusface.com/learning/owasp-llm-vector-and-embedding-weaknesses/), [Transferable Embedding Inversion Attack](https://www.aimodels.fyi/papers/arxiv/transferable-embedding-inversion-attack-uncovering-privacy-risks), [Vector Embedding Inversion (AquilaX)](https://aquilax.ai/blog/vector-embedding-inversion-attacks)).

함의는 분명합니다. 원본 문서를 지워도 벡터DB의 임베딩을 함께 지우지 않으면 PII가 잔존합니다. "삭제"는 원본·청크·임베딩·캐시·로그까지 전파되어야 완결됩니다.

### 수명주기 통제 매트릭스

| 단계 | 통제 | 임베딩 잔존 고려 |
|---|---|---|
| 보존(retention) | 분류 등급별 보존기간 설정, 만료 시 자동 정리 | 만료 청크의 임베딩 동시 만료 |
| 삭제(deletion) | 원본 삭제 → 청크·임베딩·인덱스 삭제 전파 | 인덱스에서 물리 제거까지 확인 |
| 잊혀질 권리 | 특정 개인 데이터 식별 후 전 계층 삭제 | 해당 개인 관련 임베딩 전부 추적·제거 |
| 학습/파인튜닝 데이터 | 별도 거버넌스: 동의·출처·보존 기록 | 학습 데이터는 모델 가중치에 잔류(되돌리기 곤란) |

### 학습/파인튜닝 데이터 거버넌스

RAG는 검색 데이터를 모델에 재학습시키지 않고 외부에서 보태므로, 잊혀질 권리 대응이 상대적으로 용이합니다([VCF Blog: PAIF Technical Overview](https://blogs.vmware.com/cloud-foundation/2024/03/05/vmware-private-ai-foundation-with-nvidia-a-technical-overview/)). 반면 파인튜닝·학습에 투입된 데이터는 모델 가중치에 흡수되어 사후 삭제가 어렵습니다. 따라서 학습 데이터는 인입 전 PII 처리·동의·출처 기록을 더 엄격히 적용하고, 가능하면 "삭제가 필요할 수 있는 데이터는 학습이 아닌 RAG로" 두는 설계가 안전합니다(데이터 최소화 원칙의 연장).

---

## 5.6 데이터 상주·국외 이전 통제와 멀티테넌트 경계

프라이빗 AI를 선택하는 주된 이유 중 하나는 데이터를 통제된 경계 안에 유지하는 데 있습니다. 데이터 상주(residency)는 데이터가 물리적으로 어디에 저장되는지, 데이터 주권(sovereignty)은 어느 국가의 법이 적용되는지를 뜻합니다(둘은 구분됩니다)([Data Sovereignty vs Data Residency](https://destcert.com/resources/data-sovereignty-vs-data-residency/), [What Is Data Residency (Teradata)](https://www.teradata.com/insights/data-security/what-is-data-residency)).

### 에어갭과의 연계

VCF/PAIF는 인터넷 비연결(disconnected/air-gapped) 환경에서 RAG 워크로드를 배포할 수 있으며, 이는 데이터 국외 이전 위험을 구조적으로 차단하는 가장 확실한 통제입니다([Broadcom TechDocs: RAG on VKS in a Disconnected PAIF Environment](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/deploying-rag-workloads-in-private-ai-foundation-with-nvidia/deploy-a-rag-workload-on-a-vks-cluster-in-a-disconnected-private-ai-environment.html)). 외부 모델 API로의 동적 라우팅이 추론·재시도·페일오버 중 의도치 않게 국경을 넘는 위험은 일반 AI 게이트웨이의 알려진 문제인데, 폐쇄망 PAIF는 이 경로 자체를 없앱니다([AI Gateway Data Residency 비교](https://www.truefoundry.com/blog/ai-gateway-data-residency-comparison)).

상주 통제 원칙입니다.

- 데이터·임베딩·로그·백업이 모두 지정된 GPU-Accelerated Workload Domain과 그 스토리지 경계 안에 머무르도록 합니다.
- 외부 연동이 필요한 경우 국외 이전 여부를 정책으로 명시하고, 이전 경로·로그를 추적 가능하게 남깁니다(append-only 로깅 권장).
- 역할·지역 기준 RBAC로 누가 어느 경계의 데이터를 다룰 수 있는지 제한합니다([Cross-Border Data Residency (Airbyte)](https://airbyte.com/data-engineering-resources/cross-border-data-residency)).

### 멀티테넌트 데이터 경계

여러 부서·고객이 한 플랫폼을 공유할 때, 테넌트 간 데이터가 섞이지 않아야 합니다. OWASP LLM08은 교차 테넌트 누출(cross-tenant leakage)을 벡터·임베딩 취약점의 대표 사례로 꼽습니다([OWASP LLM08](https://www.indusface.com/learning/owasp-llm-vector-and-embedding-weaknesses/)).

| 격리 수준 | 방식 | 트레이드오프 |
|---|---|---|
| 강한 격리 | 테넌트별 별도 벡터DB 인스턴스/스키마 | 자원·운영 비용 증가, 누출 위험 최소 |
| 논리 격리 | 공유 인덱스 + `tenant_id` 메타데이터 필터 | 효율적이나 필터 누락 시 누출 위험 |

② 벡터DB가 다중 워크로드에서 공유될 수 있으므로([Broadcom TechDocs: Deploy a Vector Database for PAIF](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/deploying-rag-workloads-in-private-ai-foundation-with-nvidia/deploy-a-vector-database-for-paif.html)), 공유 시에는 `tenant_id`를 검색단 권한 필터(5.3)와 동일한 강제 조건으로 적용하고, 분류 등급이 높은 테넌트는 강한 격리를 우선 검토합니다. 인프라 계층 격리(GPU WLD)는 본 시리즈 02(네트워크·테넌트·GPU 격리)와 ④ RAG 아키텍처를 함께 참조하세요.

---

## 5.7 06 앱 가드레일과의 경계

### 06 문서와의 경계 정리

본 문서(05)는 데이터 계층의 거버넌스를 다루고, 06 문서는 애플리케이션 런타임 가드레일을 다룹니다. 경계를 분명히 합니다.

| 영역 | 05(본 문서) | 06(앱 가드레일) |
|---|---|---|
| 검색단 권한 필터 | 권한 메타데이터·재동기화·필터 정책 정의 | 사용자 인증 컨텍스트 검증·전달 |
| PII | 인입 마스킹, 분류·플래그 부여 | 출력 응답 검열·차단 런타임 |
| 프롬프트 인젝션 | (범위 밖) | 인젝션 방어·입력 검증 |
| 데이터 노출 | 저장·검색·잔존 관점 통제 | 응답 시점 노출 차단 |

요약하면, 05는 "데이터에 무엇을 새겨두고 어떻게 보존·필터·삭제할지"를, 06은 "런타임에 입력·출력을 어떻게 막을지"를 책임집니다. 검색단 권한 필터(5.3)는 두 문서가 맞물리는 지점으로, 정책은 05가, 신원 전달·런타임 적용은 06이 담당합니다.

## 5.8 검증 방법

아래 항목으로 데이터 거버넌스 통제가 실제로 작동하는지 검증합니다. 모든 검증은 근거·로그를 남겨 추적 가능해야 합니다.

| # | 검증 항목 | 방법 | 합격 기준 |
|---|---|---|---|
| 1 | 분류·메타데이터 완전성 | 표본 청크의 `classification`·`acl_principals`·`pii_flag` 존재 확인 | 필수 필드 누락 0건 |
| 2 | 권한 재동기화(회수) | 원본에서 권한 회수 후 검색 노출 차단까지 측정 | 정의된 SLA 내 노출 차단 |
| 3 | 삭제 전파 | 원본 삭제 후 청크·임베딩·인덱스 잔존 조회 | 전 계층 잔존 0건 |
| 4 | 검색단 권한 필터 | 권한 없는 사용자 컨텍스트로 기밀 문서 질의 | 권한 외 문서 반환 0건 |
| 5 | deny-by-default | 권한 메타데이터 없는 청크 질의 | 노출되지 않음 |
| 6 | 인입 PII 마스킹 | 적재 전후 표본 비교, 임베딩 전 마스킹 확인 | 정의된 PII 유형 미노출 |
| 7 | 임베딩 잔존 | 삭제 대상 문서의 임베딩 복원·멤버십 추론 시도 | 색인에서 미검출 |
| 8 | 멀티테넌트 경계 | 타 테넌트 컨텍스트로 교차 질의 | 교차 테넌트 반환 0건 |
| 9 | 데이터 상주 | 데이터·임베딩·로그·백업 위치 점검 | 지정 경계 외 저장 0건 |
| 10 | 추적성 | 검색·삭제·동기화 로그 무결성(append-only) 확인 | 분류→권한→처리 추적체인 무손실 |

검증은 1회성이 아니라 정기 회귀로 운영하며, 통제 변경(스키마·필터·동기화 주기) 시 재실행합니다. 검증 결과는 5.1 책임 모델의 데이터 소유자·플랫폼 운영자에게 보고되어 시정 조치로 연결되어야 합니다.

### 관련 문서

- ② 벡터DB 가이드: [② 벡터 DB](../../02-vectordb/README.md) — pgvector 스키마·DSM 운영
- ④ RAG 참조 아키텍처: [④ RAG](../../04-rag/README.md) — 검색 파이프라인·인프라 격리
- [06 앱 가드레일](06-app-guardrails.md): 런타임 입력·출력 통제(본 시리즈)

---

[← 이전: 04 에어갭·공급망·모델 출처](04-airgap-supply-chain.md) · [목차](../README.md) · [다음: 06 앱 계층 가드레일 →](06-app-guardrails.md)

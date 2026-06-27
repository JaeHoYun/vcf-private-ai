# A1 — 부록

[← 목차로](../README.md)

이 부록은 본문에 쓰인 약어·기술 용어를 풀어 둔 **용어집**과 참조 링크, 변경 이력을 담습니다. 본문에서 모르는 용어를 만나면 여기에서 찾으세요.

## A1.1 용어집

### 가. 이 가이드에서 쓰는 용어

| 용어 | 풀이 |
|------|------|
| 설계 결정(design decision) | 설계 중 둘 이상의 경로 가운데 하나를 골라야 하는 갈림길. 이 가이드의 중심 개념 |
| D1–D12 | 12개 설계 결정에 붙인 식별 번호 (→ [06.1](../docs/06-decision-forks.md)) |
| 결정 요인(driver) | 설계 결정을 끌고 가는 요구사항·제약 (워크로드·SLO·규제·예산·기존 자산·스킬셋 등) (→ [01](../docs/01-design-process.md)) |
| 설계 결정 기록(ADR) | Architecture Decision Record(아키텍처 의사결정 기록). 결정 하나의 선택·근거·트레이드오프를 남기는 한 장짜리 기록 (→ [06.3](../docs/06-decision-forks.md)) |
| 블루프린트(소·중·대) | 여러 설계 결정을 미리 묶어 둔 레퍼런스 설계 출발점 (→ [02](../docs/02-reference-blueprints.md)) |
| 그린필드(greenfield) · 브라운필드(brownfield) | 처음부터 새로 짓는 환경 / 기존 자산(온프렘 AI·MLOps)이 이미 있는 환경 (→ [08](../docs/08-brownfield-integration.md)) |
| 점진 통합(incremental integration) | 기존 환경을 한 번에 바꾸지 않고 단계로 나눠 PAIF로 옮기는 방식 (→ [08](../docs/08-brownfield-integration.md)) |
| 온프렘 회귀(repatriation) | 퍼블릭 클라우드에 둔 워크로드를 다시 사내(온프렘)로 들이는 것. 한국어 '회수'는 reclaim/unprovisioning으로 읽히기 쉬워 '온프렘 회귀'로 표기 (→ [08](../docs/08-brownfield-integration.md)) |

### 나. VCF·인프라

| 용어 | 풀이 |
|------|------|
| VCF (VMware Cloud Foundation) | 컴퓨트·스토리지·네트워크·쿠버네티스를 묶는 프라이빗 클라우드 플랫폼 |
| 통합(consolidated) 토폴로지 | 관리와 워크로드를 한 클러스터에 합친 최소 구성 (Private AI 비권고) |
| 표준(standard) 토폴로지 | 관리 도메인과 워크로드 도메인을 분리한 구성 (Private AI 기본) |
| 워크로드 도메인 | 워크로드 전용으로 분리한 클러스터 묶음 |
| VKS (vSphere Kubernetes Service) | VCF의 관리형 쿠버네티스 서비스 |
| Supervisor | vSphere에 쿠버네티스 제어부를 올린 계층 |
| vSAN | VCF에 통합된 하이퍼컨버지드(HCI) 스토리지 |
| vSAN ESA (Express Storage Architecture) | vSAN 차세대 고성능 아키텍처 |
| HCI (Hyper-Converged Infrastructure) | 컴퓨트와 스토리지를 노드 안에 통합한 방식 |
| SPBM (Storage Policy-Based Management) | 스토리지 정책 기반 관리 |
| 프린시플(principal)·보조(supplemental) 스토리지 | 도메인의 주 스토리지 / 나중에 더하는 추가 스토리지 |
| NFS · VMFS on FC · iSCSI · vVol | 외장 스토리지 프로토콜·포맷 (vVol = 어레이 통합 가상 볼륨) |
| SAN · NAS | 스토리지 영역 네트워크 / 네트워크 결합 스토리지 |
| NSX | VCF의 소프트웨어 정의 네트워킹 |
| 전송 영역(transport zone) | 네트워크 종류를 가르는 단위 — 오버레이(캡슐화) vs VLAN(물리 연결) |
| VPC (Virtual Private Cloud) | NSX의 테넌트 셀프서비스 네트워크 단위 |
| 마이크로세그멘테이션 | 워크로드 단위로 트래픽을 분리하는 세분화 방화벽 |
| AVI (NSX Advanced Load Balancer) | 소프트웨어 정의 L7 로드밸런서 |
| AKO (Avi Kubernetes Operator) | VKS에 Avi를 자동 연동하는 오퍼레이터 |
| Foundation Load Balancer | VCF VDS 네트워킹의 기본 L4 로드밸런서 |
| kube-vip · MetalLB | 쿠버네티스 클러스터 내장형 로드밸런서 |
| WAF (Web Application Firewall) | 웹 애플리케이션 방화벽 |
| L4 · L7 | 네트워크 4계층(전송) · 7계층(애플리케이션) |

### 다. GPU·모델 서빙

| 용어 | 풀이 |
|------|------|
| PAIF (Private AI Foundation with NVIDIA) | VCF 위에서 GPU·드라이버·모델을 표준화하는 AI 인프라 계층 |
| PAIS (Private AI Services) | 모델 서빙·RAG·에이전트를 관리형으로 올리는 서비스 계층 |
| vGPU | 가상 GPU. 호스트 GPU를 가상머신에 나눠 주는 방식 (NVAIE 라이선스 필요) |
| MIG (Multi-Instance GPU) | GPU를 하드웨어 수준으로 분할하는 기능 |
| 타임슬라이싱(time-slicing) | GPU를 시간 분할로 여러 VM이 공유 |
| DirectPath I/O · 패스스루(passthrough) | VM 하나에 물리 GPU 전체를 직접 할당 |
| NVLink | NVIDIA GPU 간 고속 연결 |
| DLVM (Deep Learning VM) | AI/ML 런타임이 사전 구성된 VM 이미지 |
| NIM (NVIDIA Inference Microservices) | NVIDIA가 최적화한 추론 마이크로서비스 |
| vLLM · Infinity · llama.cpp | 오픈소스 추론·임베딩 엔진 |
| NVAIE (NVIDIA AI Enterprise) | NVIDIA AI 소프트웨어 라이선스 |
| Model Runtime · Model Gallery · Agent Builder | PAIS의 모델 실행·카탈로그·에이전트 모듈 |
| MCP (Model Context Protocol) | 모델과 도구를 잇는 표준 인터페이스 |
| Artifact Mirroring Tool | 에어갭 환경에서 모델을 반입하는 도구·절차 (동작·명령 세부는 릴리스별로 다르므로 공식 문서로 확인) |
| MLOps | 모델 학습·배포·운영을 자동화하는 방법론·도구 묶음 (기존 온프렘 MLOps의 PAIF 통합은 → [08](../docs/08-brownfield-integration.md)) |

### 라. 데이터·RAG

| 용어 | 풀이 |
|------|------|
| RAG (Retrieval-Augmented Generation) | 검색으로 근거를 찾아 모델 답변에 보강하는 방식 |
| VectorDB · 벡터 검색 | 임베딩 벡터를 저장하고 유사도로 찾는 데이터베이스 |
| 임베딩(embedding) | 텍스트 등을 수치 벡터로 변환한 것 |
| pgvector | PostgreSQL의 벡터 검색 확장 |
| DSM (Data Services Manager) | VMware의 관리형 데이터 서비스(여기서는 PostgreSQL) |
| ANN (Approximate Nearest Neighbor) | 근사 최근접 이웃 검색 (대규모 벡터에 쓰는 빠른 검색) |

### 마. 운영·가용성

| 용어 | 풀이 |
|------|------|
| SLO · SLI | Service Level Objective(목표) · Indicator(지표) |
| TTFT (Time To First Token) | 요청 후 첫 토큰이 나오기까지의 지연 |
| E2E(end-to-end) 지연 | 요청부터 최종 응답까지 전체 지연 |
| RPO · RTO | Recovery Point(복구 시점) · Time(복구 시간) Objective |
| stretched cluster | 두 사이트에 걸쳐 동기 복제하는 클러스터 |
| FTT (Failures To Tolerate) | vSAN이 견디는 동시 장애 수 |
| HA · DR | High Availability(고가용성) · Disaster Recovery(재해 복구) |
| LCM (Lifecycle Management) | 업그레이드·패치 등 수명주기 관리 |
| 에어갭(air-gap) | 외부 네트워크와 물리적으로 끊어 격리한 환경 |
| Harbor | 컨테이너 이미지 레지스트리(에어갭에서는 내부 미러로 사용) |

### 바. 보안·신원

| 용어 | 풀이 |
|------|------|
| Identity Broker (vIDB) | VCF 컴포넌트의 신원을 중개하는 서비스 (내장 또는 외부) |
| IdP (Identity Provider) | 외부 신원 공급자 (Entra ID·Okta·Ping 등) |
| OIDC · OAuth 2.0 | 표준 인증·인가 프로토콜 |
| 페더레이션(federation) | 외부 IdP와 신원을 연동하는 것 |
| soft · hard 격리 | 네임스페이스 논리 격리 / 클러스터·도메인 물리 격리 |
| 멀티테넌시 | 여러 테넌트(팀·조직)가 한 플랫폼을 공유하는 것. 전사 확장 단계에서 팀·사업부별 격리와 자원 배분의 기준이 됨 (→ [08](../docs/08-brownfield-integration.md)) |

## A1.2 참조 링크

- [시리즈 허브](../../README.md) — 7편 전체 목록
- 형제 가이드: [① 인프라](../../01-infra/README.md) · [② VectorDB](../../02-vectordb/README.md) · [③ 서빙 API](../../03-serving-api/README.md) · [④ RAG](../../04-rag/README.md) · [⑤ 보안·거버넌스](../../05-security/README.md) · [⑥ 사이징·비용](../../06-sizing-cost/README.md)
- 상위 전략: [기업용 AX 방법론 가이드](https://github.com/JaeHoYun/enterprise-ax-methodology)
- 버전 단일 기준: [① README 기반 버전표](../../01-infra/README.md#기반-버전-source-of-truth)
- 공식 문서: [Broadcom TechDocs (VCF · Private AI)](https://techdocs.broadcom.com/)

## A1.3 변경 이력

| 버전 | 날짜 | 내용 |
|------|------|------|
| v0.1 | 2026-06 | 스캐폴드 — repo 골격(README · docs 01–07 · 부록) 신설 |
| v0.2 | 2026-06 | 설계 결정 본문 12건(D1–D12) · 카탈로그(06) · 설계 프로세스(01) · 블루프린트(02) · 리뷰 관문(07) 작성 |
| v0.3 | 2026-06 | 용어집(A1.1, 범주별 6종) · 참조 링크(A1.2) 작성. 'ADR'을 '설계 결정 기록(ADR)'으로 본문 전반 풀어 표기 |
| v0.4 | 2026-06 | 채워넣기 워크시트 신설 — 결정 요인 시트(필수도·출처·미는 결정) + 설계 결정 기록(D1–D12 요약표 + 상세 양식). README·01·07에서 연결 |
| v0.5 | 2026-06 | docs/08 신설 + 02·05 보강 — 브라운필드 통합 설계(기존 온프렘 AI·MLOps의 PAIF 점진 통합, 퍼블릭 처리, 전사 확장). 용어집에 브라운필드·점진 통합·회수·MLOps·멀티테넌시(전사 확장) 보강 |
| v0.5.1 | 2026-06 | 용어 표준화 — repatriation 의미의 '회수'를 '온프렘 회귀'로 통일(용어집 헤드워드 + docs/08). 한국어 '회수'의 reclaim/unprovisioning 오독 방지. 자원 reclaim·권한 revoke 용법은 유지. AX 방법론 가이드의 동일 표준과 정합 |

---
[← 이전: 09 역할과 책임 (RACI)](../docs/09-roles-raci.md) · [목차](../README.md)

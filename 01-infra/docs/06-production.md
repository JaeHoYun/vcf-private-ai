# 06 — 프로덕션 아키텍처

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.

PAIF 기반 AI 서비스를 프로덕션에서 운영하기 위한 **HA·DR·멀티테넌트·스케일링·보안**과, 9.1에서 강화된 **관측성·에어갭(Artifact Mirroring Tool)** 을 다룹니다.

---

## 6.1 개발 vs 프로덕션

동일한 PAIF 플랫폼 위에서 **vSphere Namespace로 환경을 분리**합니다. 운영 요구사항(HA·자동 스케일링·SLA·보안·백업)이 프로덕션에서 달라질 뿐입니다.

| 요구사항 | PAIF/PAIS 대응 |
|---------|---------------|
| 가용성 | Model Endpoint 다중 Replica, VKS HA |
| 확장성 | 자동 스케일링, GPU 동적 할당(DRA, Dynamic Resource Allocation) |
| 성능 | vLLM 0.11.2 최적화, 적정 모델 선택 |
| 보안 | OIDC, NSX 마이크로세그멘테이션, vDefend(Add-on) |
| 복구 | Harbor Replication, pgvector 백업, Artifact Mirroring Tool |
| 감사 | API/도구 호출 로깅, VCF Operations 연동 |

---

## 6.2 고가용성(HA)

### 3계층 보호

| 계층 | 기술 | 보호 대상 | 복구 방식 |
|------|------|----------|----------|
| Layer 1 | vSphere HA | ESXi 호스트, VM | 다른 호스트에서 VM 자동 재시작 |
| Layer 2 | VKS ReplicaSet | K8s Pod | 다른 노드에서 Pod 자동 재생성 |
| Layer 3 | PAIS 자동복구 | Model Endpoint | Health Check 실패 시 Replica 교체 |

### Model Endpoint HA

```
ML API Gateway (LB · Health Check · Failover)
   ├─▶ Replica #1 (vLLM + GPU, ESXi Host A)
   ├─▶ Replica #2 (vLLM + GPU, ESXi Host B)
   └─▶ Replica #3 (vLLM + GPU, ESXi Host C)
장애: Replica 장애→게이트웨이 재라우팅 / 호스트 장애→vSphere HA / GPU 장애→Health Check 제외
```

**ML API Gateway**는 PAIS가 제공하는 AI 전용 API 게이트웨이로, 일반 게이트웨이와 달리 LLM 추론에 맞춘 긴 타임아웃(60초+), SSE 네이티브 스트리밍, GPU 사용률 기반 자동 스케일링 연동, 모델명 기반 라우팅을 제공합니다.

**Replica 권장**: 개발 1 / 스테이징 1–2 / 프로덕션 2–3(N+1) / 미션크리티컬 3+. GPU 점유 = 비용이므로 자동 스케일링으로 최소 유지 후 부하 시 증설.

위 그림처럼 레플리카가 서로 다른 ESXi 호스트에 놓여야 호스트 장애가 한 레플리카에서 끝납니다. vCenter 9.1.1부터는 컴퓨트 정책으로 VM-VM anti-affinity 규칙을 걸어 VKS 워커 VM을 호스트 단위로 분산하도록 강제할 수 있고, 반대로 지연이 중요한 구성요소는 affinity로 같은 호스트에 모을 수 있습니다. 쿠버네티스 쪽 파드 anti-affinity와 함께 두면 파드와 VM 두 층에서 분산이 보장됩니다. 메모리 티어링(NVMe)을 쓰는 호스트에서는 9.1.1의 vSphere HA admission control이 DRAM을 따로 추적하므로, 페일오버 용량 계산에 티어드 메모리가 아니라 DRAM 기준이 쓰인다는 점을 사이징에 반영합니다([⑦ 04](../../07-design/docs/04-network-storage-availability.md)).

### pgvector(DSM, Data Services Manager) HA / VKS HA

DSM이 PostgreSQL Primary/Standby 동기 복제와 VIP 기반 자동 Failover를 관리합니다. VKS는 Control Plane 3노드(자동) + Worker Multi-node(최소 3 권장) + Deployment Replicas 2+로 구성합니다.

---

## 6.3 재해복구(DR)

**RTO**(복구 시간 목표) / **RPO**(데이터 손실 허용 시점)를 기준으로 패턴을 선택합니다.

| 패턴 | VCF 구현 | RTO | RPO | 비용 |
|------|---------|-----|-----|------|
| **Pilot Light** | Harbor Replication, pgvector 백업, PAIS 설정 GitOps | 수 시간 | 수 시간 | 낮음 |
| **Warm Standby** | Stretched Cluster/독립 사이트 + 실시간 복제 | 수십 분 | 수 분 | 중간 |
| **Active-Active** | NSX ALB(Avi, *Add-on*) GSLB + Harbor 양방향 복제 + pgvector 동기 | 수 분 이내 | 0 | 높음 |

### 백업 대상

| 대상 | 방법 |
|------|------|
| 모델 (Harbor) | Harbor Replication (DR 사이트 복제본) |
| 벡터 (pgvector/DSM) | DSM 스냅샷 / pg_dump / 스토리지 스냅샷 (대안: 원본 재인덱싱) |
| 설정 (PAIS) | API Export 또는 **GitOps로 코드화 (권장)** — Endpoint·Agent·KB·**MCP 도구/권한 정책** 포함 |
| 앱 데이터 (VKS/앱 DB) | 앱별 DB 백업 정책 |

> **9.1 메모:** MCP 도구 등록·권한 정책도 DR 자산입니다. GitOps로 코드화하면 DR 사이트 재구성과 감사가 쉬워집니다.

**Active-Active 주의:** pgvector 양방향 동기는 복잡합니다. 단방향 복제 또는 샤딩을 권장합니다. GSLB 사용 시 세션 일관성(Sticky/Session ID 라우팅), 모델 버전 동기화, KB 동기화를 확인하세요.

---

## 6.4 멀티 테넌트

vSphere Namespace로 팀/부서/고객을 격리합니다.

| 격리 수준 | 방법 | 비용효율 | 보안 |
|----------|------|:---:|:---:|
| Namespace 격리 | vSphere Namespace | 높음 | 중간 |
| Cluster 격리 | 별도 VKS | 중간 | 높음 |
| Workload Domain 격리 | 별도 PAIF WD | 낮음 | 최고 |

대부분 **Namespace 격리**로 충분하며, 규제·극보안 시 상위 격리를 검토합니다. 네임스페이스별 **리소스 쿼터**(`nvidia.com/gpu`, CPU/Memory/Storage, Pod/Service 수)로 GPU·컴퓨팅을 통제합니다. Harbor는 프로젝트 권한, DSM은 인스턴스/스키마로 격리합니다.

### 6.4.1 공유 모델 호스팅 — 테넌트마다 모델을 복제하지 않는 길 (PAIS 3.0부터)

2.1까지는 격리 단위마다 자기 모델 엔드포인트를 띄워야 했습니다. 같은 사내 표준 LLM을 사업부 다섯 곳이 쓰면 GPU도 다섯 벌이 들었습니다. PAIS 3.0은 한 인스턴스(provider)에서 서빙 중인 completion 또는 embedding 엔드포인트를 다른 PAIS 인스턴스와 네임스페이스(consumer)에서 참조하는 **공유 모델 호스팅**을 도입했습니다. 격리 경계는 그대로 두고 모델만 공유하는 방식입니다.

| 항목 | 내용 |
|------|------|
| 구조 | 조직 관리자가 중앙 provider 인스턴스에 모델 엔드포인트를 배포하고, 발급자 인증서와 API 자격증명을 consumer 쪽 관리자에게 전달. consumer 네임스페이스는 그 모델을 자기 엔드포인트처럼 참조 |
| 무엇이 공유되나 | completion과 embedding 모델 엔드포인트만. 지식베이스, 에이전트, MCP 도구, 세션은 공유되지 않고 각 네임스페이스에 남음 |
| 전제 | provider 인스턴스 인증이 VCF Automation 계정 또는 로컬 계정이어야 함(외부 OIDC 공급자 토큰은 인스턴스 간 접근에 쓸 수 없음). consumer 네임스페이스에 LoadBalancer 지원 Ingress. API 토큰 발급 활성화([③ 05 5.6절](../../03-serving-api/docs/05-auth-and-gateway.md)) |
| 데이터 격리 | 프롬프트와 응답은 consumer의 요청 경로로 오가지만 모델 가중치와 GPU는 provider가 소유. 지식베이스 데이터는 consumer 네임스페이스 밖으로 나가지 않음 |
| 언제 쓰나 | 사내 표준 LLM, 공통 임베딩 모델처럼 여러 테넌트가 같은 모델을 쓰는 경우. 사업부 전용 파인튜닝 모델은 그대로 로컬 배포 |
| 대가 | provider 엔드포인트가 멈추면 모든 consumer가 멈춤(단일 장애점). 한 consumer의 폭주가 다른 consumer의 지연으로 번짐(소음 이웃). provider 쪽 레플리카 수, 네임스페이스 쿼터, 관측으로 상쇄 |

> 설계 결정으로서의 위치는 [⑦ 03 3.4.1절](../../07-design/docs/03-compute-gpu-topology.md)과 [⑦ 05 테넌시](../../07-design/docs/05-tenancy-security.md)에서, GPU 절감 산식은 [⑥ 02 GPU 사이징](../../06-sizing-cost/docs/02-gpu-sizing.md)에서, API 관점의 연결 방식은 [③ 02 서빙 아키텍처](../../03-serving-api/docs/02-serving-api-architecture.md)에서 다룹니다. ([근거: Share a Model with Other Private AI Services Instances](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1/what-is-private-ai-services/share-a-model-with-other-private-ai-services-instances.html), [Connect to a Shared Model](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1/what-is-private-ai-services/connect-to-shared-private-ai-services-models.html))

---

## 6.5 스케일링

| 유형 | 대상 | 트리거 |
|------|------|--------|
| 수평(Replica 증감) | Model Endpoint, 앱 Pod | GPU/요청 수 |
| 수직(리소스 증대) | Pod, VM | 메모리/성능 |

자동 스케일링: `Min Replicas`(HA 보장) / `Max Replicas`(상한) / `Target GPU Utilization`(예 70%). 야간·주말은 Min으로 축소해 비용 최적화.

PAIS 3.0은 데이터 평면의 스케일 단위를 나눴습니다. Ingress를 모델 엔드포인트와 독립적으로 스케일할 수 있고, 커스텀 모델 게이트웨이를 주입할 수 있으며, Agent Builder와 Data Indexing을 개별로 켜고 끌 수 있습니다. 서빙만 쓰는 배포라면 두 모듈을 끄고 그만큼의 컨트롤 플레인 자원을 아낄 수 있습니다. 지연과 세션 임계 기반의 모델 자동 스케일링(Model Autoscaling)은 2026-09 Explore에서 발표됐으나 아직 릴리스 노트에 없으므로, 레플리카 수는 여전히 수동 설정으로 계획합니다([문서 00 0.7.4절](00-whats-new.md)).

### Cold Start

새 Replica 시작 시 모델 로딩 지연이 발생합니다.

| 단계 | 구성요소 | 소요 |
|------|---------|------|
| Pod 스케줄링 | VKS Scheduler | 수 초 |
| GPU 할당 | vGPU/DirectPath | 수 초–수십 초 |
| 컨테이너 시작 | Runtime | 수 초 |
| 모델 로딩 | vLLM + GPU Memory | 수십 초–수 분 |
| 워밍업 | vLLM | 수 초 |

A100 80GB 기준: 8B ≈ 30초–1분, 70B ≈ 2–5분. **완화:** Min Replicas ≥ 1, 워밍업 요청, 적정 모델 선택(8B로 충분하면 70B 금지), 이미지 사전 Pull. Enhanced DirectPath I/O는 GPU 직접 액세스로 약간 빠릅니다.

---

## 6.6 워크로드 기반 사이징

"GPU를 몇 장, Replica를 몇 개 둘 것인가"는 **동시성·처리량·모델 크기·컨텍스트 길이**에서 역산합니다. 아래는 의사결정용 출발점이며, **실제 수치는 모델·양자화·시퀀스 길이·하드웨어에 따라 크게 달라지므로 반드시 실측이 필요합니다.**

핵심 흐름만 요약합니다.

- **GPU 수**: 피크 동시성·목표 처리량 → 단일 Replica 부하 실측 → `필요 Replica ≈ ⌈피크 동시성 / Replica당 안전 동시성⌉`(+HA N+1), 필요 GPU ≈ Replica 수 × Replica당 GPU(단일 GPU 미적합 시 `tensor-parallel`).
- **GPU 메모리**: 모델 가중치(FP16 ≈ 파라미터×2바이트) + KV 캐시(동시성·컨텍스트 길이에 비례) + 헤드룸. 양자화(GPTQ·AWQ·FP8)로 가중치 절감.
- **vCPU/RAM**: 토크나이즈·전처리·요청 처리용 호스트 자원 확보, 부하 테스트로 조정.

> **상세 사이징의 기준 문서는 [⑥ 사이징·용량·비용 가이드](../../06-sizing-cost/README.md)입니다** — 워크로드→GPU/노드/클러스터 환산 워크시트, VKS 클러스터 사이징, 스토리지·네트워크 용량, 용량 계획, TCO를 다룹니다. 본 절은 출발점 요약이며, 모든 수치는 환경별로 상이하므로 실측이 전제입니다 ([vLLM — Optimization and Tuning](https://docs.vllm.ai/en/stable/configuration/optimization/)).

---

## 6.7 모델 라이프사이클 (버전·승격·롤백·평가·재학습)

Model Endpoint는 **버전 → 평가 → 승격 → (필요 시) 롤백 → 재학습**의 순환으로 운영합니다. PAIS의 Model Gallery(Harbor 기반)와 GitOps로 코드화된 설정이 이 순환의 기반이 됩니다.

| 단계 | 핵심 활동 | PAIF/PAIS 연계 |
|------|----------|---------------|
| **버전 관리** | 모델·가중치·설정·프롬프트를 버전으로 고정(재현 가능) | Model Gallery(Harbor) 태그, 설정은 GitOps 코드화(§6.3) |
| **평가(게이트)** | 승격 전 정확도·관련성·안전성·지연 기준 충족 검증 | Agent Playground·오프라인 평가셋, 통과 기준을 승격 게이트로 |
| **승격(Promotion)** | DEV → STAGING → PROD로 단계 승격, 트래픽 점진 전환 | 네임스페이스 분리(§6.4), Replica 점진 전환·카나리 |
| **롤백(Rollback)** | 지표 저하 시 직전 안정 버전으로 복귀 | 이전 버전 태그 유지 → 빠른 재배포, 자동(임계치)·수동(승인) 병행 |
| **재학습 트리거** | 데이터 드리프트·성능 저하·신규 데이터 발생 시 재학습 | 관측성 지표(§6.8) 임계치 → 파이프라인 트리거, 결과는 다시 버전 관리로 |

> 위는 일반 MLOps 모델 라이프사이클 원칙입니다(모델 레지스트리의 stage 전환·평가 게이트·자동/수동 롤백·드리프트 기반 재학습). 운영 시 **각 전환마다 평가 기준과 책임자 승인을 문서로 명시**하고, 롤백을 위해 직전 버전 아티팩트를 항상 보존하세요. 부수효과가 큰 PROD 승격·롤백은 변경관리 절차와 연동하는 것을 권장합니다.

> **에이전트 포함 시:** 모델뿐 아니라 KB 버전·프롬프트·**MCP 도구/권한 정책**도 함께 버전·롤백 대상입니다(§6.3 DR 자산, [문서 05 §5.5](05-agents-mcp.md#55-거버넌스-가장-중요)).

---

## 6.8 관측성 (9.1 강화, 9.1.1 확장)

PAIS 2.1부터 AI 워크로드 관측성을 기본 제공하며, 3.0은 그 범위를 넓혔습니다.

### 모델·GPU 메트릭 대시보드

VCF Operations 콘솔에서 나머지 인프라와 **같은 화면**으로 조회합니다.

| 분류 | 지표 |
|------|------|
| 모델 메트릭 | 캐시 활용률, 토큰 처리량(throughput), 지연(latency) |
| GPU 메트릭 | 사용률(utilization), 메모리 압력, 온도, 전력 |
| 모델 수준 가시성 | Endpoint별 요청·오류율, Replica 상태 |

### LLM 트레이싱 (OpenTelemetry)

OTel Collector로 에이전트 요청을 단계별(RAG 검색 → MCP 도구 호출 → LLM 추론)로 추적합니다 → [문서 05 §5.6](05-agents-mcp.md#56-에이전트-관측성-llm-트레이싱).

> **알려진 이슈(2.1):** 일부 환경에서 LLM 트레이스가 OTel Collector에 표시되지 않을 수 있습니다(PAIS 2.1 릴리스 노트). 트레이스 수신을 검증하고, 미표시 시 릴리스 노트 Workaround를 확인하세요.

> **9.0.x 대비:** 모니터링을 직접 구축(Prometheus/Grafana/DCGM)하던 부분이 9.1에서 **플랫폼 기본 기능**으로 들어왔습니다. 자체 스택은 보완 용도로 병행할 수 있습니다.

### PAIS 3.0과 VCF 9.1.1에서 더해진 것

| 항목 | 내용 | 운영 함의 |
|------|------|-----------|
| 실시간 대시보드 | 모델과 에이전트 메트릭을 PAIS UI에서 실시간으로 조회, 추론 백엔드 헬스 실시간 노출 | Grafana 없이도 1차 확인이 가능해짐 |
| Grafana 예시 구성 | 조직이 배포한 Grafana에 올릴 예시 대시보드 제공 | 2.1의 "직접 배포" 전제는 유지되나 출발점이 생김 |
| 트레이싱 범위 | LLM 상호작용 전체 트레이싱 | 에이전트 단계별 추적이 넓어짐 |
| 임베딩 메트릭 | 문서 임베딩 진행과 품질 메트릭 개선 | 지식베이스 인덱싱 상태를 관측으로 확인 |
| 원격 모델 토큰 추적 | 원격 클라우드 모델의 토큰 사용량 추적 | 실비이자 반출 증빙([⑤ 05 5.6절](../../05-security/docs/05-data-governance.md)) |
| 수집 시작 시점 변경 | Prometheus 수집이 PAIS 관리 VKS 클러스터 가용 이후 시작 | 설치와 업그레이드 직후 메트릭 공백 구간을 알람에서 유예([문서 10 10.2.4절](10-operations.md)) |
| VCF Operations 9.1.1 | VKS 메트릭 OpenTelemetry 2초 간격 스트리밍, 멀티클러스터 VKS 뷰, Grafana 대시보드 임포트, AI Assistant | 인프라 관측과 AI 관측이 같은 표준(OTel)으로 맞춰지고, AI Assistant가 PAIS 모델을 백엔드로 진단을 도움([문서 10 10.4.4절](10-operations.md)) |

---

## 6.9 에어갭(Air-Gapped) 환경 — Artifact Mirroring Tool (9.1 신규)

방산·금융·공공·일부 제조처럼 **외부망 연결이 불가**한 환경을 위해 PAIS 2.1은 **Artifact Mirroring Tool**을 제공합니다.

```
[ 인터넷 연결 미러 호스트 ]                 [ 에어갭 환경 (내부망) ]
  NGC/Harbor/모델/컨테이너   ──Artifact Mirroring Tool 미러──▶   내부 Harbor + PAIS 2.1
  아티팩트 다운로드·패키징      (오프라인       → GPU 기반 Model Endpoint
                                반입)          → 에이전트(MCP는 내부 시스템만)
```

| 항목 | 에어갭 구성 |
|------|------------|
| 아티팩트 반입 | Artifact Mirroring Tool로 모델·컨테이너·드라이버 미러링 후 오프라인 반입 |
| 모델 소싱 | NGC/NIM 컨테이너 사전 반입, 내부 Harbor에서 Pull |
| 데이터 소스 | 내부 시스템만 (사내 PostgreSQL·SharePoint 등) |
| MCP 연동 | **내부 시스템으로 한정** (외부 SaaS 불가) |
| 업데이트 | 정기적 미러 갱신 절차 수립 |

> **9.0.x 대비 핵심:** 과거에는 Harbor 수동 구성 수준의 air-gap 지원이었으나, 9.1 Artifact Mirroring Tool은 **GPU 기반 Model Endpoint와 에이전트를 포함한 풀 Private AI 기능**을 폐쇄망에서 구동합니다. 산업별 적용은 [문서 08](08-industry.md)을 참조하세요.

> **버전 적용 범위:** Artifact Mirroring Tool은 PAIS(Private AI Services) 2.1 기능으로, **VCF 9.0.2와 9.1 모두에서 제공**됩니다. 따라서 본 절은 "9.1 신규"라기보다 "PAIS 2.1 기능"으로 이해하는 것이 정확하며, 9.1 고유 추가분은 VCF Automation UI 기반 PAIS 관리입니다 ([VMware Private AI Services Release Notes](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-release-notes/vmware-private-ai-services-release-notes.html)).

### 6.9.1 미러링 구조와 출처 레지스트리 (설계)

Artifact Mirroring Tool은 **PAIS Services 패키지와 NVIDIA GPU Operator 구성요소를 내부 Harbor 프로젝트(OCI 레지스트리)로 미러링**합니다. 인터넷 측에서 끌어오는 아티팩트의 출처 레지스트리는 다음과 같습니다 ([Upload the Private AI Services Components to a Disconnected Environment](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/deploying-private-ai-foundation-with-nvidia/installing-and-configuring-private-ai-services/upload-the-private-ai-services-components-to-a-disconnected-environment.html)).

| 출처 레지스트리 | 미러링 대상 |
|----------------|-----------|
| `pais-docker.packages.broadcom.com` | PAIS 패키지 |
| `nvcr.io` | NVIDIA 컨테이너 이미지 |
| `helm.ngc.nvidia.com` | GPU Operator Helm 차트 |
| `registry.k8s.io` | Node Feature Discovery |

흐름은 **미러 호스트에서 `vcf pais amt pull`로 아티팩트를 끌어와 오프라인 반입 → 내부망에서 `vcf pais amt push`로 내부 Harbor에 적재 → 모델 갤러리(`vcf pais models`) 적재 → Supervisor에 PAIS 설치**입니다. 용량 경계는 플랫폼 Harbor 프로젝트 **20GB**(PAIS 아티팩트)이며 모델 갤러리·NIM 이미지는 별도 산정합니다(§6.9.2). Artifact Mirroring Tool이 서명·다이제스트를 자동 검증한다는 공식 근거는 없으므로, 반입 아티팩트의 무결성·공급망 점검은 **운영자가 수행하는 별도 절차**입니다(§6.9.2 보안 가이드 딥링크).

> **실행 런북은 [문서 10 §10.1.8](10-operations.md)** 에 있습니다 — 선행조건, 절차 단계 표, `docker login` · `vcf pais amt pull/push` · `vcf pais models` 명령 예시, Supervisor 설치까지의 엔드투엔드 실행은 Day-2 운영으로 이전했습니다. 이 절은 "왜·무엇을·어디로"를, 문서 10은 "어떻게 실행하나"를 다룹니다.

### 6.9.2 갱신·운영과 인접 가이드

**미러 갱신**은 새 BOM(Bill of Materials)이나 갱신된 `pais.yml`을 기준으로 `pull` → 반입 → `push` 경로(실행 절차는 [문서 10 §10.1.8](10-operations.md))를 재실행하는 방식입니다. 구체적인 갱신 주기는 공식 수치가 없으므로 단정하지 않습니다 — **권장 주기는 환경(보안 정책·BOM 변경 빈도·반입 절차 비용)에 맞춰 수립**하세요(이는 추론에 따른 운영 권고입니다).

| 운영 항목 | 권장 처리 |
|----------|----------|
| 정기 갱신 | 새 BOM/`pais.yml` 기준 `pull`→반입→`push` 재실행(주기는 환경별 수립) |
| 무결성·공급망 | 운영자가 수행하는 점검 → ⑤ 보안 가이드 딥링크 |
| 반입·store 용량 | 플랫폼 Harbor 프로젝트 20GB(PAIS 아티팩트) + 모델/NIM 별도 → ⑥ 사이징 가이드 딥링크 |

**인접 가이드 딥링크:**

- 공급망·무결성 점검(반입 아티팩트 검증, 서명·다이제스트 운영 절차): [⑤ 보안·거버넌스 가이드 — 에어갭 공급망](../../05-security/docs/04-airgap-supply-chain.md)
- 미러 store/반입 사이징(20GB 기준 산정, 모델·NIM 저장 용량, 네트워크 반입 계획): [⑥ 사이징·용량·비용 가이드 — 스토리지·네트워크 사이징](../../06-sizing-cost/docs/05-storage-network-sizing.md)

> **용량 구분 주의:** 위 **20GB는 플랫폼 Harbor 프로젝트의 PAIS 아티팩트 용량**이며, 모델 갤러리·NIM 이미지 저장 용량과는 **별개로 산정**합니다. 모델/NIM 저장 사이징은 ⑥ 가이드를 따르세요.

---

## 6.10 네트워크 및 보안

```
[외부] → NSX Edge/LB (TLS Termination · WAF · DDoS)
       → NSX VPC (Namespace Segment)
            VKS Pods → PAIS Pods → pgvector  (Network Policy로 통신 제어)
       → Management Network (vCenter·NSX Manager·VCF: 관리 접근만)
```

| 계층 | 보안 요소 |
|------|----------|
| 경계 | Firewall, WAF, DDoS |
| 네트워크 | NSX 마이크로세그멘테이션 (vDefend는 Add-on) |
| 인증/인가 | OIDC, RBAC |
| 데이터 | TLS, 암호화 |
| 감사 | 로깅, 모니터링 |

### 프로덕션 보안 체크리스트

```
- 네트워크: 외부/내부 TLS, 불필요 포트 차단, Network Policy
- 인증/인가: OIDC, 서비스 계정 최소 권한, 토큰 정기 갱신, 관리 MFA
- 데이터: 민감 데이터 암호화, PII 마스킹, 백업 암호화, 보관 정책
- AI 특화: 프롬프트 인젝션 방어, 입출력 필터링, Harbor 접근 제어, Rate Limiting
- MCP 특화(9.1): 도구 화이트리스트, 최소 권한, 쓰기 작업 승인 게이트, 도구 호출 감사
- 감사/모니터링: 모든 API·도구 호출 로깅, 이상 탐지 알림, 정기 보안 감사
```

---

## 6.11 프로덕션 배포 체크리스트

```
인프라:   - PAIF WD - PROD 네임스페이스+쿼터 - Harbor 모델 Push - DSM HA - VKS Multi-node - 네트워크 정책
PAIS:     - Model Endpoint(Replicas≥2) - Embedding Endpoint - KB 인덱싱 - Agent+Playground - (MCP 도구 거버넌스) - 자동 스케일링
앱:       - 이미지 빌드/Push - Deployment/Service/Ingress - ConfigMap/Secret - Health Check - Resource Limits
테스트:   - 기능 - 부하 - 장애(Chaos) - 보안 - SLA
운영:     - 관측성 대시보드 - LLM 트레이싱 - 알림 규칙 - 백업 정책 - Runbook - On-call
```

배포 후 검증: 가용성(200 OK), 응답시간(예 P95<3초), 에러율(<0.1%), 자동 스케일링, 로깅/알림 수신.

---

## 6.12 핵심 요약

1. **HA** — Model Endpoint Replicas≥2, DSM HA, VKS Multi-node, 3계층 보호(vSphere HA→VKS→PAIS)
2. **DR** — Harbor/pgvector/설정(+MCP 정책)/앱 데이터 백업, Pilot Light→Warm Standby→Active-Active
3. **멀티테넌트** — Namespace 격리 + 리소스 쿼터
4. **스케일링** — 자동 스케일링, Cold Start 대비 Min Replicas≥1, DRA 활용
5. **관측성(9.1)** — 모델·GPU 대시보드 + OTel LLM 트레이싱 기본 제공
6. **에어갭(9.1)** — Artifact Mirroring Tool로 폐쇄망 풀 AI 구동
7. **보안** — TLS·OIDC·RBAC + AI/MCP 특화 통제

> PAIS를 활용하면 프로덕션 복잡성의 상당 부분을 플랫폼이 처리합니다. 인프라팀은 HA/DR/보안·**거버넌스 정책**에 집중하고, 일상 운영은 PAIS 자동화·관측성에 맡기세요.

---

[← 이전: 05 에이전트·MCP·거버넌스](05-agents-mcp.md) · [목차](../README.md) · [다음: 07 GPUaaS (PAIF GPU 자원 서비스) →](07-gpuaas.md)

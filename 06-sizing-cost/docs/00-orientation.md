# 00 — 오리엔테이션 (독자 가이드·선수지식·용어집·개념 미니맵)

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.
> 시리즈 인덱스: [시리즈 허브](../../README.md)

이 문서는 **VCF/PAIF가 처음인 독자**가 본 가이드에서 길을 잃지 않도록 돕는 출발점입니다. 어디부터 읽을지(독자별 경로), 무엇을 알고 있으면 좋은지(선수지식), 전체 그림(개념 미니맵), 모르는 용어(미니 용어집)를 정리했습니다.

---

## 0.1 독자별 경로 — 어디부터 읽나

사이징은 임원·기획자·아키텍트·인프라 담당이 서로 다른 깊이로 들여다보는 주제입니다. 자신의 목적에 맞는 경로로 들어가세요.

| 독자 | 목적 | 권장 경로 | 얻는 산출물 |
|---|---|---|---|
| 임원/의사결정자 | go/no-go·예산 윤곽 | [E0 임원 브리프](E0-executive-brief.md) → [07.6 손익분기](07-tco-cost-model.md#76-퍼블릭-gpu-클라우드-vs-온프레미스-paif-비교-프레임) | 의사결정 틀, 예산 레인지 개념 |
| IT기획자 | 사업계획용 규모·예산 | [부록 A2 입력 환산](../appendix/A2-inputs-and-defaults.md) → [08 전 과정 예제](08-reference-scenario.md) → [07 TCO](07-tco-cost-model.md) → [부록 A3 RFQ(견적 요청)](../appendix/A3-rfq-quote-checklist.md) | 규모·예산 초안 |
| 개발자/아키텍트 | 기술 사이징·클러스터 설계 | [01 방법론](01-sizing-methodology.md) → [02 GPU](02-gpu-sizing.md)·[03 컴퓨트](03-compute-memory-sizing.md) → [04 클러스터](04-vks-cluster-sizing.md) (+[부록 A1](../appendix/A1-first-order-reference.md)) | 사이징·토폴로지 설계 |
| 인프라 담당 | 구축·용량 운영 | [04 클러스터](04-vks-cluster-sizing.md) → [05 스토리지·네트워크](05-storage-network-sizing.md) → [06 용량 계획](06-capacity-planning.md) | 구축·증설 트리거 운영 |

> 처음부터 끝까지 한 시나리오로 보고 싶다면 [08 — 레퍼런스 시나리오](08-reference-scenario.md)가 가장 빠릅니다.

---

## 0.2 선수지식 체크리스트

본 가이드는 다음 개념을 **가볍게라도 알고 있으면** 훨씬 수월합니다. 모르면 0.4 용어집 또는 표의 학습 경로를 먼저 보세요.

| 영역 | 알아두면 좋은 것 | 모를 때 |
|---|---|---|
| LLM 추론 | 모델 가중치·KV 캐시·토큰·정밀도(FP16/FP8/INT8) | 0.4 용어집 + [01.2](01-sizing-methodology.md#12-워크로드-분류와-자원-특성) |
| 서빙 | vLLM, Replica, 동시성/QPS, TTFT/TPOT | 0.4 용어집 + [02.5](02-gpu-sizing.md#25-처리량지연-목표--gpu-수replica-환산) |
| 쿠버네티스 | 노드/파드, requests/limits, taint, 오토스케일 | 0.4 용어집 + 외부 K8s 입문 자료 |
| VCF/vSphere | 클러스터·호스트·vSAN·NSX·VM Class | 0.4 용어집 + [① 인프라](../../01-infra/README.md) |
| RAG | 임베딩·벡터DB·리랭커·청킹 | 0.4 용어집 + [④ RAG](../../04-rag/README.md) |

> 깊은 아키텍처·구축 절차는 본 가이드(사이징·비용)의 범위 밖이며, 시리즈 ①–⑤가 담당합니다. 본 가이드는 "얼마나·몇 개·얼마"에 집중합니다.

---

## 0.3 개념 미니맵 — 전체 흐름 개관

사이징은 워크로드 요구를 자원 → 노드 → 클러스터 → 비용으로 환산하는 단방향 흐름입니다.

```
[워크로드 정의]            무엇을, 얼마나          → 01, 부록 A2
   ↓ (모델·동시성·컨텍스트·SLA)
[자원 산정]                GPU메모리·처리량·CPU·RAM·스토리지·네트워크
   ↓                       → 02(GPU), 03(컴퓨트), 05(스토리지·네트워크), 부록 A1
[노드 매핑]                GPU 분할(MIG/vGPU)·노드 사양
   ↓                       → 02, 03
[클러스터 구성]            VKS 노드 풀·컨트롤 플레인·HA·한도
   ↓                       → 04
[용량·비용]                헤드룸·증설 트리거 / TCO·단가
                           → 06(용량), 07(TCO), 부록 A3(견적)

   (전 과정 예제: 08)      (전 과정 검증: 각 문서 "검증·실측" 절 + 06.5 PoC 로드맵)
```

핵심 원칙 셋:
- **추정으로 시작하되 실측으로 보정**합니다([01.5](01-sizing-methodology.md#15-핵심-원칙-추정으로-시작하되-실측으로-보정)). 구매 전 예산 단계의 출발 숫자는 [부록 A1](../appendix/A1-first-order-reference.md)에 격리되어 있습니다.
- **피크 기준 + 헤드룸**으로 잡습니다(평균이 아니라 피크).
- **불확실한 값은 "확인 필요"로 남기고** 진행하다 실측 후 교체합니다.

---

## 0.4 미니 용어집

처음 만나면 막히는 약어·용어를 한 줄로 풀었습니다(상세는 각 문서 본문).

### 플랫폼

| 용어 | 한 줄 풀이 |
|---|---|
| VCF (VMware Cloud Foundation) | 컴퓨트·스토리지·네트워크·관리를 묶은 통합 프라이빗 클라우드 플랫폼 |
| PAIF (Private AI Foundation with NVIDIA) | VCF 위에서 NVIDIA GPU로 AI를 돌리는 솔루션(VCF 구독에 포함) |
| PAIS (Private AI Services) | PAIF 위 상위 서비스(Agent Builder·Model Runtime·MCP·Artifact Mirroring Tool 등) |
| VKS (vSphere Kubernetes Service) | VCF 위에서 도는 프로덕션용 쿠버네티스 서비스 |
| Supervisor | vSphere에 심은 쿠버네티스 제어부. VKS 클러스터를 프로비저닝 |
| vSphere Namespace | 자원·정책 경계(테넌트/프로젝트 단위) |
| vSphere Zone | 물리 장애 도메인. 3-Zone으로 고가용성(HA) |
| Workload Domain (GPU-Accelerated) | 워크로드를 담는 자원 묶음. GPU 가속용은 GPU WLD |
| ESX(i) host | 하이퍼바이저가 도는 물리 서버 1대 |
| VM Class | 노드 1대의 vCPU·RAM·(v)GPU 사양 템플릿 |
| vSAN / NSX | 분산 스토리지 / 네트워크 가상화 |
| Harbor | 컨테이너·모델 레지스트리(저장소) |
| DSM (Data Services Manager) | DB 자동화(pgvector 등). VCF Advanced Service |
| NVAIE (NVIDIA AI Enterprise) | NVIDIA의 GPU당 라이선스(드라이버·NGC 컨테이너 사용) |
| Artifact Mirroring Tool | 에어갭(망분리) 환경으로 아티팩트를 복제·반입 |

### GPU 공유

| 용어 | 한 줄 풀이 |
|---|---|
| MIG (Multi-Instance GPU) | GPU 1장을 하드웨어로 쪼개 격리 |
| vGPU (타임슬라이스) | GPU를 시간 분할로 공유 |
| DirectPath I/O | GPU 1장 전체를 VM에 전용 할당(패스스루) |
| DRA (Dynamic Resource Allocation) | GPU를 선언적으로 청구하는 쿠버네티스 표준 |

### 추론·RAG

| 용어 | 한 줄 풀이 |
|---|---|
| 가중치(Weights) | 모델 파라미터. VRAM의 고정 비용 |
| KV 캐시 | 생성된 토큰의 Key/Value 저장. 동시성·컨텍스트에 비례하는 가변 비용 |
| 정밀도(FP16/FP8/INT8/INT4) | 파라미터를 표현하는 비트 폭. 낮을수록 메모리↓ |
| 양자화 | 저정밀도로 변환해 VRAM 절감(품질 트레이드오프) |
| TTFT / TPOT(ITL) | 첫 토큰까지 시간 / 토큰 간 지연 |
| Replica | 모델 서빙 인스턴스 1개 |
| vLLM | 대표적 LLM 추론 서빙 엔진 |
| 임베딩 / 리랭커 | 텍스트를 벡터로 변환 / 검색 결과 재정렬 |
| pgvector / HNSW | PostgreSQL 벡터 확장 / 벡터 검색 인덱스 구조 |

### 비용

| 용어 | 한 줄 풀이 |
|---|---|
| TCO | 총소유비용(하드웨어+라이선스+운영을 기간으로 합산) |
| CapEx / OpEx | 일회성 자본 지출 / 지속 운영 지출 |
| 쇼백 / 차지백 | 비용을 팀별로 보여주기 / 실제 청구 |
| 코어 최소수량 | CPU당 적용되는 라이선스 최소 코어 수 규칙 |

---

## 0.5 예산 추정 vs 확정 사이징 (요약)

이 가이드는 두 목적에 모두 쓰입니다. 자세한 구분과 사용법은 [01.1.1](01-sizing-methodology.md#111-예산-추정-vs-확정-사이징--그리고-입력값이-없을-때)을 참조하세요.

- **예산 추정**: 구매 전, 공개 출처 1차 가정치([부록 A1](../appendix/A1-first-order-reference.md))로 규모·비용 윤곽. 단가는 [부록 A3](../appendix/A3-rfq-quote-checklist.md) 견적으로.
- **확정 사이징**: [06.5 PoC→파일럿→프로덕션](06-capacity-planning.md#65-poc--파일럿--프로덕션-용량-로드맵) 실측으로 갈음. 발주·SLA의 근거.

> 다음: 목적에 맞는 경로(0.1)로 이동하거나, [08 레퍼런스 시나리오](08-reference-scenario.md)로 전체 흐름을 처음부터 끝까지 보세요.

---
[목차](../README.md) · [다음: E0 임원 브리프(요약 문서) →](E0-executive-brief.md)

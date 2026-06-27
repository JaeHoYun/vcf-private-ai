# 01 — 사이징 방법론과 워크로드 분류
> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.
> 시리즈 인덱스: [시리즈 허브](../../README.md)

이 문서는 VMware Cloud Foundation(VCF) 9.1 / VMware Private AI Foundation with NVIDIA(PAIF) 9.1 / VMware Private AI Services(PAIS) 2.1 위에서 프라이빗 AI 워크로드를 운영할 때, 자원을 얼마나 준비해야 하는지를 결정하는 **사이징 방법론의 출발점**입니다. ([VCF 9.1 발표](https://www.broadcom.com/company/news/product-releases/64326), [PAIF with NVIDIA 9.1 TechDocs](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1.html))

---

## 1.1 사이징의 목적과 본 가이드의 위치

사이징(sizing)은 "어떤 워크로드를 어느 정도 규모로 돌릴 것인가"라는 요구사항을, GPU·CPU·메모리·스토리지·네트워크라는 **물리/논리 자원량**과 그에 따른 **비용**으로 환산하는 작업입니다. 과소 산정은 지연 폭증과 가용성 저하를, 과대 산정은 비용 낭비를 부릅니다.

본 시리즈 ⑥(사이징·용량·비용)은 **사이징·용량·TCO 산정의 기준 문서**입니다. 아키텍처 구성·설치·운영 절차 등 인프라 전반은 도메인 가이드를 참조하세요.

| 주제 | 참조 위치 |
| --- | --- |
| 인프라 아키텍처 전반(워크로드 도메인 구성, 설치) | [① 인프라 가이드](../../01-infra/README.md) |
| GPU 자원 산정(메모리·MIG/vGPU·모델별) | [02-gpu-sizing.md](02-gpu-sizing.md) |
| vCPU·시스템 메모리 산정 | [03-compute-memory-sizing.md](03-compute-memory-sizing.md) |
| VKS 클러스터·노드 풀 산정 | [04-vks-cluster-sizing.md](04-vks-cluster-sizing.md) |
| 스토리지·네트워크 산정 | [05-storage-network-sizing.md](05-storage-network-sizing.md) |
| 용량 계획(헤드룸·성장 예측) | [06-capacity-planning.md](06-capacity-planning.md) |
| TCO·비용 모델 | [07-tco-cost-model.md](07-tco-cost-model.md) |

> 프로덕션 배포 기준은 **VKS(vSphere Kubernetes Service)** 클러스터입니다. PAIF는 GPU-Accelerated Workload Domain(본 문서 약칭 **PAIF Workload Domain**) 위에서 VKS로 GPU 가속 클러스터를 프로비저닝하며, 초기 클러스터에는 **최소 3대의 GPU 탑재 ESX 호스트**가 요구됩니다. ([PAIF 요구사항](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1/deploying-private-ai-foundation-with-nvidia/requirements-for-deploying-private-ai-foundation-with-nvidia.html))

### 1.1.1 예산 추정 vs 확정 사이징 — 그리고 입력값이 없을 때

사이징에는 목적이 다른 두 모드가 있습니다. 이를 구분하지 않으면 "실측이 정답"이라는 원칙과 "장비를 사기 전에 예산을 내야 한다"는 현실이 충돌합니다(닭-달걀).

| 모드 | 목적 | 정밀도 | 근거 | 산출물 |
| --- | --- | --- | --- | --- |
| **예산 추정(budgetary)** | 구매·기안 전 규모·비용 윤곽 | 1차 어림(±큼) | 공개 출처 1차 가정치 | 예산 레인지, 발주 전 검토안 |
| **확정 사이징** | 발주·SLA 약정의 근거 | 실측 기반 | 자사 PoC·부하시험 | 확정 정원·구성·단가 |

- 본 가이드의 산식과 표는 두 모드 모두에 쓰이되, **확정값은 반드시 실측으로 갈음**합니다(1.5·1.6). 실측을 못 하는 예산 단계에서는 출발 숫자가 필요하며, 이를 위해 **출처에 묶인 1차 가정치**를 [부록 A1 — 1차 가정치 레퍼런스](../appendix/A1-first-order-reference.md)에 격리해 두었습니다(예산 추정 전용, 강한 경고 포함).
- **입력값 자체를 모를 때**(예: 사용자 수만 알고 동시성·QPS·SLA를 모를 때)는 [부록 A2 — 입력값 환산·기본값·모델 선택](../appendix/A2-inputs-and-defaults.md)으로 사업 언어를 사이징 입력으로 환산합니다.
- 입력에서 비용까지 한 시나리오로 끝까지 본 예제는 [08 — 레퍼런스 시나리오](08-reference-scenario.md)에 있습니다.
- 본 가이드 곳곳의 "실측 필요"는 [06.5 PoC→파일럿→프로덕션 로드맵](06-capacity-planning.md#65-poc--파일럿--프로덕션-용량-로드맵)에서 해소됩니다. 즉 예산 추정 → PoC 실측 → 확정의 순서입니다.

---

## 1.2 워크로드 분류와 자원 특성

AI 워크로드는 자원 소비 패턴이 유형마다 크게 다릅니다. 사이징의 첫 단계는 **대상 워크로드를 정확히 분류**하는 것입니다.

| 유형 | 설명 | 지배 자원 | GPU 메모리 압박 | 비고 |
| --- | --- | --- | --- | --- |
| 추론 — 단일 모델 | 1개 모델을 여러 요청에 서빙 | GPU 메모리 대역폭(decode), GPU 연산(prefill) | 모델 가중치 + KV 캐시 | 동시성↑ → KV 캐시 급증 |
| 추론 — 멀티 모델 | 여러 모델을 한 인프라에서 서빙 | GPU 메모리(모델 수만큼 합산) | 높음 | MIG/vGPU 분할로 격리 검토 |
| RAG(검색증강생성) | 추론 + 임베딩 + 벡터 검색 | 추론 GPU + 벡터DB(CPU·RAM·스토리지) | 추론과 동일 + 임베딩 모델 | 지식은 모델 밖 벡터DB에 저장 |
| 파인튜닝(LoRA/QLoRA) | 어댑터만 학습, 가중치 동결 | GPU 메모리(옵티마이저·그래디언트) | 풀 파인튜닝 대비 대폭 절감 | 배치성·간헐적 부하 |
| 학습/풀 파인튜닝 | 전체 가중치 갱신 | GPU 메모리·다중 GPU 인터커넥트 | 매우 높음(가중치×수 배) | 다수 GPU·노드 스케일아웃 |

핵심 차이를 요약하면 다음과 같습니다.

- **추론**은 GPU 메모리 안에 **모델 가중치 + KV 캐시 + 활성화 버퍼**가 모두 들어가야 합니다. KV 캐시는 동시 요청 수와 컨텍스트 길이에 비례해 커지며, 대형 모델에서는 가중치의 **2.5–5배**까지 커져 메모리 병목의 주원인이 될 수 있습니다. ([BentoML — GPU Memory for LLM Inference](https://www.bentoml.com/blog/what-is-gpu-memory-and-why-it-matters-for-llm-inference))
- **RAG**는 지식을 모델 파라미터가 아닌 **벡터 데이터베이스**에 두므로, 추론 GPU 외에 임베딩 모델·벡터DB(주로 CPU/RAM/스토리지)를 별도로 산정해야 합니다. 검색 단계로 쿼리당 지연이 추가됩니다. ([Glean — RAG vs Fine-Tuning](https://www.glean.com/blog/retrieval-augemented-generation-vs-fine-tuning))
- **LoRA/QLoRA 파인튜닝**은 전체 파라미터의 극히 일부만 학습해 풀 파인튜닝 대비 메모리를 크게 줄입니다(예: QLoRA로 7B급을 24GB GPU 단일 장비에서 학습 가능). 다만 모든 수치는 모델·시퀀스 길이·배치에 따라 달라지므로 **실측이 필요**합니다. ([DigitalOcean — GPU Options for Finetuning](https://www.digitalocean.com/resources/articles/gpu-options-finetuning))

---

## 1.3 사이징 입력값 체크리스트

사이징은 **입력값의 품질**이 결과의 품질을 결정합니다. 착수 전 아래 항목을 확정하세요. 값이 불확실하면 "확인 필요"로 표시하고, 보수적 가정과 함께 후속 실측 대상으로 둡니다.

| 분류 | 입력값 | 사이징에 미치는 영향 |
| --- | --- | --- |
| 모델 | 파라미터 수, 정밀도(FP16/BF16/FP8/INT8), 아키텍처(dense/MoE) | 가중치 메모리 = 파라미터 수 × 파라미터당 바이트 |
| 부하 | 동시 사용자 수, QPS(초당 요청), 피크/평균 비 | KV 캐시·배치 크기·필요 GPU 수 |
| 컨텍스트 | 입력 토큰 길이, 출력 토큰 길이, 최대 컨텍스트 | KV 캐시 크기(토큰 수에 비례) |
| 지연 목표 | TTFT 목표, 토큰 간 지연(ITL/TPOT), P95/P99 | 배치·동시성 상한, GPU 등급 선택 |
| 가용성 | SLA, 다중화(N+1), 장애 도메인 | 노드 수·헤드룸·리던던시 |
| 운영 | 멀티테넌시 격리, 성장률, 데이터 주권 | 분할 방식(MIG/vGPU)·용량 계획 |

> 가중치 메모리 어림식: **메모리(GB) ≈ 파라미터 수(B) × 파라미터당 바이트 × (1 + 오버헤드)**. 예) 7B 모델을 FP16(2바이트)로 적재하면 가중치만 약 14GB입니다. 여기에 KV 캐시·활성화·프레임워크 오버헤드가 더해집니다. **이 값은 어림이며 환경별로 상이하므로 실측이 필요합니다.** ([Spheron — VRAM 계산](https://www.spheron.network/blog/gpu-memory-requirements-llm/), [VMware — LLM Inference Sizing Guidance](https://blogs.vmware.com/cloud-foundation/2024/09/25/llm-inference-sizing-and-performance-guidance/))

지연 지표 정의(서빙 기준):

- **TTFT(Time To First Token)**: 프롬프트 제출부터 첫 토큰 수신까지. 체감 응답성의 핵심 지표입니다. ([vLLM Metrics](https://docs.vllm.ai/en/stable/design/metrics/))
- **ITL/TPOT**: 토큰 간 지연 / 출력 토큰당 평균 시간. 생성 속도를 좌우합니다.
- **P95/P99**: 백분위 지연. 최악 응답성의 척도로 P99가 흔히 쓰입니다. ([Anyscale — LLM 지표](https://docs.anyscale.com/llm/serving/benchmarking/metrics))

---

## 1.4 사이징 절차: 워크로드 → 자원 → 노드 → 클러스터 → 비용

사이징은 다음 5단계를 순차로 수행하고, 마지막에 실측으로 보정합니다. 각 단계의 상세 산식은 해당 문서로 연결됩니다.

1. **워크로드 정의**: 1.2의 유형 분류 + 1.3 입력값 확정 → "무엇을, 얼마나" 고정.
2. **자원 산정**: 모델 가중치 + KV 캐시 + 활성화로 **GPU 메모리** 산정([02](02-gpu-sizing.md)), 이어 **vCPU·시스템 메모리**([03](03-compute-memory-sizing.md)), **스토리지·네트워크**([05](05-storage-network-sizing.md)).
3. **노드 매핑**: GPU 등급(MIG/vGPU 분할 포함)과 호스트 사양으로 워크로드를 물리/논리 노드에 배치([02](02-gpu-sizing.md), [03](03-compute-memory-sizing.md)).
4. **클러스터 구성**: VKS 노드 풀·컨트롤 플레인·최소 호스트 수·HA를 반영해 클러스터로 집계([04](04-vks-cluster-sizing.md)).
5. **용량·비용 산정**: 헤드룸·성장률을 반영한 용량 계획([06](06-capacity-planning.md))과 TCO 모델([07](07-tco-cost-model.md))로 마무리.

| 단계 | 산출물 | 기준 문서 |
| --- | --- | --- |
| 1 워크로드 | 워크로드 명세·입력값 표 | 본 문서(01) |
| 2 자원 | GPU/CPU/메모리/스토리지/네트워크 요구량 | [02](02-gpu-sizing.md), [03](03-compute-memory-sizing.md), [05](05-storage-network-sizing.md) |
| 3 노드 | 노드별 배치·분할 설계 | [02](02-gpu-sizing.md), [03](03-compute-memory-sizing.md) |
| 4 클러스터 | VKS 클러스터·노드 풀 구성 | [04](04-vks-cluster-sizing.md) |
| 5 용량·비용 | 용량 계획·TCO | [06](06-capacity-planning.md), [07](07-tco-cost-model.md) |

> GPU 공유가 필요한 경우, 하드웨어 격리가 강한 **MIG**(A100/H100/H200 등 지원)와 소프트웨어 기반 **vGPU 타임슬라이싱**을 워크로드 격리·활용률 요구에 맞춰 선택합니다. 분할 방식에 따라 메모리 대역폭 활용률이 달라지므로 실측 비교가 권장됩니다. ([NVIDIA AI Enterprise — vGPU](https://docs.nvidia.com/ai-enterprise/release-4/latest/infra-software/vgpu/features.html))

위 5단계는 워크로드 요구에서 자원을 도출하는 **순방향(수요 기반)** 절차입니다. 이미 고정된 자원에서 거꾸로 가능한 워크로드를 도출하는 **역방향(공급 제약)** 절차는 1.7을 참조하세요.

---

## 1.5 핵심 원칙: 추정으로 시작하되 실측으로 보정

- **추정은 출발점, 실측은 정답**: 위 산식·표는 **초기 어림**(first-order estimate)입니다. 동일 모델이라도 GPU 등급, 정밀도, 배치 정책, 프레임워크 버전, 컨텍스트 분포에 따라 결과가 달라지므로, **벤치마크와 부하시험으로 반드시 보정**합니다.
- **헤드룸 확보**: GPU 메모리·연산·노드 수에 여유(headroom)를 둡니다. KV 캐시는 동시성에 비례해 급증하므로, 가중치만 빠듯하게 맞추면 동시성 증가 시 OOM·지연 폭증이 발생합니다.
- **버스트·피크 대비**: 평균이 아닌 **피크 부하·트래픽 버스트** 기준으로 동시성과 노드 수를 잡고, 가용성 목표(N+1 등)를 별도 헤드룸으로 합산합니다.
- **불확실성 명시**: 확정되지 않은 입력값은 "확인 필요"로 남기고 보수적 가정으로 진행하되, 실측 후 재산정합니다.

---

## 1.6 검증·실측 방법

추정치는 다음 절차로 검증·보정합니다. 모든 결과는 환경별로 상이하므로 **자사 환경에서의 실측이 필수**입니다.

1. **벤치마크 환경 고정**: 대상 모델·정밀도·GPU 등급·VKS 노드 풀을 프로덕션과 동일하게 구성하고, 한 번에 하나의 변수만 바꿉니다.
2. **서빙 부하시험**: vLLM 벤치마크 등으로 요청률(request-rate)과 최대 동시성(max-concurrency)을 단계적으로 올리며 **TTFT·ITL·종단 지연·처리량**(throughput)을 측정합니다. 요청률을 무한대로 두면 최대 처리량을, 유한값으로 두면 통제된 부하를 시험할 수 있습니다. ([vLLM Benchmark CLI](https://docs.vllm.ai/en/latest/benchmarking/cli/))
3. **지표 백분위 확인**: 평균이 아닌 **P95/P99 지연**으로 SLA 충족 여부를 판정합니다(특히 TTFT). ([Anyscale — 지표 해설](https://docs.anyscale.com/llm/serving/benchmarking/metrics))
4. **포화점 탐색**: 동시성을 올리며 지연 목표를 깨는 지점(SLA 위반 임계 동시성)을 찾아 **노드당 안전 동시성**을 산출합니다.
5. **GPU 활용률 검증**: GPU 메모리 점유·연산 활용률·메모리 대역폭을 관측해, MIG/vGPU 분할 시 활용률이 기대치(예: 타임슬라이싱 대비 MIG의 대역폭 활용률 우위)에 부합하는지 확인합니다. ([Spheron — MIG/Time-Slicing 가이드](https://www.spheron.network/blog/run-multiple-llms-one-gpu-mig-time-slicing-guide/))
6. **추정 대비 보정**: 실측값과 1.4 추정치의 차이(델타)를 기록하고, 사이징 모델의 가정(오버헤드 계수·동시성 가정)을 갱신합니다. 이 보정 루프는 [06-capacity-planning.md](06-capacity-planning.md)의 용량 재평가 주기에 편입합니다.

> 검증 데이터(부하 조건·측정 백분위·하드웨어 사양)는 추적 가능하도록 기록해, 이후 02–07 문서의 산정 근거와 연결합니다. 측정 없이 확정한 수치는 어디까지나 가정임을 문서에 명시하세요.

---

## 1.7 순방향·역방향 사이징

1.1–1.6은 "어떤 워크로드를 얼마나 돌릴 것인가"라는 요구사항에서 출발해 필요한 자원을 도출하는 **순방향(수요 기반)** 사이징이었습니다. 그러나 현장에는 그 반대 방향이 흔합니다. 특정 팀·담당자·임원의 주도로 이미 도입된 GPU 자원(전형적으로 베어메탈 서버 1대에 GPU 8장, 또는 서버 3–20대 규모)이 사일로화되거나, 활용처가 불확실하거나, 전담 인력이 없거나, 특정 팀이 독점하는 등의 이유로 **유휴 상태**인 경우입니다. 이때 묻는 것은 "이 워크로드에 GPU가 몇 장 필요한가"가 아니라 "**이미 가진 이 GPU로 무엇을, 얼마나 할 수 있는가**"입니다. 이를 **역방향(공급 제약) 사이징**이라 부릅니다.

| 구분 | 순방향(수요 기반) | 역방향(공급 제약) |
| --- | --- | --- |
| 출발점 | 워크로드 요구사항 | 기보유 고정 자원 |
| 핵심 질문 | "이걸 돌리려면 GPU 몇 장?" | "이 GPU로 무엇을 얼마나?" |
| 주요 입력 | 사용자·동시성·SLA·모델 | GPU 등급·장수·호스트 사양·현 활용 상태 |
| 지배 제약 | 예산 | 물리 용량(고정) |
| 산출물 | 필요 자원·구성·TCO | 워크로드 적재 한계·할당 상한·잔여/증설 판단 |
| 전형적 상황 | 신규 도입·예산 기안 | 유휴·사일로 GPU 재활용, dev/배치 전환 |

역방향 절차는 1.4 순방향 5단계를 정확히 반대 순서로 밟습니다. "자원을 사 모으는" 대신 "고정된 자원을 워크로드로 채우는" 순서입니다.

| 단계 | 내용 | 기준 문서 |
| --- | --- | --- |
| 1 자원 인벤토리 | GPU 등급·장수·VRAM, 호스트 vCPU/RAM/네트워크, 현 활용·사일로 상태 파악 | 본 문서(01) |
| 2 실효 가용 용량 | 헤드룸·예약·플랫폼 오버헤드를 차감한 가용 VRAM·연산·처리량 천장 산정 | [02](02-gpu-sizing.md), [03](03-compute-memory-sizing.md) |
| 3 워크로드 적재(패킹) | 모델·서비스 조합을 동시성·잡 슬롯으로 적재(추론 동시성 상한·멀티모델 패킹·파인튜닝/배치 잡) | [02](02-gpu-sizing.md), [03](03-compute-memory-sizing.md) |
| 4 할당 상한·정책 | MIG/vGPU 프로파일·네임스페이스 쿼터·GPU Reservation으로 워크로드별 최대치 고정, 오버서브 경계 설정 | [04](04-vks-cluster-sizing.md), [06](06-capacity-planning.md) |
| 5 잔여·다음 행동 | 남으면 신규 워크로드 여지, 부족하면 증설·회수·양자화 다운사이즈 판단(한계비용 관점) | [06](06-capacity-planning.md), [07](07-tco-cost-model.md) |

> **역방향의 첫 함정 — 단일 박스와 플랫폼 최소요건.** 가장 흔한 "베어메탈 1대 × GPU 8장"은 프로덕션 VKS 클러스터의 **최소 3대 GPU 호스트 요건**(1.1)에 미달합니다. 따라서 단일 박스는 (가) GPU 독점 접근(DirectPath) 기반 단일 VM 용도, (나) dev·배치 등 비프로덕션 용도, (다) 호스트 2대 추가 중 하나로 귀결됩니다. "장비는 있는데 프로덕션 플랫폼으로는 못 쓰는" 이 간극이 역방향 사이징의 핵심 의사결정입니다. 고정 자원에서 비용까지 한 시나리오로 끝까지 본 역방향 전 과정 예제는 [09 역방향 시나리오](09-reverse-sizing-scenario.md)에서 다룹니다.

두 방향은 배타적이지 않습니다. 보통 역방향으로 "기보유 자원으로 가능한 범위"를 먼저 확정한 뒤, 부족분만 순방향으로 추가 산정합니다. 예산 추정 vs 확정 사이징(1.1.1)의 구분과 "추정으로 시작해 실측으로 보정"(1.5)하는 원칙은 두 방향 모두에 그대로 적용됩니다.

---
[← 이전: E0 임원 브리프(요약 문서)](E0-executive-brief.md) · [목차](../README.md) · [다음: 02 GPU 사이징 →](02-gpu-sizing.md)

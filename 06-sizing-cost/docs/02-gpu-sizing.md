# 02 — GPU 사이징

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.
> 시리즈 인덱스: [시리즈 허브](../../README.md)

이 문서는 VCF 9.1 / PAIF 9.1 / PAIS 2.1 환경의 GPU-Accelerated Workload Domain(약칭: GPU WLD) 위에서 추론 워크로드를 운영할 때, "모델 크기와 서비스 목표를 입력하면 GPU 메모리(VRAM)와 GPU 수량이 얼마나 필요한가"를 추정하는 방법을 다룹니다. vLLM·llama.cpp 등 추론 엔진을 전제로 합니다.

아래의 모든 메모리·처리량 수치는 아키텍처·정밀도·엔진 버전·하드웨어에 따라 크게 달라지는 **어림**(approximation)이며, 배포 전 반드시 대상 환경에서 실측이 필요합니다. 산식은 "1차 사이징 가이드"로만 사용하시고, 확정 용량은 실측값으로 갈음하세요.

관련 문서: 컴퓨트·시스템 메모리 사이징은 [03-compute-memory-sizing.md](03-compute-memory-sizing.md), VKS 클러스터 사이징은 [04-vks-cluster-sizing.md](04-vks-cluster-sizing.md)를 참조하세요. GPU 공유 방식의 상세 아키텍처는 시리즈 [① 인프라](../../01-infra/README.md)를 참조하세요.

---

## 2.1 VRAM 산정의 3대 구성요소

추론 시 GPU 메모리는 크게 세 덩어리로 나뉩니다.

| 구성요소 | 설명 | 크기 결정 요인 |
| --- | --- | --- |
| 가중치 메모리(Weights) | 모델 파라미터를 적재하는 고정 비용 | 파라미터 수 × 정밀도(byte/param) |
| KV 캐시(KV Cache) | 생성된 토큰의 Key/Value를 보관하는 가변 비용 | 컨텍스트 길이 × 동시 요청 수 × 레이어/헤드 구조 |
| 활성화·오버헤드 | 순전파 중간 텐서, 엔진/런타임/단편화 여유분 | 배치, 엔진 구현, 단편화 |

vLLM 공식 문서가 제시하는 전체 메모리 관계식은 다음과 같습니다([vLLM-Omni GPU Memory](https://docs.vllm.ai/projects/vllm-omni/en/latest/configuration/gpu_memory_utilization/)).

```
필요 GPU 메모리 ≈ ( 가중치 + non_torch_memory + 활성화 피크 )
                  + KV캐시(요청당) × 동시 요청 수
                  --------------------------------------------- 를 전부
                  ÷ gpu_memory_utilization 로 나눈 값
```

여기서 `gpu_memory_utilization`은 vLLM이 모델 실행기에 할당하는 GPU 메모리 비율로, 기본값은 메인라인 vLLM 기준 0.9입니다(0–1 범위; vLLM-Omni 등 일부 배포판은 0.92). vLLM은 이 값을 기준으로 남는 메모리를 KV 캐시로 자동 환산합니다([vLLM cache config](https://docs.vllm.ai/en/stable/api/vllm/config/cache/)). 즉 **사용 가능한 KV 캐시 = (총 VRAM × gpu_memory_utilization) − 가중치 − 오버헤드** 가 실무상 핵심 가용량입니다.

---

## 2.2 가중치 메모리 산정 (파라미터 × 정밀도)

가중치 메모리의 1차 어림은 단순합니다.

```
가중치 메모리(GB) ≈ 파라미터 수(십억) × (정밀도 bit / 8) × 1.??(여유 계수)
```

정밀도별 파라미터당 바이트:

| 정밀도 | byte/param | 7B 모델 어림 | 13B 모델 어림 | 70B 모델 어림 |
| --- | --- | --- | --- | --- |
| FP16 / BF16 | 2.0 | 약 14 GB | 약 26 GB | 약 140 GB |
| INT8 / FP8 | 1.0 | 약 7 GB | 약 13 GB | 약 70 GB |
| INT4 | 0.5 | 약 3.5 GB | 약 6.5 GB | 약 35 GB |

> 위 표는 가중치만 계산한 값입니다(KV 캐시·오버헤드 제외). 실제로는 정밀도 변환 시 일부 텐서가 더 높은 정밀도로 남거나, 임베딩/LM head 등이 별도로 잡히므로 표값보다 5–20% 늘어나는 것이 일반적입니다. 어림이며 실측 필요.

핵심 직관: **FP16 70B 모델의 가중치만 약 140GB**이므로, 80GB급 단일 GPU 한 장에는 들어가지 않습니다. 70B를 FP16로 서비스하려면 다중 GPU(텐서 병렬, 2.6 참조)나 양자화(2.4 참조)가 필요합니다.

---

## 2.3 KV 캐시 산정 (컨텍스트 × 동시성)

KV 캐시는 "지금 처리 중인 토큰 수"에 비례해 늘어나는 가변 메모리로, 동시성이 높거나 컨텍스트가 길수록 가중치보다 더 큰 병목이 되기도 합니다.

vLLM 커뮤니티가 정리한 토큰당 KV 캐시 어림식은 다음과 같습니다([vLLM Discussion #13803](https://github.com/vllm-project/vllm/discussions/13803)).

```
토큰당 KV 캐시(byte) ≈ 2(K,V) × 레이어 수 × KV 헤드 수 × head_dim × 정밀도(byte)

요청당 KV 캐시 ≈ 토큰당 KV 캐시 × (입력 + 출력 토큰 수)
총 KV 캐시 ≈ 요청당 KV 캐시 × 동시 요청 수
```

- **GQA(Grouped Query Attention)** 모델은 KV 헤드 수가 어텐션 헤드보다 적어 KV 캐시가 크게 줄어듭니다. 같은 파라미터라도 MHA보다 GQA가 동시성 측면에서 유리합니다.
- **FP8 KV 캐시**를 지원하는 엔진/모델이라면 KV 캐시 메모리를 추가로 절반 수준까지 줄일 수 있습니다(품질 영향은 실측 필요).

예시(어림, 구조값은 모델별 상이 — 실측 필요):

| 시나리오 | 컨텍스트(입력+출력) | 동시 요청 | KV 캐시 경향 |
| --- | --- | --- | --- |
| 짧은 챗봇 | 약 2K 토큰 | 낮음(수–수십) | 가중치 대비 작음 |
| RAG/장문 | 약 16–32K 토큰 | 중간 | 가중치에 근접/초과 가능 |
| 고동시 API | 약 4K 토큰 | 높음(수백) | KV 캐시가 주 병목 |

### 워크드 예제 — 8B급 모델 KV 캐시 (구조식 → GB)

예시 모델 카드 값(GQA): 레이어 32, KV 헤드 8, head_dim 128, 정밀도 FP16(2바이트). (`config.json`에서 구조값 떼는 법은 [부록 A2.5](../appendix/A2-inputs-and-defaults.md#a25-모델-구조값-확인-방법-kv-캐시-계산-입력) 참조.)

| 단계 | 계산 | 결과 |
| --- | --- | --- |
| 토큰당 KV | 2 × 32 × 8 × 128 × 2 | 131,072 B ≈ **0.000122 GiB/token** |
| 요청당 KV(4K 컨텍스트) | 0.000122 × 4,096 | 약 **0.5 GiB** |
| 총 KV(동시성 50) | 0.5 × 50 | 약 **25 GiB** |

- **교차검증**: 위 토큰당 0.000122 GiB는 VMware 사이징 계산기의 8B 계수와 동일합니다([부록 A1.1](../appendix/A1-first-order-reference.md#a11-추론-처리량동시성-1차-가정치)). 구조식과 공개 계산기, 두 독립 방법이 일치합니다.
- **GQA의 효과**: 같은 모델이 GQA가 아니라 MHA(KV 헤드 = 어텐션 헤드 32)였다면 토큰당 KV가 4배(약 0.5 MiB/token) → 요청당 약 2 GiB, 동시성 50이면 약 100 GiB로 80GB 단일 GPU를 초과합니다. KV 헤드 구조가 동시성에 결정적임을 보여줍니다.
- 이 예제를 가중치·노드·클러스터·비용까지 잇는 전체 흐름은 [08 — 레퍼런스 시나리오](08-reference-scenario.md)에서 시나리오 동시성(약 21)으로 적용합니다.

> 정확한 구조값(레이어/KV 헤드/head_dim)은 모델 카드·config에서 확인해야 하며, 위 경향은 어림입니다. 실측 필요.

---

## 2.4 양자화: 메모리와 품질의 트레이드오프

양자화는 가중치(및 일부 활성화)를 저정밀도로 표현해 VRAM을 줄이는 기법입니다. 일반적으로 알려진 절감·품질 경향은 다음과 같습니다([Hivenet 양자화 가이드](https://www.hivenet.com/post/llm-quantization-guide), [AWQ 논문](https://arxiv.org/pdf/2306.00978)).

| 정밀도 | 메모리 절감(FP16 대비) | 품질 영향(일반론) | 비고 |
| --- | --- | --- | --- |
| INT8 / FP8 | 약 50% (약 2배 효율) | 미미(약 1% 내외) | 표준적 절감, 대부분 안전 |
| INT4 | 약 75% (약 4배 효율) | 모델·기법에 민감 | AWQ/GPTQ 등 고급 기법 권장 |

- **GPTQ**: 가중치를 배치 단위로 처리하며 양자화 오차(MSE, 평균제곱오차)를 최소화하는 학습 후 양자화(PTQ, Post-Training Quantization) 기법. GPU 추론에 최적화.
- **AWQ**: 활성화 통계로 ~1%의 중요 가중치 채널을 식별·보존한 뒤 저비트화. 동일 비트폭에서 GPTQ보다 정확도 유지가 유리한 경향([AWQ 논문](https://arxiv.org/pdf/2306.00978)).
- **모델 크기 효과**: INT4는 소형 모델에서 품질 저하가 두드러지지만, 모델이 커질수록 영향이 완화되는 경향이 보고됩니다([AWS ML 블로그](https://aws.amazon.com/blogs/machine-learning/accelerating-llm-inference-with-post-training-weight-and-activation-using-awq-and-gptq-on-amazon-sagemaker-ai/)).

> 절감률·품질 회복률은 데이터셋·태스크·기법에 따라 달라지는 어림 수치입니다. 도입 전 대상 태스크에서 정확도/지연을 실측해 비교하세요.

---

## 2.5 처리량·지연 목표 → GPU 수·Replica 환산

용량 산정은 "메모리에 들어가는가"(2.2–2.4)와 "목표 처리량을 내는가"(이 절)의 두 축으로 봐야 합니다.

기본 환산 흐름:

```
1) 1 Replica가 내는 처리량 측정 → tokens/s 또는 QPS(초당 처리 요청 수, Queries Per Second) (실측)
2) 목표 QPS ÷ Replica당 QPS = 필요 Replica 수 (올림)
3) Replica당 GPU 수 × 필요 Replica 수 = 총 GPU 수
4) 피크/버스트·헤드룸(예: 20–30%) 가산
```

| 입력 | 의미 | 산정 시 주의 |
| --- | --- | --- |
| 목표 QPS / 동시 사용자 | 초당 요청·동시 세션 | 평균이 아니라 피크 기준 |
| 목표 지연(TTFT, TPOT) | 첫 토큰/토큰간 지연 | 배치 키우면 처리량↑·지연↑ 상충 |
| 평균 입력·출력 토큰 | 요청당 작업량 | 출력 길이가 처리량을 크게 좌우 |
| Replica당 처리량 | 1 인스턴스 실측 tokens/s | 반드시 대상 GPU에서 실측 |

핵심 트레이드오프: 배치 크기를 키우면 GPU 활용률과 총 처리량은 오르지만 개별 요청 지연(TTFT/TPOT)은 나빠집니다. 지연 SLA가 빡빡할수록 Replica 수가 늘어나는 방향으로 사이징됩니다. Replica당 처리량은 산식으로 단정할 수 없으므로 **반드시 실측**이 필요합니다.

---

## 2.6 다중 GPU: 텐서 병렬 / 파이프라인 병렬 개요

단일 GPU에 모델이 들어가지 않거나 더 높은 처리량이 필요할 때 다중 GPU로 분산합니다. vLLM의 분산 전략 가이드([vLLM Parallelism](https://docs.vllm.ai/en/stable/serving/parallelism_scaling/), [Distributed Serving](https://docs.vllm.ai/en/v0.8.0/serving/distributed_serving.html))를 요약하면 다음과 같습니다.

| 전략 | 적용 상황 | 설정 예 |
| --- | --- | --- |
| 텐서 병렬(TP) | 모델이 단일 GPU엔 안 들어가나 단일 노드 다중 GPU엔 들어감 | `tensor_parallel_size=4` (노드 내 4 GPU) |
| 파이프라인 병렬(PP) | 모델이 단일 노드에도 안 들어감 → 노드 간 분산 | TP=노드당 GPU 수, PP=노드 수 |

- 우선순위: **단일 노드 내에서는 TP를 먼저** 쓰고, 노드 경계를 넘어야 할 때 PP를 결합합니다(예: 2노드 × 8GPU → `tensor_parallel_size=8`, `pipeline_parallel_size=2`).
- **왜 노드 내 TP를 먼저 쓰나** — 텐서 병렬은 한 모델을 여러 GPU에 쪼개므로, GPU들이 **토큰을 만들 때마다 중간 계산값을 주고받습니다**. 이 교환 속도가 곧 성능이며, 노드 안에서는 GPU 직결 고속 연결인 **NVLink**가 이를 받쳐 줍니다. 노드를 넘으면 일반 네트워크를 타 대역폭이 수 배 낮아지므로(통신이 병목), 같은 모델이라도 가능하면 한 노드 안에 묶고(TP) PP는 단일 노드에 안 들어갈 때만 씁니다. 그래서 NVLink로 묶인 8-GPU 단일 노드가 중·대형 모델 TP의 기본 단위가 됩니다.
- 단일 노드는 Python 멀티프로세싱으로, 다중 노드는 Ray 런타임이 필요합니다.
- 분산은 통신 오버헤드를 동반하므로, 메모리만 보고 GPU 수를 정한 뒤에는 분산 구성에서의 처리량을 다시 실측해야 합니다.

---

## 2.7 GPU 공유 방식의 용량 함의

PAIF에서 ESXi 호스트의 GPU는 vGPU 타임슬라이스, MIG, DirectPath I/O(패스스루) 중 하나로 구성합니다([Broadcom TechDocs: vGPU/Passthrough 구성](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/deploying-private-ai-foundation-with-nvidia/configure-nvidia-vgpu-or-gpu-passthrough-on-the-esx-hosts.html)). 용량 관점의 차이는 다음과 같습니다.

| 방식 | 분할 단위 | 메모리/성능 격리 | 용량 효율이 좋은 워크로드 |
| --- | --- | --- | --- |
| vGPU 타임슬라이스 | 시간 분할(메모리는 분할) | 컴퓨트는 시분할 공유 | 소형/간헐적·저부하 다수 VM, 개발·실험 |
| MIG(하드웨어 분할) | 물리 슬라이스(인스턴스 프로파일) | 메모리·컴퓨트 모두 하드웨어 격리 | 예측 가능한 SLA가 필요한 다수 소–중형 추론 |
| DirectPath I/O(전용) | GPU 1장 전체 | 완전 전용 | 대형 모델·최대 성능(대형 추론/사전학습) |

- **MIG**는 단일 물리 GPU를 하드웨어로 쪼개 각 슬라이스를 다른 VM에 할당합니다. 예컨대 H100은 8개의 메모리 슬라이스(각 약 10GB)와 7개의 컴퓨트 슬라이스로 구성되며, `[compute]g.[memory]gb` 표기로 프로파일을 지정합니다(예: `3g.40gb` = 컴퓨트 3슬라이스·VRAM 40GB). 프로파일은 1·2·3·4·7 슬라이스를 소비하며 합이 7 이하인 조합만 유효합니다([NVIDIA MIG User Guide](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/supported-mig-profiles.html)).
- **선택 가이드(용량 효율)**: 작은 모델을 강한 격리로 여러 개 돌릴 때는 MIG, 하나의 큰 모델로 최대 성능을 낼 때는 DirectPath I/O, 부하가 낮고 간헐적인 소형 워크로드가 많을 때는 vGPU 타임슬라이스가 일반적으로 효율적입니다.
- 상세 아키텍처·구성 절차는 시리즈 [① 인프라](../../01-infra/README.md)를 참조하세요.

---

## 2.8 GPU 모델 선택 가이드 (HBM 용량·세대)

GPU 선택의 1차 기준은 **HBM 용량**(2.2–2.4의 가중치+KV 캐시가 들어가는가)과 **세대/대역폭**(토큰 생성 속도에 직결)입니다. 참고용 사양(공식 사양은 반드시 NVIDIA 데이터시트로 확인):

| GPU | 메모리 | 대역폭(어림) | 비고 |
| --- | --- | --- | --- |
| A100 80GB | 80GB HBM2e | 약 2 TB/s | 이전 세대 |
| H100 80GB | 80GB HBM3 | 약 3.35 TB/s | Hopper |
| H200 | 141GB HBM3e | 약 4.8 TB/s | 대용량 메모리, 장문/대형 모델 유리 |

(출처: [RunPod H100](https://www.runpod.io/articles/guides/nvidia-h100), [RunPod H200](https://www.runpod.io/articles/guides/nvidia-h200-gpu) — 벤더 정리 자료이므로 공식 데이터시트 교차 확인 필요)

선택 시 고려사항:
- **메모리 우선**: 장문 컨텍스트·고동시·대형 모델은 HBM 용량이 큰 세대(예: H200 계열)가 단일 장 적재·KV 캐시 여유 면에서 유리합니다.
- **대역폭 우선**: 토큰 디코딩은 메모리 대역폭에 민감하므로, 동일 메모리라면 최신 세대가 지연·처리량에서 유리합니다.
- **특정 제품 단정 금지**: 실제 도입 GPU는 PAIF 지원 매트릭스와 서버 벤더의 BCG(BIOS·펌웨어)/HCL(하드웨어 호환성 목록), NVIDIA 공식 사양으로 확정해야 합니다. 본 문서의 표는 산정 감각을 위한 참고치입니다.

---

## 2.9 고정 GPU 적재·패킹 (공급 제약)

2.1–2.8이 "모델·목표에서 필요한 GPU를 도출"하는 순방향이라면, 본 절은 그 반대 — **이미 가진 고정 GPU에 무엇이, 얼마나 들어가는가**(역방향 자원 단계, [01 §1.7](01-sizing-methodology.md#17-순방향역방향-사이징))를 다룹니다. 고정 풀에서 시작하는 전 과정 예제는 [09 역방향 시나리오](09-reverse-sizing-scenario.md)에 있습니다.

### GPU 한 장의 적재 예산 (역산)

2.1의 메모리 관계식을 "가용 KV"에 대해 풀면, 고정 GPU 한 장이 받칠 수 있는 동시성 상한이 나옵니다.

```
가용 KV(GiB) = (물리 VRAM × gpu_memory_utilization) − 가중치 − 활성화·오버헤드
최대 동시성  ≈ 가용 KV ÷ 요청당 KV 캐시(2.3)
```

예) 80GB GPU, `gpu_memory_utilization` 0.9 → 가용 약 72 GiB. 8B FP16(가중치 약 16 GiB) + 활성화·오버헤드 약 4 GiB → 가용 KV 약 52 GiB. 요청당 KV 약 0.5 GiB(4K, 2.3 워크드 예제) → 최대 동시성 약 100 `[A1 가정치]`. 이 상한이 곧 "이 한 장으로 몇 요청을 동시에 받느냐"입니다.

> 같은 80GB라도 GQA/MHA·컨텍스트 길이·양자화에 따라 이 상한이 크게 달라집니다(2.3·2.4). 위 값은 출발점이며 실측이 필요합니다.

> 이 동시성을 실제로 떠받치는 엔진 메커니즘(연속 배칭·PagedAttention)은 [③ 서빙 가이드 §0.6](../../03-serving-api/docs/00-serving-primer.md)에서 개념으로 다룹니다. PagedAttention이 KV 캐시 낭비를 줄여 같은 VRAM에 더 많은 요청을 담는 것이 위 "최대 동시성"의 밑바탕입니다.

### 큰 모델 1개 적재 — 텐서 병렬로 장수 역산

단일 GPU에 안 들어가는 모델은 텐서 병렬(2.6)로 여러 장에 나눕니다. 고정 풀에서는 "몇 장을 묶어야 들어가는가"를 역산합니다.

| 모델 | 가중치(FP16) | 80GB GPU 최소 장수 | 권장(KV 헤드룸) |
|---|---|---|---|
| 8B | 약 16GB | 1 | 1 |
| 70B | 약 140GB | 2 (TP=2, 160GB 빠듯) | 4 (TP=4, KV·활성화 여유) |
| 70B INT4(양자화) | 약 35GB | 1 | 1–2 |

> 최소 장수는 "가중치만 들어가는" 하한입니다. KV 캐시·활성화·`gpu_memory_utilization` 여유를 더하면 권장 장수가 늘어납니다. 양자화(2.4)는 같은 풀에 더 큰 모델을 담는 핵심 수단입니다.

### 여러 모델 적재 — 합산 또는 MIG 분할

작은 모델 여러 개를 한 장(또는 한 풀)에 담을 때는 두 길이 있습니다.

- **합산(soft)**: 한 GPU에 `Σ(가중치 + 요청당 KV × 동시성) ≤ 가용 VRAM`인 만큼 적재. 격리는 약합니다(같은 메모리 공간 공유).
- **MIG 분할(hard)**: 80GB GPU를 슬라이스로 쪼개 각 모델을 격리 적재(2.7). 예측 가능한 SLA·테넌트 격리에 유리하며, 프로파일 슬라이스 합이 7 이하인 조합만 유효합니다(2.7).

### 풀 전체 천장 (집계)

N장 풀의 1차 천장은 단순 집계 후 플랫폼 정원을 차감합니다.

```
풀 가용 VRAM   ≈ N × (물리 VRAM × gpu_memory_utilization)
풀 동시성 천장 ≈ Σ(장별 최대 동시성)   ← 큰 모델 TP·HA·헤드룸 차감 전
```

여기서 빼야 할 것: 가용성(N+1·HA), 버스트 헤드룸(20–30%), 플랫폼 최소요건(컨트롤 플레인·일반 워커는 GPU와 별도 노드, [04 §4.1](04-vks-cluster-sizing.md#41-vks-클러스터-토폴로지-개요)), GPU Operator 데몬셋의 호스트 자원([04 §4.3](04-vks-cluster-sizing.md#43-노드-사양-산정-노드-크기-vs-노드-수)). 이 차감과 워크로드 포트폴리오 배분의 전 과정 예제가 [09](09-reverse-sizing-scenario.md) §9.2–9.4입니다.

> 모든 수치는 `[A1 가정치]`이며 PoC 실측으로 갈음합니다([06](06-capacity-planning.md) §6.5). "GPU당 사용자 N명" 같은 고정 상수는 없습니다([A1 §A1.1](../appendix/A1-first-order-reference.md#a11-추론-처리량동시성-1차-가정치)).

---

## 2.10 학습·파인튜닝 GPU 메모리

추론(2.1–2.9)과 달리 학습·파인튜닝은 가중치 외에 **그래디언트·옵티마이저 상태·활성화**가 GPU 메모리를 크게 차지합니다([01 §1.2](01-sizing-methodology.md#12-워크로드-분류와-자원-특성) 워크로드 분류). 역방향에서 유휴 GPU를 간헐적 파인튜닝에 활용하는 경우가 많으므로([09](09-reverse-sizing-scenario.md) §9.3), 그 메모리 셈법을 정리합니다.

### 풀 파인튜닝 — 파라미터당 약 16바이트

혼합정밀(mixed precision) + Adam 옵티마이저 풀 파인튜닝의 파라미터당 메모리 구성입니다([Modal — VRAM for fine-tuning](https://modal.com/blog/how-much-vram-need-fine-tuning); DeepSpeed ZeRO 메모리 모델).

| 구성요소 | 정밀도 | 파라미터당 바이트 |
|---|---|---|
| 가중치(fp16/bf16) | 2바이트 | 2 |
| 그래디언트(fp16/bf16) | 2바이트 | 2 |
| 마스터 가중치(fp32) | 4바이트 | 4 |
| Adam 모멘텀(fp32) | 4바이트 | 4 |
| Adam 분산(fp32) | 4바이트 | 4 |
| **합계(가중치+상태)** | | **약 16바이트/param** |

여기에 활성화(activation)가 배치·시퀀스 길이에 비례해 더해집니다. 즉 풀 파인튜닝은 **추론(가중치만 약 2바이트/param)의 약 8배 메모리**가 출발점입니다. 예) 7B 풀 파인튜닝 ≈ 7B × 16바이트 ≈ 약 112GB(활성화 별도) → 단일 80GB GPU 불가, 멀티 GPU 샤딩 필수. 70B는 1TB를 크게 넘어 다수 GPU·노드가 필요합니다.

> 위 16바이트는 혼합정밀+Adam의 어림이며, 정밀도·옵티마이저·활성화 회계 방식에 따라 달라집니다(범위로 다룰 것). 핵심은 **풀 파인튜닝이 추론 대비 한 자릿수 배 크다**는 점입니다.

### LoRA / QLoRA — 옵티마이저를 어댑터에만

LoRA는 베이스 가중치를 동결하고 소형 어댑터만 학습하므로, 그래디언트·옵티마이저 상태를 **전체 파라미터가 아니라 어댑터에만** 유지합니다. 풀 파인튜닝 대비 메모리가 대폭 줄어듭니다([Towards Data Science — QLoRA on a single GPU](https://towardsdatascience.com/qlora-how-to-fine-tune-an-llm-on-a-single-gpu-4e44d6b5be32/), [RunPod — fine-tuning GPU guide](https://www.runpod.io/blog/llm-fine-tuning-gpu-guide)).

| 방식 | 베이스 가중치 | 옵티마이저·그래디언트 | 7B 어림 | 단일 GPU |
|---|---|---|---|---|
| 풀 파인튜닝 | fp16(2B/param) | 전체 파라미터 | 약 112GB+ | 멀티 GPU 필수 |
| LoRA | fp16(2B/param) | 어댑터만 | 약 16–20GB | 24GB+ 가능 |
| QLoRA | 4-bit(0.5B/param) | 어댑터만 | 약 10–16GB | 16–24GB 가능 |

> QLoRA는 4비트 베이스로 LoRA 대비 VRAM을 약 절반으로 줄입니다. 그 결과 7B는 12–16GB GPU에서, 70B는 단일 80GB GPU급에서 파인튜닝할 수 있습니다(어림, 실측 필요). 모든 수치는 모델·시퀀스 길이·배치에 따라 달라집니다.

### 멀티 GPU 학습 — 샤딩(FSDP / ZeRO-3)

단일 GPU에 안 들어가는 풀 파인튜닝·사전학습은 FSDP(PyTorch) 또는 DeepSpeed ZeRO-3로 **파라미터·그래디언트·옵티마이저 상태를 GPU에 분산**합니다. 각 GPU는 전체의 일부 샤드만 보유하고, 계산 시점에 필요한 샤드를 all-gather한 뒤 다시 분할합니다. 이상적으로 GPU당 메모리는 전체를 GPU 수로 나눈 수준(통신 오버헤드 별도)이라, 고정 풀의 장수가 늘수록 더 큰 모델을 학습할 수 있습니다([Spheron — Distributed LLM Training (FSDP/ZeRO/Megatron)](https://www.spheron.network/blog/distributed-llm-training-fsdp-deepspeed-megatron-multi-node/)).

- 역방향 함의: 유휴 8-GPU 서버(NVLink) 한 대는 노드 내 샤딩으로 중형 모델 풀 파인튜닝에, 여러 노드는 노드 간 샤딩(통신 비용 상승)으로 대형 학습에 활용할 수 있습니다(few-large, [04 §4.3](04-vks-cluster-sizing.md#43-노드-사양-산정-노드-크기-vs-노드-수)).
- 파인튜닝은 배치성·간헐적 부하이므로 추론 노드 풀과 분리하고 선점형으로 운영합니다([03 §3.7](03-compute-memory-sizing.md#37-메모리-오버커밋예약쿠버네티스-requestslimits-원칙)).

> 위 수치는 모두 어림이며 모델·시퀀스 길이·배치·기법에 따라 달라집니다. 확정은 실측으로 갈음하세요([06](06-capacity-planning.md) §6.5).

---

## 2.11 검증·실측 방법

본 문서의 산식은 1차 사이징용 어림이며, 다음 절차로 실측·검증한 뒤 확정하세요.

1. **가중치 메모리 검증**: 대상 모델·정밀도로 엔진을 기동해 로드 직후 VRAM 점유를 확인하고 2.2 표값과 대조합니다(차이 5–20%는 정상 범위).
2. **KV 캐시·동시성 검증**: vLLM 기동 로그의 KV 캐시 블록 수(또는 가용 토큰 수)를 확인하고, `gpu_memory_utilization`(메인라인 기본 0.9)을 조정해 가용 KV 캐시가 목표 동시성을 수용하는지 점검합니다([vLLM cache config](https://docs.vllm.ai/en/stable/api/vllm/config/cache/)).
3. **처리량·지연 측정**: 대표 입력/출력 토큰 분포로 부하 시험을 돌려 Replica당 QPS·tokens/s·TTFT·TPOT를 실측하고, 2.5의 Replica 환산식에 대입합니다.
4. **양자화 영향 측정**: 후보 양자화(INT8/INT4, AWQ/GPTQ)별로 정확도(태스크 평가)와 지연을 함께 측정해 메모리 절감 대비 품질 손실을 비교합니다(2.4).
5. **공유 방식 검증**: MIG 프로파일·vGPU·DirectPath I/O 각각에서 격리도와 실효 처리량을 확인하고, 워크로드 SLA에 맞는 방식을 선택합니다(2.7).
6. **헤드룸 확정**: 피크 부하 + 단편화 여유(통상 20–30%)를 반영해 총 GPU 수를 올림 확정합니다(2.5).
7. **호환성 확인**: 확정 GPU·드라이버·프로파일이 PAIF 지원 매트릭스와 서버 BCG/HCL에 부합하는지 최종 점검합니다(2.8).

> 위 절차의 모든 수치는 환경별로 달라집니다. 이 문서의 표·산식은 출발점이며, **확정 용량은 실측값으로 갈음**한다는 원칙을 유지하세요. 불확실한 항목은 "확인 필요"로 남기고 진행하세요.

---
[← 이전: 01 사이징 방법론과 워크로드 분류](01-sizing-methodology.md) · [목차](../README.md) · [다음: 03 컴퓨트·메모리 사이징 →](03-compute-memory-sizing.md)

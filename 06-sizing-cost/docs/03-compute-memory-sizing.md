# 03 — 컴퓨트·메모리 사이징

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.
> 시리즈 인덱스: [시리즈 허브](../../README.md)

본 문서는 GPU-Accelerated Workload Domain(GPU 가속 워크로드 도메인, 이하 GPU WLD)에서 **GPU 자체를 제외한 자원** — 호스트 vCPU·메모리, NUMA·PCIe 배치, 데이터 파이프라인, CPU 추론 경로, 임베딩·리랭커 같은 RAG 비-LLM 컴포넌트, 그리고 워크로드를 노드 수요로 환산하는 규칙 — 을 사이징합니다. GPU(vGPU 프로파일·VRAM) 사이징은 [02 — GPU 사이징](./02-gpu-sizing.md)에서 다루며, 본 문서는 그 결과물을 입력으로 받습니다.

아래 모든 수치는 공신력 출처를 인라인으로 표기했으나, 모델·토크나이저·배치 구성·스토리지 성능에 따라 크게 달라집니다. 따라서 **모든 값은 출발점(어림)이며 실측이 필요합니다.** 불확실한 항목은 본문에 "확인 필요"로 명시했습니다.

---

## 3.1 GPU 노드의 비-GPU 자원: vCPU·메모리 비율

GPU가 추론을 수행하더라도, GPU를 굶기지 않으려면(GPU starvation 방지) 호스트의 CPU·메모리가 데이터 공급·후처리·서빙 프레임워크를 충분히 받쳐 줘야 합니다. CPU가 데이터 공급을 못 따라가면 GPU가 그만큼 놀게 되어, 평균 GPU 사용률이 57% 수준까지 떨어질 수 있다는 측정이 보고됩니다([Hyperbolic, GPU Utilization Guide](https://www.hyperbolic.ai/blog/increase-gpu-utilization)).

### GPU당 vCPU 권장 비율

| 구분 | GPU당 권장(어림) | 근거·비고 |
| --- | --- | --- |
| 추론 전용(서빙) 하한 | 물리 코어 3–4개 / GPU | d2l.ai는 GPU 2장에 4–6코어급 CPU를 권장하며 코어 수보다 단일 스레드 클럭을 우선합니다([d2l.ai, Selecting Servers and GPUs](https://d2l.ai/chapter_appendix-tools-for-deep-learning/selecting-servers-gpus.html)). 구체 비율(예: GPU당 3코어)은 환경별 상이 — 확인 필요 |
| 에이전트·RAG 혼합 | 6–8 vCPU / GPU 이상 | 전처리·툴 호출·임베딩이 CPU에 얹히면 상향. 실측 필요([Spheron, CPU-to-GPU Ratio](https://www.spheron.network/blog/cpu-to-gpu-ratio-agentic-ai-inference/)) |
| 데이터 로더 워커 | 4–8 워커 / GPU | PyTorch DataLoader 전형값([AWS, Gluon data loader workers](https://aws.amazon.com/blogs/machine-learning/maximize-training-performance-with-gluon-data-loader-workers/)) |

코어 수보다 **단일 스레드 성능(클럭)** 이 병목이 될 수 있습니다. Python GIL 때문에 GPU가 4–8개로 늘어날 때 한 코어의 클럭이 처리량을 좌우하므로, "코어 6개·4GHz"가 "코어 8개·3.5GHz"보다 유리할 수 있습니다([d2l.ai](https://d2l.ai/chapter_appendix-tools-for-deep-learning/selecting-servers-gpus.html)).

### CPU-GPU 비율 점검 공식

요청당 (CPU 처리 시간) / (GPU 추론 시간) 비율이 **0.5를 넘으면** 규모 확장 시 CPU 기아가 나타납니다. CPU 코어가 100%에 붙는 동시에 GPU 사용률이 떨어지면 기아의 신호입니다([Spheron, CPU-to-GPU Ratio](https://www.spheron.network/blog/cpu-to-gpu-ratio-agentic-ai-inference/)).

### 호스트 메모리

호스트 RAM은 "vGPU에 할당된 vRAM 합계"가 아니라, **VM 게스트 메모리 + 서빙 프레임워크 작업 메모리 + CPU 측 KV/멀티모달 캐시 + ESXi 오버헤드**로 산정합니다. vLLM은 CPU RAM 부족 시 멀티모달 캐시를 `mm_processor_cache_gb`(기본 4GiB), CPU 백엔드 KV 캐시를 `VLLM_CPU_KVCACHE_SPACE`(기본 4GiB)로 제어합니다([vLLM, Conserving Memory](https://docs.vllm.ai/en/latest/configuration/conserving_memory/)). 구체적 게스트 메모리 합계는 워크로드별 실측이 필요합니다.

---

## 3.2 NUMA·PCIe 배치 고려

GPU 노드 성능은 GPU 자체보다 **GPU·NIC·CPU가 같은 NUMA 도메인/PCIe 루트 컴플렉스에 놓였는가**에 크게 좌우됩니다.

- 최적 처리량·지연을 위해 PCIe 토폴로지(루트 컴플렉스, 스위치)와 GPU·스토리지·NIC의 물리 배치를 점검해야 하며, 경로가 소켓/루트 컴플렉스를 가로지르면 "NUMA 세금(NUMA tax)"이 발생합니다([Medium/Daya Shankar, NUMA-Aware Storage Placement](https://medium.com/@daya-shankar/numa-aware-storage-placement-for-gpu-nodes-2d143fe54784)).
- 멀티노드 AI 워크로드에서는 GPU와 NIC를 **같은 NUMA 도메인·PCIe 루트 컴플렉스**에 배치하는 것이 권장됩니다([Medium/Daya Shankar](https://medium.com/@daya-shankar/numa-aware-storage-placement-for-gpu-nodes-2d143fe54784)).
- PCIe 전용 카드(NVLink 없는 구성)에서는 스케줄러가 PCIe·소켓 지역성을 존중하지 않으면 추론의 p99 지연 스파이크가 발생합니다(CPU 스레드·DMA 트래픽이 소켓을 가로지를 때)([DEV/Daya Shankar, How PCIe/NVLink/NUMA Affect Scheduling](https://dev.to/daya-shankar/how-pcie-nvlink-and-numa-topology-affect-gpu-scheduling-outcomes-l52)).

### vSphere 측 설정 원칙

| 항목 | 원칙 | 근거 |
| --- | --- | --- |
| vNUMA 노출 | 게스트 OS가 NUMA 토폴로지를 보도록 구성해 NUMA 인식 SW가 활용 | [Frank Denneman, vSphere CPU Topology Device Assignment](https://frankdenneman.ai/2022-10-25-vsphere-8-cpu-topology-device-assignment/) |
| Cores per Socket | 가상 소켓 수가 물리 NUMA 경계와 맞도록 설정 | [Frank Denneman](https://frankdenneman.ai/2022-10-25-vsphere-8-cpu-topology-device-assignment/) |
| 멀티-GPU VM 배치 | 토폴로지 인식 배치로 NVLink/PCIe 인접 GPU를 묶기 | [Frank Denneman, Topology-Aware Multi-GPU VM Placement](https://frankdenneman.ai/2026-03-31-Topology-Aware-Multi-GPU-VM-Placement/) |

PAIF 9.1 GPU WLD 전제로, 각 ESX 호스트에서 BIOS·그래픽 디바이스의 **SR-IOV 활성화**와 vGPU 호스트 드라이버 설치가 요구되며, 초기 클러스터는 **최소 3개 GPU 탑재 호스트**로 구성합니다([Broadcom TechDocs, Requirements for Deploying Private AI Foundation with NVIDIA](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/deploying-private-ai-foundation-with-nvidia/requirements-for-deploying-private-ai-foundation-with-nvidia.html)). 9.1 기준 세부 요구 사항은 [PAIF with NVIDIA 9.1 문서](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1.html)로 재확인이 필요합니다.

---

## 3.3 데이터 로더·전처리 오버헤드

추론 파이프라인은 "스토리지 적재 → CPU 전처리 → GPU 복사 → 추론"으로 흐르며, 어느 단계든 병목이 생기면 GPU가 다음 배치를 기다리며 유휴 상태가 됩니다([Towards Data Science, Caching Strategy for Input Pipeline](https://towardsdatascience.com/a-caching-strategy-for-identifying-bottlenecks-on-the-data-input-pipeline/)).

| 기법 | 권장값·효과 | 근거 |
| --- | --- | --- |
| DataLoader 워커 수 | GPU당 4–8 워커(전형) | [AWS, Gluon data loader workers](https://aws.amazon.com/blogs/machine-learning/maximize-training-performance-with-gluon-data-loader-workers/) |
| 메모리 피닝 | `pin_memory=True`로 CPU→GPU 전송 지연 감소 | [Towards Data Science, PyTorch Training Loop](https://towardsdatascience.com/improve-efficiency-of-your-pytorch-training-loop/) |
| 가변 전처리 시간 | `in_order=False` + 다중 워커로 느린 샘플 우회 | [Towards Data Science](https://towardsdatascience.com/improve-efficiency-of-your-pytorch-training-loop/) |

사이징 함의: 위 비-GPU 자원(워커 프로세스, 피닝된 페이지 메모리)은 **호스트 vCPU·메모리 산정에 가산**해야 하며, GPU당 워커 수만큼 추가 코어·메모리를 확보해야 합니다. 학습·파인튜닝 시 GPU 측 메모리 요건은 [02 §2.10 학습·파인튜닝 GPU 메모리](02-gpu-sizing.md#210-학습파인튜닝-gpu-메모리)에서 별도 산정합니다. 실제 워커 수와 전처리 비용은 입력 데이터 형식(텍스트/이미지/멀티모달)에 따라 달라져 실측이 필요합니다.

---

## 3.4 CPU 추론 경로(llama.cpp): 적용 범위와 사이징

GPU 없이 **소형 모델·임베딩**을 서빙해야 하는 경우(예: GPU 부족, 저지연이 불필요한 배치 작업), llama.cpp가 CPU/메모리만으로 추론을 제공합니다. llama.cpp는 `/v1/completions`, `/v1/chat/completions`, `/v1/embedding` 엔드포인트를 지원합니다([GitHub, ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)).

### GGUF 양자화별 메모리(어림)

| 모델 규모 | 4-bit(Q4) RAM(어림) | 비고 |
| --- | --- | --- |
| 7B | 약 5 GB | Q4_K_M는 메모리 약 75% 절감(어림), 품질 손실은 모델·태스크별 상이 — 실측 필요 |
| 13B | 약 9–10 GB | — |
| 70B | 약 40–45 GB | CPU 단독은 처리량 한계로 비권장 |

출처: [GitHub Discussion, Hardware specs for GGUF models](https://github.com/ggml-org/llama.cpp/discussions/3847), [Medium/Red Buffer, Running Quantized LLMs on CPU with llama.cpp](https://medium.com/red-buffer/ultimate-guide-to-running-quantized-llms-on-cpu-with-llama-cpp-1a26c34bb6dd).

### 적용 한계

- 양자화 비트가 낮을수록 빠르지만 정확도가 떨어집니다(속도·품질 트레이드오프)([Medium/Red Buffer](https://medium.com/red-buffer/ultimate-guide-to-running-quantized-llms-on-cpu-with-llama-cpp-1a26c34bb6dd)).
- CPU 경로는 **동시성·토큰 처리량이 GPU 대비 크게 낮아** 저트래픽·소형 모델·임베딩에 한정하고, 사용자 대면 저지연 LLM 서빙에는 부적합합니다. 손익분기 트래픽은 실측이 필요합니다.
- 쿠버네티스에서 llama.cpp Pod는 GPU 리소스를 요청하지 않으므로(아래 3.6) 일반 CPU 노드 풀에 배치합니다.

---

## 3.5 임베딩·리랭커 서버 사이징(RAG 비-LLM 컴포넌트)

전형적 RAG 흐름은 `질의 → 바이-인코더 검색(top 50) → 크로스-인코더 리랭커(top 10) → LLM`입니다([arXiv 2409.07691, Benchmarking Rerankers for RAG](https://arxiv.org/html/2409.07691v1)). 임베딩·리랭커는 LLM과 **별도 서버로 분리**해 독립 확장하는 것이 사이징을 단순화합니다.

| 컴포넌트 | 배치 권장 | 지연(어림) | 근거 |
| --- | --- | --- | --- |
| 임베딩(바이-인코더) | 중급 GPU 또는 CPU(저볼륨) | BGE-CPU 약 350ms vs GPU 약 80ms | [Medium/Xiwei Zhou, Reranker Speed Showdown](https://medium.com/@xiweizhou/speed-showdown-reranker-1f7987400077) |
| 리랭커(크로스-인코더) | 중급 GPU 권장 | 쌍별 평가로 임베딩보다 무거움 | [arXiv 2409.07691](https://arxiv.org/html/2409.07691v1) |

임베딩·리랭커 워크로드는 중급 GPU(예: A100, 일부 워크스테이션급)로 대부분의 프로덕션 RAG 볼륨을 H100급 없이 커버할 수 있습니다([Spheron, Self-Host Embeddings and Rerankers (TEI)](https://www.spheron.network/blog/self-host-embedding-reranker-tei-gpu-cloud/)). 대용량 코퍼스에서는 인덱싱 처리량이 병목이 되어 더 작은 임베딩 모델을 쓰고, 엄격한 서빙 지연 요구에서는 큰 리랭커가 부적합합니다([tensoria, Embedding Models 2026](https://tensoria.fr/en/blog/embedding-models-2026-guide)). 실제 모델·코퍼스별 처리량은 실측이 필요합니다(확인 필요).

---

## 3.6 Replica·동시성 환산: 워크로드 → Pod Replica → 노드 수요

[02 — GPU 사이징](./02-gpu-sizing.md)에서 "단일 Replica가 받칠 수 있는 동시성(또는 RPS)"을 산출했다는 전제 아래, 본 절은 이를 **Pod Replica 수 → 노드 수**로 환산합니다.

### 환산 단계

1. **목표 부하 정의**: 피크 동시 요청 수(또는 RPS)와 SLO(p99 지연).
2. **Replica당 용량**: vLLM 연속 배칭(continuous batching)은 정적 배칭 대비 처리량을 통상 2–4배 끌어올립니다([vLLM Blog, Anatomy of vLLM](https://blog.vllm.ai/2025/09/05/anatomy-of-vllm.html)). 연속 배칭·PagedAttention이 왜 이렇게 처리량을 끌어올리는지의 개념 설명은 [③ 서빙 가이드 §0.6](../../03-serving-api/docs/00-serving-primer.md)을 참조하세요. Replica당 유효 최대 동시성은 `max_model_len`, `max_num_batched_tokens`, `gpu_memory_utilization` 튜닝의 결과물입니다([vLLM Blog](https://blog.vllm.ai/2025/09/05/anatomy-of-vllm.html)).
3. **Replica 수** = ⌈목표 동시성 / Replica당 동시성⌉, 여기에 가용성 여유(N+1) 가산.
4. **노드 수** = Replica 수 × (Replica당 vGPU 수) ÷ (노드당 vGPU 수). 이때 노드당 vGPU는 02의 프로파일 결정에 따릅니다. 고정 GPU 인벤토리에서 거꾸로 적재량을 역산하는 공급 제약 시나리오는 [02 §2.9 고정 GPU 적재·패킹](02-gpu-sizing.md#29-고정-gpu-적재패킹-공급-제약)과 [09 역방향 사이징 시나리오](09-reverse-sizing-scenario.md)를 참조하세요.

### 환산 예시(샘플 — 실측 대체 필수)

| 항목 | 값(예시) | 비고 |
| --- | --- | --- |
| 피크 동시 요청 | 200 | 입력값 |
| Replica당 동시성 | 50 | 02·벤치 산출(어림) |
| 필요 Replica | ⌈200/50⌉ = 4 | — |
| 가용성 여유 | +1 (N+1) | 합 5 Replica |
| Replica당 vGPU | 1 | 02 입력 |
| 노드당 vGPU | 4 | 02 입력 |
| **필요 노드** | ⌈5/4⌉ = **2** | 최소 3 호스트 규칙과 병합 시 3 |

위 표의 모든 수치는 예시이며, Replica당 동시성은 모델·프로파일별 벤치마크로 대체해야 합니다.

### 오토스케일 신호

`vllm:num_requests_waiting`(스케줄러 대기 큐)가 지속 증가하면 유입 RPS가 처리 용량을 초과한다는 뜻이므로, 이를 HPA(Horizontal Pod Autoscaler, 쿠버네티스 수평 Pod 오토스케일러)·KEDA(Kubernetes Event-Driven Autoscaling, 이벤트 기반 오토스케일러) 메트릭으로 삼아 Replica를 늘립니다([vLLM, Metrics](https://docs.vllm.ai/en/latest/design/metrics/), [Red Hat Developer, Autoscaling vLLM](https://developers.redhat.com/articles/2025/11/26/autoscaling-vllm-openshift-ai-model-serving)).

---

## 3.7 메모리 오버커밋·예약(쿠버네티스 requests/limits) 원칙

| 원칙 | 권장 | 근거 |
| --- | --- | --- |
| GPU 리소스 | `limits`에만 정의(요청=한도, 정수; device-plugin 기준, DRA(Dynamic Resource Allocation, 동적 자원 할당)는 ResourceClaim 청구 — [04](04-vks-cluster-sizing.md) 참조) | [PerfectScale, K8s GPU Best Practices](https://www.perfectscale.io/blog/kubernetes-gpu) |
| 메모리 QoS | 추론 Pod는 **Guaranteed**(requests=limits)로 OOM·축출 회피 | [Kubernetes Blog, QoS for Memory (1.27)](https://kubernetes.io/blog/2023/05/05/qos-memory-resources/) |
| 메모리 오버커밋 | 저지연·임계 워크로드는 **1:1**(오버커밋 금지) | [oneuptime, Resource Requests and Limits](https://oneuptime.com/blog/post/2026-02-20-kubernetes-resource-requests-limits/view) |
| 스케줄링 기준 | 스케줄러는 `requests`로 배치 — requests를 실제 사용량에 맞게 | [k8s.guide, Scheduling Uses Requests](https://www.k8s.guide/insights/opinion/2026-03-10-kubernetes-scheduling-requests-not-limits/) |

핵심: GPU 추론 Pod와 임베딩·리랭커 Pod는 모두 저지연·임계 워크로드이므로 **메모리 requests = limits(Guaranteed)** 로 설정해 노드 메모리가 물리적으로 예약되게 하고, 커널 OOM 킬을 차단합니다([Kubernetes Blog](https://kubernetes.io/blog/2023/05/05/qos-memory-resources/)). 반대로 배치형·비임계 보조 작업(예: 야간 인덱싱)은 Burstable로 노드 집적도를 높일 수 있으나, 추론 Pod와 같은 노드에 두면 메모리 압박 시 추론이 영향을 받으므로 노드 풀을 분리하는 것이 안전합니다.

> 주의: GPU는 분할·오버커밋 불가 리소스이므로, GPU 자체의 "오버커밋"은 vGPU 타임슬라이싱/프로파일 수준(02)에서만 의미가 있으며 쿠버네티스 `limits`로는 표현되지 않습니다.

---

## 3.8 검증·실측 방법

문서의 모든 어림값은 아래 절차로 환경 실측치로 교체해야 합니다.

1. **CPU-GPU 비율 검증**
   - 단일 Replica에 부하를 주고 `nvidia-smi`(또는 vGPU 모니터링)로 GPU 사용률, `top`/`mpstat`로 코어 사용률을 동시에 관찰합니다.
   - (CPU 처리 시간)/(GPU 추론 시간) > 0.5 또는 CPU 100% + GPU 사용률 하락이면 vCPU를 증설합니다([Spheron](https://www.spheron.network/blog/cpu-to-gpu-ratio-agentic-ai-inference/)).

2. **데이터 파이프라인 병목 격리**
   - 캐싱 전략(전처리 결과 캐시)으로 GPU 유휴가 사라지는지 확인해 병목이 입력 파이프라인인지 GPU인지 판별합니다([Towards Data Science, Caching Strategy](https://towardsdatascience.com/a-caching-strategy-for-identifying-bottlenecks-on-the-data-input-pipeline/)).
   - DataLoader 워커 수를 4→8로 올리며 처리량 변화를 측정합니다.

3. **NUMA·PCIe 배치 점검**
   - 게스트에서 NUMA 노드 노출 여부, GPU·NIC가 동일 NUMA/루트 컴플렉스인지 점검하고, 소켓 교차 시 p99 지연 스파이크를 부하 테스트로 확인합니다([DEV/Daya Shankar](https://dev.to/daya-shankar/how-pcie-nvlink-and-numa-topology-affect-gpu-scheduling-outcomes-l52)).

4. **Replica 용량 벤치마크**
   - 동시성을 단계적으로 올리며 `vllm:num_requests_waiting`와 p99 지연을 측정해 SLO를 만족하는 **Replica당 동시성 상한**을 확정합니다([vLLM Metrics](https://docs.vllm.ai/en/latest/design/metrics/)). 이 값으로 3.6 환산표를 갱신합니다.

5. **임베딩·리랭커 처리량 측정**
   - 대상 모델·코퍼스로 인덱싱 처리량(임베딩)과 쌍별 리랭킹 지연을 실측해 CPU/GPU 배치 결정을 검증합니다([arXiv 2409.07691](https://arxiv.org/html/2409.07691v1)).

6. **메모리 QoS·OOM 검증**
   - 추론 Pod가 Guaranteed QoS인지(`kubectl describe pod`), 부하 중 OOMKilled가 없는지 확인합니다([Kubernetes Blog](https://kubernetes.io/blog/2023/05/05/qos-memory-resources/)).

7. **PAIF 9.1 요구 사항 재확인**
   - 호스트 수·SR-IOV·vGPU 프로파일 등 플랫폼 요건은 9.1 기준으로 [Broadcom TechDocs PAIF 9.1](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1.html)과 [Private AI Sizing Guide](https://www.vmware.com/docs/sizing-ai-workloads-on-vcf)를 대조해 확정합니다.

---

> 다음 문서에서는 본 사이징 결과를 비용으로 환산합니다. 사이징 입력(노드 수·자원)은 본 문서를, GPU 프로파일은 [02 — GPU 사이징](./02-gpu-sizing.md)을 참조하세요.

---
[← 이전: 02 GPU 사이징](02-gpu-sizing.md) · [목차](../README.md) · [다음: 04 VKS 클러스터 사이징과 인프라 →](04-vks-cluster-sizing.md)

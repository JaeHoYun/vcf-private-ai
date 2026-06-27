# 부록 A1 — 1차 가정치 레퍼런스 (예산 추정 전용)

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.
> 시리즈 인덱스: [vcf-private-ai-series](../../README.md)

> **중요 — 이 부록의 모든 숫자는 "구매 전 예산(budgetary) 추정" 단 하나의 목적을 위한 1차 가정치입니다.**
> 본문 [02 — GPU 사이징](../docs/02-gpu-sizing.md)·[03 — 컴퓨트·메모리 사이징](../docs/03-compute-memory-sizing.md)은 "Replica당 처리량은 반드시 실측"이라고 못 박습니다. 그 원칙은 그대로입니다. 이 부록은 **실측할 장비가 아직 없는 단계**에서 예산 윤곽을 잡기 위한 출발 숫자만 제공하며, 확정 사이징·발주·SLA 약정의 근거로 쓰면 안 됩니다. 모든 값은 PoC·부하시험 실측값으로 **반드시 교체**해야 합니다.

---

## A1.0 이 부록이 존재하는 이유 — 닭과 달걀

사이징의 핵심 숫자(예: "GPU 한 장이 초당 몇 토큰을 내는가", "한 Replica가 동시 몇 요청을 받치는가")는 모델·정밀도·엔진 버전·컨텍스트 분포에 따라 크게 달라지므로, 정답은 **자사 환경 실측**뿐입니다(본문 02·03의 일관된 원칙).

그런데 장비를 **사기 전에** 예산을 잡아야 하는 단계에서는 실측할 GPU가 없습니다. 출발 숫자가 없으면 첫 견적도 못 냅니다. 이것이 닭-달걀 문제입니다.

이 부록은 그 매듭만 끊습니다. 공신력 있는 출처가 공개한 수치를 **보수적 범위**로 모아 "0차 → 1차 추정"의 출발점을 제공합니다. 그 다음은 본문 절차를 그대로 따르고, [06.5 PoC→파일럿→프로덕션 로드맵](../docs/06-capacity-planning.md#65-poc--파일럿--프로덕션-용량-로드맵)에서 실측값으로 갈음합니다.

### 사용 3원칙

1. **항상 범위로, 보수적 끝을 기본값으로.** 단일 점추정 금지. 처리량은 범위의 낮은 값, 자원량은 높은 값을 기본으로 잡아 과소 산정을 피합니다.
2. **꼬리표를 단다.** 이 부록에서 가져온 모든 숫자는 산출물 옆에 `[A1 가정치]`로 표기해, 나중에 실측값으로 바꿀 대상임을 추적 가능하게 둡니다(시리즈의 근거 추적 원칙).
3. **실측으로 교체하고 델타를 기록한다.** PoC 후 실측값으로 바꾸고, 가정 대비 차이(델타)를 [01.6 검증·실측](../docs/01-sizing-methodology.md#16-검증실측-방법)·각 문서 검증 절에 남깁니다.

> 운영 지점 주의: 아래 처리량 수치는 대부분 **"최대 처리량(높은 배치)"** 작동점입니다. 저지연 SLA가 빡빡하면 동일 GPU의 실효 처리량은 더 낮아지고 필요 GPU 수는 늘어납니다(본문 [02.5](../docs/02-gpu-sizing.md#25-처리량지연-목표--gpu-수replica-환산) 트레이드오프).

---

## A1.1 추론 처리량·동시성 1차 가정치

가장 신뢰할 단일 출처는 VMware가 공개한 LLM 추론 사이징 계산기 가이드입니다. **계산기 추정치이지 실측 벤치마크가 아니므로** 규모 감각용으로만 씁니다([VMware — LLM Inference Sizing and Performance Guidance, 2024-09-25](https://blogs.vmware.com/cloud-foundation/2024/09/25/llm-inference-sizing-and-performance-guidance/)).

### 처리량(TPS, tokens/sec) — 가정: 입력 4096 / 출력 256 토큰, GPU 4장

| 모델 규모 | GPU(예시) | 처리량(TPS, 어림) | 출처 |
|---|---|---|---|
| 8B급 | L40s | 약 208 | VMware 계산기(2024-09-25) |
| 8B급 | H100 NVL | 약 907 | VMware 계산기(2024-09-25) |
| 70B급 | L40s | 약 24 | VMware 계산기(2024-09-25) |
| 70B급 | H100 NVL | 약 104 | VMware 계산기(2024-09-25) |

> VMware는 사용자 체감 하한으로 **"TPS 30 이상"**, 첫 토큰 응답 시간(TTFT, Time To First Token) 목표 **200ms 미만**을 제시합니다(동 출처). 단순 챗 응답 종단 지연 참고치: 8B/H100 NVL 약 0.3초, 8B/L40s 약 1.2초, 70B/L40s 약 10.8초(4096/256 가정, 동 출처).

측정 벤치마크(짧은 출력·고배치는 위 계산기보다 높게 나옴) 교차 참고:

| 구성 | 처리량(어림) | 출처·조건 |
|---|---|---|
| 8B급 / 단일 H100 80GB / 16-bit | 출력 약 5,500–6,300 tok/s, 약 9–10 req/s | [databasemart vLLM H100(2025)](https://www.databasemart.com/blog/vllm-gpu-benchmark-h100) — 입력 100 / 출력 600, 오프라인 |
| 8B급 / 단일 A100 80GB | H100 대비 약 25–30% 낮음 | [NVIDIA NIM 성능 문서](https://docs.nvidia.com/nim/llama-3-1-nemotron-safety-guard-8b/latest/performance.html) — 동시성 250 |
| 70B급 / H100×4 (TP=4) / BF16 | 약 2,600(입력 1000/출력 200)–7,000(200/200) TPS | [silexdata 70B(2025-05-18)](https://blog.silexdata.com/blog/evaluating-llama-33-70b-inference-h100-a100/) — 벤더 게시 자료 기반 비교, 상한값으로 해석 주의 |

> 출력 길이가 처리량을 가장 크게 좌우합니다. 짧은 출력 벤치마크는 1,000토큰 출력 대비 2–3배 높게 나올 수 있으므로, 자사 출력 분포로 보정하세요.

### 동시 요청 수(per GPU) 규칙 — RAG/챗 서빙

| 모델 규모 | GPU | 최장 컨텍스트 동시성 | 4096 컨텍스트 동시성 | 출처 |
|---|---|---|---|---|
| 8B급 | 단일 L40 48GB | 약 32 | 약 64 | VMware 계산기(2024-09-25) |
| 70B급 | A100 80GB×2 | 약 8 | 약 16 | VMware 계산기(2024-09-25) |
| 70B급 | A100 80GB×4 | 약 4.5 | — | VMware 계산기(2024-09-25) |

> "GPU당 사용자 N명" 같은 **고정 상수는 존재하지 않습니다.** 동시성은 모델·컨텍스트·배치·엔진의 함수입니다. 위 표는 출발점일 뿐이며, KV 캐시 기반 정밀 계산은 본문 [02.3](../docs/02-gpu-sizing.md#23-kv-캐시-산정-컨텍스트--동시성)과 토큰당 KV 계수(아래)를 쓰세요.

### KV 캐시 토큰당 계수(1차)

| 모델 규모 | 토큰당 KV(어림) | 교차검증 |
|---|---|---|
| 8B급 | 약 0.000122 GiB/token | VMware 계산기 = 구조식(레이어 32·KV헤드 8·head_dim 128·FP16) 동일치 |
| 70B급 | 약 0.000305 GiB/token | VMware 계산기(2024-09-25) |

> 구조식: `토큰당 KV(byte) ≈ 2 × 레이어 수 × KV 헤드 수 × head_dim × 정밀도(byte)`. 위 8B 계수는 본문 [02.3 워크드 예제](../docs/02-gpu-sizing.md#23-kv-캐시-산정-컨텍스트--동시성)에서 두 방법으로 동일하게 도출됩니다. 모델 구조값(레이어/KV헤드/head_dim)은 모델 카드·`config.json`에서 확인하세요([부록 A2](A2-inputs-and-defaults.md)).

---

## A1.2 임베딩·리랭커 1차 가정치 (RAG 비-LLM)

| 컴포넌트 | 처리량/지연(어림) | 출처·조건 |
|---|---|---|
| 임베딩(바이-인코더, 110M급) | GPU 약 4,000 문장/s, CPU 약 270 문장/s | [Hugging Face — Static Embeddings(2025-01)](https://huggingface.co/blog/static-embeddings) — `all-mpnet-base-v2` |
| 동일 모델 GPU 대비 CPU 속도 배수 | 약 3–6배 | [Sentence Transformers 효율 문서](https://sbert.net/docs/sentence_transformer/usage/efficiency.html) |
| 리랭커(크로스-인코더) 짧은 문서 | 약 0.1–0.2초(후보 수십 개) | [Oracle — Cohere Rerank 3.5 벤치](https://docs.oracle.com/en-us/iaas/Content/generative-ai/benchmark-cohere-rerank-3-5.htm) |
| 리랭커 긴 문서(2–4K 토큰) | 수 초까지 상승 | 동 출처 |

> 임베딩·리랭커는 LLM과 별도 서버로 분리해 독립 확장하는 것이 사이징을 단순화합니다(본문 [03.5](../docs/03-compute-memory-sizing.md#35-임베딩리랭커-서버-사이징rag-비-llm-컴포넌트)). 대부분의 프로덕션 RAG 볼륨은 중급 GPU로 처리됩니다.

---

## A1.3 모델 콜드스타트·로딩 1차 가정치

| 항목 | 값(어림) | 출처·조건 |
|---|---|---|
| 8B급(약 15GB) 로딩 | 기본 로더 약 15초, 스트리밍 약 3.6초 | [Azure SDK / Run:AI Model Streamer(2026-05)](https://devblogs.microsoft.com/azure-sdk/eliminate-llm-cold-starts-load-models-up-to-6x-faster-with-azure-blob-storage-and-runai-model-streamer/) |
| 대형(약 60GB) 로딩 | 기본 약 42초, 스트리밍 약 13초 | 동 출처 |
| NVMe 순차 읽기 | 약 3.5–7 GB/s(단일), RAID0 약 12 GB/s | [Level1Techs 포럼(스펙 범위 교차)](https://forum.level1techs.com/t/has-anybody-able-to-hit-the-advertised-read-speeds-from-nvme-ssd-when-it-comes-to-loading-a-slightly-bigger-llm/239935) |
| 70B safetensors 로딩 | 약 150초 → 30초 미만(fastsafetensors) | [fastsafetensors(2025)](https://www.alphaxiv.org/overview/2505.23072v1) |

> 콜드스타트 시간 ≈ (모델 GB) / (유효 읽기 GB/s). 단, 단순한 기본 로더는 NVMe 대역폭의 일부만 끌어내므로 **로더 방식(스트리밍/fastsafetensors)이 드라이브 스펙보다 더 중요**합니다. 본문 [05.3](../docs/05-storage-network-sizing.md#53-스토리지-성능--모델-로딩과-iops) 참조.

---

## A1.4 출처 일람 (도입 전 재확인 필수)

- [VMware — LLM Inference Sizing and Performance Guidance (2024-09-25)](https://blogs.vmware.com/cloud-foundation/2024/09/25/llm-inference-sizing-and-performance-guidance/) — 본 부록의 1차 앵커(계산기 추정치)
- [NVIDIA NIM 성능 문서](https://docs.nvidia.com/nim/llama-3-1-nemotron-safety-guard-8b/latest/performance.html)
- [databasemart — vLLM H100 벤치(2025)](https://www.databasemart.com/blog/vllm-gpu-benchmark-h100)
- [silexdata — Llama 70B H100/A100(2025-05-18)](https://blog.silexdata.com/blog/evaluating-llama-33-70b-inference-h100-a100/)
- [Hugging Face — Static Embeddings(2025-01)](https://huggingface.co/blog/static-embeddings)
- [Oracle — Cohere Rerank 3.5 벤치](https://docs.oracle.com/en-us/iaas/Content/generative-ai/benchmark-cohere-rerank-3-5.htm)
- [Azure SDK / Run:AI Model Streamer(2026-05)](https://devblogs.microsoft.com/azure-sdk/eliminate-llm-cold-starts-load-models-up-to-6x-faster-with-azure-blob-storage-and-runai-model-streamer/)

---

## A1.5 변동 요인 (인용 전 반드시 읽기)

- **출력 길이**가 처리량을 지배합니다(짧은 출력은 2–3배 부풀려짐). 입력/출력 토큰을 항상 고정하세요.
- **배치·동시성**: 최대 처리량 수치는 큰 배치 전제입니다. 사용자당 처리량은 동시성이 오르면 떨어지며, "최대 처리량"과 "저지연"은 다른 작동점입니다.
- **엔진·버전**: vLLM·TensorRT-LLM·SGLang·NIM이 다르고, vLLM 0.5→0.6만으로도 약 1.8–2.7배 차이가 보고됩니다. 엔진·버전 없는 수치는 비교 불가입니다.
- **정밀도**: FP8은 대역폭 병목(장문·대배치·대형 모델)에서 효과가 크고, 연산 포화 구간에서는 이득이 미미합니다.
- **벤더 best-case 주의**: MLPerf식 8-GPU 수치, "up to" 마케팅, 일부 벤더 게시 비교 자료는 낙관적 상한으로만 취급합니다.
- **교차 혼용 금지**: 모델 버전·GPU SKU·관리형 여부가 다르면 호환되지 않습니다. 점추정이 아니라 범위로 쓰세요.

> 본 부록의 어떤 수치도 확정값이 아닙니다. [06.5 로드맵](../docs/06-capacity-planning.md#65-poc--파일럿--프로덕션-용량-로드맵)의 PoC·파일럿 실측으로 갈음하고, 그 전까지는 `[A1 가정치]` 꼬리표를 유지하세요.

---
[← 이전: 09 역방향 시나리오](../docs/09-reverse-sizing-scenario.md) · [목차](../README.md) · [다음: A2 입력값 환산·기본값·모델 선택 →](A2-inputs-and-defaults.md)

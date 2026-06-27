# 05 — 스토리지·네트워크 용량 사이징

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.
> 시리즈 인덱스: [시리즈 허브](../../README.md)

이 문서는 GPU-Accelerated Workload Domain(이하 GPU WLD)에서 프라이빗 AI 추론·RAG 워크로드를 운영할 때 필요한 스토리지 용량·성능과 네트워크 대역폭을 사이징하는 방법을 다룹니다. 스토리지는 vSAN(ESA), 데이터/벡터는 DSM pgvector(②), 모델 레지스트리는 Harbor, 네트워크는 NSX를 전제로 합니다.

본 문서의 모든 수치는 공신력 있는 출처를 인라인으로 표기했으나, 실제 환경의 모델·임베딩·트래픽 특성에 따라 크게 달라집니다. 표에 제시한 값은 **어림(order-of-magnitude) 추정이며 실측이 필요**합니다. 검증 불가한 항목은 "확인 필요"로 표기했습니다.

멀티호스트 RDMA 패브릭(GPUDirect, RoCE 등) 설계는 본 문서 범위 밖이며 ① 인프라 가이드([① 인프라](../../01-infra/README.md))에 위임합니다.

---

## 5.1 스토리지 용량 — 어디에 무엇이 쌓이는가

프라이빗 AI 스택의 영속 데이터는 크게 다섯 갈래로 쌓입니다. 사이징의 출발점은 "각 갈래가 독립적으로 증가한다"는 점을 인지하는 것입니다.

| 데이터 갈래 | 저장 위치 | 1차 증가 요인 | 비고 |
|---|---|---|---|
| 모델 아티팩트(가중치) | Harbor 레지스트리 | 모델 크기 × 버전 × Revision | 가장 큰 단일 항목이 되기 쉬움 |
| 컨테이너 이미지(NIM 등) | Harbor 레지스트리 | 이미지 수 × 레이어 | 모델과 별도 적재 |
| 데이터셋/문서 코퍼스 | vSAN 데이터스토어 | 원문 크기 × 보존 정책 | 파인튜닝([02 §2.10](02-gpu-sizing.md#210-학습파인튜닝-gpu-메모리))/RAG 소스 |
| 벡터 인덱스 | DSM pgvector(②) | 차원 × 벡터 수 × 인덱스 오버헤드 | 5.4에서 별도 산정 |
| 로그·관측 데이터 | vSAN 데이터스토어 | 요청량 × 보존 기간 | 추론 로그·메트릭 |

### 모델 아티팩트(Harbor)

모델 가중치 용량은 파라미터 수와 정밀도(precision)로 1차 추정합니다. FP16(파라미터당 2바이트) 기준 70B 모델의 가중치는 약 140GB이며, 파라미터당 2바이트 환산으로 계산합니다([Spheron, "GPU Memory Requirements for LLMs"](https://www.spheron.network/blog/gpu-memory-requirements-llm/)). 양자화하면 줄어듭니다(예: FP8/INT8은 파라미터당 약 1바이트 → 70B ≈ 70GB).

핵심은 **버전·Revision 누적**입니다. Harbor는 모델·NVIDIA 추론 컨테이너의 레지스트리로 동작하며, 보안팀이 스캔·승인·RBAC로 관리하는 구조입니다([Broadcom TechDocs, "Storing ML Models in VMware Private AI Foundation"](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/what-is-private-ai-services/storing-ml-models-in-vmware-private-ai-foundation.html)). 동일 모델의 여러 버전을 보존하면 용량은 버전 수에 비례해 증가하므로, **보존 정책**(몇 개 버전을 남길지)을 먼저 정해야 합니다.

| 모델 규모(FP16 가정) | 가중치 1버전 | 3버전 보존 시 | 비고 |
|---|---|---|---|
| 7–8B | 약 14–16GB | 약 42–48GB | 어림, 실측 필요 |
| 70B | 약 140GB | 약 420GB | 어림, 실측 필요 |
| 405B | 약 810GB | 약 2.4TB | 확인 필요(정밀도·샤딩 영향 큼) |

정밀도·토크나이저·세이프텐서 샤딩 방식에 따라 실제 디스크 점유는 달라지므로 위 값은 어림이며 **레지스트리 실측이 필요**합니다.

### 데이터셋·로그

문서 코퍼스는 원문 용량에 비례하되, 청크/전처리 사본이 추가로 쌓이는 점을 감안합니다(원문 대비 1.5–2배 여유는 어림, 실측 필요). 추론 로그·관측 데이터는 "초당 요청 × 요청당 로그 크기 × 보존 일수"로 산정하며 보존 정책에 가장 민감합니다.

---

## 5.2 벡터 인덱스 용량 — DSM pgvector 산정 (② 연계)

벡터 인덱스 용량은 [② 벡터 DB](../../02-vectordb/README.md)와 연계해 별도로 산정합니다. 본 절은 용량 환산식만 다루고, 인덱스 튜닝·운영은 ②에 위임합니다.

### 기본 환산식

pgvector는 차원당 4바이트 float32로 저장하므로, 1536차원 임베딩 1건은 약 6KB입니다([Lantern Blog, "Understanding pgvector's HNSW Index Storage"](https://lantern.dev/blog/pgvector-storage); [pgvector issue #690](https://github.com/pgvector/pgvector/issues/690)).

- **원시 벡터 데이터** ≈ 벡터 수 × 차원 × 4바이트
- **HNSW 인덱스 오버헤드** ≈ 원시 벡터 크기의 약 1.5–3배(그래프 구조 포함) — 실측 변동 큼([DEV Community, "Scaling pgvector"](https://dev.to/philip_mcclarence_2ef9475/scaling-pgvector-memory-quantization-and-index-build-strategies-8m2))

실제 환경 참고치로, 1536차원 벡터 1천만 건의 HNSW 인덱스는 약 80–120GB에 이를 수 있습니다([DEV Community, "Scaling pgvector"](https://dev.to/philip_mcclarence_2ef9475/scaling-pgvector-memory-quantization-and-index-build-strategies-8m2)). 이 값은 그래프 파라미터(m, ef_construction)와 데이터 분포에 따라 변하므로 어림이며 **실측이 필요**합니다.

### 용량 환산 예시 (1536차원 가정)

| 벡터 수 | 원시 벡터(≈ ×4B) | HNSW 인덱스(약 2x 가정) | 합계(어림) |
|---|---|---|---|
| 100만 | 약 6GB | 약 12GB | 약 18GB |
| 1,000만 | 약 60GB | 약 120GB | 약 180GB |
| 5,000만 | 약 300GB | 약 600GB | 약 900GB |

> HNSW 인덱스를 1.5–3배 범위로 가정하면 합계는 위 값의 ±50% 이상 흔들립니다. 차원을 절반으로 줄이거나 float16(pgvector 0.7.0~, 인덱스 메모리 절반) 또는 양자화를 적용하면 크게 절감됩니다([Supabase, "What's new in pgvector v0.7.0"](https://supabase.com/blog/pgvector-0-7-0)). 따라서 위 표는 **상한 어림으로만** 사용하고 ②의 운영 지침에 따라 실측하세요.

또한 HNSW는 검색 성능을 위해 인덱스를 RAM에 상주시키는 것이 권장되므로, 위 용량은 **디스크뿐 아니라 메모리 사이징과도 직결**됩니다(메모리 산정은 ② 및 ⑥ 컴퓨트 사이징 문서로 위임).

---

## 5.3 스토리지 성능 — 모델 로딩과 IOPS

프라이빗 AI에서 스토리지 성능이 가장 직접적으로 체감되는 지점은 **모델 콜드스타트**(모델 로딩)입니다. 수십–수백 GB 가중치를 레지스트리/데이터스토어에서 GPU 메모리로 적재하는 시간은 곧 스토리지 순차 대역폭에 비례합니다.

### vSAN ESA 전제

VCF 9.x의 vSAN ESA는 고성능 NVMe·고속 네트워크를 전제로 한 차세대 아키텍처입니다. 동급 비교 시 합성 I/O에서 약 70% 높은 IOPS, 애플리케이션 레벨에서 약 20% 높은 IOPS를 유사한 서브밀리초 지연으로 제공한 결과가 보고됩니다([VCF Blog, "Performance Recommendations for vSAN ESA"](https://blogs.vmware.com/cloud-foundation/2023/01/01/performance-recommendations-for-vsan-esa/); [VCF Blog, "vSAN ESA Beats Performance of Top Storage Array"](https://blogs.vmware.com/cloud-foundation/2025/04/16/vsan-esa-beats-performance-of-top-storage-array-for-large-financial-firm/)).

또한 vSAN ESA는 압축이 항상 켜진(always-on) 클러스터 단위 기능이며, 데이터는 vSAN 네트워크로 전송되기 전에 압축되어 대역폭 효율을 높입니다([virtualvmx, "Key New vSAN Features in VCF 9.0"](https://www.virtualvmx.com/2025/08/key-new-vsan-features-in-vmware-cloud.html) — VCF 9.0 기준 비공식 정리, 9.1 동작은 공식 vSAN 문서로 재확인 필요). 다만 vSAN 성능은 호스트 하드웨어와 호스트 간 네트워크에서 파생되며 클러스터 호스트 수에 단순 비례하지 않습니다([VMware, "vSAN Design Guide"](https://www.vmware.com/docs/vmware-vsan-design-guide)).

### 워크로드별 성능 요건(어림)

| 워크로드 | 주요 패턴 | 1차 관심 지표 | 메모 |
|---|---|---|---|
| 모델 로딩(콜드스타트) | 대용량 순차 읽기 | 순차 대역폭(GB/s) | 콜드스타트 시간 ∝ 가중치 / 대역폭, 실측 필요 |
| 추론(상태 비저장) | 소량 랜덤 읽기 | 지연(ms) | 대부분 GPU 바운드, 스토리지 영향 낮음 |
| 벡터 검색(pgvector) | 인덱스 RAM 상주 | 메모리·지연 | 디스크 IOPS보다 RAM 상주 여부가 지배적 |
| 로깅/관측 | 지속 순차 쓰기 | 쓰기 대역폭 | 보존 정책에 따라 누적 |

콜드스타트 시간은 "가중치 용량 ÷ 유효 순차 대역폭"으로 1차 추정하되, 레지스트리 압축 해제·네트워크 경유·GPU 적재 단계가 합산되므로 단순 나눗셈보다 길어집니다. 정확한 수치는 환경별 **실측이 필요**합니다(콜드스타트 최적화는 ⑥ 운영 문서로 위임).

### 용량 오버헤드(가용 용량 환산)

성능과 별개로, vSAN ESA의 데이터 보호 정책은 **원시 용량 대비 가용 용량**에 직접 영향을 줍니다. VCF 9.1의 Auto-RAID는 3–5 호스트에서 FTT=1 RAID-5(2+1), 6 호스트 이상에서 FTT=2 RAID-6를 적용하며, 두 경우 모두 객체 기준 약 1.5배 용량 오버헤드가 발생합니다(압축·중복제거 절감 이전 기준)([VCF Blog, "Auto-RAID in vSAN for VCF 9.1"](https://blogs.vmware.com/cloud-foundation/2026/05/08/auto-raid-in-vsan-for-vcf-9-1/); [Broadcom TechDocs, "Using RAID 5/6 Erasure Coding"](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/vsan-deployment-administration-and-monitoring/administering-vmware-vsan/increasing-space-efficiency-in-a-vsan-cluster/using-raid-5-6-erasure-coding-in-vsan-cluster.html)).

즉 **필요 가용 용량 ≈ (논리 데이터 합계) × 약 1.5 ÷ (압축·중복제거 효과)** 로 1차 환산합니다. 압축·중복제거 효과는 데이터 특성에 따라 달라지므로 보수적으로 1.0(절감 없음)으로 시작해 실측으로 보정하세요.

---

## 5.4 네트워크 용량 — 추론·반입·내부 통신

네트워크 용량은 세 흐름으로 나눠 봅니다: (1) 외부→추론 트래픽, (2) 모델 반입(에어갭/Artifact Mirroring Tool), (3) 클러스터 내부 통신. 모두 NSX를 경유합니다.

### 추론 트래픽 대역폭

순수 텍스트 추론의 외부 대역폭은 토큰 단위로 추정합니다: "초당 동시 요청 × 요청당 토큰 × 토큰당 바이트". 일반적으로 텍스트 추론의 외부 대역폭은 GPU·스토리지 대비 작지만, 멀티모달(이미지·오디오·문서 업로드)이 섞이면 급증하므로 워크로드 믹스를 먼저 정의해야 합니다(수치는 환경별 어림, 실측 필요).

### 모델 반입(에어갭/Artifact Mirroring Tool)

규제·데이터 주권 요건이 있는 프라이빗 AI에서는 에어갭(disconnected) 반입이 일반적입니다. VCF 9.1에서는 Private AI Services용 아티팩트 미러링 도구(Artifact Mirroring Tool)로 설치 아티팩트를 로컬 OCI 레지스트리에 복제하여 에어갭 환경을 지원합니다([Broadcom TechDocs, "VMware Private AI Foundation with NVIDIA 9.1"](https://techdocs.broadcom.com/content/dam/broadcom/techdocs/us/en/pdf/vmware/private-ai/private-ai-nvidia/vmware-private-ai-foundation-with-nvidia-9-1.pdf)). 모델은 `vcf pais` CLI로 Harbor 모델 갤러리에 push/pull 합니다([Broadcom TechDocs, "Storing ML Models in PAIF"](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/what-is-private-ai-services/storing-ml-models-in-vmware-private-ai-foundation.html)).

반입은 일회성 대용량 전송이므로 상시 대역폭보다 **반입 창(window) 동안의 처리량**이 관건입니다. "반입 시간 ≈ 총 아티팩트 용량 ÷ 반입 경로 대역폭"으로 1차 추정합니다(에어갭 매체·미러 경로에 따라 변동, 실측 필요).

### 에어갭 미러 저장소·레지스트리 디스크

위 항목이 반입에 걸리는 **시간**을 다뤘다면, 이 항목은 반입 결과가 **내부 레지스트리에 차지하는 디스크**를 다룹니다. 에어갭 반입 시 Artifact Mirroring Tool은 PAIS Services 패키지와 NVIDIA GPU Operator 구성요소를 내부 Harbor 프로젝트(OCI 레지스트리)에 미러링합니다. 이때 플랫폼 Harbor 프로젝트는 **PAIS 플랫폼 아티팩트용으로 20GB**가 필요합니다([Broadcom TechDocs, "Upload the Private AI Services Components to a Disconnected Environment"](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/deploying-private-ai-foundation-with-nvidia/installing-and-configuring-private-ai-services/upload-the-private-ai-services-components-to-a-disconnected-environment.html)). 이 20GB는 **PAIS 플랫폼 아티팩트 기준의 고정 하한**일 뿐이며, 모델 갤러리(모델 가중치)와 NVIDIA 컨테이너 이미지(NIM/드라이버)는 여기에 포함되지 않고 **별도로 저장·별도 산정**합니다.

따라서 내부 레지스트리 총 디스크는 다음과 같이 가산식으로 1차 산정합니다.

> **내부 레지스트리 디스크 ≈ 20GB(PAIS 플랫폼 아티팩트, 고정 하한) + Σ(모델 갤러리: 모델 가중치 × 보존 버전 수) + NVIDIA 컨테이너 이미지(NIM/드라이버)**

모델 가중치 계수는 본 문서 §5.5 워크시트의 입력 가정을 재사용합니다(예: 70B FP16 ≈ 1버전 140GB — [§5.5 입력 가정](#55-사이징-워크시트--규모에서-용량으로) 참조). NVIDIA 컨테이너 이미지의 구체 용량은 공식 문서에 고정값이 없으므로 본 문서에서 지어내지 않으며, §5.5의 NIM 항목과 마찬가지로 실측으로 채웁니다.

또한 인터넷 연결 미러 호스트(반입 준비 측)에도 pull 산출물(`pais-store` 패키지)을 담을 스크래치 공간이 필요합니다. 정확한 수치는 공식 문서에 없으므로 **어림**이며, 반입 대상 아티팩트 합계와 같은 차수로 보수적으로 잡은 뒤 **실측으로 보정**하는 것이 안전합니다.

| 항목 | 1차 산정 | 메모 |
|---|---|---|
| PAIS 플랫폼 아티팩트(Harbor 프로젝트) | 20GB | 공식 고정값(고정 하한), 모델·NIM 미포함 |
| 모델 갤러리(가중치) | Σ(모델 가중치 × 보존 버전 수) | §5.5 계수 재사용(예: 70B FP16 ≈ 140GB/버전) |
| NVIDIA 컨테이너 이미지(NIM/드라이버) | 별도 산정(실측) | 공식 고정값 없음, 지어내지 않음 |
| 미러 호스트 스크래치(`pais-store`) | ≈ 반입 아티팩트 합계 차수 | 어림, 실측 보정 필요 |

### 클러스터 내부 통신·NSX 처리량

NSX Edge VM(Large)은 흐름·패킷 크기·서비스에 따라 게이트웨이당 약 20Gbps 수준을 처리하며(DPDK 코어당 약 5Gbps), VCF 9.1은 최대 8개 Edge 노드의 active-active Tier-0 게이트웨이로 North-South 처리량을 확장합니다([VCF Blog, "Simplify Workload Connectivity and Enhance Network Scale and Performance with VCF 9.1"](https://blogs.vmware.com/cloud-foundation/2026/05/05/simplify-workload-connectivity-and-enhance-network-scale-and-performance-with-vcf-9-1/); [VMware, "NSX Bare Metal Edge Performance"](https://blogs.vmware.com/networkvirtualization/2023/09/vmware-nsx-bare-metal-edge-performance.html/)). 더 높은 처리량이 필요하면 Bare Metal Edge(4×100Gbps에서 약 388Gbps North-South, 8노드 클러스터 합계 약 3Tbps)가 옵션입니다([VMware, "NSX Bare Metal Edge Performance"](https://blogs.vmware.com/networkvirtualization/2023/09/vmware-nsx-bare-metal-edge-performance.html/)). VM 기반 Edge도 VMXNET3 개선으로 10–65Gbps 범위를 지원합니다([virtualvmx, "VMXNET3 Now Supports Up to 65 Gbps"](https://www.virtualvmx.com/2025/05/vmxnet3-performance-boom-with-65-gbps.html)).

| 네트워크 흐름 | 1차 산정식 | 경유 | 메모 |
|---|---|---|---|
| 외부 추론 | 동시요청 × 토큰 × 토큰당 바이트 | NSX Tier-0/Tier-1 | 텍스트는 작음, 멀티모달 급증 |
| 모델 반입(Artifact Mirroring Tool) | 총 아티팩트 ÷ 반입 대역폭 | 에어갭 미러 경로 | 일회성 대용량, 창 기준 |
| 내부(앱↔pgvector↔모델) | 검색·프롬프트 트래픽 | NSX 분산 스위칭/DFW | DFW 정책 오버헤드 확인 필요 |
| GPU 간 RDMA 패브릭 | 범위 밖 | 전용 패브릭 | ① 인프라로 위임 |

> 멀티호스트 GPU 간 RDMA(GPUDirect/RoCE) 패브릭은 본 표에서 의도적으로 제외했습니다. 설계·사이징은 [① 인프라](../../01-infra/README.md)를 참조하세요.

---

## 5.5 사이징 워크시트 — 규모에서 용량으로

아래는 "모델·데이터·인덱스 규모"를 입력해 스토리지 용량을 환산하는 예시 워크시트입니다. 모든 계수는 본 문서의 출처에 근거한 어림이며, 표의 마지막 행은 vSAN 보호 오버헤드(약 1.5배)를 반영한 **필요 가용 용량**입니다.

### 입력 가정(예시 시나리오)

| 항목 | 입력값(예시) | 근거/계수 |
|---|---|---|
| 모델 규모 | 70B FP16, 3버전 보존 | 가중치 1버전 ≈ 140GB |
| NIM 컨테이너 이미지 | 약 50GB(어림) | 확인 필요 |
| 문서 코퍼스(원문) | 200GB | 전처리 사본 ×1.5 가정 |
| 벡터 인덱스 | 1536차원 × 1,000만 건 | 원시 ×4B + HNSW ×2 |
| 로그·관측(90일) | 100GB(어림) | 보존 정책 의존 |
| PAIS 플랫폼 아티팩트(에어갭) | 20GB(고정 하한) | 내부 Harbor 프로젝트, §5.4 참조 |

### 용량 환산

| 갈래 | 논리 용량(어림) | 산정 근거 |
|---|---|---|
| 모델 아티팩트 | 약 420GB | 140GB × 3버전 |
| 컨테이너 이미지 | 약 50GB | 어림, 실측 필요 |
| 문서 코퍼스 | 약 300GB | 200GB × 1.5 |
| 벡터 인덱스(pgvector) | 약 180GB | 60GB + 120GB(HNSW) |
| 로그·관측 | 약 100GB | 90일 보존 가정 |
| **논리 합계** | **약 1,050GB(≈1.05TB)** | 위 합산 |
| **필요 가용 용량** | **약 1.6TB** | 논리 합계 × 1.5(보호 오버헤드, 압축 절감 미반영) |

> 위 합계는 단일 예시이며, 모델 규모·보존 버전 수·벡터 건수가 바뀌면 선형 이상으로 변합니다. 특히 모델 버전 보존 정책과 벡터 인덱스 오버헤드 가정이 총량을 좌우하므로, 이 두 항목을 가장 먼저 실측·확정하세요. 압축·중복제거를 적용하면 가용 용량 요건은 줄어들 수 있으나(데이터 특성 의존), 본 워크시트는 보수적으로 절감을 반영하지 않았습니다.

---

## 5.6 검증·실측 방법

본 문서의 모든 수치는 출처 기반 어림이므로, 운영 전 다음 절차로 실측·검증하세요.

1. **모델 아티팩트 실측**: Harbor 레지스트리에서 대상 모델의 실제 정밀도·샤딩 기준 디스크 점유와 보존 버전 수를 확인합니다. FP16 140GB(70B)는 출발점일 뿐이며 양자화 시 크게 줄어듭니다([Spheron, "GPU Memory Requirements for LLMs"](https://www.spheron.network/blog/gpu-memory-requirements-llm/)).
2. **벡터 인덱스 실측**: 대표 데이터 1만–10만 건으로 pgvector HNSW를 실제 빌드해 인덱스 크기를 측정하고, 1.5–3배 오버헤드 범위 중 실제 계수를 도출합니다([Lantern Blog](https://lantern.dev/blog/pgvector-storage); [DEV Community, "Scaling pgvector"](https://dev.to/philip_mcclarence_2ef9475/scaling-pgvector-memory-quantization-and-index-build-strategies-8m2)). 운영 지침은 [② 벡터 DB](../../02-vectordb/README.md)를 따릅니다.
3. **콜드스타트 측정**: 대상 모델을 레지스트리→GPU로 실제 로딩해 콜드스타트 시간을 측정하고, "가중치 ÷ 유효 대역폭" 추정치와 비교해 단계별 병목을 식별합니다.
4. **vSAN 성능·용량 검증**: vSAN ESA 성능 대시보드로 IOPS·지연·대역폭을 확인하고([Broadcom TechDocs, "vSAN ESA Performance Dashboard"](https://techdocs.broadcom.com/us/en/vmware-cis/aria/aria-operations/8-18/vmware-aria-operations-configuration-guide-8-18/predefined-dashboards-in-vrealize-operations-manager/performance-dashboards/vsan-esa-performance-dashboard.html)), Auto-RAID 정책별 실제 가용/원시 용량 비율을 확인합니다([VCF Blog, "Auto-RAID in vSAN for VCF 9.1"](https://blogs.vmware.com/cloud-foundation/2026/05/08/auto-raid-in-vsan-for-vcf-9-1/)).
5. **네트워크 처리량 검증**: 추론 트래픽은 워크로드 믹스(텍스트/멀티모달)로 대역폭을 실측하고, NSX Edge 게이트웨이 처리량이 흐름·서비스 조합에서 예상치를 충족하는지 확인합니다([VCF Blog, "VCF 9.1 Network Scale and Performance"](https://blogs.vmware.com/cloud-foundation/2026/05/05/simplify-workload-connectivity-and-enhance-network-scale-and-performance-with-vcf-9-1/)).
6. **모델 반입 리허설**: 에어갭 환경이면 Artifact Mirroring Tool로 실제 미러링 한 사이클을 수행해 반입 창 처리량과 소요 시간을 측정합니다([Broadcom TechDocs, "PAIF with NVIDIA 9.1"](https://techdocs.broadcom.com/content/dam/broadcom/techdocs/us/en/pdf/vmware/private-ai/private-ai-nvidia/vmware-private-ai-foundation-with-nvidia-9-1.pdf)).

> 컴퓨트(GPU/CPU/메모리) 사이징, 콜드스타트 운영 최적화, 비용 환산은 본 시리즈의 다른 문서를 참조하세요. 본 문서는 스토리지·네트워크 용량에 한정합니다.

---
[← 이전: 04 VKS 클러스터 사이징과 인프라](04-vks-cluster-sizing.md) · [목차](../README.md) · [다음: 06 용량 계획과 운영 →](06-capacity-planning.md)

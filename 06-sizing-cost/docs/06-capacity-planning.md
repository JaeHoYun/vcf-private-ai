# 06 — 용량 계획과 운영

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.
> 시리즈 인덱스: [vcf-private-ai-series](../../README.md)

GPU-Accelerated Workload Domain(GPU 가속 워크로드 도메인, 이하 GPU WLD)을 한 번 구축했다고 끝이 아닙니다. AI 워크로드는 모델 교체·동시 사용자 증가·신규 테넌트 온보딩에 따라 수요가 빠르게 변합니다. 본 문서는 "지금 용량이 충분한가, 언제 무엇을 증설해야 하는가, 그 비용은 누구에게 귀속되는가"라는 운영 단계의 질문에 답하기 위한 **용량 계획(capacity planning)** 관점을 다룹니다.

- 인프라 구축·GPUaaS 테넌시 모델의 상세는 [① 인프라 가이드](../../01-infra/README.md)를 참조하세요. 본 문서는 동일 주제를 "용량" 시점으로만 다룹니다.
- 비용 모델(단가 산정·TCO·과금 공식)의 상세는 본 시리즈 [07-tco-cost-model.md](./07-tco-cost-model.md)를 참조하세요. 본 문서는 용량이 비용에 어떤 "입력값"이 되는지까지만 다룹니다.

---

## 6.1 용량 모니터링 지표 — 무엇을 봐야 의사결정이 되는가

용량 의사결정은 감(感)이 아니라 측정값에서 출발해야 합니다. VCF 9.1의 VCF Operations는 GPU·vGPU 메트릭을 기본 수집하며, 모델·에이전트 단위의 AI 메트릭(토큰 처리량, 첫 토큰까지 시간(TTFT), E2E 요청 지연)까지 대시보드로 제공합니다([VCF 9.1 AI 워크로드 블로그](https://blogs.vmware.com/cloud-foundation/2026/05/05/streamline-simplify-and-protect-all-your-ai-workloads-with-vcf-9-1/)). 더 낮은 계층의 정밀 지표는 NVIDIA DCGM(Data Center GPU Manager)이 담당합니다.

용량 계획의 입력값이 되는 핵심 지표를 계층별로 정리합니다.

| 계층 | 지표 | 출처/메트릭 | 용량 의사결정에서의 의미 |
| --- | --- | --- | --- |
| 물리 GPU | GPU 사용률(compute) | DCGM `DCGM_FI_DEV_GPU_UTIL` (0–100%) | 코어 연산 부하. 지속 고점이면 증설 신호 |
| 물리 GPU | SM(Streaming Multiprocessor, GPU 연산 코어 단위) 활성/점유 | DCGM `DCGM_FI_PROF_SM_ACTIVE`, `DCGM_FI_PROF_SM_OCCUPANCY` | GPU가 "바쁜지"와 "효율적으로 쓰이는지" 구분 |
| 물리 GPU | GPU 메모리(VRAM) | DCGM `DCGM_FI_DEV_FB_USED` / `DCGM_FI_DEV_FB_FREE` (MiB) | 모델 적재 한계. 사용률이 낮아도 VRAM이 꽉 차면 추가 배치 불가 |
| 물리 GPU | 전력·온도 | DCGM 전력/온도 메트릭, VCF Operations GPU 메트릭 | 열·전력 한계로 인한 실질 가용 한도 |
| 가상화 | vGPU 사용률 | VCF Operations vGPU 메트릭 | 프로파일 분할 후의 테넌트별 실사용 |
| 할당 | 쿼터 소진율 | 네임스페이스/프로젝트 쿼터 대비 사용량 | "물리는 남는데 정책상 못 쓰는" 구간 식별 |
| 서비스 | 대기·거부 요청, P95 지연 | VCF Operations AI 메트릭(TTFT·E2E 지연), 인퍼런스 게이트웨이 | 사용자 체감 한계. 용량 부족의 최종 증거 |

DCGM 메트릭 정의·단위는 [NVIDIA DCGM Feature Overview](https://docs.nvidia.com/datacenter/dcgm/latest/user-guide/feature-overview.html)를, GPU 사용률·VRAM·SM 메트릭의 해석은 [DCGM 모니터링 개요](https://medium.com/@MetricFire/why-gpu-monitoring-matters-tracking-utilization-power-and-errors-with-dcgm-603de3c4742b)를 참조하세요. DCGM은 DCGM-Exporter를 통해 Prometheus 형식으로 메트릭을 노출할 수 있어 Grafana 대시보드와 연동됩니다. VCF 9.1의 AI 메트릭 대시보드 역시 Grafana 배포를 전제로 합니다([VCF 9.1 AI 워크로드 블로그](https://blogs.vmware.com/cloud-foundation/2026/05/05/streamline-simplify-and-protect-all-your-ai-workloads-with-vcf-9-1/)).

핵심 해석 원칙입니다.

- **사용률과 메모리는 별개 신호입니다.** GPU 사용률이 40%여도 VRAM이 95%면 더 이상 모델을 적재할 수 없습니다. 둘 다 봐야 합니다.
- **SM 활성도와 점유율을 함께 봐야 "낭비"가 보입니다.** 사용률은 높은데 SM 점유율이 낮으면 GPU가 비효율적으로 돌고 있을 수 있습니다([DCGM Feature Overview](https://docs.nvidia.com/datacenter/dcgm/latest/user-guide/feature-overview.html)).
- **쿼터 소진율과 물리 사용률의 괴리**가 멀티테넌트 용량 문제의 출발점입니다(6.3).

---

## 6.2 증설 트리거 — 임계·헤드룸·버스트 정책

지표를 본다는 것은 "어느 선을 넘으면 행동한다"는 규칙이 있다는 뜻입니다. 증설 트리거는 단일 순간값이 아니라 **지속 시간·헤드룸·소진 속도**를 함께 봐야 오탐(false positive)을 줄일 수 있습니다.

아래 임계값은 조직마다 달라지는 출발점 예시이며, 실제 값은 워크로드 특성과 SLO(Service Level Objective, 서비스 수준 목표)에 맞춰 보정해야 합니다(확정 수치는 조직별 합의 필요).

| 트리거 후보 | 예시 임계 | 관측 창 | 행동 |
| --- | --- | --- | --- |
| 평균 GPU 사용률 | 7일 평균 70% 초과 | 7일 이동평균 | 증설 검토 착수 |
| 피크 GPU 사용률 | P95가 90% 초과 | 일 단위 | 헤드룸 잠식 경고 |
| GPU 메모리(VRAM) | 95% 초과 빈발 | 시간 단위 | 메모리 한계 우선 증설 |
| 쿼터 소진율 | 테넌트 90% 도달 | 즉시 | 쿼터 재배분 또는 증설 |
| 대기 큐/거부 요청 | 0 초과 지속 | 분 단위 | 즉시 용량 부족 신호 |
| P95 지연(E2E·TTFT) | SLO 임계 초과 | 분 단위 | 서비스 품질 저하, 긴급 검토 |

헤드룸(headroom)과 버스트(burst) 정책의 권고 방향입니다.

- **헤드룸 확보**: 프로덕션 추론은 평균 사용률을 100%까지 끌어올리지 않습니다. 트래픽 변동·노드 장애·롤링 업데이트를 흡수할 여유분(예: 20–30%)을 남깁니다. 헤드룸을 0으로 운영하면 장애 1건이 곧 SLO 위반이 됩니다.
- **버스트 흡수**: 단기 피크는 증설보다 큐잉·우선순위·MIG(Multi-Instance GPU, 단일 GPU를 격리된 여러 인스턴스로 분할)/vGPU 재분배로 흡수하고, **지속적·구조적 증가**일 때만 물리 증설로 대응합니다. 순간 피크에 반응해 증설하면 곧 유휴가 됩니다.
- **소진 속도 기반 예측**: 쿼터·VRAM·용량의 "소진 속도"를 추세선으로 보면 "며칠 후 고갈"을 미리 알 수 있습니다. VCF Operations의 용량·비용 인사이트가 이 추세 기반 권고를 제공합니다([VCF 9.1 Operations 블로그](https://blogs.vmware.com/cloud-foundation/2026/05/05/scale-simplify-and-secure-your-private-cloud-operations-with-vcf-9-1/)).

증설의 형태는 두 가지입니다. **GPU/노드 수평 증설**(GPU WLD에 호스트 추가)과 **활용 효율 개선**(리클레임·라이트사이징으로 기존 자원 회수). VCF Operations 9.1의 리클레임 대시보드와 라이트사이징 권고는 "증설 전에 회수할 자원"을 먼저 식별하게 해줍니다([VCF 9.1 Operations 블로그](https://blogs.vmware.com/cloud-foundation/2026/05/05/scale-simplify-and-secure-your-private-cloud-operations-with-vcf-9-1/)). 하드웨어 공급·비용 부담이 큰 시기일수록 "증설하기 전에 먼저 회수"하는 것이 비용을 아끼는 첫 수입니다([VCF 9.1 출시 발표](https://www.broadcom.com/company/news/product-releases/64326)).

### 역방향 진입 — 유휴·사일로 자원 진단과 회수

이미 도입했으나 유휴·사일로 상태인 GPU를 가용 풀로 되돌리는 것은 [역방향(공급 제약) 사이징](01-sizing-methodology.md#17-순방향역방향-사이징)의 출발점입니다([09](09-reverse-sizing-scenario.md) §9.5). 진단·회수는 위 6.1 지표와 6.2 트리거를 그대로 씁니다.

- **저활용 진단**: 평균 GPU 사용률은 낮은데(6.1) 특정 팀·네임스페이스가 점유 중이거나, 쿼터 소진율과 물리 사용률의 괴리(6.1·6.3)가 크면 "정책상 묶여 노는" 자원입니다.
- **회수**: VCF Operations 9.1의 리클레임·라이트사이징 권고로 미사용 예약·과대 할당을 식별해 공유 풀로 되돌립니다(6.2). 예약 점유도 비용이므로 쇼백으로 자발적 반납을 유도합니다(6.4).
- **재배치**: 회수한 자원을 [09](09-reverse-sizing-scenario.md)의 워크로드 포트폴리오(추론·멀티모델·파인튜닝)로 재배분하고, 재사일로화를 막기 위해 네임스페이스 쿼터·Reservation 상한을 다시 설정합니다(6.3).

> 증설 이전 회수가 원칙입니다(6.2). 고정 풀로도 부족분이 확인될 때만 그 초과분을 순방향으로 추가 산정합니다([01 §1.7](01-sizing-methodology.md#17-순방향역방향-사이징)).

---

## 6.3 GPU Reservation·쿼터 용량 전략 — 예약분과 가용분의 균형

GPU Reservation(GPU 예약)은 미션 크리티컬 AI 워크로드가 시작에 필요한 GPU 자원을 확보하도록 GPU 슬롯을 사전 확보하는 기능입니다([PAIF with NVIDIA 9.0.x 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-release-notes/vmware-private-ai-foundation-with-nvidia-90-release-notes.html)). 용량 관점에서 예약은 양날의 검입니다. 예약을 많이 잡으면 중요 워크로드의 가용성은 보장되지만, 미사용 예약분이 전체 가용 용량을 잠식합니다.

용량 배분의 기본 단위와 균형 원칙입니다.

| 개념 | 정의 | 용량 관점 함의 |
| --- | --- | --- |
| GPU Reservation | 워크로드용 GPU 슬롯 사전 확보 | 예약분은 가용 풀에서 차감됨. "보장 ↔ 활용률" 트레이드오프 |
| VM Class(vGPU 프로파일) | CPU·메모리·vGPU 프로파일을 정의한 템플릿 | 프로파일이 분할 단위를 고정 → 용량 입도 결정 |
| 전체 메모리 예약 | GPU 가속 VM은 풀 메모리 예약 필요 | 메모리 오버커밋 불가 → 밀도 상한 |
| 네임스페이스 쿼터 | 프로젝트/테넌트별 자원 상한 | 물리 여유와 무관하게 정책적 사용 한도 결정 |

VM Class는 관리자가 사전에 vGPU 프로파일을 골라 구성하며, 선택 가능한 프로파일은 하드웨어가 탑재한 물리 GPU에 따라 고정됩니다. AI/ML 워크로드용 GPU VM Class는 전체 메모리 예약이 필요합니다([PAIF with NVIDIA VCF Automation 설정 가이드](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/deploying-private-ai-foundation-with-nvidia/setting-up-vcf-automation-for-private-ai-foundation-with-nvidia/set-up-vmware-aria-automation-for-private-ai-foundation-with-nvidia.html)). 네임스페이스는 네임스페이스 클래스와 VPC(Virtual Private Cloud, 가상 사설 네트워크 경계)로 뒷받침되며, vCenter에서 해당 네임스페이스용 리소스 풀이 생성되어 예약·한도 값이 설정됩니다(동 가이드).

멀티테넌트 용량 배분 전략(용량 시점)입니다.

- **예약분 vs 가용분 비율을 명시적으로 관리합니다.** 예약분이 전체의 일정 비율(예: 70%)을 넘어서면 신규 예약을 막고 가용 풀을 보호하는 정책을 둡니다(확정 비율은 조직별 합의 필요).
- **쿼터는 "물리 ≥ 쿼터 합"을 깨지 않게 설계합니다.** 오버서브스크립션 정책을 쓰더라도, 쿼터 합이 물리 용량을 과도하게 초과하면 동시 피크에서 거부가 발생합니다. 쿼터 소진율(6.1)과 물리 사용률을 함께 추적해 괴리를 모니터링합니다.
- **관리자는 테넌트 간 쿼터·권한·사용량·지출을 통합 관리**해 성능과 비용을 동시에 최적화할 수 있습니다([PAIF with NVIDIA 9.1 데이터시트/가이드](https://techdocs.broadcom.com/content/dam/broadcom/techdocs/us/en/pdf/vmware/private-ai/private-ai-nvidia/vmware-private-ai-foundation-with-nvidia-9-1.pdf)).
- **독점 접근 워크로드는 별도 용량 풀로 분리합니다.** VCF 9.1 Private AI Services의 DirectPath Enablement는 단일 VM에 GPU 독점 접근을 제공하므로, 이런 워크로드는 공유 풀과 분리해 가용 용량 계산을 단순화합니다([VCF 9.1 AI 워크로드 블로그](https://blogs.vmware.com/cloud-foundation/2026/05/05/streamline-simplify-and-protect-all-your-ai-workloads-with-vcf-9-1/)).

테넌시 모델·격리 설계의 상세는 [① 인프라 가이드](../../01-infra/README.md)를 참조하세요.

---

## 6.4 쇼백·차지백의 용량·비용 입력값

용량 데이터는 그 자체로 과금의 원천입니다. 누가 얼마나 썼는지(사용량)와 무엇을 점유했는지(예약·쿼터)가 곧 쇼백(showback, 사용량 가시화)·차지백(chargeback, 실제 비용 청구)의 입력값이 됩니다.

VCF Operations 9.1은 애플리케이션 단위 쇼백·차지백을 제공하며, VKS(VMware vSphere Kubernetes Service) 비용 상세를 포함해 모던 워크로드의 빌링·쇼백·차지백 분석을 개선했습니다([VCF 9.1 Operations 블로그](https://blogs.vmware.com/cloud-foundation/2026/05/05/scale-simplify-and-secure-your-private-cloud-operations-with-vcf-9-1/)). 차지백·빌링의 기본 모델은 [VCF Cost and Capacity Management 문서](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-0/cost-and-capacity-management.html)를 참조하세요.

용량이 비용으로 환산되는 주요 입력값입니다.

| 입력값 | 출처 | 쇼백/차지백에서의 역할 |
| --- | --- | --- |
| GPU/vGPU 실사용 시간·사용률 | DCGM, VCF Operations | 사용량 기반 과금의 핵심 단위 |
| 예약된 GPU 슬롯 | GPU Reservation | 예약 점유는 "쓰지 않아도" 비용 귀속 대상 |
| 네임스페이스/프로젝트 쿼터 | VCF Automation 네임스페이스 | 테넌트 경계 = 비용 귀속 경계 |
| VKS 클러스터 비용 | VCF Operations 9.1 VKS 비용 상세 | 쿠버네티스 워크로드의 쇼백/차지백 |
| 유휴·회수 자원 | 리클레임 대시보드 | 절감액 산정·라이트사이징 권고 |

용량 운영에서 중요한 점은 **예약·쿼터 점유도 비용**이라는 사실입니다. 사용률이 낮은 예약분은 "보장의 대가"로 누군가에게 청구되어야 합니다. 그렇지 않으면 테넌트가 무한정 예약만 늘리는 도덕적 해이가 생깁니다. 쇼백으로 "점유 중인 예약분"을 테넌트에게 보여 주기만 해도 자발적 반납이 늘어 가용 용량이 회복됩니다.

과금 공식·단가·TCO 모델의 상세는 [07-tco-cost-model.md](./07-tco-cost-model.md)를 참조하세요. 본 문서는 "용량 지표가 과금의 입력값이 된다"는 연결 고리까지만 다룹니다.

---

## 6.5 PoC → 파일럿 → 프로덕션 용량 로드맵

용량은 처음부터 프로덕션 규모로 잡는 것이 아니라 단계적으로 키웁니다. 각 단계의 목표가 다르므로 용량 산정 기준도 달라집니다.

| 단계 | 기간(예시) | 용량 목표 | 핵심 측정값 | 용량 산정 기준 |
| --- | --- | --- | --- | --- |
| PoC | 약 4주 | 기술 검증 | 단일 모델 사용률·VRAM | 최소 GPU(1–2)로 동작·적합성 확인 |
| 파일럿 | 1–3개월 | 실사용 부하 측정 | 동시 사용자·P95 지연·쿼터 소진 | 실측 부하로 사용자당 자원 단가 도출 |
| 프로덕션 | 상시 | SLO 보장·확장 | 전체 트리거 지표(6.2) | 헤드룸 포함 정원 + 증설 트리거 운영 |

단계별 용량 운영 권고입니다.

- **PoC(약 4주)**: 목표는 "되는지"이지 "얼마나 크게"가 아닙니다. 최소 GPU로 모델 적합성·VRAM 소요를 측정하고, 이 수치를 파일럿 산정의 기준선으로 삼습니다. 4주 PoC 진행은 본 시리즈의 PoC 절차와 연계해 운영합니다.
- **파일럿**: 처음으로 실사용 부하가 들어옵니다. **사용자당·요청당 자원 소요**를 실측해 "사용자 N명 = GPU M개" 같은 환산식을 만듭니다. 이 환산식이 프로덕션 정원 산정의 핵심입니다. 동시에 쿼터 소진·대기 큐를 관찰해 증설 트리거 임계를 보정합니다.
- **프로덕션**: 헤드룸을 포함한 정원으로 출발하고, 6.2의 증설 트리거를 상시 가동합니다. VCF Operations의 용량·비용 인사이트와 라이트사이징·리클레임 권고로 "증설 전 회수"를 우선합니다([VCF 9.1 Operations 블로그](https://blogs.vmware.com/cloud-foundation/2026/05/05/scale-simplify-and-secure-your-private-cloud-operations-with-vcf-9-1/)). 신규 하드웨어는 NVIDIA Blackwell 계열(예: HGX B200) 등 신규 GPU 지원을 고려해 증설 세대를 계획합니다([PAIF with NVIDIA 9.1 가이드](https://techdocs.broadcom.com/content/dam/broadcom/techdocs/us/en/pdf/vmware/private-ai/private-ai-nvidia/vmware-private-ai-foundation-with-nvidia-9-1.pdf)).

점진 확장의 원칙은 "한 단계의 실측값이 다음 단계의 산정 입력이 된다"입니다. 단계를 건너뛰면 프로덕션 정원이 추정에 머물러 과소·과대 산정 위험이 커집니다.

---

## 6.6 검증·실측 방법

용량 계획은 문서가 아니라 측정으로 검증됩니다. 아래 절차로 본 문서의 지표·트리거·로드맵이 실제 환경에서 성립하는지 확인합니다.

1. **지표 수집 파이프라인 검증**: GPU WLD 호스트에서 DCGM(또는 DCGM-Exporter)이 `DCGM_FI_DEV_GPU_UTIL`, `DCGM_FI_DEV_FB_USED/FREE`, `DCGM_FI_PROF_SM_ACTIVE`를 노출하는지 확인합니다. VCF Operations에서 동일 GPU·vGPU 메트릭과 AI 메트릭(TTFT·E2E 지연)이 대시보드에 표시되는지 확인합니다. AI 메트릭 대시보드는 Grafana 배포가 전제입니다([VCF 9.1 AI 워크로드 블로그](https://blogs.vmware.com/cloud-foundation/2026/05/05/streamline-simplify-and-protect-all-your-ai-workloads-with-vcf-9-1/), [DCGM Feature Overview](https://docs.nvidia.com/datacenter/dcgm/latest/user-guide/feature-overview.html)).
2. **부하 시험으로 트리거 검증**: 합성 부하를 점증시키며 평균·P95 사용률, VRAM, 대기 큐, P95 지연이 6.2 임계에서 의도대로 경보를 내는지 확인합니다. 오탐·미탐이 있으면 관측 창·임계를 보정합니다(확정 임계는 조직별 합의 필요).
3. **예약·쿼터 한계 검증**: GPU Reservation을 설정한 워크로드가 자원 압박 상황에서도 시작 자원을 확보하는지, 쿼터 소진 시 신규 요청이 정책대로 거부되는지 확인합니다([PAIF with NVIDIA 9.0.x 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-release-notes/vmware-private-ai-foundation-with-nvidia-90-release-notes.html)).
4. **쇼백·차지백 수치 대사**: VCF Operations에서 테넌트별 GPU 사용량·예약 점유·VKS 비용이 실제 사용량과 일치하는지 표본 대사(reconciliation)합니다([VCF 9.1 Operations 블로그](https://blogs.vmware.com/cloud-foundation/2026/05/05/scale-simplify-and-secure-your-private-cloud-operations-with-vcf-9-1/)).
5. **로드맵 환산식 검증**: 파일럿 실측에서 도출한 "사용자당 자원" 환산식이 프로덕션 초기 부하에서도 오차 범위 내인지 비교하고, 벗어나면 정원·헤드룸을 재산정합니다.

검증 결과는 정량 합격 기준으로 못 박아 운영 회귀의 일부로 둡니다. 예: 핵심 지표 수집 누락 0건, 트리거 오탐률 기준 이내, 차지백 표본 대사 불일치 0건(확정 기준치는 조직별 합의 필요).

---
[← 이전: 05 스토리지·네트워크 용량 사이징](05-storage-network-sizing.md) · [목차](../README.md) · [다음: 07 TCO와 비용 모델 →](07-tco-cost-model.md)

# 04 — VKS 클러스터 사이징과 인프라 고려사항

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.
> 시리즈 인덱스: [vcf-private-ai-series](../../README.md)

이 문서는 02·03에서 산정한 워크로드 요구량(GPU·vCPU·RAM)을 실제 **VKS(vSphere Kubernetes Service)** 클러스터 토폴로지로 환산하는 방법을 다룹니다. VKS는 VCF 위에서 동작하는 프로덕션용 GPU 가속 Kubernetes 서비스로, Supervisor 위에 vSphere 네임스페이스 단위로 클러스터를 프로비저닝하며, GPU는 DRA(Dynamic Resource Allocation) 기반으로 스케줄링됩니다. 본 문서가 다루는 GPU 가속 워크로드 도메인은 공식 용어로 "GPU-Accelerated Workload Domain"(이하 GPU 워크로드 도메인)이라 부릅니다.

용어 풀이가 필요한 약어는 처음 등장할 때 풀어 씁니다. 모든 수치는 릴리스·환경별로 상이할 수 있으므로 도입 전 공식 문서로 재확인하시기 바랍니다.

---

## 4.1 VKS 클러스터 토폴로지 개요

VKS 클러스터 한 개는 크게 두 층으로 구성됩니다.

- **컨트롤 플레인(Control Plane)**: Kubernetes API 서버, etcd, 스케줄러를 호스팅하는 노드. VM으로 프로비저닝됩니다.
- **워커 노드 풀(Worker Node Pool)**: 실제 파드(워크로드)가 실행되는 노드 그룹. 노드 풀별로 VM Class(노드 1대의 vCPU·RAM·GPU 사양 템플릿)와 노드 수를 따로 지정합니다.

컨트롤 플레인 노드 수는 **반드시 홀수(1 또는 3)** 여야 합니다. 프로덕션·HA 환경에서는 **3노드 컨트롤 플레인**이 표준입니다. 컨트롤 플레인은 scale-out(노드 추가)은 지원하나 scale-in(노드 축소)은 지원하지 않으므로, 처음부터 3노드로 설계하는 편이 안전합니다(출처: [Broadcom TechDocs — Manually Scale a Cluster Using Kubectl](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vsphere-supervisor-services-and-standalone-components/latest/managing-vsphere-kuberenetes-service-clusters-and-workloads/operating-tkg-service-clusters/manually-scale-a-cluster-using-kubectl.html)).

VCF 9.1은 native Kubernetes HA의 현대적 표준으로 **3-Zone 배포 모델**(vSphere Zone 3개에 노드를 분산)을 권장합니다. 노드 풀을 vSphere Zone에 걸쳐 분산하면 단일 클러스터의 워커 노드가 물리 장애 도메인 여러 개에 걸치게 되어 진정한 HA를 확보할 수 있습니다(출처: [VCF Blog — Architecting VKS on VCF](https://blogs.vmware.com/cloud-foundation/2026/06/09/architecting-vmware-vsphere-kubernetes-service-on-vcf-top-webinar-and-field-questions-answered/)).

| 구성 요소 | 권장 (프로덕션) | 비고 |
|---|---|---|
| 컨트롤 플레인 노드 | 3 (HA) | scale-in 불가, 초기 3노드 권장 |
| 일반 워커 노드 풀 | 1개 이상 | CPU 기반 워크로드·시스템 애드온용 |
| GPU 워커 노드 풀 | 1개 이상 (분리) | GPU 워크로드 전용, taint로 격리 |
| vSphere Zone | 3 (HA) | Zone당 최소 3호스트(vSAN·HA 정족수) |

각 Zone은 vSAN·HA 정족수 유지를 위해 최소 3호스트가 필요합니다(출처: [VCF Blog — Architecting VKS on VCF](https://blogs.vmware.com/cloud-foundation/2026/06/09/architecting-vmware-vsphere-kubernetes-service-on-vcf-top-webinar-and-field-questions-answered/)).

---

## 4.2 GPU 노드 풀 분리 (가장 중요한 설계 결정)

GPU 워커 노드 풀과 일반 워커 노드 풀은 **반드시 별도 노드 풀로 분리**하는 것을 권장합니다. 이유는 다음과 같습니다.

- **비용 격리**: GPU 노드는 단가가 매우 높습니다. CPU만 쓰는 시스템 파드(모니터링, 로깅, 인그레스 등)가 GPU 노드를 점유하면 GPU가 낭비됩니다.
- **스케줄링 정확성**: GPU 노드에 `taint`를 걸고 GPU 워크로드에만 `toleration`을 부여하면, GPU가 필요 없는 파드는 GPU 노드에 배치되지 않습니다.
- **오토스케일 분리**: GPU 노드 풀과 일반 노드 풀의 오토스케일 정책(min/max)을 독립적으로 운영할 수 있습니다.

VKS 3.5+는 Kubernetes 1.34에서 **DRA(Dynamic Resource Allocation)가 stable로 승격**된 것을 통합했습니다. DRA에서는 관리자가 `DeviceClass`로 GPU 같은 하드웨어 자원을 분류하고, 워크로드는 `ResourceClaim`/`ResourceClaimTemplate`으로 특정 GPU 디바이스를 선언적으로 요청합니다. 단순 개수(count) 기반 요청보다 CEL(Common Expression Language) 기반 세밀한 필터링이 가능해 GPU 활용도가 올라가고, 여러 파드/컨테이너 간 GPU 공유도 지원합니다(출처: [VCF Blog — VKS 3.5 is Now Live](https://blogs.vmware.com/cloud-foundation/2025/10/29/build-deploy-and-scale-with-confidence-vsphere-kubernetes-service-3-5-is-now-live-with-24-month-support/)).

> 약어: DRA = Dynamic Resource Allocation(동적 자원 할당). GPU를 볼륨처럼 선언적으로 청구(claim)하는 Kubernetes 표준 메커니즘입니다.

GPU 노드 풀의 노드 사양(노드당 GPU 수, vCPU, RAM)은 VM Class로 결정됩니다. 자세한 사양 산정은 4.3을 참조하세요.

---

## 4.3 노드 사양 산정: 노드 크기 vs 노드 수

같은 총 GPU 수를 확보하더라도, **소수의 큰 노드(few-large)** 와 **다수의 작은 노드(many-small)** 중 무엇을 택하느냐에 따라 효율·장애 영향·스케일 반응성이 달라집니다.

| 구분 | few-large (노드당 GPU 다수) | many-small (노드당 GPU 소수) |
|---|---|---|
| GPU 통신 | 노드 내 NVLink 등 고대역 활용 유리 | 노드 간 네트워크 경유, 멀티노드 학습 시 불리 |
| 데몬셋 오버헤드 | 노드 수가 적어 오버헤드 총량 작음 | 노드마다 데몬셋 반복, 오버헤드 누적 |
| 장애 영향(blast radius) | 노드 1대 장애 시 GPU 다수 동시 상실 | 장애 영향 분산 |
| 스케일 단위(granularity) | 큰 단위로만 증감 (낭비 가능) | 세밀한 증감 가능 |
| 빈 패킹(bin-packing) | 큰 작업에 유리 | 작은 추론 작업 다수에 유리 |

**일반 지침**: 멀티 GPU 학습(분산 트레이닝)은 노드 내 GPU 다수 + 고속 인터커넥트가 유리하므로 few-large 쪽으로, 단일 GPU 추론(서빙)이 다수라면 활용도·세밀한 스케일을 위해 many-small 쪽으로 기우는 것이 보통입니다. 다만 호스트당 물리 GPU 장착 수와 VM Class에서 패스스루/vGPU로 노출 가능한 GPU 수에 제약이 있으므로, 물리 서버 사양과 함께 결정해야 합니다. 호스트당 GPU 슬롯 수와 VM Class 정의는 환경마다 다르므로 도입 전 실제 환경에서 확인하시기 바랍니다. 고정 GPU 적재·패킹 관점의 역산은 [02 §2.9 고정 GPU 적재·패킹](02-gpu-sizing.md#29-고정-gpu-적재패킹-공급-제약)과 [09 역방향 사이징 시나리오](09-reverse-sizing-scenario.md)를 참조하세요.

### GPU Operator 데몬셋 오버헤드

GPU 노드 풀에는 보통 NVIDIA GPU Operator가 다음 컴포넌트를 **노드마다 데몬셋(DaemonSet)** 으로 배치합니다. 이들이 GPU 노드 1대당 추가 vCPU·RAM을 상시 소비하므로, 노드 가용 자원 산정 시 반드시 헤드룸으로 빼야 합니다.

| 데몬셋 컴포넌트 | 역할 |
|---|---|
| nvidia-driver-daemonset | GPU 드라이버 설치·관리 |
| container-toolkit | 컨테이너 런타임 GPU 연동 |
| device-plugin | GPU 자원 노출 (DRA 환경에서는 DRA 드라이버와 병행/대체) |
| dcgm-exporter | GPU 텔레메트리(메트릭) 수집, 노드당 파드로 동작 |
| gpu-feature-discovery | 노드 라벨링 |

(출처: [NVIDIA GPU Operator Docs](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/troubleshooting.html), [NVIDIA DCGM Exporter Docs](https://docs.nvidia.com/datacenter/cloud-native/gpu-telemetry/latest/dcgm-exporter.html))

> 산정 팁: GPU 노드의 "워크로드 가용 RAM" = 노드 총 RAM − OS·kubelet 예약 − GPU Operator 데몬셋 합계 − 시스템 파드 여유. 실제 예약량은 컴포넌트 버전·설정별로 상이하므로 4.6 실측으로 확정하세요.

---

## 4.4 오토스케일: 헤드룸·버스트·스케일 지연

VKS는 Kubernetes Cluster Autoscaler 구현을 제공하며, 워크로드 수요에 따라 **워커 노드 풀의 노드 수를 자동 증감**합니다. VKS 3.5부터 Cluster Autoscaler가 통합 애드온(add-on) 체계로 관리되어 클러스터 버전 업그레이드 시 함께 자동 갱신됩니다(출처: [VCF Blog — VKS 3.5 is Now Live](https://blogs.vmware.com/cloud-foundation/2025/10/29/build-deploy-and-scale-with-confidence-vsphere-kubernetes-service-3-5-is-now-live-with-24-month-support/)).

핵심 동작과 제약:

- **scale-out / scale-in 모두 지원**하나, 특정 애플리케이션(로컬 스토리지 사용, PodDisruptionBudget 등)이 노드를 붙들면 scale-in이 일어나지 않을 수 있습니다.
- **scale-from-zero / scale-to-zero**(노드 0개에서 시작·축소)는 **VKS 3.3+ 및 VKr 1.31.4+** 에서 지원됩니다.
- **버전 일치 요건**: VKr(vSphere Kubernetes release)의 마이너 버전과 Cluster Autoscaler 패키지의 마이너 버전이 일치해야 합니다.

(출처: [Broadcom TechDocs — About Cluster Autoscaling](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-service-administration-and-development/9-0/managing-vsphere-kuberenetes-service-clusters-and-workloads/autoscaling-tkg-service-clusters/about-cluster-autoscaling.html))

### GPU 노드 오토스케일에서 특히 주의할 점

- **스케일 지연(provisioning time)**: GPU 노드는 신규 VM 부팅 + 드라이버/GPU Operator 데몬셋 기동까지 시간이 걸려, 일반 CPU 노드보다 "준비 완료(Ready)"까지 지연이 큽니다. 추론 트래픽 급증(버스트)에 즉시 대응하려면 **최소 노드 수(min)에 헤드룸을 미리 확보**해 두는 편이 안전합니다.
- **min/max 분리 운영**: GPU 노드 풀과 일반 노드 풀에 서로 다른 min/max를 두어, GPU는 약간의 상시 여유(warm pool 성격)를, 일반 노드는 공격적 scale-to-zero를 적용하는 식의 조합이 가능합니다.
- 노드 풀별 라벨·테인트는 MachineDeployment 어노테이션(`capacity.cluster-autoscaler.kubernetes.io/labels`, `.../taints`)으로 오토스케일러에 전달됩니다.

구체적 노드 풀별 min/max 상한 수치는 공식 문서에 단일 값으로 명시되어 있지 않으므로(환경·릴리스별 상이), 4.6 실측과 함께 도입 전 공식 확인이 필요합니다.

---

## 4.5 스케일 한도와 단일 대형 vs 다중 클러스터 설계

용량 계획에서 가장 중요한 사실은 **Supervisor당 스케일 한도**입니다.

| 한도 항목 | 값 | 출처·단서 |
|---|---|---|
| Supervisor당 VKS 클러스터 수 | 최대 **500** | VCF 9.1 / VKS 3.6 기준, 이전 대비 약 2.5배 상향 |
| Supervisor당 VKS 클러스터 노드 총수 | 최대 **4,000** | VCF 9.1 / VKS 3.6 기준 |
| vSphere Namespace당 vSphere Zone | 최대 3 (최소 1) | HA는 3-Zone 권장 |
| 컨트롤 플레인 노드 | 1 또는 3 (홀수) | scale-in 불가 |

VCF 9.1은 클러스터 수를 약 2.5배 늘려 **Supervisor 한 개당 최대 500 VKS 클러스터, 최대 4,000 VKS 클러스터 노드**를 지원합니다. 수평 확장을 위해 Supervisor를 여러 개 배포하지 않아도 되어 운영 부담이 줄어듭니다(출처: [Broadcom TechDocs — VMware vSphere Kubernetes Service Release Notes](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-service-administration-and-development/9-0/release-notes/vmware-tanzu-kubernetes-grid-service-release-notes.html); [VCF Blog — Deploy Modern Apps Faster with VKS on VCF 9.1](https://blogs.vmware.com/cloud-foundation/2026/05/05/deploy-modern-apps-faster-scale-smarter-and-lower-your-tco-with-vks-on-vcf-9-1/)).

> 위 500/4,000 수치는 VCF 9.1과 함께 출하된 VKS 3.6 릴리스 노트 기준입니다. 한도는 릴리스·환경별로 상이할 수 있으므로 도입 시점의 공식 Configuration Maximums 문서로 반드시 재확인하시기 바랍니다. 본 문서는 §4.2–4.4에서 VKS 3.5+ 기능을, §4.5에서 VKS 3.6 동반 한도를 함께 다루므로 단일 릴리스로 오해하지 마세요.

### 단일 대형 클러스터 vs 다중 클러스터 (용량 관점)

| 판단 기준 | 단일 대형 클러스터 | 다중 클러스터 |
|---|---|---|
| 자원 풀링 효율 | 높음(GPU를 한 풀에서 공유) | 낮음(클러스터마다 여유 분산) |
| 격리(팀·환경·보안) | 약함(네임스페이스 격리에 의존) | 강함(클러스터 경계로 격리) |
| 장애 영향 범위(blast radius) | 큼(컨트롤 플레인 장애 영향 광범위) | 작음 |
| 업그레이드 영향 | 한 번에 큰 영향 | 클러스터별 점진 가능 |
| 한도 소진 | 단일 클러스터 노드 상한에 먼저 도달 | Supervisor 한도(500/4,000) 내 분산 |

용량 관점 권장: GPU 풀 활용도 극대화가 최우선이고 격리 요구가 낮으면 큰 클러스터에 노드 풀을 다수 두는 방향이, 팀·환경·규제 격리가 중요하면 클러스터를 나누고 Supervisor 한도 내에서 다중 클러스터로 가는 방향이 유리합니다. 둘 다 Supervisor당 500 클러스터 / 4,000 노드 한도 안에서 환산해야 합니다.

---

## 4.6 인프라 고려사항과 사이징 워크시트

### 노드 배치 (용량 관점)

- **anti-affinity**: 동일 클러스터의 컨트롤 플레인 3노드, 그리고 GPU 워커 노드는 가급적 서로 다른 호스트·Zone에 분산되도록 배치 정책(Placement Policy)을 적용합니다. DRS/HA가 노드 VM을 호스트에 분산합니다.
- **호스트당 GPU**: 물리 호스트에 장착된 GPU 수와 VM Class가 노출하는 GPU 수가 GPU 노드 밀도를 결정합니다. few-large 전략은 호스트당 GPU가 많아야 성립합니다.
- vSAN 용량·네트워크(대역폭, vNIC, 멀티네트워크) 사이징은 본 문서 범위를 넘으며 [05-storage-network-sizing.md](05-storage-network-sizing.md)에서 다룹니다.
- 전반 아키텍처와 구축 순서는 시리즈 ① [인프라 가이드](../../01-infra/README.md)를 참조하세요.

### 사이징 워크시트 (워크로드 → 노드 풀 → 클러스터)

02·03에서 산정한 워크로드 요구량을 다음 순서로 환산합니다. 아래는 예시 수치이며 실제 값은 환경에 맞게 대입하세요.

| 단계 | 입력 | 산식 / 예시 |
|---|---|---|
| 1. 총 GPU 수요 | 02·03 결과 | 예: 학습 16 GPU + 추론 24 GPU = 40 GPU |
| 2. GPU 노드 사양 결정 | VM Class | 예: 노드당 4 GPU (few-large) |
| 3. GPU 워커 노드 수 | 총 GPU ÷ 노드당 GPU | 40 ÷ 4 = **10 노드** |
| 4. 헤드룸/버스트 | 스케일 지연 대비 | +20% → max 12 노드, min 2 노드 |
| 5. 일반 워커 노드 | 시스템·CPU 워크로드 | 예: 3 노드 (HA) |
| 6. 컨트롤 플레인 | HA | 3 노드 |
| 7. 노드 합계(클러스터당) | 합산 | 3 + 3 + 12 = **18 노드** |
| 8. 클러스터 수 | 격리·한도 반영 | 팀 5개 격리 → 5 클러스터 |
| 9. Supervisor 한도 점검 | 500 / 4,000 | 5 클러스터 × 18 = 90 노드 ≪ 4,000, 5 ≪ 500 → 여유 |

이 워크시트의 4단계 헤드룸과 GPU Operator 데몬셋 오버헤드(4.3)는 반드시 함께 반영해야 GPU 노드가 실제 워크로드를 담을 수 있습니다.

---

## 4.7 검증·실측 방법

설계 수치를 실제 환경에서 검증하는 절차입니다. 모든 수치는 환경·릴리스별로 다르므로 도입 전 실측을 권장합니다.

1. **노드 가용 자원 실측**: `kubectl describe node <gpu-node>` 로 Allocatable vs Capacity 차이(예약량)와 GPU Operator 데몬셋 파드의 requests를 확인해 노드당 실제 워크로드 가용 vCPU·RAM·GPU를 산출합니다.
2. **GPU 노출·DRA 확인**: `kubectl get resourceslices` / `kubectl get deviceclasses` 로 DRA가 GPU를 정상 노출하는지, ResourceClaim이 의도대로 바인딩되는지 점검합니다.
3. **오토스케일 반응 시간 측정**: 부하 생성으로 scale-out을 유발하고, 신규 GPU 노드가 `Ready` 상태가 될 때까지(VM 부팅 + 드라이버/데몬셋 기동 포함) 걸린 시간을 기록해 헤드룸(min) 값을 보정합니다.
4. **스케일 한도 대비 점검**: 현재 Supervisor의 클러스터 수·노드 총수를 집계해 500 / 4,000 한도 대비 소진율을 모니터링합니다.
5. **배치 검증**: 컨트롤 플레인 3노드와 GPU 워커 노드가 anti-affinity·Zone 정책대로 서로 다른 호스트/Zone에 분산되었는지 확인합니다.
6. **공식 문서 재확인**: 위 한도·동작 수치는 [Broadcom TechDocs(VKS/Supervisor)](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vsphere-supervisor-services-and-standalone-components/latest/managing-vsphere-kubernetes-service/running-tkg-service-clusters/tkg-service-components.html)와 해당 릴리스의 Configuration Maximums로 도입 시점에 다시 확인합니다.

스토리지·네트워크 실측은 [05-storage-network-sizing.md](05-storage-network-sizing.md)로 이어집니다.

---
[← 이전: 03 컴퓨트·메모리 사이징](03-compute-memory-sizing.md) · [목차](../README.md) · [다음: 05 스토리지·네트워크 용량 사이징 →](05-storage-network-sizing.md)

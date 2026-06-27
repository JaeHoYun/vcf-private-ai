# 11 — GPU Enablement 핸즈온 (딥다이브 트랙)

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.

> **이 문서는 시리즈 표준보다 깊은 핸즈온/딥다이브 트랙입니다.** 도입 검토·아키텍처 수준에서는 [문서 02 §2.3 GPU 할당 방식](02-architecture.md)과 [문서 07 GPUaaS](07-gpuaas.md)의 개념·결정 설명으로 충분합니다. 이 문서는 PoC·파일럿에서 **GPU를 실제로 물려 보는 엔지니어**를 위한 것입니다. 물리 GPU가 하이퍼바이저에 보이고, VM·컨테이너에 할당되며, PAIS가 소비하기까지의 **수직 경로**와 그 길에서 가장 자주 막히는 지점을 단계로 정리합니다.

> **정확도 주의:** 본 문서의 버전·동작은 작성 시점(2026-06, VCF 9.1 / PAIF 9.1 / PAIS 2.1) 공식 문서와 검증 보고를 근거로 합니다. GPU 드라이버·NVAIE·GPU Operator 버전은 빠르게 변하므로, **구체 버전 숫자는 반드시 §11.2의 공식 매트릭스로 재확인**하고, 본문은 숫자보다 **인터락 규칙**을 따르십시오. "확인 필요"로 표기한 항목은 공개 공식 문서에서 단정하지 못한 부분입니다.

---

## 11.1 이 문서의 위치 — GPU enablement 수직 경로

GPU를 "쓴다"는 것은 한 가지 설정이 아니라 여러 계층을 차례로 통과시키는 일입니다. 한 계층이라도 어긋나면 위 계층에서 GPU가 보이지 않습니다. 전체 경로는 다음과 같습니다.

```
물리 GPU (서버에 장착)
  │  ① 하드웨어/BIOS 전제  (§11.3)
  ▼
ESXi 하이퍼바이저 인식
  │  ② 할당 모드 결정·구성  (§11.4–11.5)
  │     · passthrough(전용)  → VIB 불필요
  │     · vGPU/MIG(공유·격리) → vGPU Manager VIB
  ▼
VM (VKS 워커 노드)
  │  ③ 버전 인터락  (§11.6–11.7)
  │     호스트 VIB ↔ 게스트 드라이버 ↔ GPU Operator
  ▼
쿠버네티스(VKS) — NVIDIA GPU Operator
  │  ④ GPU를 컨테이너에 노출  (§11.8)
  ▼
PAIS Model Runtime — 모델이 GPU 소비  (§11.9)
```

각 단계가 끝날 때 "이 계층에서 GPU가 보이나"를 확인하는 검증 경로는 §11.10에 모았습니다. NVLink/NVSwitch·GPUDirect RDMA 같은 멀티호스트 고속 패브릭은 [문서 02 §2.3의 멀티호스트 RDMA 노트](02-architecture.md)가 다루며, 본 문서 범위 밖입니다.

## 11.2 단일 출처 — 호환성은 매트릭스로, 여기서는 규칙으로

GPU 스택의 버전 호환은 빠르게 변합니다. 그래서 이 문서는 특정 숫자를 기준으로 삼지 않고, **공식 매트릭스를 단일 출처으로 가리키고** 변하지 않는 **인터락 규칙**(§11.6)을 본문에 둡니다. 구성 전 아래를 1차 기준으로 확인하십시오.

- **Broadcom 호환성 가이드(GPU·가속기, AI/ML)** — VCF/ESXi가 어떤 GPU·서버를 지원하는지의 기준: [compatibilityguide.broadcom.com](https://compatibilityguide.broadcom.com/)
- **PAIF 9.1 배포 요구사항** — PAIF가 요구하는 GPU 전제·드라이버: [techdocs — Requirements for Deploying PAIF with NVIDIA](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1/deploying-private-ai-foundation-with-nvidia/requirements-for-deploying-private-ai-foundation-with-nvidia.html)
- **NVIDIA vGPU 제품 지원 매트릭스** — ESXi 버전 ↔ vGPU 소프트웨어 ↔ 지원 GPU: [docs.nvidia.com/vgpu — product-support-matrix](https://docs.nvidia.com/vgpu/latest/product-support-matrix/index.html)
- **NVIDIA AI Enterprise(NVAIE) 버전별 지원 매트릭스** — vGPU Manager ↔ 게스트 드라이버 ↔ GPU Operator 조합: NVAIE 릴리스별 `support-matrix`
- **NVIDIA GPU Operator 플랫폼 지원** — Operator ↔ 쿠버네티스 ↔ 드라이버: [docs.nvidia.com — gpu-operator/platform-support](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/platform-support.html)

## 11.3 0단계 — 하드웨어·BIOS 전제

GPU enablement에서 가장 흔한 1차 실패는 BIOS입니다. 아래 설정이 빠지면 ESXi가 GPU를 아예 인식하지 못하거나, VRAM이 큰 GPU에서 MMIO 충돌로 GPU가 사라집니다. 항목명은 서버 벤더마다 다릅니다.

| BIOS/펌웨어 설정 | 자주 쓰이는 항목명 | 필요한 경로 | 없으면 |
|------------------|--------------------|-------------|--------|
| **VT-d / AMD-Vi (IOMMU)** | Intel VT-d, AMD IOMMU | DirectPath·vGPU 전부 | passthrough 자체 불가, ESXi가 DirectPath 비활성 처리 |
| **Above 4G Decoding** | Memory Mapping Above 4G, 64-Bit Resource Handling | VRAM 큰 GPU 전부 | GPU 미인식 또는 MMIO 주소 충돌([NVIDIA KB 4119](https://nvidia.custhelp.com/app/answers/detail/a_id/4119/)) |
| **SR-IOV 활성화** | SR-IOV Global Enable | vGPU·MIG | vGPU 모드 불가(PAIF 요건에 명시) |
| **Resizable BAR / Large BAR** | Re-Size BAR Support | 고용량 VRAM GPU | BAR1이 작은 기본값으로 제한 |
| **ACS** (Access Control Services) | PCIe ACS | 다중 GPU 개별 passthrough(IOMMU 그룹 분리) | 여러 GPU가 한 IOMMU 그룹에 묶여 개별 할당 불가 |
| **ATS** (Address Translation Services) | PCIe ATS | SR-IOV·RDMA 경로 최적화(GPUDirect 시) | 서버·플랫폼별 지원 상이 — 벤더 문서 확인 |
| **FLR (Function-Level Reset)** | — | 권장(전 경로) | VM 재기동·이동 시 GPU 상태 초기화 불안정 |
| **UEFI 부팅(CSM 비활성)** | UEFI Boot Mode | Large BAR 전제 | Above 4G 옵션이 안 보이거나 VBIOS 미인식 |

VRAM이 큰 GPU(H100 80GB, B200, RTX PRO 6000 등)를 **passthrough**로 여러 장 물릴 때는 VM 측 64-bit MMIO 크기도 키워야 합니다. ESXi 8.x/9.x VM 고급 설정에서 다음을 둡니다(값은 장착 GPU 수·VRAM에 따라 조정, 2의 거듭제곱으로 반올림).

```
pciPassthru.use64bitMMIO = "TRUE"
pciPassthru.64bitMMIOSizeGB = "512"   # 예시 — GPU 수 × VRAM 합을 수용하도록 산정
```

이 설정이 부족하면 고용량 GPU 2장 이상에서 CUDA 초기화 실패(Xid 31 / IOMMU Fault)가 보고됩니다([NVIDIA Developer Forum 사례](https://forums.developer.nvidia.com/t/rtx-pro-6000-blackwell-se-iommu-fault-detected-esxi/358104), 커뮤니티 보고).

## 11.4 1단계 — 하이퍼바이저가 GPU를 인식하게 하기

할당 모드에 따라 호스트 준비가 갈립니다.

### 11.4.1 Passthrough(전용) 경로 — VIB 불필요

물리 GPU 전체를 한 VM에 전용으로 줍니다. **NVIDIA vGPU Manager(VIB)를 설치하지 않으며, 그래서 NVAIE 라이선스도 필요 없습니다.** 게스트 OS가 표준 NVIDIA 데이터센터 드라이버를 직접 씁니다.

1. vSphere Client → 호스트 → 구성 → 하드웨어 → PCI 장치에서 대상 GPU를 passthrough로 전환(필요 시 호스트 재부팅).
2. VM에 PCI 장치(또는 Dynamic/Enhanced DirectPath) 추가.
3. (고용량 VRAM) §11.3의 64-bit MMIO 설정 적용.
4. 게스트 OS에 NVIDIA 데이터센터 드라이버 설치.

### 11.4.2 vGPU·MIG(공유·격리) 경로 — vGPU Manager VIB 필요

물리 GPU를 여러 VM에 나눠 주거나 하드웨어 격리(MIG)를 쓰려면 ESXi에 **NVIDIA vGPU Manager VIB**를 설치합니다. 이 경로는 **NVAIE 라이선스가 필요**합니다.

1. NVIDIA Application Hub에서 ESXi 9.x용 vGPU Manager VIB 내려받기(NVAIE 계정 필요).
2. vSphere Lifecycle Manager(vLCM) 이미지에 컴포넌트로 추가 → 호스트를 유지보수 모드로 전환 후 remediate → 재부팅.
3. 호스트 그래픽 타입을 "Shared"로 설정.
4. (MIG) 호스트에서 MIG 모드 활성화 후 인스턴스 생성(§11.5.3).
5. VM에 vGPU 프로파일 추가, 게스트에 vGPU 게스트 드라이버 설치(VKS에서는 GPU Operator가 대행 — §11.8).

VKS 환경에서는 이 호스트 준비 위에서 GPU Operator가 게스트 측 드라이버·런타임을 자동화합니다([NVIDIA VIB 설치 KB](https://knowledge.broadcom.com/external/article/367541/)).

## 11.5 할당 모드 4종(+세부) 비교와 enablement

| 모드 | 격리/공유 | vMotion | NVAIE | enablement 요점 | 권장 용도 |
|------|-----------|:------:|:------:|-----------------|-----------|
| **레거시 DirectPath I/O** | GPU 전체 전용(고정 주소) | 불가 | 불필요 | PCI passthrough 활성 + 고정 장치 | 단순 전용, 이동 불요 |
| **Dynamic DirectPath I/O** | GPU 전체 전용(런타임 선택) | 불가 | 불필요 | vendor/device ID 풀 지정, DRS·HA는 지원 | 풀 기반 전용 |
| **Enhanced DirectPath I/O** | GPU 전체 전용 | **지원**(§11.5.2 단서) | 불필요 | 신 API, vMotion·HA·DRS·스냅샷·핫애드 | 전용 + 이동성·라이선스 절감 |
| **vGPU(타임슬라이스)** | 시간 분할 공유 | 지원 | 필요 | vGPU VIB + 프로파일, 소프트웨어 분리 | 다수 소규모 추론·개발 |
| **MIG** | 하드웨어 분할 격리 | (경로별 상이) | MIG 직접 passthrough면 불필요 / MIG-backed vGPU면 필요 | MIG 모드+인스턴스 생성 | 강격리 멀티테넌트 |
| **MIG-backed vGPU** | 하드웨어 슬라이스 위 vGPU | 지원(동일 MIG 구성 타깃) | 필요 | MIG 인스턴스 + vGPU 프로파일 | 격리 + 일관 성능 |

정리하면 **이동성(vMotion)이 필요하면 Enhanced DirectPath I/O 또는 vGPU 계열**이고, 레거시·Dynamic DirectPath는 vMotion이 안 됩니다([Broadcom KB 312208](https://knowledge.broadcom.com/external/article/312208/)).

### 11.5.1 NVAIE 라이선스가 갈리는 지점

- **passthrough 계열(레거시/Dynamic/Enhanced DirectPath, MIG를 직접 passthrough)** → vGPU VIB를 설치하지 않으므로 **NVAIE 불필요**.
- **vGPU·MIG-backed vGPU** → vGPU VIB 경유이므로 **NVAIE 필요**.
- 단, 할당 모드와 무관하게 **NVAIE NGC 컨테이너·NIM 마이크로서비스를 쓰면** 그 자체로 NVAIE 라이선스가 필요합니다(passthrough 환경이라도).

### 11.5.2 Enhanced DirectPath I/O와 vMotion — 9.1의 핵심, 그리고 단서

VCF 9.1에서 Enhanced DirectPath I/O는 near-native 성능을 유지하면서 vMotion·HA·DRS·스냅샷·Storage vMotion·핫애드를 지원하도록 설계됐습니다([VCF 블로그 — Why Enhanced DirectPath Wins](https://blogs.vmware.com/cloud-foundation/2026/04/20/why-enhanced-directpath-wins-for-high-performance-apps/), [VCF 9.1 vSphere What's New](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/release-notes/vmware-cloud-foundation-9-1-0-0-release-notes/what-s-new/whats-new-vsphere.html)).

> **확인 필요:** 공식 문서는 "모든 기능이 모든 장치에서 지원되는 것은 아니다"라고 단서를 답니다. Enhanced DirectPath I/O + vMotion이 공식 매트릭스에서 명시 확인된 장치는 일부(Intel Flex/Gaudi, AMD MI 계열 등)이며, **특정 NVIDIA 데이터센터 GPU의 EDPIO+vMotion 지원은 장치별로 [Broadcom 호환성 가이드](https://compatibilityguide.broadcom.com/)에서 확인**하시기 바랍니다. 라이선스 절감(passthrough=NVAIE 불요)은 경로 특성으로 분명하나, vMotion 보장은 장치 단위로 검증하는 것이 안전합니다.

### 11.5.3 MIG 활성화 절차(호스트)

MIG는 Ampere 이상(A100·A30·H100·H200·B200, RTX PRO Blackwell 등)에서만 동작합니다([MIG User Guide — Supported GPUs](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/supported-gpus.html)).

```bash
# 1) MIG 모드 활성화 (Ampere는 활성화 후 호스트/GPU 재부팅 필요)
sudo nvidia-smi -i 0 -mig 1

# 2) 사용 가능한 GPU 인스턴스 프로파일 확인
nvidia-smi mig -lgip

# 3) GPU 인스턴스 생성 (예: 3g.40gb)
sudo nvidia-smi mig -cgi 3g.40gb -C

# 4) 생성 확인
nvidia-smi mig -lgi
```

주의: Ampere는 MIG 모드가 GPU에 영속되지만 Hopper 이상은 재부팅 시 MIG가 비활성화될 수 있어 운영 자동화가 필요합니다. VM당 MIG 프로파일은 1종만 할당됩니다([MIG-Backed vGPU](https://docs.nvidia.com/ai-enterprise/release-8/latest/infra-software/vgpu/features/mig-backed-vgpu.html)).

## 11.6 2단계 — 버전 인터락 규칙 (숫자보다 규칙)

GPU 스택은 호스트 VIB → 게스트 드라이버 → GPU Operator → 컨테이너 드라이버가 한 사슬로 맞아야 합니다. 숫자는 변하니 **규칙**을 기억하십시오.

- **규칙 1 — 게스트 ≤ 호스트.** vGPU 게스트 드라이버는 호스트 vGPU Manager(VIB)와 **같은 메이저 브랜치이거나 최대 한 브랜치까지만 낮아야** 합니다(두 브랜치 이상 낮으면 비지원). 게스트가 호스트보다 최신 브랜치이면 비지원이며, 증상은 "vGPU fails to load"(VM은 뜨나 vGPU 비활성)입니다([NVIDIA vGPU vSphere 릴리스 노트](https://docs.nvidia.com/vgpu/latest/grid-vgpu-release-notes-vmware-vsphere/index.html)).
- **규칙 2 — passthrough는 vGPU 인터락에서 자유.** passthrough 경로는 호스트 VIB가 없으므로 vGPU 브랜치 인터락이 없고, 대신 **GPU 아키텍처 ↔ 데이터센터 드라이버** 호환만 맞추면 됩니다(Blackwell은 580.x 계열부터).
- **규칙 3 — 라이선스 서버(DLS) 선업그레이드.** vGPU 18.0+/NVAIE 6.0+ 환경에서 DLS가 3.3.x 이하이면 라이선스 획득이 실패합니다. **DLS를 3.4+로 먼저 올린 뒤** vGPU를 올립니다([라이선싱 트러블슈팅](https://docs.nvidia.com/vgpu/troubleshooting/latest/licensing.html)).
- **규칙 4 — VKS의 vGPU 모드는 게스트 드라이버 이미지를 별도 빌드.** GPU Operator가 기본 설치하는 데이터센터 드라이버(예: 580.x)와 **호스트 vGPU 브랜치가 다르면** vGPU 모드에서 동작하지 않습니다. vGPU 모드에서는 호스트 vGPU 브랜치에 맞춘 게스트 드라이버 컨테이너 이미지를 빌드해 사설 레지스트리에 올려 Operator가 쓰게 합니다(§11.8.2).
- **규칙 5 — GPU Operator는 플랫폼이 고정한 버전을 따른다.** PAIS 2.1은 GPU Operator를 특정 버전(아래 스냅샷)으로 고정합니다. 임의 상향 전 §11.2 매트릭스로 검증하십시오.

## 11.7 Known-good 스냅샷 (PAIS 2.1, 2026-05 GA 기준)

아래는 **PAIS 2.1 GA 시점에 검증된 조합의 스냅샷**입니다. 시점 고정 참고값이며 기준이 아닙니다 — 적용 전 §11.2 매트릭스로 재확인하십시오.

| 계층 | 검증 조합(스냅샷) | 근거 |
|------|-------------------|------|
| PAIS | 2.1 | PAIS 2.1 릴리스 노트 |
| GPU Operator | 25.10.1 (PAIS 2.1 기본 탑재) | PAIS 릴리스 노트 |
| Container Toolkit | v1.18.2 | Broadcom KB437128 / 릴리스 노트 |
| 게스트 드라이버 | 580.x 계열 | GPU Operator 25.10.1 설치값 |
| VKS | 3.5.0 이상 권장 | PAIS 릴리스 노트 |
| Kubernetes | 1.33 | PAIS 릴리스 노트 |
| 워커 노드 OS | Ubuntu 24.04 | PAIS 릴리스 노트 |
| ESXi vGPU 소프트웨어 | vGPU 20.x (ESXi 9.0+; MIG-backed vGPU·일부 Blackwell GPU는 ESXi 9.0.1.0(9 U1)+ 필수) | NVIDIA vGPU 지원 매트릭스 |

> **확인 필요:** GPU Operator 25.10.x는 NVIDIA 기준 이후 버전(26.x 계열)이 나오며 deprecated 단계로 들어갑니다. PAIS 2.1이 25.10.1을 고정값으로 쓰므로, **상위 Operator로 임의 교체하지 말고** PAIS가 지정·검증한 버전을 따르십시오. VCF 9.1 전용 ESXi 빌드번호와 PAIF 9.1의 전체 지원 GPU 목록은 [Broadcom 호환성 가이드](https://compatibilityguide.broadcom.com/)에서 확인합니다.

## 11.8 3단계 — VKS에서 GPU Operator 구성

VKS(VCF Kubernetes Service)는 9.1에서 DRA(Dynamic Resource Allocation) 기반 GPU 스케줄링과 Kubernetes AI Conformance를 지원합니다([문서 02 §2.3](02-architecture.md)). GPU Operator가 노드의 드라이버·컨테이너 런타임·디바이스 플러그인·(MIG) 매니저를 자동화합니다.

### 11.8.1 MIG 모드 — 전략 선택

```bash
# 모든 GPU를 동일 프로파일로
--set mig.strategy=single
# GPU마다 다른 프로파일 허용
--set mig.strategy=mixed

# 노드에 MIG 프로파일 지정
kubectl label node <node> nvidia.com/mig.config=all-1g.10gb --overwrite
```

### 11.8.2 vGPU 모드 — 게스트 드라이버 이미지(규칙 4)

vGPU 모드에서는 GPU Operator가 드라이버를 직접 설치하지 않고, **호스트 vGPU 브랜치에 맞춘 게스트 드라이버 컨테이너 이미지**를 별도로 빌드·푸시해 참조하게 합니다.

```bash
helm install gpu-operator nvidia/gpu-operator \
  --set driver.repository=<PRIVATE_REGISTRY> \
  --set driver.version=<VGPU_GUEST_DRIVER_VERSION> \
  --set driver.imagePullSecrets=<REGISTRY_SECRET> \
  --set driver.licensingConfig.secretName=licensing-config
```

> VKS 전용 GPU Operator 값은 공개 페이지에 인라인으로 정리돼 있지 않아, **NVIDIA AI Enterprise vSphere 배포 가이드**를 별도 기준으로 따릅니다(확인 필요).

### 11.8.3 CDI — 25.10부터 기본 활성화

GPU Operator 25.10.0부터 **CDI(Container Device Interface)** 가 기본 활성화되어, `runtimeClassName: nvidia` 없이 컨테이너 런타임이 CDI 스펙(`/var/run/cdi/nvidia.yaml`)으로 GPU를 주입합니다([GPU Operator CDI](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/cdi.html)). 이 기본값이 ESXi 위 containerd 환경과 충돌하는 사례가 §11.11.1에서 다루는 대표 함정입니다.

## 11.9 4단계 — PAIS가 GPU를 소비

PAIS Model Runtime Pod가 VKS 워커 노드에 스케줄되어 GPU를 소비합니다. 아래 스택이 모두 맞아야 모델이 GPU를 잡습니다.

```
PAIS Model Runtime Pod  (GPU 리소스 요청)
   └─ NVIDIA GPU Operator (Device Plugin + Container Toolkit)
        └─ containerd (Ubuntu 24.04 워커)
             └─ ESXi 호스트 드라이버(VIB) 또는 passthrough
                  └─ 물리 GPU
```

PAIS의 GPU 전제(드라이버·Operator·vGPU/MIG)는 §11.7 스냅샷을 따르며, 구성 키는 [PAIF 9.1 요구사항 문서](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1/deploying-private-ai-foundation-with-nvidia/requirements-for-deploying-private-ai-foundation-with-nvidia.html)를 따릅니다.

## 11.10 PoC 빠른 검증 경로 — 계층별 "GPU가 보이나"

문제가 생기면 위에서부터가 아니라 **아래 계층부터** 끊어 확인합니다. 각 단계가 통과해야 다음이 의미가 있습니다.

| # | 계층 | 확인 | 통과 기준 |
|---|------|------|-----------|
| 1 | BIOS | VT-d·Above 4G·SR-IOV(vGPU 시) 활성 | 설정 ON |
| 2 | ESXi 호스트 | (vGPU) 호스트 셸 `nvidia-smi`, 그래픽 Shared / (passthrough) PCI 장치 passthrough 상태 | GPU 표시 |
| 3 | VM 게스트 | `nvidia-smi` | GPU·드라이버 표시 |
| 4 | 라이선스(vGPU) | `nvidia-smi -q \| grep -i "License Status"` | `Licensed` |
| 5 | 쿠버네티스 노드 | `kubectl describe node <n> \| grep nvidia.com/gpu` + device plugin Pod | `nvidia.com/gpu` 용량 노출, 플러그인 Running |
| 6 | 컨테이너 주입(CDI) | GPU 요청 Pod 생성 | CDI 오류 없이 Running(§11.11.1) |
| 7 | PAIS | Model Runtime Pod·추론 | Pod Running, 추론 응답 |

## 11.11 자주 막히는 함정 — PoC에서 가장 흔한 두 지점

> **이 절은 PoC 핸즈온 깊이입니다.** 같은 두 증상의 **운영 관점 런북**(증상→진단→조치 요약)은 [문서 10 §10.2](10-operations.md)에 있습니다. 운영 중 빠른 분류는 그쪽을, 실제 ConfigMap·점검표를 들고 PoC에서 막힌 곳을 뚫는 작업은 이 절을 보세요.

### 11.11.1 "CDI device injection failed"

PoC에서 6단계(컨테이너 GPU 주입)가 막히는 대표 증상입니다. PAIS 2.1 + GPU Operator 25.10.1(CDI 기본 활성) + ESXi 위 containerd 조합에서 보고됩니다([Broadcom KB437128](https://knowledge.broadcom.com/external/article/437128/)).

```
failed to create containerd container: CDI device injection failed: unresolvable CDI devices
```

**원인:** GPU Operator 25.10.1의 CDI 기본 활성이 ESXi 위 containerd 환경과 맞지 않아 CDI 스펙이 해석되지 않습니다.

**조치(공식 KB):** GPU Operator를 **CDI 비활성 + Legacy 런타임**으로 돌리도록 Helm 값을 ConfigMap으로 주고, PAISConfiguration에서 이를 참조합니다.

```yaml
# GPU Operator 네임스페이스에 생성
apiVersion: v1
kind: ConfigMap
metadata:
  name: helm-values
data:
  values.yaml: |
    cdi:
      enabled: false            # 핵심: CDI 비활성화
    toolkit:
      version: "v1.18.2"
      env:
        - name: NVIDIA_CONTAINER_RUNTIME_MODE
          value: "legacy"
        - name: CDI_ENABLED
          value: "false"
```

```yaml
# PAISConfiguration에서 위 ConfigMap 참조
spec:
  nvidiaConfig:
    gpuOperatorOverridesRef:
      name: helm-values
```

### 11.11.2 vGPU "Unlicensed"

4단계(라이선스)가 막히는 증상입니다. 원인은 하나가 아니므로 아래를 순서대로 점검합니다([Broadcom — vGPU Unlicensed](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/5-2/private-ai-foundation-5-2/deploying-a-deep-learning-virtual-machine/troubleshooting-deep-learning-vm-deployment/the-nvidia-vgpu-driver-is-shown-as-unlicensed.html), [NVIDIA 라이선싱 트러블슈팅](https://docs.nvidia.com/vgpu/troubleshooting/latest/licensing.html)).

| 점검 | 내용 |
|------|------|
| 토큰 형식·만료 | `client_configuration_token.tok`의 형식·`exp` 만료 확인. 토큰 파일에 CRLF가 섞이면 서명 검증 실패(Windows에서 `cmd` 리다이렉트 주의 — 줄바꿈 없이 기록) |
| 시간 동기화 | VM 시계와 라이선스 서버(NLS) NTP 편차 |
| 네트워크 | 라이선스 서버 443 포트 도달, DNS 해소 |
| 프로파일-라이선스 매칭 | Q 프로파일=vWS, A/B 프로파일=vApps/vPC |
| DLS 버전 | vGPU 18.0+에서 DLS 3.4+ (규칙 3) |

```bash
nvidia-smi -q | grep -i "License Status"
cat /var/log/nvidia-gridd.log     # Linux 라이선스 데몬 로그
```

> "원인은 JWT 형식·만료, 조치는 토큰 검증"은 부분적으로 맞지만 유일한 원인이 아닙니다. 위 표 전체를 순서대로 보십시오.

## 11.12 PAIF 9.1에서 달라진 점 (요약)

이 문서가 다루는 GPU enablement에 직접 영향을 주는 PAIF 9.1 변경 사항입니다(상세·근거는 [문서 00 What's New](00-whats-new.md)).

- **Enhanced DirectPath I/O + 이동성** — 전용 GPU를 NVAIE 없이 쓰면서 vMotion·HA·DRS를 노립니다. 단, 공식 확인 장치는 주로 NIC·특정 가속기 계열이며 **NVIDIA 데이터센터 GPU의 EDPIO+vMotion은 §11.5.2 단서대로 [Broadcom 호환성 가이드](https://compatibilityguide.broadcom.com/)에서 장치별 확인이 필수**입니다.
- **no-NVAIE 경로의 명확화** — passthrough 계열은 vGPU VIB·NVAIE 없이 전용 GPU. 라이선스 비용 설계에 직접 영향(§11.5.1).
- **DRA 기반 GPU 스케줄링·AI Conformance** — VKS가 오픈 표준으로 GPU를 선언·할당, 멀티클러스터·이식성 향상.
- **Blackwell 지원** — HGX B200, RTX PRO 6000/4500 Blackwell 지원(passthrough 확인). vGPU 모드는 ESXi 9.0.1.0+ 요구, 데이터센터 B200의 ESXi vGPU 지원·일부 Blackwell vGPU 알려진 이슈는 **확인 필요**([VCF 9.1 AI 블로그](https://blogs.vmware.com/cloud-foundation/2026/05/05/streamline-simplify-and-protect-all-your-ai-workloads-with-vcf-9-1/), NVIDIA vGPU 매트릭스).

---
[← 이전: 10 Day-2 운영](10-operations.md) · [목차](../README.md) · [다음: A1 FAQ·버전 매트릭스·용어집 →](../appendix/A1-appendix.md)

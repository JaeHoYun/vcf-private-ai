# 02 — 네트워크·테넌트·GPU 격리

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)을 참조하세요.
> 시리즈 인덱스: [시리즈 허브](../../README.md)

이 문서는 사내 Private AI 플랫폼에서 "한 테넌트(계열 법인·사업부)의 워크로드, 네트워크, 데이터, GPU 자원이 다른 테넌트로 새어 나가지 않도록" 만드는 격리 설계를 보안 관점에서 다룹니다. 인프라 구축 절차 자체(파드/도메인 배치, 활성화 순서 등)는 [① 인프라 가이드](../../01-infra/README.md)에 있으므로 중복을 피하고, 여기서는 위협 모델([01-threat-model.md](01-threat-model.md))에서 식별한 횡적 이동(lateral movement)·자원 침범·데이터 누출 위협을 어떻게 통제로 막는지를 심화합니다.

이 문서에서 "강격리(hard isolation)"는 정책 설정 실수만으로는 경계가 무너지지 않고, 하드웨어 또는 네트워크 데이터플레인 수준에서 분리가 강제되는 상태를 가리킵니다.

---

## 2.1 격리 계층 개요

Private AI 워크로드의 격리는 단일 통제가 아니라 여러 계층의 중첩(defense in depth)으로 성립합니다. 각 계층은 독립적으로 동작하며, 한 계층이 잘못 설정되어도 다른 계층이 침범을 차단하도록 설계합니다.

| 계층 | 격리 단위 | 핵심 기술 | 강제 지점 |
|------|-----------|-----------|-----------|
| 멀티테넌트 경계 | 법인/사업부 | NSX Project, VCF Automation 조직·네임스페이스 쿼터 | 관리·정책 평면 |
| 네트워크 (논리) | VPC·세그먼트 | NSX VPC, 서브넷 접근 모드, Transit Gateway | NSX 데이터플레인 |
| 동/서 트래픽 | 워크로드 vNIC | vDefend 분산 방화벽(DFW), 분산 IDS/IPS | ESXi 커널(각 vNIC) |
| 남/북 트래픽 | 경계 게이트웨이 | vDefend Gateway Firewall, URL/Geo-IP 필터링 | T0 Edge / Provider Gateway |
| 컴퓨트 | 네임스페이스·VM 클래스 | VKS 네임스페이스, 쿼터, GPU Reservation | Supervisor / vSphere |
| GPU (하드웨어) | GPU 인스턴스 | NVIDIA MIG, vGPU 프로파일 | GPU 실리콘 |

위 표에서 아래로 갈수록 "정책으로 푸는 격리"에서 "하드웨어로 강제되는 격리"로 이동합니다. 가장 민감한 테넌트 경계일수록 하단 계층(MIG, DFW 데이터플레인)으로 격리를 강제하는 것이 안전합니다.

이 중첩 관계를 그림으로 보면 다음과 같습니다. 바깥 계층일수록 정책(설정)으로 강제되어 설정 실수에 취약하고, 안쪽으로 갈수록 하드웨어가 강제해 무너뜨리기 어렵습니다. 한 계층이 뚫려도 다음 안쪽 계층이 침범을 막는 다층 방어 구조입니다.

```
바깥 = 정책으로 강제(설정 실수에 취약)   ── 안으로 갈수록 ──▶   안쪽 = 하드웨어로 강제(강격리)

┌ 멀티테넌트 경계 — NSX Project · VCF Automation 조직/쿼터
│ ┌ 네트워크(논리) — NSX VPC · 세그먼트 · Transit Gateway
│ │ ┌ 동/서 마이크로세그 — vDefend 분산 방화벽(DFW) · 분산 IDS/IPS (각 vNIC)
│ │ │ ┌ 컴퓨트 — VKS 네임스페이스 · 쿼터 · GPU Reservation
│ │ │ │ ┌ GPU 하드웨어 — NVIDIA MIG · vGPU 프로파일 (GPU 실리콘)
│ │ │ │ │    가장 민감한 테넌트 경계일수록 이 안쪽(하드웨어) 계층에 의존
│ │ │ │ └─────────────────────────────────────────────
│ │ │ └───────────────────────────────────────────────
│ │ └─────────────────────────────────────────────────
│ └───────────────────────────────────────────────────
└─────────────────────────────────────────────────────
   남/북 출입구(스택 외곽): vDefend Gateway Firewall · URL/Geo-IP 필터 (T0 Edge)
```

각 계층의 구체 통제는 이어지는 절에서 다룹니다 — 네트워크(§2.2), 동/서 마이크로세그(§2.3), vDefend 탐지(§2.4), 컴퓨트·GPU(§2.5).

---

## 2.2 네트워크 격리: NSX VPC와 세그먼트

VCF 9.x의 NSX는 두 가지 네트워킹 오브젝트 모델을 제공합니다. 하나는 전통적인 **세그먼트(Segment) 모델**, 다른 하나는 퍼블릭 클라우드형 자기서비스 경험을 제공하는 **VPC(Virtual Private Cloud) 모델**입니다([VCF VPC 블로그](https://blogs.vmware.com/cloud-foundation/2025/07/02/vmware-virtual-private-cloud/)).

- **NSX Project**: NSX에서 테넌트를 정의하는 단위로, 네트워킹·보안 오브젝트를 묶어 멀티테넌시와 관리 권한·쿼터 위임을 가능하게 합니다. 각 Project는 자체 Transit Gateway를 가집니다. 계열 법인 단위 강격리의 1차 경계로 이 Project를 사용합니다.
- **VPC**: vCenter 안에서 사용자가 직접 IP 주소·라우팅·보안 정책을 가진 논리적으로 격리된 네트워크를 정의·관리하는 자기서비스 모델입니다. "VPC 안에 설정한 정책은 그 VPC 안에서만 적용되며 다른 VPC에 영향을 주지 않는다"는 점이 격리의 핵심입니다([VCF VPC 블로그](https://blogs.vmware.com/cloud-foundation/2025/07/02/vmware-virtual-private-cloud/)).

서브넷 접근 모드는 인그레스/이그레스 정책의 출발점입니다.

| 서브넷 모드 | 외부 노출 | 통신 범위 | AI 워크로드 활용 |
|-------------|-----------|-----------|------------------|
| Public | 외부 광고됨, NAT 불필요 | 환경에 직접 도달 | 외부 추론 API 게이트웨이 (신중히) |
| Private-VPC | 비노출 | 해당 VPC 내부만, 외부는 NAT 필요 | 학습 데이터 처리·내부 전용 모델 |
| Private-Transit Gateway | 비노출 | 같은 게이트웨이의 다른 VPC와 라우팅 | 공유 서비스(레지스트리, 로깅) 연동 |

기본값은 가장 닫힌 모드(Private-VPC)로 두고, 외부 노출이 꼭 필요한 추론 엔드포인트만 명시적으로 Public 또는 Gateway Firewall 뒤의 경계로 올리는 것이 원칙입니다([VCF VPC 블로그](https://blogs.vmware.com/cloud-foundation/2025/07/02/vmware-virtual-private-cloud/)).

VCF 9.1에서는 VPC를 물리 패브릭에 직접 연결하거나, Gateway Firewall이 적용된 Centralized Transit Gateway 허브를 통해 트래픽을 검사하도록 선택할 수 있습니다([vDefend 9.1 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-security-load-balancing/vdefend/vdefend-firewall/9-1/release-notes/vmware-vdefend-91-release-notes.html)).

---

## 2.3 마이크로세그멘테이션과 동/서 트래픽 통제

테넌트 경계를 나눠도, 같은 테넌트 안 또는 같은 네트워크 안에서 워크로드끼리 무제한 통신하면 침해된 한 노드가 횡적으로 퍼질 수 있습니다. 이를 막는 것이 **마이크로세그멘테이션**이며, NSX의 **vDefend 분산 방화벽**(Distributed Firewall, DFW)으로 구현합니다.

- DFW는 각 워크로드의 가상 NIC(vNIC) 지점, 즉 ESXi 커널 데이터플레인에서 동작합니다. 정책이 VM을 따라다니므로 VM이 이동·재생성되어도 격리가 유지됩니다([vDefend Distributed Firewall](https://www.vmware.com/products/security/vdefend-distributed-firewall), [VCF VPC 블로그](https://blogs.vmware.com/cloud-foundation/2025/07/02/vmware-virtual-private-cloud/)).
- VPC 모델의 기본 DFW 규칙은 동일 Project 내 워크로드 간 통신(및 DHCP)만 허용하고 그 외 모든 통신은 차단합니다. 또한 VPC 서브넷 전체를 담는 그룹이 자동 생성되어 DFW 규칙에 바로 활용할 수 있습니다([VCF VPC 블로그](https://blogs.vmware.com/cloud-foundation/2025/07/02/vmware-virtual-private-cloud/)).
- DFW는 L7(애플리케이션 계층) 규칙을 지원하며, vDefend 9.1 기준 5,000개 이상의 L7 App ID로 포트 기반 방화벽보다 정밀하게 트래픽을 식별할 수 있습니다([vDefend 9.1 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-security-load-balancing/vdefend/vdefend-firewall/9-1/release-notes/vmware-vdefend-91-release-notes.html)).

AI 워크로드에서 주의할 동/서 트래픽 통제 지점:

- 학습 클러스터 노드 간 통신은 허용하되, 학습 네임스페이스에서 추론 네임스페이스로 향하는 트래픽은 기본 차단합니다.
- 모델·데이터 레지스트리, 시크릿 스토어 같은 공유 서비스는 명시적 허용 그룹으로만 도달하게 합니다.
- 인그레스(외부 → 추론 엔드포인트)와 이그레스(워크로드 → 외부 모델 허브·인터넷)를 분리해 정책화하고, 이그레스는 데이터 유출 방지 관점에서 기본 차단 후 허용 목록 방식으로 운영합니다.

### TLS 암호화

세그먼트 경계와 방화벽만으로는 전송 중 데이터(학습 데이터셋, 모델 가중치, 추론 입출력)의 기밀성이 보장되지 않습니다. 워크로드 간 및 인그레스 트래픽은 TLS로 암호화하고, 인증서·키는 테넌트별로 분리 관리하는 것을 원칙으로 합니다. 평문 통신은 위협 모델에서 데이터 누출 경로로 식별되므로 회귀 점검 대상입니다([01-threat-model.md](01-threat-model.md)). 구체적 키 관리·시크릿 통제는 [03-identity-access.md](03-identity-access.md)에서 다룹니다.

---

## 2.4 위협 탐지·방어: vDefend (Add-on)

NSX 기본 방화벽이 "허용/차단" 정책 경계라면, **vDefend**는 그 위에 위협 탐지·방어 계층을 더합니다. vDefend는 VCF에 추가(Add-on)되는 보안 제품군으로, 라이선스·활성화가 별도임을 전제로 설계합니다.

| 기능 | 위치 | 역할 |
|------|------|------|
| 분산 방화벽(DFW) | 각 워크로드 vNIC (ESXi 커널) | 동/서 마이크로세그멘테이션 |
| 분산 IDS/IPS | 각 워크로드 vNIC | 동/서 트래픽의 침입 탐지·차단 |
| Gateway Firewall | T0 Edge / Provider Gateway | 남/북 트래픽 검사 |

- **분산 IDS/IPS**: 워크로드 단에서 동/서 트래픽을 검사합니다. vDefend 9.1에서 Turbo Mode가 도입되어 9.1 ESXi 호스트의 기본 모드로 더 높은 검사 처리량을 제공합니다. 규칙 액션은 기존 "Detect", "Detect and Prevent"에 더해 특정 트래픽이 검사를 우회하도록 하는 "Exempt"가 추가되어 성능을 최적화할 수 있습니다([vDefend 9.1 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-security-load-balancing/vdefend/vdefend-firewall/9-1/release-notes/vmware-vdefend-91-release-notes.html)).
- **Gateway Firewall**: T0 Edge 및 Provider Gateway에서 남/북 트래픽을 검사하며, 9.1에서 URL 필터링과 Geo-IP 필터링이 추가되었습니다. 외부 모델 허브로 향하는 이그레스를 도메인·지역 기준으로 통제할 때 활용합니다([vDefend 9.1 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-security-load-balancing/vdefend/vdefend-firewall/9-1/release-notes/vmware-vdefend-91-release-notes.html)).
- **멀티테넌트 위임**: Provider 관리자가 vDefend 방화벽 서비스를 조직/테넌트 관리자에게 위임할 수 있어, 각 법인이 자기 영역의 게이트웨이·분산 방화벽을 자기서비스로 통제하면서도 상위 거버넌스 경계는 유지됩니다([vDefend 9.1 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-security-load-balancing/vdefend/vdefend-firewall/9-1/release-notes/vmware-vdefend-91-release-notes.html)).

분산 방식의 보안 함의: 검사 지점이 경계 단일 초크포인트가 아니라 모든 워크로드 vNIC에 분산되므로, 같은 호스트·같은 서브넷 안에서 일어나는 횡적 이동도 탐지·차단할 수 있습니다. 이는 전통적 경계 방화벽이 보지 못하던 사각지대입니다.

---

## 2.5 컴퓨트·GPU 격리

### 네임스페이스와 쿼터

VKS(VCF용 Kubernetes) 환경에서 테넌트는 네임스페이스로 분리되고, 자원 침범은 쿼터로 1차 통제합니다. VM 클래스에 GPU 장치를 구성할 때는 DirectPath I/O를 위한 메모리 예약(memory reservation)이 필요하며, 조직 단위 쿼터는 리전·존(zone) 기준으로 배정됩니다([PAIF 9.1 문서](https://techdocs.broadcom.com/content/dam/broadcom/techdocs/us/en/pdf/vmware/private-ai/private-ai-nvidia/vmware-private-ai-foundation-with-nvidia-9-1.pdf), [vGPU 용량 블로그](https://blogs.vmware.com/cloud-foundation/2025/06/19/viewing-usage-capacity-for-virtual-gpus-in-vmware-cloud-foundation-9-0/)). 쿼터는 "남이 내 GPU를 다 써버리는" 자원 고갈(DoS)형 침범을 막지만, 메모리 내용 격리까지 보장하지는 않습니다. 후자는 아래 MIG가 담당합니다.

VCF 9.1에서는 VKS의 Dynamic Resource Allocation(DRA)을 통한 Kubernetes AI Conformance가 도입되어, 표준화된 방식으로 GPU 자원을 파드에 할당할 수 있습니다([PAIF NVIDIA 9.1 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1.html)).

### GPU 공유 방식과 격리 함의

GPU를 테넌트 간에 공유할 때 어떤 방식을 쓰느냐가 격리 강도를 결정합니다.

| 방식 | 분리 수준 | 메모리/장애 격리 | 보안 위치 |
|------|-----------|------------------|-----------|
| Enhanced DirectPath I/O (Passthrough) | GPU 전체를 단일 VM에 전용 할당 | 완전(공유 없음) | 강 — 공유 자체가 없음 |
| MIG (Multi-Instance GPU) | GPU를 하드웨어 인스턴스로 공간 분할 | 하드웨어 강제 격리 | 강 — 실리콘 수준 |
| vGPU (time-sliced, MIG 미적용) | 시간 분할 공유 | 메모리·장애 격리 없음 | 약 — 동일 신뢰 경계 내만 |
| MIG-backed vGPU | MIG 슬라이스 위 vGPU | 슬라이스 단위 하드웨어 격리 | 강 — MIG 경계 상속 |

- **Enhanced DirectPath I/O**: GPU(또는 vGPU 프로파일 장치)를 VM에 거의 베어메탈 성능으로 전용 할당합니다. 공유가 없으므로 격리 측면에서는 가장 단순·강력하지만 밀도가 낮습니다([PAIF 9.1 문서](https://techdocs.broadcom.com/content/dam/broadcom/techdocs/us/en/pdf/vmware/private-ai/private-ai-nvidia/vmware-private-ai-foundation-with-nvidia-9-1.pdf), [William Lam PAIS 랩](https://williamlam.com/2025/10/ms-a2-vcf-9-0-lab-deploying-model-endpoint-with-directpath-i-o-using-vmware-for-private-ai-services-pais.html)).
- **MIG 하드웨어 격리**: NVIDIA MIG는 GPU 다이 자체를 공간 분할해 최대 7개의 격리된 GPU 인스턴스로 나눕니다. 각 인스턴스는 전용 SM(Streaming Multiprocessor), L2 캐시 뱅크, 메모리 컨트롤러, DRAM 주소 버스를 별도로 할당받아 메모리 시스템 전체에 걸쳐 분리된 경로를 가집니다. 결과적으로 한 테넌트가 다른 테넌트의 GPU 메모리를 읽거나 덮어쓸 수 없고, 한 인스턴스의 장애가 다른 인스턴스에 영향을 주지 않습니다([NVIDIA MIG User Guide](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/latest/), [NVIDIA MIG 기술 브리프](https://www.nvidia.com/content/dam/en-zz/Solutions/design-visualization/solutions/resources/documents1/Technical-Brief-Multi-Instance-GPU-NVIDIA-Virtual-Compute-Server.pdf)).
- **vGPU(time-sliced) vs MIG의 함의**: 시간 분할(time-sliced) vGPU만 사용하는 경우 복제본 간 메모리·장애 격리가 없습니다. 따라서 서로 다른 신뢰 경계(다른 법인 테넌트)를 같은 GPU에 시간 분할만으로 얹는 것은 권장되지 않습니다. 신뢰 경계가 다른 테넌트를 한 물리 GPU에 함께 둘 때는 MIG로 먼저 하드웨어 인스턴스를 나눈 뒤, 필요하면 그 인스턴스 안에서만 시간 분할을 운용하는 MIG-backed 방식을 사용합니다([NVIDIA GPU Operator – Time-Slicing](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/24.9.0/gpu-sharing.html), [NVIDIA MIG-Backed vGPU](https://docs.nvidia.com/ai-enterprise/release-8/latest/infra-software/vgpu/features/mig-backed-vgpu.html)).

원칙: **테넌트 경계 = 신뢰 경계가 다르면 GPU 격리도 하드웨어(MIG 또는 전용 Passthrough)로 강제한다.** 시간 분할 공유는 동일 테넌트 내부의 워크로드끼리만 허용합니다.

### GPU Reservation

GPU Reservation은 특정 워크로드/테넌트에 GPU 용량을 예약해, 다른 테넌트가 가용 GPU를 선점·고갈시키는 것을 방지합니다. 쿼터가 상한이라면 Reservation은 하한(보장)에 해당하며, 둘을 함께 써서 자원 침범과 자원 굶주림(starvation)을 동시에 막습니다([vGPU 용량 블로그](https://blogs.vmware.com/cloud-foundation/2025/06/19/viewing-usage-capacity-for-virtual-gpus-in-vmware-cloud-foundation-9-0/)). 정확한 9.1 예약 동작은 배포 모드별 차이가 있어 구성 시 공식 문서 재확인이 필요합니다(확인 필요).

---

## 2.6 멀티테넌트·계열사 강격리

계열 법인 단위 강격리는 위 계층들을 한 테넌트 경계로 묶어 일관되게 정렬할 때 성립합니다.

| 경계 | 테넌트별 분리 수단 |
|------|--------------------|
| 관리/정책 | VCF Automation 조직, NSX Project, 위임된 vDefend 정책 권한 |
| 네트워크 | 테넌트별 VPC, 기본 차단 DFW, 분리된 인그레스/이그레스 |
| 컴퓨트 | 테넌트별 네임스페이스·쿼터·Reservation |
| GPU | MIG 인스턴스 또는 전용 Passthrough |
| 데이터 | 테넌트별 스토리지 정책·암호화 키([03-identity-access.md](03-identity-access.md)) |

핵심 불변식(invariant): **한 테넌트의 워크로드는 다른 테넌트의 자원·네트워크·데이터에 도달할 수 없다.** VCF Automation에서 조직 관리자는 네임스페이스 단위로 Private AI Services를 활성화·관리하고, 리전 쿼터는 Supervisor 단위로 분리되므로 한 테넌트의 자원 정의가 다른 테넌트로 넘어가지 않습니다([PAIF NVIDIA 9.1 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1.html), [VCF Automation 설정 문서](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/deploying-private-ai-foundation-with-nvidia/setting-up-vcf-automation-for-private-ai-foundation-with-nvidia/set-up-vmware-aria-automation-for-private-ai-foundation-with-nvidia.html)).

이 불변식을 깨는 시도는 모두 회귀 테스트로 고정합니다(다음 절).

---

## 2.7 검증 방법

격리는 "설정했다"가 아니라 "침범이 실제로 실패한다"로 검증합니다. 아래는 테넌트 A에서 테넌트 B로의 침범을 시도해 차단을 확인하는 회귀 케이스입니다. 모든 케이스의 기대 결과는 "차단/거부"이며, 한 건이라도 통과되면 회귀 실패로 간주합니다([01-threat-model.md](01-threat-model.md)의 위협과 1:1 매핑).

| # | 회귀 케이스 | 시도 | 기대 결과 |
|---|-------------|------|-----------|
| R1 | 동/서 횡적 이동 | 테넌트 A VM → 테넌트 B VM IP로 직접 접속 | DFW 기본 차단으로 거부 |
| R2 | 크로스-VPC 도달 | 테넌트 A Private-VPC 서브넷 → 테넌트 B 서브넷 라우팅 | 도달 불가 |
| R3 | 침입 탐지 | 알려진 공격 시그니처 트래픽을 동/서로 주입 | 분산 IDS/IPS가 Detect/Prevent |
| R4 | 무단 이그레스 | 워크로드 → 허용 목록 외 외부 도메인 | Gateway Firewall URL 필터로 차단 |
| R5 | GPU 메모리 침범 | 같은 물리 GPU의 다른 MIG 인스턴스 메모리 접근 시도 | 하드웨어 격리로 불가 |
| R6 | 자원 고갈 | 테넌트 A가 쿼터 초과 GPU/네임스페이스 자원 요청 | 쿼터로 거부, 타 테넌트 Reservation 보존 |
| R7 | 정책 권한 침범 | 테넌트 A 관리자가 테넌트 B의 방화벽/네임스페이스 정책 수정 | 위임 경계로 거부 |
| R8 | 평문 전송 | 테넌트 간/인그레스 트래픽 캡처로 평문 데이터 노출 확인 | TLS로 평문 없음 |

검증 도구·증거 수집 원칙:

- **네트워크(R1–R4)**: NSX 트래픽 흐름 분석과 방화벽 로그로 차단 이벤트를 증거로 남깁니다. 규칙셋 변경은 적용 전후 정책 diff를 보관합니다.
- **GPU(R5–R6)**: `nvidia-smi`로 MIG 구성·인스턴스 경계를 확인하고, 인스턴스 간 메모리 접근 실패 및 쿼터 거부 로그를 증거화합니다([NVIDIA MIG User Guide](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/latest/)).
- **거버넌스(R7–R8)**: 권한 위임 경계 위반 시도의 거부 감사 로그, TLS 핸드셰이크/인증서 검증 결과를 보관합니다.
- **추적성**: 각 회귀 케이스는 위협 모델의 위협 ID와 본 문서의 통제(2.x 절)에 양방향으로 연결되어야 하며, 추적 체인이 끊기면 합격으로 보지 않습니다.

검증 결과는 버전 변경(NSX/vDefend/PAIF 업그레이드) 시마다 재실행하며, 기대 결과가 바뀌는 항목은 공식 릴리스 노트로 근거를 재확인합니다.

---

[← 이전: 01 위협 모델·보안 아키텍처 전경](01-threat-model.md) · [목차](../README.md) · [다음: 03 ID·인증·접근통제 →](03-identity-access.md)

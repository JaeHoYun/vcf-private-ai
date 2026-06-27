# 10 — Day-2 운영

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.

구축([문서 09](09-deployment-scenarios.md))이 끝나면 플랫폼을 **굴리는** 단계가 시작됩니다. Day-2 운영은 "어떻게 깔까"가 아니라 **"깔아둔 것을 어떻게 유지·운영하나"** 입니다. 업그레이드·패치, 장애 대응, 백업·복구, 인증서 관리, 관측·SLO, 네트워크·스토리지 운영, 일상 점검이 여기에 속합니다.

> **이 문서의 경계:** 플랫폼/인프라 Day-2 운영을 다룹니다. 보안 운영(위협·접근통제·공급망·감사)은 [⑤ 보안·거버넌스 가이드](../../05-security/README.md), 용량·비용 운영은 [⑥ 사이징·용량·비용 가이드](../../06-sizing-cost/README.md)로 위임합니다.

> **이 문서가 다루는 것:** **업그레이드(LCM, 수명주기 관리)** · **트러블슈팅** · **백업·복구와 인증서 회전** · **SLO·알람·온콜** · **네트워크·스토리지 Day-2** · **운영자 독자 트랙**. 운영을 처음 맡으셨다면 §10.6 운영자 독자 트랙의 상황별 라우터에서 시작하세요.

> **이 문서를 읽기 전에:** Day-2 운영은 여러 계층(인프라 → Kubernetes → GPU → PAIS)에 걸쳐 폭이 넓습니다. 아래 개념을 알아두면 각 절을 빠르게 따라올 수 있고, 모르는 용어는 '모를 때' 링크부터 펴 보세요.

| 영역 | 알아두면 좋은 것 | 모를 때 |
|------|-----------------|---------|
| LCM·업그레이드 순서 | VCF는 코어→관리서비스→Kubernetes→GPU→PAIS가 서로 의존하므로 **순서대로** 올려야 한다는 개념 | §10.1 · [A1 용어집](../appendix/A1-appendix.md) |
| 백업·복구(RTO/RPO) | "백업이 있다"와 "복구된다"는 다르며, 복구 허용 시간(RTO)·데이터 손실 허용 시점(RPO)을 수치로 약속한다는 개념 | §10.3 · [06 프로덕션](06-production.md) §6.3 · [A1 용어집](../appendix/A1-appendix.md) |
| 인증서·Trust Bundle | 만료된 인증서는 접근 불가·기동 실패를 부르며, PAIS Trust Bundle은 OIDC·Harbor·DSM 인증서 묶음이라는 개념 | §10.3.3 · [02 아키텍처](02-architecture.md) · [A1 용어집](../appendix/A1-appendix.md) |
| SLI/SLO·TTFT | 어떤 지표(SLI)가 어느 값(SLO)을 넘으면 알람·온콜인지 약속한다는 개념. TTFT는 첫 토큰까지의 지연 | §10.4 · [06 프로덕션](06-production.md) §6.8 · [A1 용어집](../appendix/A1-appendix.md) |
| vSAN·NSX 운영 기초 | vSAN Effective Capacity·Adaptive Resync, NSX Edge 건전성 등 이미 깔린 인프라를 운영하는 관점의 기본 용어 | §10.5 · [02 아키텍처](02-architecture.md) · [A1 용어집](../appendix/A1-appendix.md) |
| VCF Operations 알람 | Symptom(증상)+임계치로 Alert를 정의하고 Notification으로 통지하는 알람 프레임워크 | §10.4.2 · [06 프로덕션](06-production.md) §6.8 · [A1 용어집](../appendix/A1-appendix.md) |

> 운영 점검·업그레이드·복구·SLO를 기록하려면 [10 Day-2 운영 워크시트](../worksheet/10-day2-ops-checklist.md)를 함께 쓰세요.

---

## 10.1 플랫폼 업그레이드·패치 (LCM 런북)

업그레이드는 **이미 돌아가는 플랫폼의 라이프사이클 관리**이므로 구축이 아니라 Day-2 운영에 속합니다. [문서 09 §9.3 브라운필드](09-deployment-scenarios.md)에서 "기존 VCF가 9.1 미만이면 먼저 업그레이드"라고 참조한 절차의 본가가 이 절입니다.

PAIF/PAIS는 **여러 계층이 서로 의존**합니다(VCF 코어 → 관리 서비스 → Kubernetes → GPU → PAIS). 그래서 업그레이드는 **순서가 가장 중요**합니다. 순서를 어기면 호환성 오류·기동 실패가 납니다.

### 10.1.1 업그레이드 순서 — 기반(VCF)부터 위로

| 순서 | 계층 | 대상 | 수행 위치 |
|:---:|------|------|-----------|
| 1 | **VCF 코어** | SDDC Manager → NSX → vCenter → ESX → vSAN | SDDC Manager 라이프사이클 관리 |
| 2 | **VCF 관리 서비스** | VCF Operations · Automation · Identity Broker | 9.1에서 플릿(fleet) 라이프사이클로 전환(Operations 업그레이드 시 처리) |
| 3 | **Kubernetes** | Supervisor, VKS(3.5.0+) / VKr(1.32 → 1.33) | Supervisor/VKS 업그레이드 |
| 4 | **GPU 스택** | NVIDIA GPU Operator(24.9.0 → 25.10.1), 드라이버(v580.x) | PAISConfiguration / GPU Operator |
| 5 | **PAIS** | Private AI Services 2.0.x → 2.1 (Supervisor Service) | "Supervisor Service를 새 버전으로 업그레이드" |

> **순서의 핵심:** VCF 코어 자체의 순서는 **SDDC Manager가 가장 먼저**입니다(이후 컴포넌트 업그레이드를 SDDC Manager가 수행). 그 위에서 Kubernetes → GPU → PAIS 순으로 올라갑니다. GPU Operator·드라이버는 PAIS보다 먼저 올려 두어야 ModelRuntime이 정상 기동합니다.

> **적용 전 확인:** VCF 코어 순서(SDDC Manager → NSX → vCenter → ESX → vSAN)와 9.1의 관리 서비스 플릿 라이프사이클 전환은 공식 문서 기준이나, **정확한 버전 경로·세부 단계는 적용 전 반드시 [공식 업그레이드 시퀀스 문서](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/deployment/upgrading-cloud-foundation.html)와 [업그레이드 시퀀스·이슈 KB](https://knowledge.broadcom.com/external/article/440630/upgrade-sequence-and-related-issues-for.html)로 재확인**하시기 바랍니다.

### 10.1.2 사전 점검 (Precheck)

업그레이드 전 다음을 반드시 확인합니다.

```
- SDDC Manager 라이프사이클 관리에서 Precheck 실행 → 오류 0 확인 후 진행
- 하드웨어 호환성 BCG/HCL 재확인 (특히 Blackwell, ConnectX-7/BlueField-3)
- 현재 버전 인벤토리 + 변경 영향 분석 → 문서 00 §0.6 (9.0.x→9.1 체크리스트) 연계
- 업그레이드 전 백업 선행 (VCF 구성, pgvector/DSM, PAIS 설정) → 문서 06 §6.3
- 유지보수 창 공지 (특히 PAIS 단계는 다운타임 동반 — 10.1.3)
```

### 10.1.3 다운타임·영향 — 가장 중요

업그레이드는 무중단이 아닙니다. 특히 **PAIS 단계의 다운타임을 사전 계획**해야 합니다.

| 영향 | 내용 | 대비 |
|------|------|------|
| **PAIS 2.0.x → 2.1** | 모델 엔드포인트를 호스팅하는 **VKS 클러스터를 삭제·재생성** → 노드 재생성·모델 재다운로드 동안 다운타임 | 유지보수 창 + 모델 재다운로드 시간 산정, 사전 모델 캐시 |
| **Model Endpoint 재배포 실패** | 업그레이드 후 메모리 부족으로 재배포 실패 가능(PAIS 2.1 알려진 이슈, [문서 02 §2.9](02-architecture.md)) | 리소스 여유 확보, 업그레이드 후 재배포 검증 |
| **GPU 드라이버 교체** | 드라이버(v580.x) 교체는 테넌트 GPU 워크로드에 영향([문서 07 §7.7](07-gpuaas.md)) | 유지보수 창, MIG 설정 회귀 테스트 |

> ESX 호스트의 보안·버그 패치는 **라이브 패치**(§10.1.4)로 재부팅·VM 이전 없이 적용할 수 있습니다. 위 표의 다운타임은 주로 PAIS·GPU 계층에 해당합니다.

### 10.1.4 라이브 패치 — ESX 무중단 패치 (9.1에서 실용화)

ESX 호스트 패치는 전통적으로 **호스트를 유지보수 모드로 비우고(vMotion) → 재부팅**하는 절차였습니다. **라이브 패치**(ESX Live Patch)는 실행 중인 하이퍼바이저 메모리에 패치를 적용하고 **필요한 sub-process만 재시작**하므로, **호스트 재부팅도 VM 이전도 없이** 보안·버그 패치를 온라인으로 반영합니다. 정기 보안 패치를 다운타임 없이 돌릴 수 있어, 9.1 LCM에서 가장 체감되는 개선입니다.

**동작 방식**

- 대상 호스트는 전체 유지보수 모드가 아니라 **부분 유지보수 모드**(partial maintenance mode)로 들어갑니다 → 기존 VM은 계속 실행되고, 신규 VM 생성·해당 호스트로의 vMotion만 잠시 막힙니다.
- VM은 **비우지 않습니다.** 패치가 VM 실행 런타임(vmx)을 건드릴 때만 VM이 **FSR**(Fast-Suspend-Resume, 빠른 일시정지·재개)를 한 번 거칩니다 — 게스트 재부팅이 아니라 아주 짧은 멈춤이라 사실상 무중단입니다. vmkernel·user-space·NSX 패치는 FSR 없이 적용될 수 있습니다.
- 라이브 패치 대상이 아닌 패치는 **자동으로 "유지보수 모드 + 재부팅"으로 폴백**합니다(또는 enforce 설정으로 비대상 패치를 차단).

**버전 경계 — 왜 "9.1부터"인가**

| 버전 | 라이브 패치 범위 |
|------|------------------|
| vSphere 8.0 U3 | 최초 도입 — vmx(VM 실행 컴포넌트) 패치만 대상 |
| VCF 9.0 | vmkernel·user-space 데몬·NSX 컴포넌트까지 확장, vGPU VM의 FSR 가속(AI/ML 워크로드 무중단) |
| **VCF 9.1** | **TPM 활성 호스트 지원 + 클러스터 기본 활성**, vSAN·코어 스토리지 데몬까지 확장. 벤더 기준 **ESX 패치의 최대 80**%가 라이브 패치 대상 |

9.0까지는 **TPM 2.0이 켜진 호스트에서는 라이브 패치를 쓸 수 없는** 한계가 있었습니다. 요즘 서버 대부분이 TPM을 켜고 출하되어 실무 적용이 막히곤 했는데, **9.1에서 TPM 지원이 추가되고 클러스터 기본 활성으로 바뀌면서** 현장 대다수 하드웨어에서 쓸 수 있는 기능이 되었습니다. 보안 패치 적용 압박이 큰 AI 인프라일수록 효과가 큽니다.

**전제조건**

- vLCM **이미지로 관리되는 클러스터**, **DRS 완전 자동화** 모드, 적용 패치와 호환되는 현재 빌드(각 라이브 패치는 호환 가능한 직전 빌드를 명시).

**범위·한계**

- **ESX 호스트 패치 계층 한정**입니다. PAIS 2.0.x → 2.1처럼 **VKS 재생성·모델 재다운로드가 따르는 단계의 다운타임(§10.1.3)은 라이브 패치로 줄지 않습니다.**
- **모든 패치가 대상은 아닙니다.** 커널의 대규모 변경 등은 폴백 경로(재부팅)를 탑니다 — 그래서 "최대 80%"이지 100%가 아닙니다.
- 9.0까지 제약이던 **DPU(분산 서비스 엔진)·병렬 리메디에이션(parallel remediation) 동시 사용**의 9.1 해소 여부는 적용 전 확인이 필요합니다.

> **적용 전 확인:** TPM 지원·기본 활성·범위 확장은 9.1 공식 발표 기준입니다. 라이브 패치 적용 가능 여부는 **패치별로 다르므로**, 전제조건·잔존 제약과 함께 적용 전 공식 문서로 재확인하시기 바랍니다 ([VCF 9.1 vSphere 신기능 블로그](https://blogs.vmware.com/cloud-foundation/2026/05/12/whats-new-with-vsphere-9-1/), [Live patch 확장 — VCF 9.0 블로그](https://blogs.vmware.com/cloud-foundation/2025/07/15/live-patch-gets-even-better-in-vsphere-with-vmware-cloud-foundation-9-0/), [라이브 패치 요건 KB](https://knowledge.broadcom.com/external/article/419942/requirements-for-enabling-the-vsphere-li.html)).

### 10.1.5 롤백

컴포넌트별 롤백 가능 범위가 다르므로, **업그레이드 전 백업·스냅샷이 사실상의 롤백 수단**입니다.

- 모델 아티팩트는 Harbor 태그로, PAIS 설정은 GitOps로 보존하면 재구성 경로가 확보됩니다([문서 06 §6.3](06-production.md)).
- 직전 안정 버전 아티팩트를 항상 보존합니다.
- 부수효과가 큰 PROD 업그레이드·롤백은 변경관리 절차와 연동하는 것을 권장합니다.

### 10.1.6 업그레이드 후 검증

```
- 코어 헬스: SDDC Manager·vCenter·NSX 정상, Supervisor READY=True
- PAIS: Model Endpoint 재가동, 추론 200 OK, 임베딩 동작, LLM 트레이스 수신 확인(2.1 트레이스 이슈 점검)
- GPU: 드라이버 버전·MIG 설정 확인, GPU 메트릭 대시보드 정상
- 배포 후 검증 체크리스트 재사용 → 문서 06 §6.11
```

### 10.1.7 인접 영역 위임

- 보안 패치 정책·CVE 대응 → [⑤ 보안·거버넌스 가이드](../../05-security/README.md)
- 업그레이드에 따른 용량 변동·재산정 → [⑥ 사이징·용량·비용 가이드](../../06-sizing-cost/README.md)
- 9.0.x → 9.1 한눈 변경 체크리스트 → [문서 00](00-whats-new.md) §0.6

### 10.1.8 에어갭 아티팩트 미러링 런북 (Artifact Mirroring Tool 실행)

에어갭(폐쇄망) 환경에 PAIS 아티팩트를 반입하는 일은 **이미 깔린 플랫폼을 갱신·운영**하는 Day-2 작업입니다. 미러 갱신을 재실행하는 주기가 LCM 리듬에 묶이므로 LCM 런북 바로 옆에 둡니다. **아키텍처·설계(왜 필요·구성도·출처 레지스트리·용량/무결성 경계)는 [문서 06 §6.9](06-production.md)** 에서 다루며, 이 절은 그 위에서 **실제로 끌어오고 반입하고 적재하는 실행 절차**입니다.

Artifact Mirroring Tool은 **PAIS Services 패키지와 NVIDIA GPU Operator 구성요소를 내부 Harbor 프로젝트(OCI 레지스트리)로 미러링**합니다. 출처 레지스트리 표는 [문서 06 §6.9](06-production.md)를 참조하세요.

> **명령 레퍼런스 표기 주의:** 공식 [VCF CLI 명령 레퍼런스](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-consumption/latest/consumer-interfaces-in-vcf/installing-and-using-vcf-cli-v9/command-reference2/pais2.html)에는 `vcf pais models` 하위 명령만 문서화되어 있고, 아래 `vcf pais amt` 하위 명령은 [Disconnected Environment 절차 페이지](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/deploying-private-ai-foundation-with-nvidia/installing-and-configuring-private-ai-services/upload-the-private-ai-services-components-to-a-disconnected-environment.html) 기준입니다.

**선행조건** ([같은 출처](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/deploying-private-ai-foundation-with-nvidia/installing-and-configuring-private-ai-services/upload-the-private-ai-services-components-to-a-disconnected-environment.html)):

1. PAIS용 **Harbor 프로젝트 사전 생성** — 플랫폼 Harbor 프로젝트는 PAIS 아티팩트용으로 **20GB**가 필요합니다(모델 갤러리/NIM 이미지는 별도 산정).
2. **로컬 Ubuntu 패키지 저장소** 미러 + 인덱스 파일.
3. `pais` 플러그인이 포함된 **VCF Consumption CLI**.
4. bastion/admin 호스트에 **Docker 설치**.

**절차 단계:**

| 단계 | 위치 | 작업 |
|------|------|------|
| 1 | 미러 호스트 | 출처 레지스트리 인증(`docker login`) |
| 2 | 미러 호스트 | `vcf pais amt pull`로 아티팩트 끌어오기 |
| 3 | 미러 호스트 | 산출물(`pais-store` 등)을 에어갭으로 오프라인 반입 |
| 4 | 내부망 | 내부 Harbor 인증(`docker login`) |
| 5 | 내부망 | `vcf pais amt push`로 내부 Harbor 적재 |
| 6 | 내부망 | 모델 갤러리 push/pull(`vcf pais models`) |
| 7 | 내부망 | Supervisor에 PAIS 설치(`pais.yml` + `yaml-svc-cfg.yaml`) |

먼저 인터넷 연결 미러 호스트에서 출처 레지스트리에 인증한 뒤 아티팩트를 끌어옵니다. `vcf pais amt pull`은 `pais-store` 디렉터리를 생성하고, 설치 파일 `pais.yml`과 `yaml-svc-cfg.yaml`의 갱신본을 함께 생성합니다.

```bash
# 1) 출처 레지스트리 인증 (pull 전)
docker login pais-docker.packages.broadcom.com
docker login nvcr.io/nvidia/vgpu

# 2) 아티팩트 pull → pais-store 디렉터리 + pais.yml·yaml-svc-cfg.yaml 갱신 생성
vcf pais amt pull <path-to-pais-yaml>
# 예: vcf pais amt pull ./pais.yml
```

산출물을 에어갭 내부망으로 반입한 뒤, 내부 Harbor에 인증하고 적재합니다. Ubuntu 저장소 목록은 `--ubuntu-repo-list` 인자로 전달합니다.

```bash
# 3) 내부 Harbor 인증 (push 전)
docker login <harbor_fqdn>

# 4) 내부 Harbor로 push
vcf pais amt push <harbor_fqdn>/<project> \
  --ubuntu-repo-list "$(cat <repo-list-path>/custom-repo.list)"
```

모델 갤러리(모델 가중치 아티팩트)는 Artifact Mirroring Tool과 별개로 `vcf pais models` 명령으로 적재·조회합니다 ([VCF CLI 명령 레퍼런스](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-consumption/latest/consumer-interfaces-in-vcf/installing-and-using-vcf-cli-v9/command-reference2/pais2.html)).

```bash
# 모델 갤러리 push / pull / list
vcf pais models pull|push|list --modelStore <harbor>/<project>
```

마지막으로 Supervisor에 PAIS를 설치합니다. pull 단계에서 갱신된 `pais.yml`을 업로드하고, `yaml-svc-cfg.yaml`의 내용을 설치 워크플로우에 붙여넣습니다 ([Install Private AI Services on the Supervisor](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/deploying-private-ai-foundation-with-nvidia/installing-and-configuring-private-ai-services/install-private-ai-services-on-the-supervisor.html)).

> **무결성 점검은 별도 단계입니다:** Artifact Mirroring Tool이 서명·매니페스트·다이제스트를 자동 검증한다는 공식 근거는 확인되지 않았습니다. 반입 아티팩트의 무결성·공급망 점검은 **운영자가 수행하는 별도 절차**로 보고, [문서 06 §6.9.2](06-production.md)의 보안 가이드 딥링크를 따르세요.

> **미러 갱신:** 새 BOM(Bill of Materials)이나 갱신된 `pais.yml`을 기준으로 위 `pull` → 반입 → `push` 경로를 재실행합니다. 갱신 주기·갱신·운영 항목과 인접 가이드 딥링크는 [문서 06 §6.9.2](06-production.md)에 정리돼 있습니다.

---

## 10.2 트러블슈팅 런북 (증상 → 진단 → 조치)

장애 대응은 Day-2에서 가장 자주 펴보는 부분입니다. [문서 02 §2.9 알려진 이슈](02-architecture.md)를 **운영자 관점의 증상 → 진단 → 조치**로 재구성했습니다. 알려진 이슈의 Workaround는 버전에 따라 바뀌므로 적용 전 공식 릴리스 노트로 최신 내용을 재확인하세요.

> **이 절은 운영 런북입니다(증상→진단→조치).** GPU 주입 실패(`CDI device injection failed`)의 ConfigMap 우회나 vGPU Unlicensed 점검표 같은 **핸즈온 깊은 수정·PoC 단계 절차**는 [문서 11 §11.11](11-gpu-enablement.md)을 보세요.

### 10.2.1 진단 기본 흐름

증상 식별 → **계층 좁히기**(인프라 / Kubernetes / PAIS / 앱) → 로그·이벤트 확인 → 알려진 이슈 대조 → 조치·검증.

| 계층 | 1차 확인 |
|------|----------|
| Supervisor / PAIS | `kubectl get paisconfiguration`(READY=True), `kubectl get pods` + Pod 이벤트 |
| GPU | GPU Operator Pod 상태, 드라이버·MIG 설정, GPU 메트릭 대시보드([문서 06 §6.8](06-production.md)) |
| 모델 | Model Endpoint·Replica 상태, ML API Gateway 응답 |
| 관측성 | OTel Collector 트레이스 수신 여부 |

### 10.2.2 GPU · ModelRuntime

| 증상 | 가능 원인 | 조치 |
|------|----------|------|
| ModelRuntime GPU Pod 시작 실패 (`CDI device injection failed`) | PAIS 2.1 + GPU Operator 25.10.1 알려진 이슈 | GPU Operator Helm 차트 값을 커스터마이즈해 **CDI(Container Device Interface) 비활성화** (공식 Workaround) |
| vGPU 드라이버가 Unlicensed로 표시 | 라이선스 무효·만료·형식 오류 | 라이선스가 JWT 형식인지 검증(jwt.io로 디코드해 만료·node server URL 확인) 후 재적용 |
| GPU Pod 스케줄 실패 | vGPU 호스트 드라이버·SR-IOV 미구성, GPU 쿼터 소진 | 각 ESX의 SR-IOV(BIOS)·vGPU 드라이버 확인, 네임스페이스 `nvidia.com/gpu` 쿼터 확인 |

### 10.2.3 모델 엔드포인트

| 증상 | 가능 원인 | 조치 |
|------|----------|------|
| 업그레이드 후 Endpoint 재배포 실패 | 메모리 부족 (PAIS 2.1 알려진 이슈) | 리소스 여유 확보 후 재배포, 적정 모델·양자화 검토 |
| 첫 응답이 느림 (Cold Start) | 새 Replica의 모델 로딩 지연 | Min Replicas ≥ 1, 워밍업 요청, 이미지 사전 Pull ([문서 06 §6.5](06-production.md)) |
| 간헐 오류·일부 Replica 장애 | GPU/Pod 장애 | Health Check가 자동 제외·교체([문서 06 §6.2](06-production.md)), GPU 메트릭 점검 |

### 10.2.4 관측성 · 트레이싱

| 증상 | 가능 원인 | 조치 |
|------|----------|------|
| LLM 트레이스 미표시 | OTel Collector 수신 문제 (PAIS 2.1 알려진 이슈) | 트레이스 수신 검증, 릴리스 노트 Workaround 확인 ([문서 06 §6.8](06-production.md)) |

### 10.2.5 DLVM · 드라이버 (9.0.x 보고 — 재확인 필요)

| 증상 | 가능 원인 | 조치 |
|------|----------|------|
| vGPU 드라이버 다운로드 실패 (인증서 오류) | HTTPS 프록시 | cloud-init `noProxy` 설정 |
| Clone한 DLVM의 IP 충돌 | 원본 VM의 IP 상속 | Clone 전 netplan에서 MAC 주소 라인 제거 |

> GPU Operator가 25.10.1(드라이버 v580.x)로 상향됐으므로, 위 9.0.x Workaround는 적용 전 **재검증**하세요.

> **적용 전 확인:** 위 Workaround는 공식 릴리스 노트·문서 기준이며 버전별로 해결·변경될 수 있습니다. 적용 전 [PAIS 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-release-notes/vmware-private-ai-services-release-notes.html)로 재확인하시기 바랍니다.

---

## 10.3 백업·복구와 인증서·시크릿 회전

구축 후 상시 돌아가야 하는 두 위생 작업입니다. (1) 플랫폼 구성·데이터의 백업과 **복구 가능성** 보장, (2) 인증서·시크릿의 정기 회전. 둘 다 "필요할 때 안 되면 치명적"이라 평소에 손봐야 합니다.

### 10.3.1 백업 대상 — 플랫폼 구성까지 확장

[문서 06 §6.3](06-production.md)이 AI 자산(모델·벡터·PAIS 설정·앱 데이터) 백업을 다룹니다. 운영자는 여기에 **플랫폼 구성 백업**을 더해야 전체 복구가 가능합니다.

| 분류 | 대상 | 방법 |
|------|------|------|
| 플랫폼 구성 | SDDC Manager · vCenter · NSX Manager | **파일 기반 백업**(상태를 파일로 export → 운영 도메인과 다른 위치 저장). NSX는 기본적으로 SDDC Manager VM에 1시간 주기 백업되며 **외부 SFTP 서버 권장** |
| AI 자산 | 모델(Harbor) · 벡터(pgvector/DSM) · PAIS 설정(GitOps) · 앱 데이터 | [문서 06 §6.3](06-production.md) |

> **보안 주의:** VCF 백업 파일에는 **평문 비밀번호 등 민감정보**가 포함됩니다. 접근을 통제하고, 복구용으로 복호화한 파일은 작업 후 안전 삭제하세요(거버넌스 → [⑤ 보안·거버넌스 가이드](../../05-security/README.md)).

### 10.3.2 복구 훈련 — "백업"이 아니라 "복구"를 검증

백업이 있다고 복구되는 것은 아닙니다. 정기 훈련으로 **복구 가능성**을 검증합니다.

복구 절차 골격(파일 기반):

- **SDDC Manager**: 새 어플라이언스를 OVA로 배포 → 파일 기반 백업 복원
- **vCenter**: 파일 기반 백업에서 복원 → **복원 후 SDDC Manager 상태 검증**
- 복원에 필요한 **자격증명을 사전 확보**해 별도 안전 보관
- VCF 인스턴스 단위 복구 계획(Recovery Plan) 수립

```
- 분기/반기 복구 훈련 수행(최소 비프로덕션)
- 복원 후 헬스·일관성 검증(§10.1.6 검증 재사용)
- RTO/RPO 실측값 측정 → 문서 06 §6.3 DR 패턴과 대조
- 백업 자격증명·암호화 키의 별도 안전 보관 확인
```

### 10.3.3 인증서·시크릿 회전

만료된 인증서는 UI 접근 불가·기동 실패로 이어집니다. VCF 9는 자동 갱신을 제공하나, 수동 교체 경로도 알아야 합니다.

**VCF 9 인증서 — 자동 갱신 우선:**

- VCF 9의 **Fleet Management 어플라이언스가 관리 컴포넌트의 CA 역할**을 하여 만료 전 자동 갱신합니다. Microsoft CA로 발급한 인증서도 자동 갱신 대상입니다.
- 관리 컴포넌트는 **Microsoft CA만** 지원하고, 인스턴스 컴포넌트는 Microsoft CA 또는 OpenSSL을 지원합니다.
- **수동 교체가 필요한 때**: 인증서 만료/임박, 또는 발급 CA가 인증서를 폐기한 경우.

**PAIS Trust Bundle · 시크릿:**

- PAIS **Trust Bundle = OIDC · Harbor · DSM 인증서**([문서 02 §2.3](02-architecture.md) Phase 3). 이들 인증서 갱신 시 Trust Bundle을 재구성합니다.
- 시크릿 = Harbor 레지스트리 자격증명, OIDC 클라이언트 시크릿, 서비스 계정 토큰([문서 06 §6.10](06-production.md)) → 정기 회전.

> **적용 전 확인:** VCF 9의 자동 인증서 갱신(Fleet Management CA)·파일 기반 백업·복구 절차는 공식 문서 기준이나, 정확한 단계와 9.1 차이는 적용 전 [백업·복구 문서](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-0/fleet-management/backup-and-restore-of-cloud-foundation/file-based-backups-for-sddc-manager-and-vcenter-server.html)·[인증서 자동 갱신(VCF 블로그)](https://blogs.vmware.com/cloud-foundation/2025/06/19/automatic-certificate-renewal-in-vcf-9/)로 재확인하시기 바랍니다.

---

## 10.4 SLO · 알람 · 온콜

[문서 06 §6.8 관측성](06-production.md)은 "무엇을 볼 수 있나"(대시보드)를 다룹니다. 운영 단계에서는 **"어떤 값이 나쁘면 누가 언제 깨어나나"** 를 별도로 정해야 합니다. 즉 SLI/SLO 정의 → 알람 임계치 → 온콜·에스컬레이션입니다. ([문서 06 §6.11](06-production.md) 배포 체크리스트의 "알림 규칙·On-call"을 운영 절차로 구체화한 것입니다.)

### 10.4.1 SLI/SLO — 무엇을 약속하나

PAIS가 노출하는 AI 지표에서 SLI(서비스 수준 지표)를 고릅니다(지표 자체는 [문서 06 §6.8](06-production.md)).

| SLI | 지표(예) | SLO 예시(환경별 조정) |
|-----|---------|----------------------|
| 가용성 | Endpoint 요청 성공률(2xx) | 99.x% |
| 지연 | Time to First Token(TTFT), E2E P95 지연 | TTFT·P95 목표 이내 |
| 오류율 | Endpoint 오류율 | 0.x% 미만 |
| GPU 건전성 | GPU 사용률·메모리 압력 | 임계 초과 시간 비율 |

> SLO 수치는 워크로드·모델·하드웨어에 좌우되므로 **기준선(baseline)을 실측해 설정**합니다([문서 06 §6.6](06-production.md) 사이징·§6.8 관측 연계). 위 값은 형식 예시이며 실제 목표값이 아닙니다.

### 10.4.2 알람 — VCF Operations 알람 정의

VCF Operations의 **Alert Definition(Symptom + 임계치) · Notification**으로 알람을 구성합니다. AI·GPU 지표가 나머지 인프라와 같은 콘솔에 있어 통합 알람이 가능합니다.

- **증상(Symptom)**: 지표가 임계치를 넘는 조건 정의(예: P95 지연 초과, 오류율 급증, GPU 메모리 압력 지속, Endpoint 다운).
- **알람(Alert)**: 증상 조합 + 심각도(Critical/Warning).
- **알림(Notification)**: 이메일·웹훅 등으로 통지.
- 9.1은 신규 알람(예: vCenter High Session Count·Increased request load)과 전체 헬스 대시보드를 제공합니다.

알람 설계 원칙(노이즈 방지):

```
- 증상 기반으로(원인에 가깝게), 단일 임계치 남발 금지
- 심각도 분리: 즉시 깨울 것(Critical) vs 업무시간 처리(Warning)
- 알람마다 대응 런북 링크(→ §10.2 트러블슈팅)
- 자동 액션은 신중히(오탐 시 영향 큰 작업은 제외)
```

### 10.4.3 온콜 · 에스컬레이션

- **심각도별 대응 시간**(예: Critical 즉시, Warning 익일 업무시간)을 정의합니다.
- **1차 대응 = 트러블슈팅 런북(§10.2)** 으로 증상 → 진단 → 조치. 미해결 시 에스컬레이션합니다.
- **에스컬레이션 경로**: 1차(운영자) → 2차(플랫폼팀) → 벤더 지원(Broadcom). 보안 사고는 [⑤ 보안·거버넌스 가이드](../../05-security/README.md) 절차로 분기.
- **사후**: 인시던트 기록·포스트모템, 반복 이슈는 알람·런북에 반영(피드백 루프).

> **적용 전 확인:** VCF Operations의 Alert/Symptom/Notification 프레임워크와 9.1 AI·GPU 지표(TTFT·토큰 처리량·GPU 사용률)는 공식 문서 기준이나, 정확한 알람 정의·지표 명칭은 적용 전 [알람 정의 모범사례 문서](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-0/infrastructure-operations/configuring-alerts-and-actions/defining-alerts-best-practices.html)로 확인하시기 바랍니다.

---

## 10.5 네트워크·스토리지 Day-2 운영

플랫폼을 굴리다 보면 **네트워크와 스토리지**가 AI 워크로드의 체감 성능·안정성을 좌우합니다. 모델 로딩은 스토리지 처리량에, 추론 응답·분산 학습은 네트워크에 민감합니다. **구성·설계는 [문서 02](02-architecture.md)·[문서 09](09-deployment-scenarios.md)에서, 용량 산정은 [⑥ 사이징·용량·비용 가이드](../../06-sizing-cost/README.md)에서** 다뤘으므로, 이 절은 **이미 깔린 네트워크·스토리지를 운영(건전성·성능·용량 추세·장애 대응)** 하는 데 집중합니다.

> **이 절의 경계:** 구성·설계 → [문서 02](02-architecture.md)·[문서 09](09-deployment-scenarios.md) / 용량·사이징 → [⑥ 가이드](../../06-sizing-cost/README.md)(벡터 DB는 [② 데이터 가이드](../../02-vectordb/README.md)) / 보안 네트워크(마이크로세그멘테이션·접근통제·감사) → [⑤ 보안·거버넌스 가이드](../../05-security/README.md) / 백업 타깃 → §10.3. 여기서는 **Day-2 운영 점검**만 다룹니다.

### 10.5.1 네트워크 Day-2

PAIF 네트워크는 **NSX(Edge·VPC·세그먼트)** + **모델 엔드포인트 앞단 로드밸런서** + (분산 워크로드에 한해) **GPU 패브릭**으로 이뤄집니다. 운영 관점에서 다음을 점검합니다.

| 운영 영역 | 무엇을 보나 | 조치·연계 |
|----------|------------|-----------|
| NSX Edge·Transport Node 건전성 | VCF Operations가 Edge 메트릭을 20초 주기로 수집 — VTEP 상태, DataPath IPC Thread, Edge Agent 상태 등 | 임계 초과 시 알람(§10.4), 장애 시 §10.2 |
| 모델 엔드포인트 로드밸런서(NSX Edge/ALB) | TLS 종단·백엔드 헬스·세션, 인증서 만료 임박 | 인증서 회전 → §10.3.3, 알람 → §10.4 |
| East-West 정책(Network Policy) | replica ↔ pgvector ↔ PAIS 통신, 정책 변경에 따른 단절 | 통신 장애는 §10.2, 마이크로세그·보안 정책 운영은 ⑤ |
| GPU 분산 패브릭(GPUDirect RDMA·RoCE) — 해당 시 | 링크 상태·대역폭·드롭 등 **운영 증상 1차 확인** | 무손실 물리 패브릭 설계·튜닝(PFC/ECN)은 **네트워크팀 영역**([문서 02](02-architecture.md)) — 증상 식별 후 위임 |

> **업그레이드 연계:** VCF 9의 **NSX Edge Host Affinity**는 vSphere LCM 호스트 업그레이드 중 Edge를 통한 트래픽 중단을 최소화합니다 → §10.1 LCM과 함께 계획하세요.

### 10.5.2 스토리지 Day-2

PAIF 스토리지는 **vSAN(플랫폼·VM·VKS 노드)** + **AI 자산 store(모델 레지스트리 Harbor·벡터 pgvector/DSM)** 로 나뉩니다.

**vSAN 운영:**

| 운영 영역 | 무엇을 보나 | 메모 |
|----------|------------|------|
| 용량 | VCF 9.1 신규 **Effective Capacity 뷰**(+ Auto-RAID)가 운영 예비·호스트 재구축 예비(과거 "슬랙 스페이스")를 자동 산정 → 광고된 여유 용량을 안전하게 사용 | 디스크 공간 헬스 알람을 모니터하고 임계 도달 전 조치 |
| 건전성 | **vSAN Skyline Health**로 클러스터·디바이스 상태 점검 | 디바이스 장애 시 객체 자동 resync |
| 리밸런스·resync | **Automatic Rebalance**(용량 불균형이 임계 초과 시, 최대 30분 대기 후 시작). resync는 유지보수 모드·리밸런스·정책 변경·장애 복구 시 발생하며 그동안 용량이 "operations usage"로 표시 | **ESA + 10G**에서는 resync 트래픽이 Adaptive Resync 20% 목표를 넘어 VM IO에 영향 줄 수 있음 → 유지보수 창·대역 고려 |

**AI 자산 스토리지 운영:**

| 운영 영역 | 무엇을 보나 | 메모 |
|----------|------------|------|
| 모델 레지스트리(Harbor) 증가 | 모델·NIM(NVIDIA 추론 마이크로서비스) 누적에 따른 저장소 증가 추세 | Day-2 추세 점검은 여기, **용량 산정은 ⑥**. 플랫폼 Harbor 20GB 구분은 [문서 06 §6.9.2](06-production.md) |
| 벡터 DB(pgvector/DSM) 증가 | 인덱스·벡터 데이터 증가 | 추세 점검은 여기, 사이징은 ⑥ / 상세 운영은 [② 데이터 가이드](../../02-vectordb/README.md) |
| 스토리지 지연 → 모델 콜드스타트 | datastore 지연·처리량이 모델 로딩 속도를 좌우 | 콜드스타트 증상은 §10.2.3, 스토리지 정책(SPBM) 점검 |

### 10.5.3 인접 위임 (경계 한 줄)

- **구성·설계**(NSX 토폴로지·vSAN 설계·GPUDirect RDMA 구성) → [문서 02](02-architecture.md)·[문서 09](09-deployment-scenarios.md)
- **용량·사이징**(스토리지·네트워크 용량 산정) → [⑥ 사이징·용량·비용 가이드](../../06-sizing-cost/README.md); 벡터 DB 운영은 [② 데이터 가이드](../../02-vectordb/README.md)
- **보안 네트워크**(마이크로세그멘테이션·접근통제·감사) → [⑤ 보안·거버넌스 가이드](../../05-security/README.md)
- **백업·복구 타깃** → §10.3

> **적용 전 확인:** vSAN 9.1의 Effective Capacity 뷰·Auto-RAID, Automatic Rebalance(최대 30분 대기)·Adaptive Resync(ESA 10G 20% 목표), NSX Edge 메트릭의 VCF Operations 수집(20초 주기)·Edge Host Affinity는 공식 문서·블로그 기준이나, 정확한 임계치·메트릭 명칭·절차는 적용 전 공식 문서로 재확인하시기 바랍니다 — [vSAN 운영 가이드(VCF 9)](https://www.vmware.com/docs/vmw-vsan-operations-guide), [vSAN Effective Capacity(VCF 9.1 블로그)](https://blogs.vmware.com/cloud-foundation/2026/05/11/effective-capacity-view-in-vsan-for-vcf-9-1/), [vSAN 용량 모니터링(TechDocs)](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-0/vsan-deployment-administration-and-monitoring/vsan-monitoring-and-troubleshooting/monitor-the-vsan-cluster/monitor-vsan-capacity.html), [VCF Operations 신규 기능(NSX Edge 메트릭, TechDocs)](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-0/release-notes/vmware-cloud-foundation-90-release-notes/platform-whats-new/whats-new-vcf-ops.html).

---

## 10.6 운영자 독자 트랙

**무슨 일이 생기면 어디로 가나** — 이 문서(및 ① 전반)의 Day-2 운영 내용을 **인프라 운영자 관점의 진입로**로 묶습니다. 처음 운영을 맡았거나, 특정 상황에서 어디를 봐야 할지 빠르게 찾을 때 사용하세요.

### 10.6.1 상황별 라우터

| 상황 / 할 일 | 가는 곳 |
|-------------|---------|
| 플랫폼을 새 버전으로 올려야 함 | §10.1 LCM 런북 |
| 뭔가 고장났다 / 에러가 난다 | §10.2 트러블슈팅 |
| 백업·복구를 점검·훈련해야 함 | §10.3 백업·복구 |
| 인증서가 만료된다 / 시크릿 교체 | §10.3.3 인증서·시크릿 회전 |
| 알람을 설정하거나 SLO를 정해야 함 | §10.4 SLO·알람·온콜 |
| 새벽에 알람을 받았다(온콜) | §10.4.3 → §10.2 |
| 네트워크가 느리다 / Edge·LB·Network Policy 점검 | §10.5.1 네트워크 Day-2 |
| 스토리지 용량·성능 / vSAN 점검 | §10.5.2 스토리지 Day-2 |
| HA/DR 설계가 궁금하다 | [문서 06](06-production.md) §6.2~6.3 |
| GPU를 테넌트에 서비스로 제공·운영 | [문서 07](07-gpuaas.md) §7.7 Day-2 |
| 보안 운영(접근통제·감사·공급망) | [⑤ 보안·거버넌스 가이드](../../05-security/README.md) |
| 용량·비용(사이징·차지백) | [⑥ 사이징·용량·비용 가이드](../../06-sizing-cost/README.md) |

### 10.6.2 운영자 정기 점검 리듬

Day-2를 "사고 났을 때만"이 아니라 주기로 돌립니다.

```
일간:  관측 대시보드(모델·GPU) 확인, 활성 알람·온콜 처리, Endpoint 헬스, 네트워크·vSAN 헬스 알람
주간:  쿼터 소진·유휴 GPU, 백업 성공 로그, 인증서 만료 임박 점검, NSX Edge·LB 상태
월간:  용량 추세 검토(vSAN·모델 store·벡터 DB → ⑥), 알람 노이즈·임계치 튜닝, 패치 대기 항목 정리
분기:  복구 훈련(§10.3.2), 업그레이드 계획 점검(§10.1), 멀티테넌트 격리 회귀
```

### 10.6.3 운영 책임 경계 (한 줄 정리)

- **① 이 문서**: 플랫폼/인프라 Day-2 운영(업그레이드·장애·백업복구·인증서·SLO·네트워크·스토리지).
- **PAIS 플랫폼**: 일상 운영의 상당 부분을 자동화·관측으로 처리([문서 06 §6.12](06-production.md)). 운영자는 HA/DR·거버넌스·라이프사이클에 집중.
- **⑤ 보안 / ⑥ 용량**: 보안 운영과 용량·비용은 각 가이드로 위임.

---

> **이 문서의 Day-2 운영 범위:** 업그레이드(LCM)·트러블슈팅·백업복구·인증서·SLO·**네트워크·스토리지 Day-2**·운영자 트랙을 다룹니다. 더 깊은 주제(예: 분산 학습 패브릭 성능 튜닝, 스토리지 정책 자동화)는 향후 보강 후보입니다.

---

[← 이전: 09 구축 시나리오](09-deployment-scenarios.md) · [목차](../README.md) · [다음: 11 GPU Enablement 핸즈온 →](11-gpu-enablement.md)

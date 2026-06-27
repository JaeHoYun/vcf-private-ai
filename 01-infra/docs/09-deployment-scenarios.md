# 09 — 구축 시나리오

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.

같은 PAIF/PAIS를 깔더라도 **어디서 출발하느냐**에 따라 구축 절차가 크게 달라집니다. 아무것도 없는 곳에 새로 까는 것과, 이미 돌아가는 환경에 얹는 것과, 다른 플랫폼에서 옮겨오는 것은 밟아야 할 단계도 조심할 것도 다릅니다.

이 문서는 출발 상황을 **세 가지 시나리오**로 나눠 각각의 **선결요건·절차 골격·리스크·의사결정 기준**을 가이드 수준에서 정리합니다. 상세한 단계별 작업계획서가 아니라, "지금 상황에서는 어디서부터, 무엇을 조심하며 시작하나"를 잡는 지도입니다.

> **이 문서의 경계:** 구축의 *출발 시나리오*만 다룹니다. 상세 사이징은 [⑥ 사이징·용량·비용 가이드](../../06-sizing-cost/README.md), 보안 베이스라인은 [⑤ 보안·거버넌스 가이드](../../05-security/README.md), 구축 *이후*의 운영·업그레이드(Day-2)는 운영 영역에서 다룹니다.

> **선수지식 — 가볍게 알고 시작하면 수월합니다:** 이 문서는 다음 개념을 가볍게 알면 수월합니다. 모르면 아래 '모를 때'의 참고경로를 먼저 보세요.

| 영역 | 알아두면 좋은 것 | 모를 때 |
|---|---|---|
| VCF 구성 | SDDC Manager, 관리 도메인·워크로드 도메인의 분리 구조 | [A1 용어집](../appendix/A1-appendix.md) + [02 아키텍처](02-architecture.md) |
| GPU 워크로드 도메인 | GPU-Accelerated Workload Domain이 일반 도메인과 분리·공존하는 방식 | [A1 용어집](../appendix/A1-appendix.md) + [02 아키텍처](02-architecture.md) |
| 출발 상황 구분 | 그린필드·브라운필드·마이그레이션의 의미 차이 | [A1 용어집](../appendix/A1-appendix.md) + [01 개념](01-concepts.md) |
| VCF 편입 경로 | Import(가져오기)·Convert(전환)로 기존 vSphere를 워크로드 이전 없이 편입 | [A1 용어집](../appendix/A1-appendix.md) + [02 아키텍처](02-architecture.md) |
| 워크로드 이전 | Workload Mobility로 VM을 재부팅 없이 대량 이전하는 개념 | [A1 용어집](../appendix/A1-appendix.md) |
| 라이선스·사이징 선결 | NVAIE(NVIDIA AI Enterprise) 필요 여부, 용량 사이징을 착수 전에 확정해야 하는 이유 | [A1 용어집](../appendix/A1-appendix.md) + [01 개념](01-concepts.md) |

> 구축을 시작하기 전에 [구축 시나리오 결정·SoW 정의 워크시트](../worksheet/09-deployment-decision.md)에 현 상황·선결요건을 채우고, 시나리오별 작업기술서(SoW)까지 정의해 두면 좋습니다.

---

## 9.1 세 가지 구축 시나리오 — 무엇을 고를까

| 시나리오 | 한 줄 설명 | 출발 상태 | 대표 상황 |
|---------|-----------|----------|----------|
| **신규 구축** (그린필드) | 백지에서 처음부터 쌓음 | VCF 없음 | 신규 데이터센터, PoC 전용 클러스터 |
| **기존 환경에 얹기** (브라운필드) | 돌아가는 VCF/vSphere 위에 AI만 추가 | VCF 또는 vSphere 운영 중 | 기존 가상화에 AI 인프라만 증설 |
| **전환** (마이그레이션) | 타 플랫폼에서 VCF로 옮기며 구축 | 경쟁사 가상화 운영 중 | 타사 플랫폼 → VCF 표준화 |

> **용어 참고:** 그린필드(아무것도 없는 백지)·브라운필드(기존 환경 위)는 인프라 업계에서 쓰는 표현입니다. "레드필드" 같은 표현은 표준이 아니며, 경쟁사에서 갈아타는 경우는 **마이그레이션**(전환)으로 부릅니다.

**간단 의사결정:**

- 기존에 VMware vSphere 또는 VCF를 쓰고 있나? → 아니오면 **신규**, 예면 **브라운필드**
- 타사 가상화(예: Nutanix, Red Hat OpenShift 등)에서 옮겨오나? → **전환**
- 셋은 배타적이지 않습니다. 예컨대 타사에서 전환하면서 신규 클러스터를 일부 새로 까는 혼합도 흔합니다.

---

## 9.2 신규 구축 (그린필드)

가장 단순한 경로입니다. VCF부터 PAIF/PAIS까지 정해진 순서로 쌓습니다.

- **절차 골격:** [문서 02 §2.6 구축 Phase 개요](02-architecture.md)가 기준 문서입니다(여기서 반복하지 않음). 요약하면 **VCF 9.1 → PAIF(GPU) Workload Domain → Harbor/DSM → PAIS 2.1 → 카탈로그** 순입니다.
- **신규 구축 추가 점검:** 초기 용량은 [⑥], 보안 베이스라인은 [⑤]를 *처음 설계에 반영*하면 나중 재작업이 줄어듭니다. 네임스페이스·네이밍 표준은 초기에 확정하세요(가동 후 바꾸기 어렵습니다).
- **리스크:** 상대적으로 낮습니다. 다만 **GPU 하드웨어 호환성(BCG=Broadcom 호환성 가이드 / HCL=하드웨어 호환성 목록)** 과 라이선스(NVAIE 필요 여부, [문서 01 §1.2](01-concepts.md))를 착수 전 반드시 확인합니다.

---

## 9.3 기존 환경에 얹기 (브라운필드)

이미 vSphere나 VCF를 운영 중인 곳에 PAIF/PAIS를 추가하는 경우입니다. 출발점에 따라 두 갈래입니다.

### (A) 이미 VCF를 운영 중 — GPU 워크로드 도메인 추가

기존 VCF에 **GPU-Accelerated Workload Domain**(GPU 가속 워크로드 도메인)을 새로 만들고 그 위에 PAIS를 설치합니다. 기존 일반 업무 워크로드와는 도메인으로 분리·공존합니다.

- **선결:** 기존 VCF가 9.1 호환 버전인지 확인 → 미달이면 PAIF 추가 *전에* 먼저 업그레이드(아래 박스).
- GPU 호스트 증설, NSX·스토리지(vSAN) 가용 용량 확인.

### (B) VCF 없이 vSphere만 운영 중 — 먼저 VCF로 편입

VCF 9는 기존 vSphere를 **워크로드 이전 없이** VCF로 편입하는 두 경로를 제공합니다(기존 구성·가동 중 워크로드를 보존하므로 이전 리스크가 낮습니다).

| 경로 | 언제 | 무엇을 하나 |
|------|------|------------|
| **Convert(전환)** | 아직 VCF 인스턴스가 없고, 기존 vCenter·NSX·Operations만 있을 때 | 기존 구성요소로 VCF 관리 도메인을 구성하고, 빠진 컴포넌트는 자동 배포 |
| **Import(가져오기)** | 이미 VCF가 있을 때 | 기존 vSphere를 추가 VI 워크로드 도메인으로 편입(빠진 NSX 등 자동 배포) |

편입이 끝나면 (A)와 동일하게 GPU 워크로드 도메인 추가로 진행합니다.

> **업그레이드는 여기서가 아니라 운영(Day-2)에서 다룹니다.** 기존 VCF가 9.1 미만이면 PAIF 추가 전 업그레이드가 필요합니다. 9.0.x → 9.1 한눈 체크리스트는 [문서 00](00-whats-new.md)의 §0.6에 있고, 순서·롤백을 포함한 상세 업그레이드 런북은 운영 영역에서 별도로 다룹니다(업그레이드는 *이미 돌아가는 플랫폼의 라이프사이클 관리*이므로 Day-2 운영에 속합니다).

- **리스크:** 기존 운영 워크로드에 미치는 영향(유지보수 창 필요), 버전·하드웨어 호환, 기존 네트워크/스토리지 자원 잠식.

> **적용 전 확인:** VCF의 Convert/Import 두 경로와 기존 VCF에 GPU 워크로드 도메인을 추가하는 방식은 공식 문서 기준입니다. 다만 9.1의 정확한 절차·전제조건은 적용 전 [Broadcom TechDocs](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1.html)로 재확인하시기 바랍니다 ([기존 vSphere의 VCF 9 편입 — VCF 블로그](https://blogs.vmware.com/cloud-foundation/2026/02/05/how-to-converge-a-vmware-vsphere-environment-to-vmware-cloud-foundation-9-0/), [GPU 가속 워크로드 도메인 배포 — TechDocs](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/deploying-private-ai-foundation-with-nvidia/deploy-a-vi-workload-domain-in-vmware-cloud-foundation.html)).

---

## 9.4 전환 — 경쟁사에서 이전 (개요)

타사 가상화(예: Nutanix AHV, Red Hat OpenShift Virtualization 등)에서 VCF로 옮기며 PAIF/PAIS를 구축하는 시나리오입니다. **본 절은 개요·골격**이며, 상세 전환 플레이북은 후속 작업 또는 별도 가이드 후보입니다.

**골격 단계:**

1. **평가(자산 인벤토리):** 옮길 VM·데이터·GPU 워크로드를 식별하고 호환성·의존성을 파악
2. **착지 환경 준비:** 신규(§9.2) 또는 브라운필드(§9.3)로 목표 VCF 환경을 먼저 구축
3. **워크로드 이전:** **VCF Operations Workload Mobility**(구 HCX)로 vSphere·비vSphere VM을 재부팅 없이 대량 이전
4. **병행 운영·컷오버:** 단계적으로 옮기며 검증 후 전환, 롤백 경로 확보
5. **AI 재구성:** 모델·Knowledge Base·에이전트는 단순 VM 이전과 별개로 ①의 구축·개발 절차([문서 03](03-workflows.md))로 재구성

> **전환 동인(맥락):** vSphere 8은 2027년 10월 일반 지원 종료가 예고되어, 플랫폼 현대화 시점 판단의 참고가 됩니다.

> **적용 전 확인:** Workload Mobility의 비vSphere(경쟁사) 소스 지원 범위와 제품 명칭은 변경이 잦으므로 적용 전 공식 문서로 확인하시기 바랍니다. 경쟁사 고유의 전환 도구·절차는 본 가이드 범위 밖입니다 ([VCF Operations Workload Mobility — VMware](https://www.vmware.com/products/cloud-infrastructure/vcf-operations-workload-mobility)).

---

## 9.5 시나리오 비교 + 공통 선결요건

| 항목 | 신규(그린필드) | 기존에 얹기(브라운필드) | 전환(마이그레이션) |
|------|:---:|:---:|:---:|
| 출발 상태 | 백지 | 기존 VCF/vSphere | 타 플랫폼 |
| 난이도·리스크 | 낮음 | 중간(기존 영향) | 높음(이전·컷오버) |
| 핵심 도구 | VCF 설치 | VCF Import/Convert + GPU WD | Workload Mobility |
| 워크로드 이전 | 없음 | 없음(편입) | 있음 |
| 대표 리스크 | 하드웨어 호환 | 운영 영향·다운타임 | 데이터 이전·컷오버 |

**공통 선결요건 체크리스트:**

```
- GPU 하드웨어 BCG/HCL 호환 확인 (특히 Blackwell, ConnectX-7/BlueField-3)
- 라이선스 확인 (VCF, NVAIE 필요 여부) → 문서 01 §1.2
- 용량 사이징 → ⑥ 사이징·용량·비용 가이드
- 보안 베이스라인 → ⑤ 보안·거버넌스 가이드
- 네임스페이스·네이밍 표준 사전 확정
- (브라운필드·전환) 유지보수 창 + 롤백 계획 수립
```

---

[← 이전: 08 한국 산업군 적용 시나리오](08-industry.md) · [목차](../README.md) · [다음: 10 Day-2 운영 →](10-operations.md)

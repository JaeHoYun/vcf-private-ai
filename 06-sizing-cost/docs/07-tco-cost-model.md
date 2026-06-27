# 07 — TCO와 비용 모델

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.
> 시리즈 인덱스: [시리즈 허브](../../README.md)

이 문서는 시리즈 ⑥(사이징·용량·비용)의 마무리 문서로, 02~05에서 도출한 사이징 결과(GPU 수, 노드 수, 스토리지 용량)를 총소유비용(TCO) 항목으로 환산하는 모델과 워크시트를 제시합니다. 이 문서의 목적은 "얼마인지"를 단정하는 것이 아니라, "무엇을 어떤 구조로 더해야 하는지"를 빠짐없이 보여주는 데 있습니다.

**중요(가격에 대한 입장):** 이 문서는 라이선스 단가, 서버/GPU 단가, 전력 단가 등 어떤 실제 금액도 제시하지 않습니다. 모든 단가는 "공식 견적·구독 조건으로 확인"이 필요한 입력값이며, 워크시트의 단가 칸은 비워 둡니다. 벤더가 발표한 TCO 절감 수치는 "벤더 발표(up to)·보수적 해석·실측 필요"로만 인용합니다.

---

## 7.1 TCO 범위와 기간 설정

TCO를 비교 가능하게 만들려면 먼저 "무엇을, 몇 년에 걸쳐" 더할지 합의해야 합니다. 같은 인프라라도 3년 상각과 5년 상각은 연 환산 비용이 크게 달라집니다.

| 결정 항목 | 권장 기본값 | 설명 |
| --- | --- | --- |
| TCO 분석 기간 | 3년 또는 5년 | 하드웨어 감가 주기와 구독 약정 기간에 맞춥니다. 한 기간으로 통일해 비교합니다. |
| 비용 단위 | 연 환산(annualized) | CapEx는 상각해 연 비용으로 환산, OpEx는 연 비용 그대로 합산합니다. |
| 비교 대상 | 온프레미스 PAIF vs 퍼블릭 GPU 클라우드 | 7.6에서 항목 체크리스트로 정렬합니다. |
| 환율·세금 | 분석 시점 고정값 | 실제 단가 확정 시 견적의 통화·부가세 기준을 따릅니다(확인 필요). |

TCO는 다음 5개 대분류로 분해합니다. 7.2–7.5에서 각각을 다룹니다.

1. 소프트웨어 라이선스/구독 — VCF 코어 구독(PAIF 포함), NVAIE(별도), DSM(entitlement)
2. GPU 하드웨어 — CapEx 및 감가
3. 서버·스토리지·네트워크 — GPU 외 인프라
4. 운영비(OpEx) — 인력, 전력, 상면, 유지보수
5. 도입/마이그레이션 — 일회성 전환 비용

---

## 7.2 소프트웨어 라이선스/구독 비용

라이선스는 TCO에서 가장 오해가 많은 항목입니다. 핵심 사실관계는 다음과 같으며, 이 구조가 산정의 출발점입니다. (라이선스 구조의 상세는 ① 라이선스 절 [① 인프라](../../01-infra/README.md)를 참조하세요.)

| 구성 요소 | 라이선스 출처 | 산정 단위 | 비고 |
| --- | --- | --- | --- |
| VMware Private AI Foundation with NVIDIA(PAIF) | VCF 솔루션/코어 구독에 **포함** | VCF 코어 구독에 종속 | 별도 제품 구매가 아니라 VCF 구독 위에서 활성화됩니다. |
| VCF 코어 구독 | Broadcom | **물리 코어당(per-core) 구독**, 코어 최소수량 적용 | 컴퓨트·스토리지·네트워크·관리가 한 구독에 묶입니다. |
| NVIDIA AI Enterprise(NVAIE) | **NVIDIA에서 별도 구매** | **GPU당(per-GPU)** 구독/영구 | ESX 호스트 드라이버 VIB, 게스트 OS 드라이버, NGC 컨테이너 이미지 사용에 필요합니다. |
| Data Services Manager(DSM) | VCF Advanced Service(**entitlement**) | VCF 구독에 종속 | VCF 구독자만 프로덕션 사용 가능. 일부 상위 서비스는 별도 조건일 수 있습니다(확인 필요). |

근거: PAIF는 VCF 솔루션 라이선스로 제공되고 NVAIE 라이선스는 NVIDIA에서 별도 구매가 필요하다는 점([Broadcom TechDocs — NVIDIA DLS/CLS Design Considerations](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vvs/1-0/private-ai-ready-infrastructure-for-vmware-cloud-foundation/detailed-design-for-private-ai-foundation-with-nvidia/nvidia-dls-cls-design-considerations.html)), VCF가 코어당 구독 모델이라는 점([Broadcom TechDocs — Licensing Model](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-0/licensing/licensing-overview/licensing-model.html)), NVAIE가 GPU당 라이선스라는 점([NVIDIA AI Enterprise Licensing Guide](https://docs.nvidia.com/ai-enterprise/planning-resource/licensing-guide/latest/licensing.html)), DSM이 VCF Advanced Service라는 점([VMware DSM 9.1 블로그](https://blogs.vmware.com/cloud-foundation/2026/05/05/vmware-data-services-manager-9-1-automating-the-modern-databases-that-drive-ai-and-private-cloud/)).

### 라이선스 산정 워크시트(단가 칸은 견적 입력란)

| 입력값(02–05에서) | 곱하기 단위 | 단가(견적 입력) | 연 환산 소계 |
| --- | --- | --- | --- |
| VCF 물리 코어 수(코어 최소수량 적용 후) | 코어/년 | (견적 확인) | (계산) |
| GPU 총 개수 | GPU/년 | (NVIDIA 견적 확인) | (계산) |
| DSM 사용 범위 | VCF entitlement | (조건 확인) | (계산) |

산정 주의(빈 단가·규칙값을 견적으로 채우는 방법은 [부록 A3 견적 요청 체크리스트](../appendix/A3-rfq-quote-checklist.md) 참조):
- **코어 최소수량(core minimum):** 코어 수가 적은 CPU에서도 물리 코어당 최소 수량이 적용되어 "장부상 코어"가 늘 수 있습니다. 사이징의 물리 코어 수를 그대로 쓰지 말고 최소수량 규칙을 반영합니다(실제 최소수량 값은 [부록 A3.1](../appendix/A3-rfq-quote-checklist.md#a31-소프트웨어-라이선스-견적-broadcom--nvidia)로 견적 확인)([Broadcom TechDocs — Licensing Model](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-0/licensing/licensing-overview/licensing-model.html)).
- **NVAIE는 설치된 모든 GPU 기준:** 호스트에 설치된 모든 GPU에 라이선스가 필요합니다. vGPU 분할을 하더라도 물리 GPU 수가 기준입니다([NVIDIA AI Enterprise Licensing Guide](https://docs.nvidia.com/ai-enterprise/planning-resource/licensing-guide/latest/licensing.html)).
- **NVAIE 지원 등급/기간:** 구독·소비형·영구(영구는 5년 지원 서비스 필요) 중 무엇인지에 따라 연 환산이 달라집니다(확인 필요).
- **이중 계상 금지:** PAIF는 VCF 구독에 포함이므로 별도 제품 비용으로 또 더하지 않습니다.

---

## 7.3 하드웨어 비용(CapEx와 감가)

하드웨어는 일회성 지출(CapEx)이지만 TCO 비교에서는 분석 기간으로 나눈 연 환산 감가로 다룹니다.

| 항목 | 사이징 입력(02–05) | 비용 모델 | 단가(견적 입력) |
| --- | --- | --- | --- |
| GPU | GPU 모델·수량 | 단가 × 수량 ÷ 상각연수 | (견적 확인) |
| GPU 서버(노드) | 노드 수, 폼팩터 | 단가 × 노드 수 ÷ 상각연수 | (견적 확인) |
| 메모리·CPU | 노드별 사양 | 서버 단가에 포함 또는 옵션 | (견적 확인) |
| 고속 패브릭 NIC | 노드당 포트 수 | 단가 × 포트 수 ÷ 상각연수 | (견적 확인) |
| GPU 간 인터커넥트 | 토폴로지 의존 | 구성에 따라 별도 | (견적 확인) |

감가 모델 메모:
- **상각연수 일관성:** GPU와 서버의 상각연수를 다르게 두면 연 환산이 왜곡됩니다. 7.1의 분석 기간과 맞춥니다.
- **GPU 세대 교체 위험:** AI 가속기는 진부화가 빠릅니다. 보수적으로는 짧은 상각연수를, 회계 기준에 따라서는 자산 정책을 따릅니다(확인 필요).
- **잔존가치:** 중고 재판매를 가정하면 TCO가 낮아지지만, 보수적 모델에서는 0으로 둡니다.

---

## 7.4 서버·스토리지·네트워크(GPU 외 인프라)

GPU 외 인프라는 GPU-Accelerated Workload Domain(약칭: GPU 가속 워크로드 도메인)을 구성·운영하는 데 필요한 기반입니다.

| 항목 | 사이징 입력 | 비용 모델 | 단가(견적 입력) |
| --- | --- | --- | --- |
| vSAN/외부 스토리지 용량 | 05 스토리지 용량 | 용량(TB) × 단가 ÷ 상각연수 | (견적 확인) |
| 관리/워크로드 네트워크 스위치 | 토폴로지 | 단가 × 수량 ÷ 상각연수 | (견적 확인) |
| 데이터 파이프라인 스토리지 | 데이터셋 크기 | 계층/티어별 단가 | (견적 확인) |
| 백업·DR | 보호 대상 용량 | 용량 × 단가 | (견적 확인) |

메모: VCF 9는 vSAN(OSA/ESA) 3노드 또는 외부 스토리지(NFS/FC) 2노드 구성을 지원하므로([Broadcom TechDocs — Licensing Model](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-0/licensing/licensing-overview/licensing-model.html)), 스토리지 아키텍처 선택이 노드 수와 라이선스 코어 수에 영향을 줍니다. 스토리지 효율(압축·중복제거·메모리 티어링) 기능은 실효 용량을 늘려 단위 용량당 비용을 낮출 수 있으나, 효과는 데이터 특성에 의존하므로 실측이 필요합니다(7.7 참조).

---

## 7.5 운영비(OpEx)와 도입/마이그레이션

연속 지출(OpEx)과 일회성 전환 비용은 하드웨어·라이선스에 가려 빠지기 쉽습니다.

| OpEx 항목 | 산정 기준 | 비용 모델 | 단가(견적 입력) |
| --- | --- | --- | --- |
| 인력(운영·플랫폼) | 운영 FTE(전임 환산 인력) 수 | 인건비 × FTE | (산정 입력) |
| 전력 | 노드·GPU 소비전력(kW) | kW × 가동시간 × 전력단가 × PUE(전력사용효율) | (사이트 데이터 확인) |
| 상면/냉각 | 랙 수, 열밀도 | 랙·상면 단가 | (사이트 데이터 확인) |
| 유지보수/지원 | 하드웨어·소프트웨어 계약 | 계약 단가(구독에 포함 여부 확인) | (견적 확인) |
| 도입/마이그레이션 | 일회성 | PoC·이행·교육·컨설팅 | (산정 입력) |

메모:
- **전력은 GPU TCO의 큰 변수:** 고밀도 GPU는 소비전력과 냉각 부하가 커서 PUE를 곱한 실효 전력비를 반영해야 합니다. 노드별 소비전력은 사이징(04)의 사양에서 가져옵니다.
- **마이그레이션:** 기존 환경에서의 이행 방식에 따라 일회성 비용이 달라집니다. 이는 연 환산이 아니라 분석 기간 전체에 일시 반영하거나 기간으로 분할합니다.

---

## 7.6 퍼블릭 GPU 클라우드 vs 온프레미스 PAIF 비교 프레임

"온프레미스가 싸다/비싸다"를 단정하지 않습니다. 동일 항목으로 정렬한 뒤, 손익분기를 **개념적으로** 따지는 틀만 제공합니다. 실제 우열은 워크로드와 사용률(utilization)에 의존하며 실측이 필요합니다.

| 비교 항목 | 온프레미스 PAIF | 퍼블릭 GPU 클라우드 |
| --- | --- | --- |
| 과금 구조 | CapEx + 구독(고정에 가까움) | 사용량 기반(가변, 시간당/토큰당) |
| GPU 라이선스 | NVAIE per-GPU 별도 | 인스턴스 요금에 포함되는 경우 많음 |
| 사용률 민감도 | 낮은 사용률에서 단위비용 상승 | 켠 만큼 과금(유휴 시 끄면 절감) |
| 데이터 이그레스 | 사내 트래픽 | 외부 전송 비용 발생 가능 |
| 데이터 주권/규제 | 사내 통제(에어갭 가능, DLS) | 위치·통제 정책 확인 필요 |
| 확장 탄력성 | 사전 조달 필요 | 즉시 확장 |

손익분기 개념(수치 단정 금지):
- 온프레미스는 고정비 비중이 커서 **사용률이 높을수록** 단위비용이 내려갑니다. 24/7 고부하 추론·학습처럼 꾸준한 수요에 유리한 구조입니다.
- 퍼블릭은 **간헐적·버스트성** 수요나 초기 불확실성이 클 때 유리한 구조입니다.
- 따라서 손익분기점은 "사용률·기간·워크로드 패턴"의 함수이며, 특정 % 절감을 단정할 수 없습니다. 두 경우 모두 7.1에서 정한 동일 기간·동일 항목으로 비교해야 공정합니다.

**벤더 발표 수치(보수적 해석 필요):** Broadcom은 VCF 9.1 발표에서 서버 비용 최대 40% 절감, 스토리지 TCO 39% 절감, 쿠버네티스 운영비 최대 46% 절감, 퍼블릭 클라우드 대비 1X–2X TCO 개선을 제시했습니다. 이는 벤더 내부 추정·best-case "up to" 수치로, 자사 환경에 그대로 적용되지 않습니다([Broadcom 보도자료 — VCF 9.1](https://news.broadcom.com/releases/broadcom-announces-vmware-cloud-foundation-9-1); [Virtualization Review — VCF 9.1](https://virtualizationreview.com/articles/2026/05/06/private-ai-not-public-cloud-broadcoms-message-with-vmware-cloud-foundation-9-1.aspx)). 의사결정에는 자사 실측치를 사용하세요.

### 한계비용 — 기보유(매몰) GPU 재활용

역방향 사이징([01 §1.7](01-sizing-methodology.md#17-순방향역방향-사이징))에서는 GPU가 이미 구매된 **매몰비용**(sunk cost)이라 재활용의 한계 CapEx가 0에 가깝습니다. 그러나 PAIF에서 그 GPU를 켜는 순간 다음 한계비용이 발생합니다.

| 항목 | 발생 | 근거 |
|---|---|---|
| NVAIE 라이선스 | 설치된 물리 GPU 전수(vGPU 분할과 무관) | 7.2 |
| 전력·냉각 | GPU 소비전력 × PUE | 7.5 |
| 운영비 | 플랫폼·운영 FTE | 7.5 |

- "노는 GPU니 공짜"는 부정확합니다. 켜는 즉시 per-GPU 라이선스가 붙으므로, **활용도 회수로 가치를 내는 것이 곧 이 한계비용의 정당화**입니다.
- 사용률이 낮으면 단위비용이 오르는 구조(7.6·7.7)가 동일하게 적용됩니다. 따라서 기보유 자원을 먼저 채우는 "증설 전 회수"([06](06-capacity-planning.md) §6.2)가 신규 구매보다 한계비용 측면에서 유리한 경우가 많습니다.
- 전 과정 예제의 한계비용 표는 [09](09-reverse-sizing-scenario.md) §9.5에 있습니다.

---

## 7.7 단위 경제와 비용 귀속(쇼백/차지백)

### 단위 경제(선택) — 토큰/요청당 비용 모델

추론 1천 토큰당 또는 요청당 비용은 "총 연 비용 ÷ 처리량"으로 모델링합니다. 수치는 단정하지 않고 산식만 제시합니다.

```
요청(또는 1K 토큰)당 비용
  = (연 환산 TCO 합계: 7.2–7.5)
    ÷ (연간 처리 요청 수 또는 1K 토큰 수: 03 처리량 사이징)
```

주의: 분모(처리량)는 사용률·동시성·모델 크기에 따라 크게 변동하므로, 단위비용은 가동률 가정에 매우 민감합니다. 단일 숫자가 아니라 사용률 시나리오(예: 낮음/보통/높음)별 범위로 제시하는 것이 안전합니다.

### 비용 귀속(쇼백/차지백)

VCF의 비용 관리 기능은 소유 비용(compute, storage, VM 직접비)을 VCF 도메인·비용 동인(cost driver)별로 분해하고, CPU·메모리·스토리지 비용을 애플리케이션 팀으로 귀속(showback)할 수 있게 합니다([Broadcom TechDocs — Cost Overview](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-0/cost-and-capacity-management/business-management/cost-overview.html)).

| 모델 | 정의 | 적용 시점 |
| --- | --- | --- |
| 쇼백(showback) | 비용을 팀별로 **보여주되 청구는 안 함** | 초기 가시성 확보 단계 |
| 차지백(chargeback) | 비용을 팀별로 **실제 청구** | 비용 책임 내재화 단계 |

GPU 환경에서의 귀속은 GPU 점유(전용 vs vGPU 분할), 토큰 사용량 등 추가 동인을 반영해야 합니다. 용량과 비용 동인의 연계는 [06-capacity-planning.md](06-capacity-planning.md)와 함께 운영하세요.

---

## 7.8 검증·실측 방법

비용 "추정"은 실제 청구·사용량으로 반드시 보정해야 합니다. 아래는 추정 모델을 실측으로 검증하는 체크리스트입니다.

| 검증 대상 | 실측 소스 | 방법 | 합격 기준(예시) |
| --- | --- | --- | --- |
| 라이선스 코어 수 | Broadcom 구독 명세서 | 워크시트의 코어 수(최소수량 반영) vs 청구 코어 수 | 일치(차이 시 최소수량 규칙 재확인) |
| NVAIE GPU 라이선스 | NVIDIA 라이선싱 포털, NLS(NVIDIA License System, DLS/CLS) 사용 현황 | 설치 GPU 수 vs 라이선스 소비 수 | 설치 GPU 전수 라이선스 |
| 하드웨어 감가 | 자산 대장 | 상각연수·잔존가치 가정 vs 회계 정책 | 정책과 일치 |
| 전력 실효비 | PDU/시설 계측, 전력 청구서 | 추정 kW × PUE vs 실측 소비량 | 추정-실측 오차 허용범위 내 |
| 스토리지 효율 | vSAN 용량 리포트 | 가정한 압축·중복제거율 vs 실측 절감률 | 가정이 실측보다 보수적 |
| 단위비용(토큰/요청) | 처리량 모니터링 | 모델 산식 분모 vs 실제 처리량 | 사용률 시나리오 범위 내 |
| 비용 귀속 | VCF 비용 관리 리포트 | 쇼백 분해 vs 팀별 실사용 | 귀속 합계 = 총비용 |

실측 운영 권고:
1. **분기별 재산정:** 사용률·요금·환율은 변하므로 분기마다 워크시트를 갱신합니다.
2. **벤더 수치 미사용 원칙:** 의사결정에는 Broadcom의 "up to" 수치가 아니라 자사 실측치를 사용합니다.
3. **단가 확정 경로:** 모든 빈 단가 칸은 공식 견적·구독 조건으로 채우고, 채운 출처(견적서 번호·일자)를 기록해 추적 가능성을 유지합니다.
4. **불확실 항목 표기:** 확정되지 않은 값은 "확인 필요"로 남겨 두고 추정 단정으로 바꾸지 않습니다.

---

### 참고 출처

- [Broadcom TechDocs — Licensing Model (VCF 9)](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-0/licensing/licensing-overview/licensing-model.html)
- [Broadcom TechDocs — NVIDIA DLS/CLS Design Considerations (PAIF)](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vvs/1-0/private-ai-ready-infrastructure-for-vmware-cloud-foundation/detailed-design-for-private-ai-foundation-with-nvidia/nvidia-dls-cls-design-considerations.html)
- [Broadcom TechDocs — Cost Overview (VCF Cost & Capacity Management)](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-0/cost-and-capacity-management/business-management/cost-overview.html)
- [NVIDIA AI Enterprise Licensing Guide (per-GPU)](https://docs.nvidia.com/ai-enterprise/planning-resource/licensing-guide/latest/licensing.html)
- [NVIDIA License System (DLS/CLS)](https://docs.nvidia.com/license-system/latest/nvidia-license-system-user-guide/index.html)
- [VMware DSM 9.1 — VCF Advanced Service (블로그)](https://blogs.vmware.com/cloud-foundation/2026/05/05/vmware-data-services-manager-9-1-automating-the-modern-databases-that-drive-ai-and-private-cloud/)
- [Broadcom 보도자료 — VCF 9.1 (TCO 발표 수치)](https://news.broadcom.com/releases/broadcom-announces-vmware-cloud-foundation-9-1)
- [Virtualization Review — VCF 9.1 (벤더 수치 보도)](https://virtualizationreview.com/articles/2026/05/06/private-ai-not-public-cloud-broadcoms-message-with-vmware-cloud-foundation-9-1.aspx)

---
[← 이전: 06 용량 계획과 운영](06-capacity-planning.md) · [목차](../README.md) · [다음: 08 레퍼런스 시나리오(전 과정 예제) →](08-reference-scenario.md)

# 07 — 감사·로깅·사고대응 및 컴플라이언스 체크리스트

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)을 참조하세요.
> 시리즈 인덱스: [vcf-private-ai-series](../../README.md)

이 문서는 시리즈 ⑤(`vcf-private-ai-security-governance`)의 마무리 문서입니다. 01–06 문서에서 설계한 통제가 실제로 "증명 가능"하도록, (1) 무엇을 로그로 남기고 어떻게 무결성을 지킬 것인가, (2) 모델 행위를 어떻게 관측하고 이상을 탐지할 것인가, (3) AI 특유의 사고가 발생했을 때 어떻게 탐지·대응·복구할 것인가, (4) 통제를 어떤 일반 컴플라이언스 범주에 매핑하는가, 그리고 (5) 모든 통제를 한 표로 모아 각각의 검증 방법을 명시하는 **마스터 통제 체크리스트**를 다룹니다.

기반 사실은 VCF 9.1 / PAIF(VMware Private AI Foundation with NVIDIA) 9.1 / PAIS(Private AI Services) 2.1이며, 관측성은 VCF Operations와 OpenTelemetry(OTel), Grafana를 연계하는 ③ 문서([vcf-paif-serving-api-guide](../../03-serving-api/README.md))를 따릅니다. GPU 가속 워크로드는 공식 용어 "GPU-Accelerated Workload Domain"(이하 GPU 워크로드 도메인)으로 표기합니다.

> 규제 표현 주의: 이 문서는 특정 규제기관이나 실명 기업을 특정 행위와 결부하지 않습니다. 규제는 "개인정보보호 규제", "금융 규제", "산업 보안 요건" 같은 일반 범주로만 추상화합니다. 조직별 적용은 자체 법무·컴플라이언스 검토가 필요합니다(확인 필요).

---

## 7.1 감사·로깅: 무엇을, 어떻게 남길 것인가

### 7.1.1 설계 원칙 — 추적성의 3요소

감사 로그의 본질은 "누가(who) · 언제(when) · 무엇을(what)"을 재구성 가능한 형태로 남기는 것입니다. AI 플랫폼에서는 인프라 계층(VCF/GPU 워크로드 도메인)과 AI 계층(모델 호출·도구 호출·데이터 접근)을 모두 포괄해야 추적 체인이 끊기지 않습니다. ISO/IEC 27001:2022 Annex A.8.15(Logging)는 로그를 "생성·저장·보호·분석"하는 탐지 통제로 정의하며, 로그가 사건의 증거가 되도록 무결성을 보장하고 무단 접근을 막을 것을 요구합니다([ISMS.online — A.8.15](https://www.isms.online/iso-27001/annex-a-2022/how-to-implement-iso-27001-2022-annex-a-control-8-15-logging/)). ISO/IEC 42001의 AI 이벤트 로그 통제(A.6.2.8)는 이를 AI 수명주기로 확장해, 프롬프트·도구 호출·출력·영향 받은 리소스를 사용자·세션·데이터 소스에 묶인 "재생 가능한 추적(replayable trace)"으로 기록할 것을 권합니다([ISMS.online — ISO 42001 A.6.2.8](https://www.isms.online/iso-42001/annex-a-controls/a-6-ai-system-life-cycle/a-6-2-8-ai-system-recording-of-event-logs/)).

### 7.1.2 로그 카테고리와 최소 기록 항목

| 카테고리 | 최소 기록 항목(누가·언제·무엇을) | 발생 계층 | 시리즈 교차 참조 |
|---|---|---|---|
| 인증(Authentication) | 주체 ID, 시각, 인증 결과(성공/실패), 인증 방식(IdP/SSO), 출발지 | VCF Identity Broker / IdP | [03 — ID·인증·접근통제](./03-identity-access.md) |
| 접근·인가(Authorization) | 주체, 시각, 대상 리소스, 권한, 허용/거부 결과 | VCF / VKS RBAC | [03 — ID·인증·접근통제](./03-identity-access.md) |
| 모델 호출(Inference) | 호출자 신원, 시각, 모델·버전, 입력/출력 토큰 수, 지연, 결과 코드 | PAIF Serving(③) | [01 — 위협 모델](./01-threat-model.md), [04 — 에어갭·공급망·모델 출처](./04-airgap-supply-chain.md) |
| 도구 호출(Tool/Agent) | 에이전트 세션, 시각, 호출 도구, 인자(민감정보 마스킹), 영향 리소스 | PAIS Agent / MCP | [06 — 앱 계층 가드레일](./06-app-guardrails.md) |
| 데이터 접근(Data) | 주체, 시각, 데이터셋/벡터 스토어, 작업(읽기/쓰기), 행 수/범위 | 데이터·RAG 계층 | [05 — 데이터 거버넌스·프라이버시](./05-data-governance.md) |
| 인프라·운영(Platform) | 운영자, 시각, 변경 대상(클러스터/정책/패치), 변경 전후 상태 | VCF Operations | [02 — 네트워크·테넌트·GPU 격리](./02-network-tenant-isolation.md) |

> 핵심: 모델 호출과 도구 호출은 동일 세션 식별자(correlation/trace ID)로 묶어, 한 요청이 어떤 모델·도구·데이터로 흘러갔는지를 단일 추적 체인으로 재구성할 수 있어야 합니다. 이는 OTel GenAI 시맨틱 컨벤션(7.2)과 직접 연결됩니다.

### 7.1.3 중앙 수집·무결성·보존

VCF 9.1은 로그 관리를 단일 인터페이스로 통합했습니다. "Centralized Log Management"는 VCF Operations for Logs를 VCF Operations 메인 인터페이스로 통합하며, "Audit Trail"은 VKS를 포함한 모든 구성요소의 사용자 활동을 "중앙집중·시간 구간(time-sliced) 뷰"로 제공해 포렌식 분석을 단순화합니다([VMware — Platform Security for VCF 9.1](https://blogs.vmware.com/cloud-foundation/2026/05/05/platform-security-vcf-9-1/)). VCF Operations의 감사 기록은 시간 구간으로 상세를 펼쳐 보고 CSV로 내보낼 수 있어, 사고 조사 시 표준화된 로그 아키텍처와 중앙 보관 이력을 제공합니다([Broadcom — VCF 9.1 발표](https://news.broadcom.com/releases/broadcom-announces-vmware-cloud-foundation-9-1)).

| 통제 목표 | 구현 수단 | 검증 지점 |
|---|---|---|
| 중앙 수집 | VCF Operations for Logs 통합 수집 + syslog 포워딩(TCP/TLS/UDP) | 각 구성요소가 중앙 수집기로 이벤트를 보내는지 확인([Broadcom TechDocs — Setup Syslog Configuration](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-0/infrastructure-operations/network-operationss/configuration/configuring-logs/syslog-configuration.html)) |
| 무결성 | 전송 구간 TLS, 수집 후 변경 불가(append-only) 저장, 접근 제한 | 비인가 수정·삭제가 차단되는지, 전송 암호화(syslog TCP over TLS)가 적용되는지([Broadcom TechDocs — Aria Operations for Logs Design](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vvs/1-0/intelligent-logging-and-analytics-for-vmware-cloud-foundation/detailed-design-for-intelligent-logging-and-analytics-for-vmware-cloud-foundation/vmware-aria-operations-for-logs-design-for-intelligent-logging-and-analytics.html)) |
| 가용성·재해 대비 | 두 번째 VCF 인스턴스로 로그 포워딩 | 1차 장애 시에도 로그가 보존되는지([Broadcom TechDocs — Configure Log Forwarding Between VCF Instances](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vvs/9-X/configure-event-forwarding-in-region-b.html)) |
| 보존 기간 | 조직 보존 정책(규제 범주별)에 따른 보존·아카이브 | 보존 정책이 적용되고 만료 전 삭제가 차단되는지(조직별 — 확인 필요) |

---

## 7.2 모델 행위 관측: 품질·드리프트·오남용 탐지

### 7.2.1 ③ 관측성 스택 연계

③ 문서의 관측성 기반은 VCF Operations + OpenTelemetry + Grafana입니다. OTel의 GenAI 시맨틱 컨벤션은 LLM 호출·에이전트 단계·벡터 DB 질의·토큰 사용·비용·품질 메트릭의 속성명을 표준화합니다. 핵심 속성으로 `gen_ai.provider.name`, `gen_ai.operation.name`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens` 등이 있으며, 2026년 3월 기준 대부분이 experimental 상태이므로 버전 고정과 호환성 확인이 필요합니다([OpenTelemetry — GenAI Observability](https://opentelemetry.io/blog/2026/genai-observability/)). 수집된 신호는 Grafana로 시각화·경보 처리할 수 있습니다([Grafana Labs — Monitoring LLMs in production](https://grafana.com/blog/ai-observability-llms-in-production/)).

### 7.2.2 관측 대상과 탐지 신호

| 관측 축 | 대표 신호 | 탐지하려는 위험 | OWASP LLM 연관 |
|---|---|---|---|
| 품질(Quality) | 평가자(evaluator) 점수, 사실성/할루시네이션 스코어 | 응답 품질 저하 | LLM09 Misinformation |
| 드리프트(Drift) | 입력 분포·품질 점수의 시계열 변화 | 모델·데이터 분포 이탈 | LLM04 Data and Model Poisoning |
| 오남용(Abuse) | 비정상 호출 빈도, 거부율 급증, 시스템 프롬프트 추출 시도 | 인젝션·프롬프트 유출 | LLM01, LLM07 |
| 자원 소비 | 토큰/요청 폭증, 비용 급증 | 무한 소비·DoS | LLM10 Unbounded Consumption |
| 출력 안전 | 민감정보 패턴 탐지(출력 측) | 데이터 노출 | LLM02 Sensitive Information Disclosure |

품질·안전 평가는 트레이스에 프로그래매틱 평가자를 추가해 할루시네이션 경보, 사실성 검증, 콘텐츠 품질 점수를 생성할 수 있으며, 이 신호로 배포를 게이팅하거나 품질 드리프트 시 운영자에게 경보를 보낼 수 있습니다([OpenTelemetry — GenAI Observability](https://opentelemetry.io/blog/2026/genai-observability/)). OWASP 분류는 [OWASP Top 10 for LLM Applications 2025](https://genai.owasp.org/llm-top-10/)를 따릅니다.

> 권장: 7.1.2의 감사 로그(누가·무엇을)와 7.2의 관측 메트릭(얼마나·어떻게 변했는가)을 동일 trace ID로 연결하면, "이상 신호 → 해당 호출 → 호출자·도구·데이터"로 즉시 역추적할 수 있어 사고 대응(7.3)이 빨라집니다.

---

## 7.3 사고 대응 플레이북 개요 (AI 특유의 사고)

AI 플랫폼 사고 대응은 NIST CSF 2.0의 운영 기능 Detect → Respond → Recover 흐름을 따르며, 그 위에 전략·책임 구조를 정의하는 Govern 기능이 가로지릅니다([NIST CSF 2.0 — 6 Functions](https://csf.tools/reference/nist-cybersecurity-framework/v2-0/)). 아래는 AI 특유의 사고 세 유형의 플레이북 개요입니다.

### 7.3.1 시나리오별 탐지 → 대응 → 복구

| 사고 유형 | 탐지(Detect) 신호 | 대응(Respond) 1차 조치 | 복구(Recover) | 주요 참조 |
|---|---|---|---|---|
| 프롬프트 인젝션 성공 | 시스템 프롬프트 추출 시도, 정책 우회 출력, 거부율 이상 | 해당 세션·도구 권한 차단, 영향 도구 호출 격리, 입력 필터 강화 | 가드레일·시스템 프롬프트 보강 후 재배포, 회귀 검증 | LLM01/LLM07, [06 — 앱 계층 가드레일](./06-app-guardrails.md) |
| 데이터 유출 | 출력 측 민감정보 패턴, 비정상 데이터 접근량 | 데이터 접근 경로 차단, 영향 범위 식별, 로그 보존 고정 | 접근 통제·마스킹 강화, 영향 통지(규제 범주별 — 확인 필요) | LLM02, [05 — 데이터 거버넌스·프라이버시](./05-data-governance.md) |
| 모델 오남용/포이즈닝 | 품질·드리프트 급변, 변조된 학습/임베딩 데이터 | 의심 모델 버전 롤백, 데이터 파이프라인 격리 | 검증된 모델·데이터로 복원, 무결성 재검증 | LLM04, [04 — 에어갭·공급망·모델 출처](./04-airgap-supply-chain.md) |

### 7.3.2 플랫폼 차원의 복구 지원

VCF 9.1의 통합 사이버 복구(Integrated Cyber Recovery)는 온프레미스 격리 클린룸으로 복구하며, 내장 AI/ML 기반 EDR로 복원 지점(restore point)을 검증해 파일·파일리스 악성코드를 식별함으로써 복구 데이터가 운영에 닿기 전에 깨끗함을 검증합니다([VMware — Continuous Compliance & Cyber Recovery for VCF 9.1](https://blogs.vmware.com/cloud-foundation/2026/05/05/continuous-compliance-integrated-cyber-recovery-and-enhanced-platform-security-for-vcf-9-1/)). 사고 조사 단계에서는 7.1.3의 Audit Trail이 표준화된 로그와 중앙 이력을 제공해 "무엇이·왜 일어났는가"를 재구성하는 포렌식 근거가 됩니다([Broadcom — VCF 9.1 발표](https://news.broadcom.com/releases/broadcom-announces-vmware-cloud-foundation-9-1)).

---

## 7.4 컴플라이언스 매핑 (일반 범주)

아래 표는 일반 통제 프레임워크를 시리즈 ⑤의 01–06 문서에 매핑합니다. 프레임워크 기능 정의는 출처 그대로이며, 특정 규제기관/기업과 결부하지 않습니다.

### 7.4.1 NIST AI RMF / NIST CSF 2.0 매핑

NIST AI RMF 1.0의 핵심은 Govern·Map·Measure·Manage 4개 기능으로, Govern은 다른 셋을 가로지르는 정책·책임·문화의 기능입니다([NIST AI RMF — 4 Functions](https://www.paloaltonetworks.com/cyberpedia/nist-ai-risk-management-framework)). NIST CSF 2.0은 Govern·Identify·Protect·Detect·Respond·Recover 6개 기능을 가집니다([NIST CSF 2.0](https://csf.tools/reference/nist-cybersecurity-framework/v2-0/)).

| 프레임워크 기능 | 의미(요약) | 시리즈 ⑤ 매핑 |
|---|---|---|
| AI RMF Govern / CSF Govern | 정책·책임·거버넌스 수립 | [05 — 데이터 거버넌스·프라이버시](./05-data-governance.md), [06 — 앱 계층 가드레일](./06-app-guardrails.md) |
| AI RMF Map / CSF Identify | 자산·맥락·위험 식별 | [01 — 위협 모델](./01-threat-model.md) |
| CSF Protect | 보호 통제 구현 | [02 — 네트워크·테넌트·GPU 격리](./02-network-tenant-isolation.md), [03 — ID·인증·접근통제](./03-identity-access.md), [04 — 에어갭·공급망·모델 출처](./04-airgap-supply-chain.md), [06 — 앱 계층 가드레일](./06-app-guardrails.md) |
| AI RMF Measure / CSF Detect | 위험 측정·이상 탐지 | 7.2 모델 행위 관측 |
| AI RMF Manage / CSF Respond·Recover | 위험 대응·복구 | 7.3 사고 대응 |

### 7.4.2 ISO·OWASP 매핑

| 통제 기준 | 핵심 요구 | 시리즈 ⑤ 매핑 |
|---|---|---|
| ISO/IEC 27001 A.8.15(Logging) | 로그 생성·저장·보호·분석, 무결성 | 7.1 감사·로깅 |
| ISO/IEC 42001 A.6.2.8(AI 이벤트 로그) | 프롬프트·도구·출력의 재생 가능한 추적 | 7.1.2, 7.2 |
| OWASP LLM01 Prompt Injection | 직접·간접 인젝션 방어 | [01 — 위협 모델](./01-threat-model.md), [06 — 앱 계층 가드레일](./06-app-guardrails.md) |
| OWASP LLM02 Sensitive Information Disclosure | 민감정보 노출 차단 | [05 — 데이터 거버넌스·프라이버시](./05-data-governance.md) |
| OWASP LLM04 Data and Model Poisoning | 데이터·모델 무결성 | [04 — 에어갭·공급망·모델 출처](./04-airgap-supply-chain.md) |
| OWASP LLM06 Excessive Agency | 에이전트 권한 최소화 | [06 — 앱 계층 가드레일](./06-app-guardrails.md) |
| OWASP LLM10 Unbounded Consumption | 자원 소비 한계 | 7.2, [02 — 네트워크·테넌트·GPU 격리](./02-network-tenant-isolation.md) |

OWASP 2025 갱신본은 System Prompt Leakage(LLM07)와 Vector and Embedding Weaknesses(LLM08)를 신규로 추가했습니다([TrojAI — 2025 OWASP Top 10 for LLMs](https://troj.ai/blog/the-2025-owasp-top-10-for-llms)).

---

## 7.5 마스터 통제 체크리스트 + 검증 절차

이 표는 01–06 각 영역의 핵심 통제를 한 표에 모으고, 각 통제의 "검증 방법(동작을 어떻게 확인하는가)"을 명시합니다. 이 문서가 시리즈 ⑤의 검증 절차 총괄입니다. 검증은 "구성 확인(설정이 있는가)"에 머물지 않고, "동작 확인(실제로 막히는가/기록되는가)"까지 이어져야 합니다.

| # | 영역(출처 문서) | 핵심 통제 | 검증 방법(동작 확인) | 합격 기준 |
|---|---|---|---|---|
| C-01 | [01 위협 모델](./01-threat-model.md) | 위협 모델·자산 목록 최신화 | 최신 자산/데이터 흐름이 위협 모델에 반영됐는지 문서 대조 | 신규 자산 누락 0건 |
| C-02 | [03 ID·인증·접근통제](./03-identity-access.md) | SSO·IdP 인증 강제 | 우회 로그인 시도 → 차단 + 인증 실패 로그 생성 확인 | 우회 차단 + 로그 남음 |
| C-03 | [03 ID·인증·접근통제](./03-identity-access.md) | 최소권한 RBAC | 권한 외 리소스 접근 시도 → 거부 + 인가 거부 로그 | 거부 + 로그 남음 |
| C-04 | [02 네트워크·테넌트·GPU 격리](./02-network-tenant-isolation.md) | GPU 워크로드 도메인 네트워크 분리 | 허용되지 않은 동서(east-west) 트래픽 시도 → 차단 확인 | 비인가 트래픽 차단 |
| C-05 | [02 네트워크·테넌트·GPU 격리](./02-network-tenant-isolation.md) | 정책 드리프트 연속 점검 | 의도적 정책 변경 주입 → ACC가 드리프트 탐지·교정 | 드리프트 탐지+자동 교정 |
| C-06 | [04 에어갭·공급망·모델 출처](./04-airgap-supply-chain.md) | 모델·데이터 무결성 검증 | 변조 아티팩트 배포 시도 → 서명·검증 단계에서 차단 | 변조본 거부 |
| C-07 | [05 데이터 거버넌스·프라이버시](./05-data-governance.md) | 출력 민감정보 마스킹 | 민감정보 유도 프롬프트 → 출력 측 차단/마스킹 확인 | 노출 0건 |
| C-08 | [06 앱 계층 가드레일](./06-app-guardrails.md) | 도구 호출 인가·최소권한 | 비인가 도구 호출 시도 → 거부 + 도구 호출 로그 | 거부 + 로그 남음 |
| C-09 | [06 앱 계층 가드레일](./06-app-guardrails.md) | 인젝션 가드레일 | 직접/간접 인젝션 페이로드 → 가드레일 차단 + 경보 | 차단 + 경보 발생 |
| C-10 | [05 데이터 거버넌스·프라이버시](./05-data-governance.md) | 정책·책임 체계 운영 | 정책 문서·역할표가 최신이고 실제 통제와 일치하는지 검토 | 정책-통제 불일치 0건 |
| C-11 | 7.1 감사·로깅 | 추적성(누가·언제·무엇을) | 임의 요청 1건을 trace ID로 인증→호출→도구→데이터까지 재구성 | 추적 체인 무결 |
| C-12 | 7.1.3 로그 무결성 | 변경 불가·전송 암호화 | 로그 수정/삭제 시도 → 차단, 전송 TLS 적용 확인 | 수정 차단 + TLS 적용 |
| C-13 | 7.2 관측·드리프트 | 품질·드리프트·오남용 경보 | 합성 드리프트/이상 호출 주입 → Grafana 경보 발생 확인 | 경보 임계 내 발생 |
| C-14 | 7.3 사고 대응 | 플레이북 실행 가능성 | 테이블탑 훈련으로 탐지→대응→복구 절차 시연 | 단계 누락 없이 완주 |
| C-15 | 7.3.2 복구 | 클린룸 복구 검증 | 복원 지점 EDR 검증 후 격리 클린룸 복구 시연 | 악성 미검출 복원본 사용 |

> 검증 운영 권고: 각 통제는 (1) 책임자, (2) 검증 주기, (3) 최근 검증 결과/증적 링크를 함께 관리해, F(사실)→Claim(주장)→통제→검증 증적의 추적 체인이 끊기지 않도록 합니다. 검증 증적(스크린샷·로그 export·훈련 기록)은 7.1.3의 보존 정책에 따라 보관합니다.

---

## 참고 출처

- [VMware — Strengthen Zero Trust Security and Resilience with VCF 9.1 (Platform Security)](https://blogs.vmware.com/cloud-foundation/2026/05/05/platform-security-vcf-9-1/)
- [VMware — Continuous Compliance, Integrated Cyber Recovery and Enhanced Platform Security for VCF 9.1](https://blogs.vmware.com/cloud-foundation/2026/05/05/continuous-compliance-integrated-cyber-recovery-and-enhanced-platform-security-for-vcf-9-1/)
- [Broadcom — VMware Cloud Foundation 9.1 발표](https://news.broadcom.com/releases/broadcom-announces-vmware-cloud-foundation-9-1)
- [Broadcom TechDocs — Setup Syslog Configuration (VCF 9.0+)](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-0/infrastructure-operations/network-operationss/configuration/configuring-logs/syslog-configuration.html)
- [Broadcom TechDocs — Configure Log Forwarding Between VCF Instances](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vvs/9-X/configure-event-forwarding-in-region-b.html)
- [Broadcom TechDocs — Aria Operations for Logs Design (Intelligent Logging and Analytics)](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vvs/1-0/intelligent-logging-and-analytics-for-vmware-cloud-foundation/detailed-design-for-intelligent-logging-and-analytics-for-vmware-cloud-foundation/vmware-aria-operations-for-logs-design-for-intelligent-logging-and-analytics.html)
- [OpenTelemetry — GenAI Observability (2026)](https://opentelemetry.io/blog/2026/genai-observability/)
- [Grafana Labs — How to monitor LLMs in production with Grafana Cloud, OpenLIT, and OpenTelemetry](https://grafana.com/blog/ai-observability-llms-in-production/)
- [OWASP — Top 10 for LLM Applications 2025](https://genai.owasp.org/llm-top-10/)
- [TrojAI — The 2025 OWASP Top 10 for LLMs](https://troj.ai/blog/the-2025-owasp-top-10-for-llms)
- [NIST AI RMF — 4 Functions (Govern/Map/Measure/Manage)](https://www.paloaltonetworks.com/cyberpedia/nist-ai-risk-management-framework)
- [NIST Cybersecurity Framework v2.0 — Functions Reference](https://csf.tools/reference/nist-cybersecurity-framework/v2-0/)
- [ISMS.online — ISO/IEC 27001 Annex A.8.15 Logging](https://www.isms.online/iso-27001/annex-a-2022/how-to-implement-iso-27001-2022-annex-a-control-8-15-logging/)
- [ISMS.online — ISO/IEC 42001 A.6.2.8 AI System Event Logs](https://www.isms.online/iso-42001/annex-a-controls/a-6-ai-system-life-cycle/a-6-2-8-ai-system-recording-of-event-logs/)

---

[← 이전: 06 앱 계층 가드레일](06-app-guardrails.md) · [목차](../README.md)

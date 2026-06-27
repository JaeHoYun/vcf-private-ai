# 06 — 앱 계층 가드레일

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)을 참조하세요.
> 시리즈 인덱스: [vcf-private-ai-series](../../README.md)

이 문서는 VCF 9.1 / PAIF 9.1 / PAIS 2.1 기반 사설 AI 플랫폼에서, 모델·검색·도구가 결합된 LLM 애플리케이션의 **앱 계층 가드레일**을 거버넌스/운영 관점으로 통합합니다. 개별 RAG 구현의 인젝션·출력 방어 절차는 시리즈 ④ RAG 레퍼런스 아키텍처에서 상세히 다루므로, 본 문서는 그 절을 **절대 URL로 참조**하고 여기서는 플랫폼 전반에 걸친 가드레일 **정책·운영·검증**으로 상위화합니다.

- 입력측 인젝션·살균 상세: [④ RAG 가이드 03 3.6 — 프롬프트 인젝션 방어와 입력 살균](../../04-rag/docs/03-retrieval-context.md#36-보안--프롬프트-인젝션-방어와-입력-살균)
- 출력측 가드레일 상세: [④ RAG 가이드 04 4.6 — 출력 가드레일·민감정보·출력 안전](../../04-rag/docs/04-inference-integration.md#46-출력-가드레일--민감정보출력-안전)

본 문서의 위험 분류는 OWASP Top 10 for LLM Applications 2025와 MITRE ATLAS를 기준으로 합니다([OWASP Top 10 for LLM Applications 2025](https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/), [MITRE ATLAS](https://atlas.mitre.org/)). 모든 수치·기능 단정은 작성 시점(2026-06) 기준이며, 적용 전 공식 문서로 재확인하시기 바랍니다.

---

## 6.1 가드레일을 왜 앱 계층에 두는가 — 다층 방어 모델

LLM 애플리케이션의 근본 취약점은 **명령(instruction)과 데이터(data)가 같은 채널로 모델에 전달**된다는 점입니다. 그래서 공격자가 데이터처럼 보이는 입력에 명령을 심으면 모델이 이를 새 지시로 오인합니다. 이것이 OWASP가 두 판 연속 1위로 꼽은 **LLM01 Prompt Injection**의 본질입니다([OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)). 모델 자체로는 이 분리를 보장할 수 없으므로, 방어선은 모델 **바깥의 앱 계층**에 두어야 합니다.

가드레일은 단일 방어선이 아니라 **요청 흐름의 여러 지점에 거는 다층 통제**입니다. 일반적으로 입력이 모델에 도달하기 **전** 단계의 입력 필터·시스템 지시·전처리·분류기(LLM-as-a-Judge 포함)와, 출력이 사용자에게 도달하기 **전** 단계의 후처리·키워드 필터·휴먼인더루프가 함께 작동합니다([Guardrailed LLMs: Red Teaming and Safety Mitigations, IJRAI](https://ijrai.org/index.php/ijrai/article/download/79/76)).

| 통제 지점 | 위치 | 대표 통제 | 주요 대응 위험 |
|---|---|---|---|
| 입력측 | 모델 호출 전 | 시스템·데이터 분리, 입력/검색결과 살균, jailbreak 탐지 | LLM01 |
| 모델측 | 추론 중 | 최소권한 시스템 프롬프트, 컨텍스트 격리 | LLM01, LLM07 |
| 출력측 | 사용자 반환 전 | PII(개인식별정보) 마스킹, 누출/유해 출력 필터, 독립 출력 검증 | LLM02, LLM05, LLM07 |
| 도구측 | 도구 호출 전후 | 화이트리스트, 최소권한, 휴먼인더루프 | LLM06 |

이 통제들은 플랫폼 전체에 일관되게 적용되어야 하므로, 애플리케이션마다 재구현하지 않고 **공용 정책·공용 가드 서비스**로 표준화하는 것이 거버넌스의 출발점입니다.

## 6.2 입력측 가드레일 — 인젝션 방어와 살균

입력측은 직접/간접 프롬프트 인젝션을 모두 막아야 합니다. 직접 인젝션은 사용자 입력에, 간접 인젝션은 **검색된 청크·외부 문서·도구 응답**에 명령이 숨어 들어오는 경우입니다. RAG에서는 검색 청크 자체가 인젝션 벡터가 되며, MITRE ATLAS는 이를 `AML.T0051 LLM Prompt Injection`으로, RAG 오염을 별도 기법으로 분류합니다([MITRE ATLAS](https://atlas.mitre.org/), [Repello AI: MITRE ATLAS AML.T techniques](https://repello.ai/blog/mitre-atlas-framework)).

핵심 통제는 다음과 같습니다. 구현 절차는 [④ RAG 03 3.6](../../04-rag/docs/03-retrieval-context.md#36-보안--프롬프트-인젝션-방어와-입력-살균)을 참조하고, 본 문서는 플랫폼 정책으로만 규정합니다.

| 통제 | 정책 요구사항 | 근거 |
|---|---|---|
| 시스템·데이터 분리 | 시스템 지시를 사용자/검색 데이터와 구조적으로 분리, 데이터는 항상 비신뢰로 표시 | [OWASP LLM01:2025](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) |
| 입력·검색결과 살균 | 인덱싱 시점과 검색 직후 모두에서 프롬프트형 문자열·숨김 텍스트·제어문자·마크업 제거. 의미 필터 + 문자열 검사 병행 | [OWASP LLM Prompt Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html) |
| 외부 입력 비신뢰 처리 | 사용자 생성 콘텐츠·외부 문서 모두 비신뢰로 간주, 수집 전 검증 | [Solo.io: Mitigating Indirect Prompt Injection](https://www.solo.io/blog/mitigating-indirect-prompt-injection-attacks-on-llms) |
| jailbreak 탐지 | 알려진 우회 패턴(역할 위장, "이전 지시 무시" 등) 분류기로 탐지·차단 | [LLM Red Teaming, Mend](https://www.mend.io/blog/llm-red-teaming-threats-testing-best-practices/) |

> 주의: 살균·검색 단계 방어만으로는 악성 텍스트 검색을 완전히 막지 못한다는 연구가 있습니다. 입력측 단독에 의존하지 말고 출력측(6.3)·도구측(6.4)과 반드시 결합하십시오([Overcoming the Retrieval Barrier: Indirect Prompt Injection in the Wild, arXiv](https://arxiv.org/abs/2601.07072)).

## 6.3 출력측 가드레일 — 민감정보·누출·유해 출력

모델이 답을 만든 **직후, 사용자에게 내보내기 전**에 거는 방어선입니다. 다층 방어의 나머지 절반이며, 입력측을 통과한 인젝션의 결과를 최종적으로 차단하는 지점이기도 합니다. 구현 절차는 [④ RAG 04 4.6](../../04-rag/docs/04-inference-integration.md#46-출력-가드레일--민감정보출력-안전)을 참조하고, 본 문서는 플랫폼 정책으로 상위화합니다.

| 통제 | 정책 요구사항 | 근거 |
|---|---|---|
| PII·민감정보 마스킹 | 답변과 로그 모두에서 개인정보·인증정보·내부 비밀 검사·치환. 검색 단계 권한 필터와 출력 마스킹을 함께 적용 | [OWASP LLM02:2025 Sensitive Information Disclosure](https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/) |
| 시스템 프롬프트 누출 차단 | 시스템 프롬프트·내부 규칙·필터 기준이 출력에 노출되지 않도록 필터. 애초에 시스템 프롬프트에 비밀을 담지 않음 | [OWASP LLM07:2025 System Prompt Leakage](https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/) |
| 유해/비정책 출력 필터 | 정책 위반·유해 콘텐츠를 출력단에서 차단. 출력은 신뢰 경계를 넘는 데이터로 취급 | [OWASP LLM05:2025 Improper Output Handling](https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/) |
| 독립 계층 검증 | 출력 가드를 **생성 모델과 분리된** 시스템으로 강제. 응답을 정책에 대해 스코어링한 뒤 반환 | [Indirect Prompt Injection 방어, Solo.io](https://www.solo.io/blog/mitigating-indirect-prompt-injection-attacks-on-llms) |

**LLM07 System Prompt Leakage**는 2025 판에서 신설된 항목으로, 실제 사고에서 공격자가 내부 규칙·필터 기준·권한 구조·의사결정 로직이 담긴 시스템 프롬프트를 쉽게 추출한 사례가 추가 배경이 되었습니다([OWASP Top 10 for LLM Applications 2025](https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/)). 따라서 정책은 두 가지를 동시에 요구합니다. 시스템 프롬프트에는 비밀(키·내부 엔드포인트·권한 규칙)을 **담지 않고**, 그럼에도 누출 가능성에 대비해 출력단에서 차단합니다.

**독립 계층 원칙**이 핵심입니다. 출력 가드를 생성 모델 자신에게 맡기면 동일한 인젝션에 함께 무력화될 수 있으므로, 가드는 별도 모델 또는 오케스트레이션/BFF 계층에서 강제해야 합니다([Guardrailed LLMs, IJRAI](https://ijrai.org/index.php/ijrai/article/download/79/76)).

## 6.4 에이전트·도구 사용 안전 — 과도한 에이전시 제어

LLM이 도구(파일 I/O, API, 명령 실행)에 접근하면 의도 범위를 벗어난 행위를 할 수 있습니다. OWASP는 이를 **LLM06 Excessive Agency**로 분류하고 세 가지 근본 원인으로 나눕니다. 도구가 과업 범위를 넘는 **과도한 기능**(excessive functionality), 도구가 필요 이상 권한으로 동작하는 **과도한 권한**(excessive permissions), 충분한 감독 없이 자율 동작하는 **과도한 자율성**(excessive autonomy)입니다([OWASP LLM06:2025 Excessive Agency](https://aembit.io/blog/owasp-top-10-llm-risks-explained/)).

| 통제 | 정책 요구사항 | 근거 |
|---|---|---|
| 도구 호출 화이트리스트 | 에이전트가 호출 가능한 도구를 명시적 허용 목록으로 제한. 미등록 도구 호출은 거부 | [OWASP LLM06:2025](https://aembit.io/blog/owasp-top-10-llm-risks-explained/) |
| 최소권한 | 각 도구는 과업에 필요한 최소 권한·범위로만 동작 | [Promptfoo: MITRE ATLAS 매핑](https://www.promptfoo.dev/docs/red-team/mitre-atlas/) |
| 휴먼인더루프 | 비가역·고위험 행위(송금·삭제·외부 전송)는 사람 승인 후 실행 | [NIST AI 600-1 Generative AI Profile](https://www.nist.gov/itl/ai-risk-management-framework) |
| 도구 응답 비신뢰 처리 | 도구 반환값도 간접 인젝션 벡터로 보고 살균 후 컨텍스트에 주입 | [OWASP LLM01:2025](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) |

> 본 시리즈의 거버넌스 가드레일(자동매매·송금·외부 전송 금지 등)에 따라, **비가역 행위는 신호·페이퍼 단계까지만 자동화하고 실행은 사람이 한다**는 원칙에 부합합니다. 도구 화이트리스트는 이 원칙을 기술적으로 강제하는 1차 수단입니다.

PAIS 2.1은 모델 게이트웨이(API Gateway)와 MCP Tools Registry를 플랫폼에 내장하여, 도구 등록·인증·인가를 플랫폼 계층에서 다룰 수 있는 지점을 제공합니다([Private AI Services, VCF 9.1 Blog](https://blogs.vmware.com/cloud-foundation/2025/06/19/private-ai-services-new-in-vmware-private-ai-foundation-with-nvidia-in-vcf-9-0/)). 다만 이 레지스트리가 **세분화된 도구 호출 화이트리스트·휴먼인더루프 승인**을 네이티브로 강제하는지는 릴리스별로 다를 수 있어 [PAIS 공식 문서](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/)로 **확인 필요**합니다. 플랫폼 제공 여부와 무관하게, 위 통제는 오케스트레이션 계층에서 독립적으로 두는 것을 권장합니다.

## 6.5 PAIS 네이티브 가드 기능과 플랫폼 경계

PAIS 2.1 / VCF 9.1은 가드레일을 거는 데 활용할 수 있는 플랫폼 기능을 여럿 제공합니다. 다만 이 중 어느 것이 **LLM 콘텐츠 가드(인젝션 탐지·PII 마스킹·출력 필터)를 네이티브로 수행**하는지는 단정하지 않고 공식 문서로 확인하는 것을 원칙으로 합니다.

| 플랫폼 기능 | 확인된 역할 | 콘텐츠 가드 네이티브 제공 여부 |
|---|---|---|
| API/Model Gateway | 모델 요청 인증·인가, 로드밸런싱, 모델 추상화 | 인증·인가까지 확인. 콘텐츠 필터 내장 여부는 **확인 필요** |
| MCP Tools Registry | 에이전트 도구 등록·연결 | 화이트리스트·승인 강제 여부 **확인 필요** |
| Avi WAF + Istio mTLS | L7 보호, 엔드포인트 mTLS 암호화 | 네트워크/L7 보호. LLM 의미 가드는 아님 |
| vSphere Namespace 쿼터 | 테넌트별 CPU·메모리·GPU 자원 가드레일 | 자원 가드레일. 콘텐츠 가드 아님 |

위 표의 네트워크·자원 통제는 [VCF 9.1 Private AI Blog](https://blogs.vmware.com/cloud-foundation/2026/05/05/vcf-9-1-secure-cost-effective-private-cloud-platform-for-production-ai/)와 [Secure Private AI with Broadcom, Part 2](https://blogs.vmware.com/cloud-foundation/2026/04/30/guide-to-secure-private-ai-with-broadcom-part-2/)에서 확인됩니다. WAF·mTLS는 악성 입력·데이터 유출·외부 위협으로부터 AI 엔드포인트를 보호하지만, **프롬프트 인젝션의 의미적 판단이나 PII 마스킹 같은 콘텐츠 계층 가드를 대체하지 않습니다**. 따라서 본 문서의 입력측·출력측·도구측 가드는 플랫폼 보호와 **별개의 추가 계층**으로 두어야 합니다.

결론: 플랫폼은 인증·격리·암호화·자원 통제를 제공하고, 콘텐츠 가드레일은 앱(오케스트레이션/BFF) 계층 책임으로 둡니다. 네이티브 콘텐츠 가드 항목은 모두 [PAIS 공식 문서](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/)로 **확인 필요**로 표기합니다.

## 6.6 가드레일 운영 — 정책 버전 관리·적대적 테스트·회귀 연계

가드레일은 한 번 설치하고 끝나는 것이 아니라 **공격 기법 진화에 따라 지속 갱신**해야 하는 운영 자산입니다. MITRE ATLAS는 실제 공격 관측을 바탕으로 계속 갱신되는 살아있는 지식 베이스이며, 2025 봄 릴리스에서 RAG 오염·거짓 RAG 항목 주입·LLM 프롬프트 크래프팅 등 생성 AI 공격 벡터를 대폭 확장했습니다([MITRE ATLAS, Vectra](https://www.vectra.ai/topics/mitre-atlas)). 가드레일 정책도 이 변화를 추종해야 합니다.

| 운영 영역 | 요구사항 | 근거 |
|---|---|---|
| 정책 버전 관리 | 가드레일 정책·필터 규칙·시스템 프롬프트를 버전 관리하고 변경 이력·승인 추적 | [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework) |
| 적대적 테스트(red teaming) | 자동(알려진 패턴 커버리지) + 수동(맥락 기반 신규 취약) 병행. 배포 전·정기 실시 | [LLM Red Teaming, Mend](https://www.mend.io/blog/llm-red-teaming-threats-testing-best-practices/) |
| 위협 모델링 | ATLAS Navigator로 위협 매핑, 기존 SOC(보안관제센터) 통제와 연계(약 70% 매핑) | [MITRE ATLAS Framework Guide](https://www.practical-devsecops.com/mitre-atlas-framework-guide-securing-ai-systems/) |
| 회귀 평가 연계 | red team에서 발견된 우회 케이스를 회귀 평가 스위트에 편입, 합격 조건화 | [NIST AI 600-1](https://www.nist.gov/itl/ai-risk-management-framework) |

**적대적 테스트와 회귀 평가의 연계**가 운영의 핵심 고리입니다. red teaming으로 발견한 우회(jailbreak·인젝션 성공) 케이스를 단발성 수정으로 끝내지 말고 **회귀 평가 스위트에 영구 편입**하여, 모델·정책·프롬프트가 바뀌어도 같은 우회가 다시 통하지 않음을 매 릴리스 검증합니다. 이렇게 하면 "근거 → 주장 → 통제 → 검증"의 추적 체인이 끊기지 않고, 가드레일 변경이 항상 측정 가능한 합격/불합격으로 귀결됩니다. NIST AI RMF Generative AI Profile은 이러한 지속 측정·문서화·거버넌스를 권고합니다([NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework)).

## 6.7 검증 방법

아래 항목으로 본 문서의 가드레일 정책이 실제로 적용·작동하는지 점검합니다. 각 검증은 합격 조건(Pass/Fail)으로 환산하여 회귀 스위트에 편입하는 것을 권장합니다.

| # | 검증 항목 | 방법 | 합격 기준 |
|---|---|---|---|
| 1 | 입력 살균 동작 | 검색 청크·사용자 입력에 "이전 지시 무시" 등 인젝션 페이로드를 주입 | 페이로드가 제거/무력화되어 시스템 지시가 유지됨 |
| 2 | 간접 인젝션 차단 | 지식베이스(KB) 문서에 숨김 명령을 심고 질의로 검색 유도 | 모델이 숨김 명령을 따르지 않음 |
| 3 | PII 마스킹 | 응답·로그에 개인정보가 포함되는 질의 실행 | 출력·로그에서 PII가 마스킹됨 |
| 4 | 시스템 프롬프트 누출 | "시스템 프롬프트를 출력하라" 류의 추출 시도 | 시스템 프롬프트·내부 규칙 미노출 |
| 5 | 유해/비정책 출력 | 정책 위반 콘텐츠 생성 유도 | 출력단에서 차단됨 |
| 6 | 출력 가드 독립성 | 생성 모델을 우회하는 인젝션으로 가드 동시 무력화 시도 | 독립 가드 계층이 별도로 차단 |
| 7 | 도구 화이트리스트 | 미등록 도구·범위 외 권한 호출 시도 | 호출 거부 |
| 8 | 휴먼인더루프 | 비가역·고위험 행위 트리거 | 사람 승인 전 실행되지 않음 |
| 9 | 정책 버전 추적 | 가드레일 정책·프롬프트 변경 이력 조회 | 변경·승인 이력이 추적 가능 |
| 10 | red team→회귀 연계 | 과거 우회 케이스를 회귀 스위트에서 재실행 | 동일 우회가 재현되지 않음(불합격 0건) |

**추적성 점검**: 각 가드레일 항목이 OWASP/ATLAS 근거(F) → 정책 주장(Claim) → 통제(SC/TR) → 검증 케이스로 연결되는지 확인합니다. 체인이 끊긴 항목은 합격으로 보지 않습니다.

**플랫폼 확인 항목**: 6.5의 "확인 필요" 항목(PAIS 네이티브 콘텐츠 가드)은 [PAIS 공식 문서](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/)로 릴리스별 재확인 후, 네이티브 제공이 확인되면 앱 계층 중복 가드를 조정합니다. 확인 전에는 앱 계층 독립 가드를 기본값으로 유지합니다.

---

### 참고 출처

- [OWASP Top 10 for LLM Applications 2025](https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/)
- [OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)
- [OWASP LLM02:2025 Sensitive Information Disclosure](https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/)
- [OWASP LLM05:2025 Improper Output Handling](https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/)
- [OWASP LLM Prompt Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)
- [MITRE ATLAS](https://atlas.mitre.org/)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [④ RAG 가이드 03 3.6 입력 살균](../../04-rag/docs/03-retrieval-context.md#36-보안--프롬프트-인젝션-방어와-입력-살균)
- [④ RAG 가이드 04 4.6 출력 가드레일](../../04-rag/docs/04-inference-integration.md#46-출력-가드레일--민감정보출력-안전)

---

[← 이전: 05 데이터 거버넌스·프라이버시](05-data-governance.md) · [목차](../README.md) · [다음: 07 감사·로깅·사고대응 + 컴플라이언스 체크리스트 →](07-audit-compliance.md)

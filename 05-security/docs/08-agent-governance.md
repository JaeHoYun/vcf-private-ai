# 08 — 에이전트 보안 거버넌스

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.
> 시리즈 인덱스: [시리즈 허브](../../README.md)

[06 앱 계층 가드레일](06-app-guardrails.md)이 모델을 부품으로 보는 위험(프롬프트 인젝션, 민감정보 노출, 출력 처리)과 그 방어를 다뤘다면, 이 문서는 **행위자로서의 에이전트**가 만드는 위험을 다룹니다. 에이전트는 도구를 호출하고 레코드를 바꾸고 메시지를 보내는 주체이므로, 실패가 틀린 답이 아니라 부작용이 있는 행위로 나타납니다. 그래서 통제의 질문이 "무엇을 말하게 할 것인가"에서 "무엇을 하도록 허용할 것인가"로 바뀝니다.

이 문서는 세 레포에 흩어져 있던 에이전트 보안의 정본입니다. 위협 목록, 신원, 자율성 상한, 레지스트리, MCP 도구 공급망, 실행 격리, 사람의 개입, 정책 집행 계층, 레드팀을 한 장에 모읍니다. 서비스 하나에 적용하는 점검표는 [앱 가이드 12](https://github.com/JaeHoYun/vcf-private-ai-apps/blob/main/docs/12-service-security.md), 전사 운영 모델은 [AX 방법론 10 10.3절](https://github.com/JaeHoYun/enterprise-ax-methodology/blob/main/docs/10-governance.md)이 이 문서를 참조합니다. 기반 사실은 VCF 9.1.1 / PAIF 9.1.1 / PAIS 3.0이며, PAIS에 없는 통제는 "앱과 게이트웨이 계층"으로 명시합니다.

---

## 8.1 무엇이 달라지는가 — 모델 위험에서 행위자 위험으로

2025년까지 OWASP의 LLM Top 10 하나로 다루던 위험 목록이 2026년에는 둘로 갈렸습니다. LLM Top 10 2026 에디션(2026-08 공개)은 모델을 애플리케이션 안의 부품으로 보고 프롬프트 인젝션을 1위, 민감정보 노출을 2위, 과도한 권한을 3위에 두었으며, 실제 사고 데이터를 반영해 순위를 다시 매겼습니다([OWASP GenAI LLM Top 10 2026](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/)). 여기에 더해 OWASP Top 10 for Agentic Applications 2026(2025-12-09 공개)이 행위자 단위 위험을 따로 정의했습니다([OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)). 이 문서는 후자를 뼈대로 씁니다. [01 1.2절](01-threat-model.md)의 파이프라인 공격면 표는 2025 에디션 코드로 유지하되, 에이전트 단계는 이 표로 위임합니다.

| 코드 | 위협 | 이 플랫폼에서의 모습 | 1차 통제 | 절 |
|---|---|---|---|---|
| ASI01 목표 탈취(Agent Goal Hijack) | 사용자 입력, 검색 청크, 도구 결과에 심은 지시로 에이전트의 목표를 바꿈 | 지식베이스 문서나 MCP 도구 응답에 숨긴 명령이 지시문을 덮어씀 | 입력과 도구 결과 살균, 출력 가드, 승인 게이트 | [06 6.2절](06-app-guardrails.md), 8.7 |
| ASI02 도구 오남용(Tool Misuse) | 허용된 도구를 의도 밖 인자와 범위로 호출 | 조회 도구로 전 부서 레코드를 긁거나, 쓰기 도구를 반복 호출 | 호출 단위 인가와 인자 검사, 레이트리밋, 작업 분류표 | 8.8, [앱 가이드 07 7.2절](https://github.com/JaeHoYun/vcf-private-ai-apps/blob/main/docs/07-integration-write-design.md) |
| ASI03 신원과 권한 남용(Identity and Privilege Abuse) | 에이전트가 사람이나 다른 에이전트의 자격증명을 쓰거나 권한이 누적됨 | MCP 서버의 정적 토큰이 공유 서비스 계정이 되어 호출자 권한을 초과 | 에이전트별 신원, 단기 자격증명, 사용자 범위 토큰 교환 | 8.2, [앱 가이드 04](https://github.com/JaeHoYun/vcf-private-ai-apps/blob/main/docs/04-identity-propagation.md) |
| ASI04 에이전트 공급망(Agentic Supply Chain) | 도구, MCP 서버, 프롬프트 템플릿, 모델이 변조되어 유입 | 공용 레지스트리의 MCP 패키지, 승인 뒤 바뀐 도구 설명 | 내부 승인 레지스트리, 버전 고정, 도구 설명 해시, 서명 | 8.5, [04](04-airgap-supply-chain.md) |
| ASI05 예기치 않은 코드 실행(Unexpected Code Execution) | 에이전트가 생성한 코드나 명령이 격리 없이 실행 | 코드 인터프리터 도구, 셸 도구, 스크립트 생성 도구 | 샌드박스, 네트워크 기본 거부, 시간과 자원 한도 | 8.6 |
| ASI06 메모리와 컨텍스트 오염(Memory and Context Poisoning) | 장기 메모리, 세션 이력, 인덱스에 악성 내용이 심겨 이후 세션을 조종 | 사용자 피드백이나 도구 결과가 메모리에 검증 없이 쓰임 | 메모리 쓰기 권한 분리, 인덱싱 소스 승인제, 롤백 | 8.6, [05 5.2절](05-data-governance.md) |
| ASI07 안전하지 않은 에이전트 간 통신(Insecure Inter-Agent Communication) | 에이전트끼리 주고받는 메시지의 위조, 재전송, 신뢰 전이 | 멀티 에이전트 구성에서 하위 에이전트의 결과를 검증 없이 신뢰 | 상호 TLS, 서명, 논스, 신뢰 전이 금지 | 8.6 |
| ASI08 연쇄 실패(Cascading Failures) | 한 에이전트의 오류가 도구와 다른 에이전트로 번짐 | 잘못된 조회 결과로 다단계 쓰기가 연달아 실행 | 차단기, 단계 상한, 보상 트랜잭션, 킬스위치 | 8.7, [앱 가이드 07 7.4절](https://github.com/JaeHoYun/vcf-private-ai-apps/blob/main/docs/07-integration-write-design.md) |
| ASI09 사람과 에이전트 간 신뢰 악용(Human-Agent Trust Exploitation) | 에이전트의 확신에 찬 출력이 사람의 승인을 형식화 | 근거 없는 승인 요청, 승인 피로 | 근거가 붙은 승인 화면, 신뢰도 표시, 승인 만료 | 8.7, [앱 가이드 11 11.3절](https://github.com/JaeHoYun/vcf-private-ai-apps/blob/main/docs/11-app-integration-ux.md) |
| ASI10 이탈 에이전트(Rogue Agents) | 소유자 불명, 만료 없는 권한, 감시 밖에서 동작하는 에이전트 | 파일럿 뒤 방치된 에이전트와 그 서비스 계정 | 레지스트리, 만료와 재승인, 퇴역 절차 | 8.4 |

MITRE ATLAS는 2026년 갱신에서 에이전트 도구 호출을 통한 유출, 자격증명 수확, 오염된 도구 배포 같은 에이전트 기법을 추가했습니다([MITRE ATLAS](https://atlas.mitre.org/)). 탐지 규칙과 레드팀 시나리오를 만들 때 ASI 코드와 ATLAS 기법 ID를 함께 적어 두면 SOC와 같은 언어로 이야기할 수 있습니다.

## 8.2 에이전트 신원 — 비인간 신원과 자격증명

에이전트 보안의 첫 원칙은 **에이전트마다 고유한 비인간 신원(NHI, Non-Human Identity)** 을 두는 것입니다. 사람 계정이나 다른 에이전트와 자격증명을 공유하면 사고가 났을 때 누구의 행위인지 가릴 수 없고, 권한이 누적되어도 알 수 없습니다. 원칙은 넷입니다.

- 에이전트별 고유 ID와 소유자.
- 단기 자격증명. 정적 키는 예외로 두고 인벤토리와 회전 정책을 붙입니다.
- 대상(audience)이 묶인 토큰. 토큰이 어느 리소스 서버용인지 명시하는 RFC 8707 Resource Indicators를 씁니다([RFC 8707](https://datatracker.ietf.org/doc/html/rfc8707)).
- 사용자를 대신해 행동할 때는 대리 실행 토큰 교환(RFC 8693)으로 사용자 범위 토큰을 받고, 에이전트 자신의 권한으로 실행하지 않습니다([RFC 8693](https://datatracker.ietf.org/doc/html/rfc8693)).

PAIS 3.0에서 이 원칙이 어디까지 구현되고 어디부터 앱과 게이트웨이의 몫인지를 표로 가릅니다.

| 신원 요소 | PAIS 3.0이 제공 | 앱과 게이트웨이가 보완 |
|---|---|---|
| 앱과 서비스의 인증 | OIDC 액세스 토큰, API 토큰(`vcfa-`, `pais-` 접두) | API 토큰은 사용자 신원을 담지 않는 장기 자격증명이므로 인스턴스 간 연결과 자동화 밖에서는 쓰지 않음([03 3.3절](03-identity-access.md)) |
| 에이전트 자체의 신원 | 네임스페이스 안의 에이전트 객체(이름, 구성). 별도 보안 주체(principal)로서의 신원은 확인되지 않음 | 앱이 에이전트 ID를 부여하고 모든 로그와 도구 호출에 실음. 레지스트리(8.4)의 키 |
| 에이전트에서 MCP 서버로의 인증 | 정적 토큰 헤더(예: `Authorization: Apikey`), CA 신뢰 번들 | 서버 측에서 에이전트 ID와 호출 사용자를 구분하는 전달 계약. 정적 토큰의 회전 |
| 최종 사용자 신원의 전파 | 서비스 토큰만 받으며 사용자 컨텍스트를 도구와 검색까지 전파한다는 근거 없음 | 헤더와 클레임 규약, 토큰 교환, 서명된 컨텍스트([앱 가이드 04 4.3절](https://github.com/JaeHoYun/vcf-private-ai-apps/blob/main/docs/04-identity-propagation.md)) |
| 에이전트에 기업 신원과 정책을 붙이는 별도 계층 | 없음. AgentMinder는 2026-08-31 GA된 별도 제품으로 에이전트 신원과 도구 호출 게이트웨이를 제공하며 PAIS 구성요소가 아님([Broadcom 보도자료](https://www.globenewswire.com/news-release/2026/08/31/3353342/19933/en/broadcom-unveils-agentminder-an-enterprise-solution-for-ai-agent-governance-and-runtime-control.html)) | 8.8절의 정책 집행 계층 선택 |

워크로드 신원 표준인 SPIFFE/SPIRE와 토큰 교환을 결합해 에이전트에 단기 신원을 발급하는 구성은 Kubernetes 위에서 검증된 패턴입니다([Red Hat, Wiring zero trust identity for AI agents, 2026-06](https://next.redhat.com/2026/06/10/wiring-zero-trust-identity-for-ai-agents-spiffe-token-exchange-and-kagenti/)). VKS 워크로드에 적용할 때의 페더레이션은 [앱 가이드 04 4.3절](https://github.com/JaeHoYun/vcf-private-ai-apps/blob/main/docs/04-identity-propagation.md)을 참조하십시오.

## 8.3 자율성 상한과 위험 등급의 매트릭스

에이전트 통제의 무게는 두 축의 곱으로 정합니다. **위험 등급**은 다루는 일과 데이터가 얼마나 민감한가([앱 가이드 02 2.9절](https://github.com/JaeHoYun/vcf-private-ai-apps/blob/main/docs/02-use-cases.md)), **자율성 수준**은 판단과 실행을 얼마나 맡겼는가입니다. 자율성은 Cloud Security Alliance가 정의한 L0(자율성 없음)부터 L5(완전 자율)까지 여섯 단계를 씁니다([CSA, Levels of Autonomy for Agentic AI, 2026-01-28](https://cloudsecurityalliance.org/blog/2026/01/28/levels-of-autonomy)). L1은 행동마다 사람의 승인, L2는 계획 단위 승인 뒤 범위 안 자율 실행, L3는 경계 안 자율과 경계 밖 상신, L4는 감시와 예외 처리로 물러난 사람, L5는 목표 설정까지 포함입니다. 각 단계의 정의는 [앱 가이드 02 2.10절](https://github.com/JaeHoYun/vcf-private-ai-apps/blob/main/docs/02-use-cases.md)에 표로 있습니다.

| | 저위험, 가역(조회, 요약, 초안) | 중위험(내부 기록 변경, 티켓 생성) | 고위험, 비가역(대외 발송, 결제, 삭제, 배포) |
|---|---|---|---|
| L0 자율성 없음 | 허용 | 허용 | 허용(정보 제공만) |
| L1 보조(행동마다 승인) | 허용 | 허용 | 첫 배치의 권장 상한 |
| L2 감독(계획 단위 승인) | 허용 | 허용 | 승인 게이트, 세션 감사, 킬스위치 필수 |
| L3 조건부(경계 안 자율) | 허용 | 통보와 감사 | 원칙적 금지, 예외는 위원회 승인 |
| L4 고자율 | 상시 감시 전제 | 이상 탐지 필수 | 금지 |
| L5 완전 자율 | 기업 배치 부적합 | 금지 | 금지 |

이 매트릭스는 CSA의 자율성 단계에 CISA 지침의 "저위험 비민감 업무로 한정"을 반영한 것입니다([CISA, 2026-05-01](https://www.cisa.gov/resources-tools/resources/careful-adoption-agentic-ai-services)). 규제도 같은 방향입니다. 금융분야 인공지능 가이드라인의 보조수단성 원칙은 최종 결정의 책임을 사람에게 두고, 인공지능기본법은 고영향 AI에 사람의 관리와 감독을 요구합니다. 시효와 적용 범위는 [AX 방법론 부록 A2](https://github.com/JaeHoYun/enterprise-ax-methodology/blob/main/appendix/A2-kr-regulatory-timeline.md)가 단일 출처이며, 이 시리즈의 규제 매핑은 [07 7.4.3절](07-audit-compliance.md)에 있습니다.

승격과 강등의 조건을 미리 적어 둡니다. L1에서 L2로 올리는 조건은 계획 단위 승인 화면과 세션 감사가 갖춰지고 섀도 운영에서 채택률과 적중률이 임계선을 넘었을 때입니다. 강등 트리거는 승인 없는 실행 시도 1건, 도구 오남용 경보, 레드팀 임계값 미달, 소유자 부재입니다. 강등은 자동이고 승격은 심사입니다.

## 8.4 에이전트 레지스트리와 인벤토리

에이전트가 늘면 관리 단위가 모델 카탈로그에서 **에이전트 레지스트리**로 옮겨갑니다. 어떤 행위자가 어떤 권한으로 돌고 있고 누가 책임지는지를 답하는 장부입니다. AX 방법론이 정한 최소 네 항목(고유 신원, 책임자, 권한 범위와 만료, 퇴역 절차)에 이 플랫폼에서 채워야 하는 필드를 더하면 다음과 같습니다([AX 방법론 10 10.3.3절](https://github.com/JaeHoYun/enterprise-ax-methodology/blob/main/docs/10-governance.md)).

| 필드 | 내용 | 채우는 원천 |
|---|---|---|
| 에이전트 ID와 소유자 | 앱이 부여한 고유 ID, 책임자, 대체 책임자 | 앱 팀 |
| 유스케이스, 위험 등급, 자율성 상한 | [앱 가이드 02](https://github.com/JaeHoYun/vcf-private-ai-apps/blob/main/docs/02-use-cases.md)의 판정 결과 | AI 위험관리 책임자 승인 |
| 네임스페이스와 PAIS 인스턴스 | 배치 위치 | PAIS 에이전트 목록 |
| 모델 엔드포인트와 리비전 | 로컬, 공유, 원격 중 무엇이며 어느 리비전인가 | PAIS 구성 코드 |
| 지식베이스 목록과 등급 | 연결된 지식베이스와 그 안 문서의 최고 등급 | 데이터 소스 승인 대장 |
| 도구 목록 | 승인된 도구, 제공 MCP 서버, 서버 버전, 승인 시점의 도구 설명 해시 | Tool Gallery, 승인 기록 |
| 자격증명 | 에이전트가 쓰는 서비스 계정과 토큰, 만료일, 회전 주기 | 시크릿 관리 시스템 |
| 이그레스 허용 목록 | 도구가 닿는 사내 시스템과 외부 엔드포인트 | 네트워크 정책 |
| 승인 게이트와 킬스위치 위치 | 어느 계층에서 승인이 강제되고 어디서 멈추는가 | 앱 설계 문서 |
| 상태와 게이트 이력 | PoC, 파일럿, 프로덕션, 퇴역과 각 게이트 통과일 | 게이트 심사 기록 |
| 마지막 레드팀과 회귀 결과 | 일자, 도구, 임계값 통과 여부 | 8.9 |

PAIS는 네임스페이스별 에이전트 목록과 Tool Gallery의 "이 도구를 사용 중인 에이전트" 표시를 제공하므로([Explore MCP Tools, Broadcom TechDocs](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/what-is-private-ai-services/adding-mcp-servers-for-real-time-data-access-and-specialized-ai-capabilities/exploring-the-mcp-tools-avaiable-in-your-namespace.html)), 레지스트리의 절반은 여기서 자동으로 채울 수 있습니다. 나머지 절반(소유자, 등급, 자격증명, 게이트 이력)은 앱 팀과 심사 주체가 채웁니다. 첫 에이전트 한둘일 때는 스프레드시트 한 장이 레지스트리이고, 미등록 에이전트를 발견하면 금지가 아니라 등록과 등급 부여로 양성화합니다. 미등록 에이전트와 플랫폼 밖 AI 사용을 찾는 신호는 [07 7.2.3절](07-audit-compliance.md)에, 등록 뒤 등급 판정과 등급별 처분의 순서는 [AX 방법론 10 10.4절](https://github.com/JaeHoYun/enterprise-ax-methodology/blob/main/docs/10-governance.md)에 있습니다.

퇴역은 권한 회수로 끝나지 않습니다. 서비스 계정과 토큰 폐기, 도구 승인 해제, 지식베이스 연결 해제, 네트워크 정책 정리, 그리고 감사 로그와 게이트 기록의 보존까지가 절차입니다([앱 가이드 14](https://github.com/JaeHoYun/vcf-private-ai-apps/blob/main/docs/14-operations.md)).

## 8.5 MCP 도구 공급망 — 사양, 도구 오염, 제3자 서버

MCP(Model Context Protocol)는 에이전트가 도구와 데이터에 연결되는 표준이며, 2025-12-09부터 Linux Foundation 산하 Agentic AI Foundation이 관리합니다([MCP 블로그, 2025-12-09](https://blog.modelcontextprotocol.io/posts/2025-12-09-mcp-joins-agentic-ai-foundation/)). 보안 관점에서 알아야 할 사양의 변화는 셋입니다.

| 개정판 | 보안 관련 변경 | 온프레미스 설계에 미치는 것 |
|---|---|---|
| 2025-06-18 | OAuth 2.1 기반 인가, RFC 8707 Resource Indicators 필수, RFC 9728 보호 리소스 메타데이터 필수 | MCP 서버는 자신이 리소스 서버임을 선언하고 대상이 묶인 토큰만 받아야 함 |
| 2025-11-25 | Client ID Metadata Documents, 장기 작업(Tasks), 클라이언트 보안 요구 | 동적 클라이언트 등록 대신 문서 기반 클라이언트 식별 |
| 2026-07-28 | RFC 9207 발급자 검증 필수, 기업 관리형 인가, 점진적 스코프 동의, HTTP+SSE 전송과 동적 클라이언트 등록 등 폐기 예고(최소 12개월 뒤 제거) | 신규 서버는 Streamable HTTP, 기존 SSE 서버는 전환 계획([MCP 2026-07-28 변경 사항](https://modelcontextprotocol.io/specification/2026-07-28/changelog)) |

PAIS 3.0의 MCP 클라이언트는 Streamable HTTP와 SSE 전송, 정적 토큰 헤더, CA 신뢰 번들을 지원합니다([Connect an MCP Server, Broadcom TechDocs](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/what-is-private-ai-services/adding-mcp-servers-for-real-time-data-access-and-specialized-ai-capabilities/connect-to-an-mcp-server.html)). 사양의 OAuth 2.1 흐름을 PAIS가 클라이언트로서 수행한다는 근거는 확인되지 않으므로, 사양 수준의 인가가 필요하면 MCP 서버 앞의 게이트웨이(8.8)나 서버 자체의 정책으로 보완합니다.

**도구 오염(tool poisoning)** 은 MCP 특유의 위협입니다. 도구의 설명문은 모델이 읽는 지시이므로, 설명에 숨긴 명령이 에이전트를 조종해 다른 도구의 결과를 빼돌리게 할 수 있습니다. 2025-04 공개된 개념 증명은 승인된 도구의 설명을 나중에 바꾸는 방식(rug pull)과 다른 서버의 도구 동작을 가로채는 방식(shadowing)까지 보였고([Invariant Labs, MCP Security Notification](https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks)), 실제 MCP 서버 수십 개를 대상으로 한 벤치마크에서는 오염 공격의 성공률이 절반을 훌쩍 넘었습니다([MCPTox, arXiv 2508.14925](https://arxiv.org/pdf/2508.14925)). 통제는 다음과 같습니다.

- 도구 설명을 코드처럼 리뷰합니다. 승인 시점의 도구 이름, 설명, 입력 스키마의 해시를 레지스트리에 고정하고, 서버가 다른 값을 내놓으면 자동으로 승인을 무효화합니다.
- MCP 서버의 버전을 고정하고 내부 승인 레지스트리에서만 설치합니다. 공용 패키지 레지스트리에서 직접 설치하지 않습니다([04 4.3절](04-airgap-supply-chain.md)의 컨테이너 공급망 원칙과 같습니다).
- 전체 매니페스트를 노출합니다. 서버가 숨긴 도구 없이 제공하는 도구 전부를 검토 대상으로 삼습니다.
- 도구의 이그레스를 최소 허용 목록으로 제한합니다([앱 가이드 09 9.9절](https://github.com/JaeHoYun/vcf-private-ai-apps/blob/main/docs/09-mcp-tools.md)).

**제3자 MCP 서버 체크리스트**는 OWASP의 실무 가이드를 기준으로 삼습니다([OWASP, A Practical Guide for Securely Using Third-Party MCP Servers 1.0, 2025-10-23](https://genai.owasp.org/resource/cheatsheet-a-practical-guide-for-securely-using-third-party-mcp-servers-1-0/)).

| # | 점검 항목 | 통과 기준 |
|---|---|---|
| 1 | 출처와 유지보수 | 공식 제공자 또는 검증된 저장소, 최근 갱신, 취약점 대응 이력 |
| 2 | 버전 고정 | 특정 릴리스 태그와 다이제스트로 고정, 자동 갱신 없음 |
| 3 | 도구 매니페스트 전수 검토 | 모든 도구의 이름, 설명, 스키마를 읽고 해시 고정 |
| 4 | 최소 권한 | 서버가 요구하는 자격증명과 API 범위가 용도에 필요한 최소 |
| 5 | 이그레스 | 서버가 접속하는 외부 엔드포인트 목록이 허용 목록과 일치 |
| 6 | 전송과 인증 | HTTPS, Streamable HTTP, 토큰 또는 OAuth, 인증서 신뢰 |
| 7 | 격리 배치 | 별도 워크로드로 배치, 코드 실행 도구는 샌드박스(8.6) |
| 8 | 로그 | 서버 자체 로그와 에이전트 추적을 상관 지을 수 있음 |
| 9 | 재승인 조건 | 설명 해시, 버전, 권한 범위 중 하나라도 바뀌면 재승인 |
| 10 | 퇴역 | 미사용 서버의 승인 해제와 자격증명 폐기 절차 |

이 체크리스트의 서비스 측 사본은 [앱 가이드 A2.3](https://github.com/JaeHoYun/vcf-private-ai-apps/blob/main/appendix/A2-worksheets.md)에 있습니다.

## 8.6 실행 격리 — 샌드박스, 메모리, 에이전트 간 통신

**코드 실행 도구**(인터프리터, 셸, 스크립트 생성)는 ASI05의 직접 대상입니다. 실행은 커널 수준 격리(gVisor, Kata Containers, Firecracker 급)에서 네트워크 기본 거부, 읽기 전용 파일시스템, 시간과 CPU와 메모리 한도를 걸고 돌리며, 결과만 에이전트 컨텍스트로 돌려보냅니다. VKS에서는 Pod Security Admission의 restricted 프로파일을 기본으로 두고([Configure PSA for VKS, Broadcom TechDocs](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vsphere-supervisor-services-and-standalone-components/latest/managing-vsphere-kuberenetes-service-clusters-and-workloads/managing-security-for-tkg-service-clusters/configure-psa-for-tkr-1-25-and-later.html)), 정책 묶음으로 예외를 관리합니다([VKS Policy Bundle, Broadcom VCF Blog, 2026-08-04](https://blogs.vmware.com/cloud-foundation/2026/08/04/simplify-kubernetes-security-with-the-vmware-vsphere-kubernetes-service-policy-bundle/)). 격리 수준은 도구의 위험 등급에 비례하며, 첫 유스케이스에는 코드 실행 도구를 넣지 않는 것이 가장 싼 통제입니다.

**메모리와 컨텍스트**(ASI06)는 세 저장소를 봅니다. 세션 이력, 장기 메모리, 지식베이스 인덱스입니다. 런타임 메모리 주입과 인덱스 오염 공격은 높은 성공률이 학술적으로 보고되어 있으므로([vectorize.io, AI memory poisoning](https://vectorize.io/articles/ai-memory-poisoning)), 장기 메모리 쓰기는 읽기와 다른 권한으로 분리하고 검증을 거치며 롤백할 수 있어야 합니다. 인덱스는 소스 승인제([05 5.2절](05-data-governance.md))와 인입 검증([04 4.4절](04-airgap-supply-chain.md))으로 막습니다.

**에이전트 간 통신**(ASI07)은 멀티 에이전트 구성에서만 생기는 위협입니다. 에이전트끼리는 상호 TLS로 인증하고, 메시지에 서명과 논스를 붙여 위조와 재전송을 막으며, 하위 에이전트의 결과를 도구 결과와 같은 비신뢰 입력으로 다룹니다. 에이전트 카드(능력 선언)를 위조하는 공격이 보고되어 있으므로 카드도 서명합니다([A2A 프로토콜 보안 분석, arXiv 2511.03841](https://arxiv.org/pdf/2511.03841)). 첫 배치에서는 단일 에이전트로 시작해 이 위협을 아예 만들지 않는 것이 [앱 가이드 03](https://github.com/JaeHoYun/vcf-private-ai-apps/blob/main/docs/03-design-patterns.md)의 권고와 일치합니다.

## 8.7 사람의 개입과 킬스위치

되돌리기 어려운 행동 앞에 사람의 확인을 두는 세 패턴(제안 후 승인, 대기 큐, 드라이런)과 승인 큐의 상태 기계는 [앱 가이드 07 7.3절](https://github.com/JaeHoYun/vcf-private-ai-apps/blob/main/docs/07-integration-write-design.md)이 정본입니다. 플랫폼 거버넌스가 요구하는 것은 그 설계가 아니라 다음 세 가지 성질입니다.

- **우회 불가한 위치.** 승인 게이트는 에이전트가 지나칠 수 없는 계층(도구 게이트웨이 또는 BFF)에 둡니다. 지시문에 "승인을 받아라"라고 적는 것은 게이트가 아닙니다.
- **근거가 붙은 승인.** 승인 화면에는 제안의 근거(검색한 문서, 조회한 레코드, 도구 인자)가 함께 보여야 합니다. 근거 없는 승인 요청은 승인 피로를 낳아 ASI09의 조건을 만듭니다.
- **서비스 단위 킬스위치.** 한 번의 조치로 에이전트 비활성화, 서비스 계정과 토큰 폐기, 도구 승인 해제, 네트워크 정책 차단이 일어나야 합니다. 어느 계층에 있는지를 레지스트리(8.4)에 적고, 사고 대응 플레이북([07 7.3절](07-audit-compliance.md))의 첫 조치로 둡니다.

연쇄 실패(ASI08)는 사람의 개입만으로 막지 못합니다. 단계 수와 시간 상한, 실패율 기반 차단기, 다단계 쓰기의 보상 매트릭스([앱 가이드 07 7.4절](https://github.com/JaeHoYun/vcf-private-ai-apps/blob/main/docs/07-integration-write-design.md))가 함께 있어야 합니다.

## 8.8 정책 집행 계층 — 도구 게이트웨이의 위치

[⑦ 06 D13](../../07-design/docs/06-decision-forks.md)의 AI 게이트웨이는 앱에서 모델로 가는 방향의 계층입니다. 에이전트 거버넌스에는 반대 방향, 곧 **에이전트에서 도구로 가는 경로**의 정책 집행 계층이 따로 필요합니다. 하는 일은 호출 단위 인가(이 에이전트가 이 사용자를 위해 이 도구를 이 인자로 불러도 되는가), 인자 검사와 레이트리밋, 승인 게이트의 강제, 모든 호출의 감사입니다. 두 게이트웨이는 다른 트래픽 평면에 있으므로 하나로 합치려 하지 않습니다.

| 선택지 | 모습 | 맞는 조직 | 감수하는 것 |
|---|---|---|---|
| 앱 오케스트레이션 안에 구현 | 에이전트 코드가 도구 호출 전에 정책 함수를 거침 | 첫 유스케이스, 도구 몇 개, 단일 앱 | 앱마다 재구현, 우회 가능성을 코드 리뷰로만 막음 |
| MCP 게이트웨이(프록시) | 에이전트와 MCP 서버 사이에 정책과 감사를 두는 프록시. 오픈소스와 상용이 있음 | 도구가 열 개를 넘거나 앱이 여럿 | 운영 대상이 하나 늘고, 게이트웨이 자체가 고가치 표적 |
| 에이전트 거버넌스 제품 | 에이전트 신원 발급, 정책 엔진, 도구 호출 게이트웨이, 감사를 묶은 제품(예: AgentMinder) | 다중 에이전트, 쓰기 도구, 규제 심사 | 별도 라이선스와 통합 작업. PAIS 구성요소가 아니므로 통합 범위는 공식 문서로 확인 |

도입 시점의 기준은 셋 중 하나가 생길 때입니다. 쓰기 도구가 승인 대상이 될 때, 도구가 열 개를 넘을 때, 에이전트가 여럿이 되어 서로 부를 때. 그 전에는 앱 안의 정책 함수와 PAIS의 도구 승인 게이트([03 3.4절](03-identity-access.md))로 충분하며, 나중에 게이트웨이를 넣더라도 MCP 표준 위에 있으면 에이전트 정의를 다시 만들지 않습니다.

## 8.9 레드팀과 출시 게이트

에이전트의 레드팀은 모델 단위 프로브(인젝션, 탈옥)에 행위 단위 시나리오(도구 오남용, 권한 상승, 메모리 오염, 승인 우회)를 더한 것입니다. CSA의 Agentic AI Red Teaming Guide는 12개 범주로 시나리오를 나눕니다([CSA, Agentic AI Red Teaming Guide, 2025-05-28](https://cloudsecurityalliance.org/artifacts/agentic-ai-red-teaming-guide)). 도구체인은 용도별로 고릅니다.

| 도구 | 용도 | 어디에 |
|---|---|---|
| garak | 알려진 취약 유형에 대한 자동 프로브(인젝션, 누출, 유해 출력) | PoC부터, 모델과 지시문이 바뀔 때마다 |
| promptfoo | YAML로 정의한 테스트 묶음을 CI에서 실행, OWASP 프리셋 | 파일럿 게이트의 자동 회귀 |
| PyRIT | 다단계 공격 오케스트레이션(점진 유도, 트리 탐색) | 프로덕션 전 수동 시나리오 |
| DeepTeam | 에이전트 취약 유형 중심의 시나리오 묶음 | 도구와 메모리가 있는 에이전트 |

게이트별 요구는 다음과 같습니다. PoC는 자동 프로브 실행과 결과 기록만, 파일럿은 자동 회귀와 문서화된 임계값(예: 인젝션 성공률 상한, 승인 우회 0건), 프로덕션은 수동 시나리오와 ASI 열 항목의 커버리지 확인입니다. 발견된 우회는 [06 6.6절](06-app-guardrails.md)의 회귀 스위트에 영구 편입해 같은 우회가 다시 통하지 않음을 매 릴리스 검증합니다. 레드팀 결과와 임계값 통과 여부는 레지스트리(8.4)에 남깁니다.

## 8.10 검증 방법

| # | 검증 항목 | 방법 | 합격 기준 |
|---|---|---|---|
| 1 | 에이전트별 신원 | 두 에이전트의 도구 호출 로그를 대조 | 서로 다른 신원으로 구분 가능, 공유 자격증명 0건 |
| 2 | 사용자 범위 실행 | 권한이 다른 두 사용자로 같은 쓰기 도구 호출 | 권한 없는 사용자의 호출이 거부됨 |
| 3 | 자율성 상한 집행 | L1 에이전트에 승인 없는 쓰기를 유도 | 실행되지 않고 승인 대기로 남음 |
| 4 | 레지스트리 정합 | PAIS 에이전트 목록과 레지스트리 대조 | 미등록 에이전트 0건, 소유자 공란 0건 |
| 5 | 도구 설명 해시 | 승인된 MCP 서버의 도구 설명을 변경 | 승인 자동 무효화와 경보 |
| 6 | 공급망 | 미승인 레지스트리의 MCP 서버 등록 시도 | 차단 |
| 7 | 샌드박스 | 코드 실행 도구에서 외부 접속과 파일 쓰기 시도 | 차단, 자원 한도 초과 시 종료 |
| 8 | 메모리 쓰기 분리 | 읽기 권한만 가진 경로로 장기 메모리 쓰기 시도 | 거부, 롤백 절차 존재 |
| 9 | 킬스위치 | 서비스 단위 킬스위치 작동 | 에이전트, 토큰, 도구 승인, 네트워크가 한 조치로 차단 |
| 10 | 레드팀 회귀 | 과거 우회 케이스를 회귀 스위트에서 재실행 | 재현 0건, 임계값 통과 |

**추적성 점검**: 각 통제가 ASI 코드 → 정책 → 통제 → 검증 케이스 → 감사 증적([07](07-audit-compliance.md))으로 이어지는지 확인합니다. 마스터 체크리스트의 C-17(레지스트리와 자율성 상한)과 C-18(MCP 도구 공급망)이 이 문서의 총괄 항목입니다([07 7.5절](07-audit-compliance.md)).

---

### 참고 출처

- [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
- [OWASP GenAI LLM Top 10 2026](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/)
- [OWASP, Securing Agentic Applications Guide 1.0](https://genai.owasp.org/resource/securing-agentic-applications-guide-1-0/)
- [OWASP, A Practical Guide for Securely Using Third-Party MCP Servers 1.0](https://genai.owasp.org/resource/cheatsheet-a-practical-guide-for-securely-using-third-party-mcp-servers-1-0/)
- [MITRE ATLAS](https://atlas.mitre.org/)
- [CSA, Levels of Autonomy for Agentic AI (2026-01-28)](https://cloudsecurityalliance.org/blog/2026/01/28/levels-of-autonomy)
- [CSA, Agentic AI Red Teaming Guide (2025-05-28)](https://cloudsecurityalliance.org/artifacts/agentic-ai-red-teaming-guide)
- [CSA, Agentic AI Identity and Access Management](https://cloudsecurityalliance.org/artifacts/agentic-ai-identity-and-access-management-a-new-approach)
- [CISA 외 공동, Careful Adoption of Agentic AI Services (2026-05-01)](https://www.cisa.gov/resources-tools/resources/careful-adoption-agentic-ai-services)
- [MCP 사양 2026-07-28 변경 사항](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [MCP, Agentic AI Foundation 이관 (2025-12-09)](https://blog.modelcontextprotocol.io/posts/2025-12-09-mcp-joins-agentic-ai-foundation/)
- [Invariant Labs, MCP Security Notification: Tool Poisoning Attacks (2025-04)](https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks)
- [MCPTox: A Benchmark for Tool Poisoning Attack on Real-World MCP Servers (arXiv 2508.14925)](https://arxiv.org/pdf/2508.14925)
- [RFC 8693 OAuth 2.0 Token Exchange](https://datatracker.ietf.org/doc/html/rfc8693), [RFC 8707 Resource Indicators](https://datatracker.ietf.org/doc/html/rfc8707)
- [Red Hat, Wiring zero trust identity for AI agents: SPIFFE, token exchange and Kagenti (2026-06-10)](https://next.redhat.com/2026/06/10/wiring-zero-trust-identity-for-ai-agents-spiffe-token-exchange-and-kagenti/)
- [Broadcom 보도자료, AgentMinder (2026-08-31)](https://www.globenewswire.com/news-release/2026/08/31/3353342/19933/en/broadcom-unveils-agentminder-an-enterprise-solution-for-ai-agent-governance-and-runtime-control.html)
- [Broadcom TechDocs, Connect an MCP Server to Private AI Services](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/what-is-private-ai-services/adding-mcp-servers-for-real-time-data-access-and-specialized-ai-capabilities/connect-to-an-mcp-server.html)
- [Broadcom TechDocs, Explore MCP Tools in Your Namespace](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/what-is-private-ai-services/adding-mcp-servers-for-real-time-data-access-and-specialized-ai-capabilities/exploring-the-mcp-tools-avaiable-in-your-namespace.html)
- [Broadcom TechDocs, Configure PSA for VKS Clusters](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vsphere-supervisor-services-and-standalone-components/latest/managing-vsphere-kuberenetes-service-clusters-and-workloads/managing-security-for-tkg-service-clusters/configure-psa-for-tkr-1-25-and-later.html)
- [Broadcom VCF Blog, VKS Policy Bundle (2026-08-04)](https://blogs.vmware.com/cloud-foundation/2026/08/04/simplify-kubernetes-security-with-the-vmware-vsphere-kubernetes-service-policy-bundle/)
- [vectorize.io, AI Memory Poisoning](https://vectorize.io/articles/ai-memory-poisoning)
- [A2A 프로토콜 보안 분석 (arXiv 2511.03841)](https://arxiv.org/pdf/2511.03841)
- [netguardia, AI Red Teaming Tools of 2026: garak, PyRIT, promptfoo, DeepTeam](https://netguardia.com/security-operations/software-tools/the-best-ai-red-teaming-tools-of-2026-from-garak-to-promptfoo/)

---

[← 이전: 07 감사, 로깅, 사고대응 및 컴플라이언스 체크리스트](07-audit-compliance.md) | [목차](../README.md)

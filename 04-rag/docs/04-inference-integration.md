# 04 — 추론 통합

[← 목차로](../README.md)

조립한 근거 + 질문을 모델에 보내 답을 받는 단계입니다. 여기서 ③ 서빙 API를 직접 호출하게 됩니다.

## 4.1 Agent vs Model Endpoint — 무엇을 호출할까

PAIS는 두 수준의 추론 인터페이스를 제공합니다(③ 상세).

| | Model Endpoint | Agent |
|---|----------------|-------|
| 추상화 | 단일 모델 API(완성/임베딩) | RAG·세션·도구사용까지 캡슐화 |
| 검색 통합 | 앱이 직접(경로 B) | 플랫폼이 Knowledge Base 검색 포함(경로 A) |
| 적합 | 커스텀 파이프라인 | 표준 문서 Q&A 빠르게 |

- **경로 A(Agent)**: Agent Builder가 완성 모델·Knowledge Base·인덱스 오케스트레이션을 처리하므로, 앱은 Agent에 질문만 보내면 검색+생성이 한 번에 됩니다.
- **경로 B(Model Endpoint)**: 03에서 앱이 만든 컨텍스트를 완성 모델에 직접 보냅니다. 검색·조립을 앱이 통제합니다.

두 경로의 차이는 한마디로 **"검색을 누가 통제하는가"** 입니다. 경로 B는 앱이 검색·조립을 직접 짜 모델에 넘기고, 경로 A는 그 오케스트레이션을 플랫폼(Agent)에 맡깁니다.

```
경로 B — Model Endpoint (앱이 검색을 통제)

  [앱 / 오케스트레이션]
      │  (1) 질문
      ▼
  검색 · 컨텍스트 조립 (03) ──검색──▶ pgvector (②)
      │  (2) 질문 + 근거(조립된 컨텍스트)
      ▼
  Model Endpoint — 완성 모델 (③)
      │  (3) 답변 (스트리밍)
      ▼
  [앱]   출처는 실제 검색 청크 메타데이터로 표기 (4.5)


경로 A — Agent (플랫폼이 검색을 포함)

  [앱]
   │  질문만 전달
   ▼
  Agent (Agent Builder)
   │   ├─▶ (동적 판단) KB 검색 ──MCP 도구──▶ pgvector (②)
   │   │◀──────────────── 근거 ────────────────┘
   │   └─▶ 완성 생성 (③)
   ▼
  답변 + 근거 ──▶ [앱]
```

경로 A의 검색은 파이프라인에 고정된 단계가 아니라 **에이전트가 호출 여부·검색어를 스스로 정하는 행위**입니다(에이전틱 검색, §4.3). 단순 질의는 검색을 건너뛰기도 합니다.

## 4.2 OpenAI 호환 완성 호출 (경로 B)

PAIS는 OpenAI 호환 API를 제공합니다. **기존 OpenAI 코드의 `base_url`만 사내 PAIS로 바꾸면** 사내 추론으로 전환됩니다(③ 핵심 메시지).

```python
# 경로/모델명은 예시 — ③ 및 공식 API 레퍼런스로 확인
from openai import OpenAI
client = OpenAI(base_url="https://<PAIS>/compatibility/openai/v1", api_key="<token>")

resp = client.chat.completions.create(
    model="<completion-model>",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": assembled_context_and_question},  # 03 산출물
    ],
    temperature=0.1,        # 사실 기반 Q&A는 낮게
    stream=True,
)
```

- **temperature 낮게**: RAG 사실 응답은 창의성보다 충실도. 0–0.3 권장.
- **시스템 프롬프트로 가드**: "근거에 있는 내용만, 없으면 모른다" 규칙을 시스템 메시지에 고정(03 골격).

## 4.3 에이전트 호출 (경로 A)

Agent를 쓰면 검색이 호출 안에 포함됩니다. 앱은 Knowledge Base에 연결된 Agent에 질문을 던지고, Agent가 검색→조립→생성을 수행해 답과 근거를 반환합니다. Agent 선언·호출 엔드포인트와 요청/응답 스키마는 ③과 [PAIS 공식 API 레퍼런스](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/)를 따릅니다.

> 같은 OpenAI 호환 인터페이스를 쓰므로, OpenWeb UI 같은 표준 클라이언트를 Agent에 붙이는 것도 가능합니다(③ 참조).

**에이전틱 검색(agentic retrieval)** — PAIS 2.1에서는 Data Indexing·Retrieval이 **MCP 도구**로 통합되어, 각 Knowledge Base마다 검색 도구를 노출하는 MCP 서버로 구현됩니다. 이 구조에서는 검색이 파이프라인에 고정된 단계가 아니라 **에이전트가 스스로 호출 여부와 검색어를 결정하는 행위**가 됩니다. 모델은 도구 설명과 지시에 따라 적절한 MCP 도구를 선택하고, 에이전트가 그 도구를 호출해 결과를 컨텍스트로 끌어옵니다([Broadcom TechDocs — Explore the MCP Tools Available in Your Namespace](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/what-is-private-ai-services/adding-mcp-servers-for-real-time-data-access-and-specialized-ai-capabilities/exploring-the-mcp-tools-avaiable-in-your-namespace.html)). 단순 질의는 검색을 건너뛰고, 근거가 필요한 질의에서만 검색어를 만들어 KB를 조회하는 동적 판단이 가능합니다. 이는 시리즈 ①의 **MCP Tools Registry**와 직접 연결되는 경로로, 같은 메커니즘으로 사내 API·다른 데이터 소스를 추가 도구로 붙여 에이전트의 검색 범위를 확장할 수 있습니다(① 05). 도구 스키마·구성 절차는 위 공식 문서와 ①을 따릅니다.

## 4.4 스트리밍

문서 Q&A는 답변이 길어 **토큰 스트리밍**으로 첫 글자 지연(TTFT)을 줄이는 것이 UX에 중요합니다. OpenAI 호환 `stream=True`를 사용하고, 앱은 SSE를 받아 점진 렌더링합니다. 출처는 보통 마지막에 묶어 표시합니다.

## 4.5 인용·출처 표기

RAG의 신뢰는 **"이 답의 근거가 어디냐"** 에서 나옵니다.

- **경로 B**: 03에서 청크에 붙인 출처 라벨을 모델이 답변에 인용하도록 프롬프트로 유도하고, 앱은 사용된 청크의 메타데이터로 출처 카드(문서명·링크)를 별도 렌더링합니다(모델 환각 인용 방지 — 실제 검색된 청크 메타데이터를 신뢰).
- **경로 A**: Agent 응답에 포함되는 근거/출처 필드를 사용. 스키마는 공식 API로 확인.

> 권장: 모델이 본문에 단 인용 텍스트보다 **앱이 실제 검색 결과 메타데이터로 만든 출처**를 1차 진실로 삼으세요. 모델 인용은 보조 표시.

## 4.6 출력 가드레일 — 민감정보·출력 안전

검색 단계의 입력측 방어([03 3.6](03-retrieval-context.md#36-보안--프롬프트-인젝션-방어와-입력-살균))만으로는 충분하지 않습니다. 모델이 답을 만든 **직후**, 사용자에게 내보내기 전에 출력측 방어선도 함께 두어야 합니다.

- **PII·민감정보 마스킹**: 답변(및 로그)에 개인정보·인증정보·내부 비밀이 새어 나가지 않게 검사·치환합니다. RAG는 벡터 DB가 테넌트 간 공유될 때 유사도 검색이 경계를 넘어 데이터를 노출할 수 있어 위험이 가중되므로([OWASP LLM02:2025 Sensitive Information Disclosure](https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/)), 검색 단계 권한 필터(03)와 출력 마스킹을 **함께** 둡니다. Presidio 기반 PII 레닥션 등 독립 가드 도구를 출력단에 적용하는 패턴이 널리 쓰입니다.
- **시스템 프롬프트 누출 차단**: 알려진 시스템 프롬프트 조각이 답변에 재출력되는지 모니터링하고 차단합니다. 시스템 프롬프트 유출은 OWASP LLM07로 별도 분류되며, 인젝션 공격의 흔한 1차 목표입니다.
- **유해/부적합 출력 필터**: 정책 위반·유해 콘텐츠를 출력단에서 거릅니다. OWASP는 모델 출력에 대한 **검증·살균이 미흡한 것(Improper Output Handling, [LLM05:2025](https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/))** 을 별도 위험으로 보며, 출력은 신뢰 경계를 넘는 데이터로 취급해 다운스트림에 넘기기 전 검증하라고 권고합니다.
- **독립 시스템으로 검증**: 가드레일은 답을 만든 모델과 **분리된** 시스템으로 강제하는 것이 권장됩니다. 출력 가드를 생성 모델 자신에게 맡기면 같은 인젝션에 함께 무력화될 수 있습니다.

> **PAIS 연계**: PAIS 2.1이 출력 필터·민감정보 가드를 네이티브로 제공하는지, 또는 MCP/게이트웨이 계층에 가드 훅을 둘 수 있는지는 릴리스별로 다를 수 있어 [PAIS 공식 문서](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/)로 **확인 필요**합니다. 플랫폼 제공 여부와 무관하게, 위 출력 가드는 오케스트레이션/BFF 계층에서 독립적으로 두는 것을 권장합니다.

## 4.7 핵심 결정 요약

| 결정 | 기본 권장 |
|------|-----------|
| Agent vs Endpoint | 표준 Q&A→Agent(A), 커스텀→Endpoint(B) |
| temperature | 0–0.3 (사실 충실) |
| 스트리밍 | 켜기(TTFT/UX) |
| 출처 진실원 | 실제 검색 청크 메타데이터 |
| 근거 가드 | 시스템 프롬프트에 "없으면 모른다" 고정 |
| 출력 가드레일 | PII 마스킹 + 시스템 프롬프트 누출/유해 출력 필터를 독립 계층에서(4.6) |

---
[← 이전: 03 검색·컨텍스트 조립](03-retrieval-context.md) · [목차](../README.md) · [다음: 05 앱 통합 패턴 →](05-app-integration.md)

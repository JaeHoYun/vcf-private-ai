# 03 — OpenAI 호환 엔드포인트

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.
> 이 문서의 경로·필드는 [공식 PAIS API 레퍼런스](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/) 기준입니다. PAIS 버전에 따라 변경될 수 있으므로 적용 직전 공식 레퍼런스와 제품 내 Sample Code로 확인하시기 바랍니다.

PAIS의 모델 추론은 **OpenAI 호환 인터페이스**로 노출됩니다. OpenAI가 정의한 `models`·`embeddings`·`chat/completions` 형태를 그대로 따르므로, OpenAI SDK·클라이언트를 거의 수정 없이 씁니다.

> **형제 가이드와의 경로 차이 안내** — 형제 가이드 [04](../../01-infra/docs/04-dev-scenarios.md)는 경로를 `/v1/agents/{name}/chat` 등으로 적되 "9.0.x에서 이어받은 **미검증 예시**"라고 명시합니다. 본 가이드의 경로(`/api/v1/compatibility/openai/v1/...`)는 **공식 API 레퍼런스 기준 검증값**으로, 두 가이드를 함께 보신다면 본 문서의 경로를 최신 기준으로 삼으시기 바랍니다.

---

## 3.1 Base URL과 경로 구조

```
https://{instance-fqdn}/api/v1/compatibility/openai/v1/{...}
└──────────┬──────────┘└──┬──┘└────────┬────────┘└────────┬────────┘
        인스턴스          API 버전   OpenAI 호환 API       개별 리소스
```

- **인스턴스 FQDN** — PAIS 인스턴스 주소(조직별)
- **`/api/v1`** — PAIS API 버전 프리픽스
- **`/compatibility/openai/v1`** — OpenAI 호환 API. OpenAI SDK의 `base_url`에 `…/api/v1/compatibility/openai/v1`까지 넣으면, SDK가 그 뒤에 `chat/completions` 등을 붙입니다.

> OpenAI SDK는 `base_url` 뒤에 `/chat/completions`, `/embeddings`, `/models`를 자동으로 붙입니다. 따라서 클라이언트에는 **`…/compatibility/openai/v1`까지만** `base_url`로 지정하면 됩니다.

---

## 3.2 모델 목록 — `GET /models`

현재 인스턴스에서 호출 가능한 모델·엔드포인트를 조회합니다.

| 항목 | 값 |
|------|----|
| 경로 | `GET /compatibility/openai/v1/models` |
| 응답 | `object`, `data[]` (각 항목: `id`, `object`, `created`, `owned_by`, `model_type`, `model_engine`) |

```bash
curl -s 'https://{fqdn}/api/v1/compatibility/openai/v1/models' \
  -H 'Authorization: Bearer <access-token>'
```

> `model_type`(completion/embedding)·`model_engine`(vLLM/Infinity/llama.cpp 등)으로 그 모델이 무엇을 할 수 있는지 구분합니다. 앱에서 사용할 `model` 이름은 여기 `id`에서 가져옵니다. 같은 completion 모델이라도 **GPU(vLLM)인지 CPU(llama.cpp)인지**가 `model_engine`에 드러나므로, 지연·처리량 기대치를 여기서 가늠할 수 있습니다(9.1에서 llama.cpp 기반 CPU 추론 추가 → [02.5](02-serving-api-architecture.md#25-model-runtime--추론-엔진과-멀티-액셀러레이터-91)).

---

## 3.3 임베딩 생성 — `POST /embeddings`

텍스트를 벡터로 변환합니다. RAG의 색인과 질의 단계 모두에서 쓰입니다.

| 항목 | 값 |
|------|----|
| 경로 | `POST /compatibility/openai/v1/embeddings` |
| 요청 | `input`, `model` |
| 응답 | `object`, `data[]`(임베딩 배열), `model`, `usage`(`prompt_tokens`, `total_tokens`) |

```bash
curl -s -X POST 'https://{fqdn}/api/v1/compatibility/openai/v1/embeddings' \
  -H 'Authorization: Bearer <access-token>' -H 'Content-Type: application/json' \
  -d '{"model":"<embedding-model-id>","input":"사내 보안 정책 문서"}'
```

> 임베딩 모델은 CPU 추론 엔진(Infinity·llama.cpp 등)으로도 서빙될 수 있어, GPU 없이도 비용 효율적으로 운영하는 경우가 많습니다. 9.1에서는 **completion 모델도 llama.cpp로 CPU 추론**이 가능하므로, 경량·PoC 워크로드는 GPU 없이 돌릴 수 있습니다([02.5](02-serving-api-architecture.md#25-model-runtime--추론-엔진과-멀티-액셀러레이터-91)). 어떤 엔진/리소스로 떠 있는지는 `GET /models`의 `model_engine`과 형제 가이드 인프라 편을 참조하세요.

---

## 3.4 채팅 완성 — `POST /chat/completions`

핵심 추론 엔드포인트입니다. **OpenAI `chat/completions`와 동일한 형태**입니다.

| 항목 | 값 |
|------|----|
| 경로 | `POST /compatibility/openai/v1/chat/completions` |
| 요청 | `model`, `messages[]`(`role`, `content`), `temperature`, `max_tokens`, `stream` |
| 응답 | `id`, `object`, `created`, `model`, `choices[]`(`message`, `finish_reason`), `usage` |

```bash
curl -s -X POST 'https://{fqdn}/api/v1/compatibility/openai/v1/chat/completions' \
  -H 'Authorization: Bearer <access-token>' -H 'Content-Type: application/json' \
  -d '{
    "model":"<completion-model-id>",
    "messages":[
      {"role":"system","content":"너는 사내 IT 도우미다."},
      {"role":"user","content":"VPN 접속이 안 될 때 점검 순서는?"}
    ],
    "temperature":0.2,
    "max_tokens":512
  }'
```

응답(요약):

```json
{
  "id":"chatcmpl-...","object":"chat.completion","model":"<completion-model-id>",
  "choices":[{"message":{"role":"assistant","content":"① 네트워크 연결 확인 …"},
              "finish_reason":"stop"}],
  "usage":{"prompt_tokens":48,"completion_tokens":120,"total_tokens":168}
}
```

> 이 엔드포인트는 **상태 비저장**입니다. 멀티턴 대화를 하려면 이전 `messages`를 앱이 직접 누적해 매 요청에 다시 보내야 합니다. 세션·이력을 PAIS에 맡기고 싶으면 [04 Agent API](04-agent-rag-api.md)를 사용하세요.

---

## 3.5 스트리밍 (SSE)

`"stream": true`를 주면 토큰이 생성되는 대로 **서버-전송 이벤트(SSE)** 청크로 흘러나옵니다. Open WebUI 연동 등 실사용 사례에서 스트리밍 지원이 확인됩니다.

```python
# OpenAI SDK — stream=True 만 추가
for chunk in client.chat.completions.create(
        model="<completion-model-id>",
        messages=[{"role":"user","content":"분기 매출 보고서를 3줄로 요약해줘"}],
        stream=True):
    delta = chunk.choices[0].delta.content or ""
    print(delta, end="", flush=True)
```

> AI 응답은 초 단위로 길어질 수 있습니다. 사용자 체감 지연을 줄이려면 **스트리밍 + 진행 표시**를 기본으로 두는 것을 권장합니다. 첫 토큰 지연(TTFT)을 줄이려면 복제본 최소 1개를 항상 켜 두는 구성([07 운영](07-observability-ops.md))이 도움이 됩니다.

---

## 3.6 함수 호출(tool/function calling)

OpenAI 호환 인터페이스이므로, `chat/completions`에 **`tools`/`tool_choice`** 를 실어 모델이 외부 함수를 호출하도록 유도하고, 응답의 **`tool_calls`** 를 앱이 실행해 결과를 되돌려주는 표준 함수 호출 흐름을 그대로 따를 수 있습니다.

> **PAIS의 tool calling과의 관계** — PAIS 2.1은 에이전트가 **MCP tool calling**을 수행하도록 설계되어 있습니다. 모델이 tool calling을 지원하지 않는 경우를 위해 PAIS는 `x-pais-force-static-tool-execution` 메타데이터 헤더로 정적 도구 실행(레거시 동작)을 강제하는 폴백을 제공합니다(헤더명·세부 동작은 적용 전 공식 레퍼런스로 확인). 즉 **함수 호출은 ① 앱이 직접 `tools`를 정의해 Model Endpoint로 호출하는 방식**과, **② 에이전트가 등록된 MCP 도구를 호출하는 방식([06](06-mcp-tools-api.md))** 두 갈래로 나타납니다. 이 절은 ①(OpenAI 호환 인터페이스에서의 함수 호출)을 다룹니다. ([PAIS 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-release-notes/vmware-private-ai-services-release-notes.html), [OpenAI Function calling](https://developers.openai.com/api/docs/guides/function-calling))

**① 요청 — `tools`와 `tool_choice`**

`tools[]`에 함수의 이름·설명·JSON Schema 파라미터를 선언합니다. `tool_choice`로 호출 정책을 정합니다(`auto` 기본 / `none` 미사용 / `required` 강제 / 특정 함수 지정).

```json
{
  "model": "<completion-model-id>",
  "messages": [
    {"role": "user", "content": "서울 지금 날씨 알려줘"}
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "도시의 현재 날씨를 조회한다",
        "parameters": {
          "type": "object",
          "properties": {
            "city": {"type": "string", "description": "도시 이름"}
          },
          "required": ["city"]
        }
      }
    }
  ],
  "tool_choice": "auto"
}
```

**② 응답 — `finish_reason: "tool_calls"` + `tool_calls[]`**

모델이 도구가 필요하다고 판단하면, 텍스트 대신 `tool_calls` 배열로 **어떤 함수를 어떤 인자로 부를지**를 돌려줍니다. `finish_reason`은 `tool_calls`가 됩니다.

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "choices": [{
    "message": {
      "role": "assistant",
      "content": null,
      "tool_calls": [{
        "id": "call_abc123",
        "type": "function",
        "function": {"name": "get_weather", "arguments": "{\"city\":\"서울\"}"}
      }]
    },
    "finish_reason": "tool_calls"
  }]
}
```

**③ 도구 실행 결과를 되돌려 최종 답변 받기**

앱이 실제 함수를 실행한 뒤, 그 결과를 `role: "tool"` 메시지(같은 `tool_call_id`)로 붙여 **두 번째 호출**을 보내면 모델이 최종 자연어 답변을 생성합니다.

```json
{
  "model": "<completion-model-id>",
  "messages": [
    {"role": "user", "content": "서울 지금 날씨 알려줘"},
    {"role": "assistant", "content": null,
     "tool_calls": [{"id": "call_abc123", "type": "function",
       "function": {"name": "get_weather", "arguments": "{\"city\":\"서울\"}"}}]},
    {"role": "tool", "tool_call_id": "call_abc123",
     "content": "{\"temp_c\": 24, \"sky\": \"맑음\"}"}
  ]
}
```

> **면책** — 위 요청/응답 JSON은 OpenAI 함수 호출 표준 형태에 기반한 **예시**입니다. PAIS의 OpenAI 호환 인터페이스에서 `tools`/`tool_choice` 지원 여부·세부 필드는 **모델·엔진(vLLM 등)의 tool calling 지원 여부에 따라 달라질 수 있으므로**, 적용 전 [공식 PAIS API 레퍼런스](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/)와 제품 내 Sample Code, 그리고 대상 모델의 tool calling 지원 여부를 반드시 확인하시기 바랍니다. RAG·세션과 도구를 PAIS가 묶어서 처리하길 원하면, 직접 `tools`를 다루는 대신 [04 Agent API](04-agent-rag-api.md) + [06 MCP](06-mcp-tools-api.md)를 사용하는 편이 단순합니다.

> 응답 **본문 자체**를 정해진 JSON 스키마로 받고 싶으면(도구에 넘길 인자가 아니라), 함수 호출과 별개인 **구조화 출력(§3.7)** 을 사용합니다.

---

## 3.7 구조화 출력(JSON 모드)

함수 호출(3.6)이 **도구에 넘길 인자**를 구조화한다면, 구조화 출력은 **응답 본문 자체**를 정해진 JSON 스키마로 강제합니다. 분류·추출·라우팅처럼 **앱이 모델 출력을 코드로 파싱**해 다음 단계로 넘겨야 할 때 씁니다. 사람이 읽는 자연어 답변에는 필요 없습니다.

프롬프트로 JSON 형식을 요청하기만 하면, 모델이 앞뒤에 설명을 덧붙이거나 따옴표를 빠뜨려 `json.loads`가 깨지는 일이 잦습니다. 구조화 출력은 이를 **생성 단계에서 원천 차단**합니다.

**동작 원리** — 모델은 토큰마다 "다음에 올 단어"의 확률을 내는데, 구조화 출력은 **스키마에 맞지 않는 토큰을 후보에서 제거(마스킹)** 합니다. 그래서 결과가 항상 유효한 JSON(또는 지정한 형식)이 됩니다. 이를 제약 디코딩(constrained/guided decoding)이라 하며, vLLM은 `xgrammar`·`outlines` 같은 백엔드로 처리합니다. ([Red Hat Developer](https://developers.redhat.com/articles/2025/06/03/structured-outputs-vllm-guiding-ai-responses), [vLLM Structured Outputs](https://docs.vllm.ai/en/latest/features/structured_outputs.html))

**두 가지 요청 방식** — PAIS의 OpenAI 호환 `chat/completions`에서 다음 중 하나로 지정합니다.

| 방식 | 형태 | 용도 |
|------|------|------|
| 표준 `response_format` | `{"type":"json_object"}` | 형식만 JSON 보장(스키마 없음) |
| 표준 `response_format` | `{"type":"json_schema","json_schema":{...}}` | 정해진 스키마 강제(필드·타입) |
| vLLM 확장 `guided_*` (extra_body) | `guided_json`·`guided_choice`·`guided_regex`·`guided_grammar` | 스키마/택1/정규식/문법 강제 |

> `guided_choice`는 출력을 **미리 정한 라벨 중 하나로** 묶을 때 특히 유용합니다(예: 문의를 `["계정","결제","기술지원"]` 중 하나로). 분류·라우팅 전처리에 적합합니다.

**예시 — 스키마 강제(`json_schema`)** — 사내 문의를 분류해 `{category, urgency, summary}`로 받는 경우:

```json
{
  "model": "<completion-model-id>",
  "messages": [
    {"role":"system","content":"사용자 문의를 분류한다."},
    {"role":"user","content":"VPN이 어제부터 계속 끊겨 업무가 안 됩니다."}
  ],
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "ticket",
      "schema": {
        "type": "object",
        "properties": {
          "category": {"type":"string","enum":["계정","네트워크","기술지원","기타"]},
          "urgency":  {"type":"string","enum":["낮음","보통","높음"]},
          "summary":  {"type":"string"}
        },
        "required": ["category","urgency","summary"]
      }
    }
  }
}
```

응답의 `choices[].message.content`가 위 스키마를 따르는 JSON 문자열로 돌아오므로, 앱은 안전하게 `json.loads`로 파싱해 다음 단계(티켓 라우팅 등)로 넘길 수 있습니다.

```python
# vLLM 확장 형태(extra_body) — 표준 response_format이 노출되지 않을 때의 대안
resp = client.chat.completions.create(
    model="<completion-model-id>",
    messages=[{"role":"user","content":"VPN이 어제부터 끊깁니다"}],
    extra_body={"guided_choice": ["계정","네트워크","기술지원","기타"]},
)
```

**함정과 주의**

- **형식만 보장, 의미는 아님** — 스키마는 "JSON 모양"을 보장할 뿐, 값이 **사실로 맞는지**는 보장하지 않습니다(환각은 여전히 가능). 값 검증은 앱 몫입니다.
- **잘린 JSON** — `max_tokens`가 부족하면 JSON이 중간에 끊겨 파싱이 실패합니다. 스키마 크기에 맞춰 넉넉히 두십시오.
- **복잡한 스키마 = 지연·실패↑** — 깊게 중첩되거나 거대한 스키마는 제약 디코딩 비용을 키우고 모델이 채우기 어려워집니다. 필요한 필드만 두십시오.
- **프롬프트도 함께** — 스키마를 줘도 시스템 프롬프트에 "지정한 형식으로만 답하라"를 함께 적으면 품질이 안정적입니다.

**언제 쓰나** — 분류·엔티티 추출·의도 라우팅·도구 파이프라인의 중간 산출처럼 **다운스트림이 코드로 소비**하는 단계. 에이전트가 도구 결과를 정형으로 받아 처리하는 패턴은 별도 최상위 [에이전트 가이드](https://github.com/JaeHoYun/vcf-private-ai-agents)와 함께 보면 좋습니다.

> **PAIS 적용 — 확인 필요** — PAIS Model Runtime은 vLLM 기반이라 구조화 출력을 **엔진 차원에서 지원**합니다(작성 시점 vLLM 기준). 다만 PAIS의 OpenAI 호환 인터페이스가 `response_format`(특히 `json_schema`)과 `guided_*` 중 **무엇을, 어떤 필드까지 노출**하는지는 모델·엔진·PAIS 버전에 따라 다를 수 있으므로, 적용 전 [공식 PAIS API 레퍼런스](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/)와 제품 내 Sample Code, 대상 모델의 지원 여부를 확인하시기 바랍니다.

---

## 3.8 엔드포인트 치트시트 (모델 직접 호출)

이 문서가 다룬, 에이전트·RAG·MCP를 거치지 않는 **모델 직접 호출** 엔드포인트입니다.

| 동작 | 메서드·경로 |
|------|------------|
| 모델 목록 | `GET /compatibility/openai/v1/models` |
| 임베딩 생성 | `POST /compatibility/openai/v1/embeddings` |
| 채팅 완성 | `POST /compatibility/openai/v1/chat/completions` |

`chat/completions`는 **같은 경로에 옵션을 실어** 동작을 바꿉니다. 각 옵션의 상세는 해당 절을 참고하십시오.

| 옵션 | 요청 필드 | 상세 |
|------|----------|------|
| 스트리밍 | `"stream": true` | §3.5 |
| 함수 호출 | `tools` · `tool_choice` | §3.6 |
| 구조화 출력 | `response_format` · `guided_*` | §3.7 |
| 에러·재시도 | 상태코드별 처리 · 지수 백오프 | §3.9 |

> 에이전트·RAG·MCP 등 나머지 엔드포인트는 [04](04-agent-rag-api.md)·[06](06-mcp-tools-api.md)에서 다룹니다. 전체 치트시트는 [08 레퍼런스 구현](08-reference-implementation.md#엔드포인트-전체-치트시트)에 모았습니다.

---

## 3.9 에러 처리와 재시도

OpenAI 호환 인터페이스이므로 실패도 **HTTP 상태코드 + 에러 응답 바디**라는 표준 형태로 돌아옵니다. 앱은 상태코드별로 다르게 처리해야 합니다.

| 상태코드 | 의미 | 일반적 원인 | 앱의 처리 |
|---------|------|-----------|----------|
| **401** Unauthorized | 인증 실패 | 토큰 없음/만료/서명 불일치 | 토큰 갱신 후 1회 재시도, 계속 실패 시 재인증 → [05](05-auth-and-gateway.md) |
| **403** Forbidden | 인가 실패 | 토큰은 유효하나 그 모델·에이전트 호출 권한 없음 | 재시도 금지(권한/네임스페이스 점검) |
| **404** Not Found | 리소스 없음 | 잘못된 `model` id·경로·에이전트 id | 재시도 금지(요청 값 교정) |
| **422** Unprocessable Entity | 요청 검증 실패 | 필드 누락·타입 오류·잘못된 파라미터 | 재시도 금지(페이로드 교정) |
| **429** Too Many Requests | 속도 초과/혼잡 | 동시 요청 과다, 큐 포화 | **지수 백오프 재시도**(아래) |
| **503** Service Unavailable | 일시적 불가 | 복제본 기동 중(Cold Start)·일시 과부하 | **지수 백오프 재시도**(아래) |

> 위 상태코드·바디 형태는 OpenAI 호환 표준 및 일반적 HTTP 규약에 기반한 **예시**입니다. PAIS가 실제로 반환하는 정확한 코드·에러 스키마는 모델·게이트웨이 구성에 따라 다를 수 있으므로, 적용 전 [공식 API 레퍼런스](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/)로 확인하시기 바랍니다.

**에러 응답 바디(예시)** — OpenAI 호환 클라이언트는 보통 다음과 같은 `error` 객체를 기대합니다.

```json
{
  "error": {
    "message": "Rate limit exceeded, please retry later.",
    "type": "rate_limit_error",
    "code": "rate_limit_exceeded",
    "param": null
  }
}
```

**429/503 지수 백오프 재시도(예시)** — 재시도해도 안전한 코드(429·503·일부 5xx)에만 적용하고, 4xx 중 401을 제외한 클라이언트 오류(403/404/422)는 재시도하지 않습니다. 서버가 `Retry-After` 헤더를 주면 그 값을 우선합니다.

```python
import time, random, httpx

RETRIABLE = {429, 500, 502, 503, 504}

def call_with_backoff(url, headers, payload, max_attempts=5):
    for attempt in range(max_attempts):
        resp = httpx.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code < 400:
            return resp.json()
        if resp.status_code not in RETRIABLE or attempt == max_attempts - 1:
            resp.raise_for_status()        # 재시도 불가 또는 마지막 시도 → 예외
        # Retry-After 우선, 없으면 지수 백오프 + 지터
        wait = float(resp.headers.get("Retry-After", 0)) or (2 ** attempt) + random.random()
        time.sleep(wait)
```

> **타임아웃과 함께** — AI 응답은 초 단위로 길어질 수 있어, 재시도 못지않게 **요청 타임아웃·동시성 제한**이 중요합니다. 무한 재시도는 과부하를 키우므로 **최대 시도 횟수·상한 대기시간**을 두세요. 게이트웨이 측 속도 제어 현황은 [05.5](05-auth-and-gateway.md#55-레이트리밋쿼터로드밸런싱복제본)를 참조하시기 바랍니다.

---

[← 이전: 02 서빙 API 아키텍처](02-serving-api-architecture.md) · [목차](../README.md) · [다음: 04 에이전트·RAG API →](04-agent-rag-api.md)

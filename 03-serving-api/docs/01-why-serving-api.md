# 01 — 왜 사내 추론 API인가

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.

LLM을 앱에 붙이는 가장 쉬운 길은 외부 SaaS API(예: 퍼블릭 LLM API)를 호출하는 것입니다. 그런데 기업 환경에서는 이 방법이 통하지 않을 때가 많습니다. 이 문서는 **왜 모델을 사내 인프라에서 API로 직접 서빙하는가**, 그리고 **PAIS의 OpenAI 호환 API가 그 전환을 왜 쉽게 만드는가**를 정리합니다.

---

## 1.1 외부 LLM API의 3가지 벽

| 벽 | 내용 | 사내 추론 API로 해결되는 방식 |
|----|------|------------------------------|
| **데이터 주권** | 프롬프트·문서·답변이 외부로 나감. 규제 산업(금융·방산·공공·의료)은 반출 자체가 불가 | 추론이 VCF 내부에서 실행 → 데이터가 경계를 넘지 않음. 폐쇄망(에어갭) 아티팩트 반입(Artifact Mirroring Tool, 아티팩트 미러링 도구)까지 가능 ([근거](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-release-notes/vmware-private-ai-services-release-notes.html)) |
| **비용 구조** | 토큰당 종량 과금 → 사용량이 늘수록 비용이 선형 증가, 예측 어려움 | GPU 자산 기반 고정비 → 일정 트래픽(손익분기) 이상에서 단위 비용 하락 |
| **레이턴시·통제** | 외부 네트워크 왕복, 모델 버전·정책을 벤더가 통제 | 내부망 호출, 모델·버전·스케일·정책을 조직이 직접 통제 |

> 요점은 하나입니다 — **반출 불가 데이터·예측 가능한 비용·내부 통제**가 필요한 워크로드에는 사내 추론 API가 구조적으로 맞습니다. 외부 API의 문제가 아니라 워크로드 성격의 문제입니다. 많은 조직이 실험은 외부 API로, 프로덕션 민감 워크로드는 사내 API로 분리합니다.

> 비용은 무조건 유리하지 않습니다. GPU는 고정비라 **손익분기 트래픽 이하에서는 종량제가 더 쌀 수 있습니다.** 실제 손익분기는 모델 크기·GPU 점유율·트래픽 패턴에 따라 달라지므로, 도입 전 자체 워크로드 기준으로 검증하시기 바랍니다.

---

## 1.2 "그럼 코드를 다 새로 짜야 하나요?" — 아니요

사내 추론으로 옮길 때 가장 큰 걱정은 **기존 코드를 버려야 하는가**입니다. PAIS는 이 부담을 거의 없앱니다. **PAIS Model Endpoint와 Agent는 OpenAI 호환 API 형태로 제공**되기 때문입니다.

```
기존 (외부 LLM API)                    전환 후 (사내 PAIS)

  client = OpenAI(                       client = OpenAI(
    base_url="https://api.<vendor>/v1",    base_url="https://pais.company.com/api/v1/compatibility/openai/v1",
    api_key="sk-...")                      api_key="<PAIS_TOKEN>")
  client.chat.completions.create(...)    client.chat.completions.create(...)
        │                                       │
        └── 외부로 데이터 전송                   └── 사내 VCF 내부에서 추론, 데이터 미반출

  바뀐 것: base_url, 인증 토큰, model 이름.  바뀌지 않은 것: 호출 코드 구조.
```

OpenAI SDK·LangChain·LlamaIndex 등 OpenAI 인터페이스를 따르는 클라이언트는 대부분 **`base_url`·인증·`model` 이름만 바꾸면** 그대로 동작합니다. (실제 예제는 [08 레퍼런스 구현](08-reference-implementation.md))

> "호환"은 인터페이스 호환을 뜻합니다. 모든 OpenAI 전용 파라미터·기능이 1:1로 동일하게 동작한다는 보장은 아니므로, 사용하는 파라미터는 [03 엔드포인트](03-openai-compatible-endpoints.md)의 지원 필드와 [공식 API 레퍼런스](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/)로 확인하시기 바랍니다.

---

## 1.3 두 종류의 API — Endpoint와 Agent

PAIS는 소비 방식이 다른 **두 종류의 API**를 제공합니다. 이 구분은 가이드 전체를 관통하므로 먼저 짚습니다.

| | **Model Endpoint API** | **Agent API** |
|---|---|---|
| 한 줄 | 단일 모델을 그대로 호출 | RAG·세션·도구까지 묶어서 호출 |
| 상태 | 상태 비저장(stateless) — 대화 이력을 앱이 관리 | 상태 저장 — 세션·이력을 PAIS가 관리 |
| RAG | 없음 (직접 구현) | 내장 (Knowledge Base 연결) |
| 외부 도구 | 없음 | MCP 도구 연동 (PAIS 2.1) |
| OpenAI 호환 | 지원 `chat/completions`, `embeddings` | 지원 `agents/{id}/chat/completions` |
| 적합 | 커스텀 RAG, 단순 챗봇, 임베딩 생성 | 표준 문서 Q&A·에이전트(대다수) |

> **대부분의 RAG 앱은 Agent API가 정답입니다.** 검색·세션·출처 제공을 직접 짤 필요가 없습니다. 고급 검색(멀티홉·리랭킹)이나 기존 RAG 자산 재사용이 필요할 때만 Model Endpoint API + 직접 구현으로 내려갑니다. (이 선택의 상세 의사결정은 형제 가이드 [04](../../01-infra/docs/04-dev-scenarios.md) 참조)

---

## 1.4 이 가이드를 읽는 위치

```
[인프라]               [데이터]                  [서빙·소비 = 본 가이드]
 PAIF 구축      ──▶     pgvector / KB      ──▶    OpenAI 호환 API로 노출
 (Guide 1)             (Guide 2)                 앱이 base_url만 바꿔 소비

 본 가이드의 범위: "모델이 이미 떠 있다"를 전제로, 그것을 API로 노출하고
 소비하는 계층. 모델 배포·GPU 구성 자체는 Guide 1, 벡터 DB는 Guide 2.
```

다음 문서에서 이 API들이 **아키텍처적으로 어디서 나오는지**(Model Runtime·API Gateway)를 봅니다.

---

[← 이전: 00 추론 서빙은 어떻게 동작하나](00-serving-primer.md) · [목차](../README.md) · [다음: 02 서빙 API 아키텍처 →](02-serving-api-architecture.md)

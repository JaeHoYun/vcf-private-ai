# 03 — 역할별 워크플로우

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.

이 문서는 AI 플레이그라운드에서 **모델 준비 → RAG/에이전트 구성 → 앱 연동**까지 페르소나별로 무엇을 어떤 순서로 하는지 다룹니다. 9.1의 **VCF Automation UI 셀프서비스**를 기본 경로로 삼습니다.

---

## 3.1 환경 분리 = vSphere Namespace 분리

AI 플레이그라운드 내 DEV/QA/STAGING/PROD는 **vSphere Namespace**로 분리됩니다.

| 리소스 | 네임스페이스별 격리 | 공유 방식 |
|--------|:---:|----------|
| DLVM / Model Endpoint / Agent / KB / VKS | 격리됨 | 각 NS에서 독립 배포 |
| Harbor 모델 | 공유(격리 미지원) | 프로젝트 권한으로 접근 제어 |
| pgvector DB | 공유(격리 미지원) | 스키마/테이블로 격리 |

---

## 3.2 전체 워크플로우 (End-to-End)

```
Phase A: 인프라 구축 (Platform Engineer / VI Admin)
  VCF 9.1 → PAIF WD → Harbor/DSM → PAIS 2.1 → 카탈로그
  [산출물] AI 플레이그라운드 완성
        ↓
Phase B: 모델 준비 (Data Scientist + MLOps)
  DLVM → 모델 다운로드 → 검증/튜닝 → Harbor Push → Endpoint 생성
  [산출물] Model Endpoint URL + 최적 설정
        ↓
Phase C: RAG/에이전트 구성 (Data Scientist)
  Data Source 연결 → Knowledge Base → Agent (+MCP 도구) → Playground 테스트
  [산출물] Agent API URL + 프롬프트 가이드
        ↓
Phase D: 앱 개발·배포 (App Developer + DevOps)
  API 연동 → Frontend/Backend → 컨테이너 → VKS 배포
  [산출물] 프로덕션 AI 애플리케이션
```

---

## 3.3 Phase B: 모델 준비

### Step 1 — DLVM 배포

VCF Automation 카탈로그에서 **AI Workstation** 또는 **AI RAG Workstation**을 요청합니다.

| 옵션 | 권장값 |
|------|--------|
| VM Class | vgpu-a100-40c (개발), vgpu-a100-80c (대형) / 또는 Enhanced DirectPath I/O |
| Software Bundle | PyTorch (권장) |
| vCPU / Memory | 8 vCPU / 32GB 이상 |
| Storage | 200GB+ (대형 모델) |
| NGC API Key | Personal 또는 Service Key |

```bash
ssh vmware@<dlvm_ip>            # SSH 접속
https://<dlvm_ip>:8888          # JupyterLab (토큰: 배포 시 설정)
```

### Step 2 — 모델 다운로드

```bash
# Hugging Face
pip install huggingface_hub
huggingface-cli download meta-llama/Llama-3.1-8B-Instruct --local-dir ./llama-3.1-8b-instruct

# NGC (NVIDIA 최적화 모델 / NIM)
ngc registry model download-version nvidia/nemo/megatron_llama3_8b:1.0
```

### Step 3 — 모델 검증

```bash
sha256sum ./llama-3.1-8b-instruct/model*.safetensors   # 무결성
pip install vllm
vllm serve ./llama-3.1-8b-instruct --host 0.0.0.0 --port 8000 --tensor-parallel-size 1
curl http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"model":"./llama-3.1-8b-instruct","messages":[{"role":"user","content":"Hello"}],"max_tokens":100}'
```

### Step 4 — Harbor에 모델 Push

```bash
docker login harbor.company.com -u <username> -p <password>
# Harbor CA 신뢰 (Linux)
sudo cp harbor-ca.crt /usr/local/share/ca-certificates/ && sudo update-ca-certificates

cd ./llama-3.1-8b-instruct        # 주의 반드시 모델 폴더 안에서 실행
pais models push \
  --modelName meta-llama/llama-3.1-8b-instruct \
  --modelStore harbor.company.com/models -t v1
```

> **9.1 적용 전 확인:** 위 `pais models push`는 **예시이며 정확한 구문이 아닐 수 있습니다.** PAIF 9.1(NVIDIA) 릴리스 노트에는 pais CLI 제공이 명시되어 있으나 **PAIS 2.1 릴리스 노트에는 명시가 없습니다.** 정확한 CLI 명칭·하위 명령·인자는 [공식 CLI 문서](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1.html)로 확인하시기 바랍니다. 신규 작업은 **VCF Automation UI**를 우선 권장합니다. 모델명은 DNS 명명 규칙(소문자, 공백 없음)을 따릅니다.

### Step 5 — Model Endpoint 생성

**방법 A: PAIS UI (권장)** — `VCF Automation > Build & Deploy > [네임스페이스] > Services > Private AI > Model Runtime > New Model Endpoint`에서 Endpoint 이름·Model URL·타입(Completion/Embedding)·엔진·VM Class·Replicas를 설정합니다.

**방법 B: kubectl** — 주의 아래 매니페스트는 **구조 이해용 예시**입니다. 정확한 CRD `apiVersion`·필드명·`modelEngine` enum 값·VM Class 명칭은 PAIS 2.1 공식 문서/UI로 확인하세요(본 가이드에서 검증되지 않음).

```yaml
apiVersion: pais.vcf.broadcom.com/v1alpha1   # 예시 — 실제 apiVersion 확인 필요
kind: ModelEndpoint
metadata:
  name: llama-3-1-8b-instruct
  namespace: dev-ns
spec:
  modelType: COMPLETIONS
  modelEngine: VLLM            # 또는 LLAMACPP(CPU), INFINITY(Embedding)
  modelUrl: harbor.company.com/models/meta-llama/llama-3.1-8b-instruct:v1
  vmClass: vgpu-a100-40c
  replicas: 1
  registryCredentialsSecret: harbor-registry-creds
```

**CPU 추론 / Embedding (GPU 불필요)**

```yaml
# Embedding (Infinity, CPU 가능)
spec: { modelType: EMBEDDINGS, modelEngine: INFINITY, vmClass: best-effort-small, replicas: 1 }
# Completion CPU 추론 (9.1 신규, llama.cpp)
spec: { modelType: COMPLETIONS, modelEngine: LLAMACPP, vmClass: best-effort-medium, replicas: 1 }
```

> **비용 절감 (9.1, 검증됨):** Embedding은 물론, 소규모/테스트용 **Completion 추론도 llama.cpp로 CPU 배포**가 가능합니다(PAIS 2.1 릴리스 노트 "CPU-based inference and embeddings"). 대규모·실시간 추론은 GPU(vLLM)를 사용하세요.
> 위 YAML의 `modelEngine` 값(VLLM/INFINITY/LLAMACPP)과 `vmClass`(best-effort-* 등)는 **예시 표기**입니다 — 실제 enum/명칭은 PAIS 2.1 UI·문서로 확인하세요.

---

## 3.4 Phase C: RAG/에이전트 구성

### Step 1 — Data Source 연결

`Services > Private AI > Data Indexing & Retrieval > Data Sources > Add Data Source`. 지원 소스: Confluence · SharePoint · Google Drive · **Google Workspace(9.1)** · S3 · 로컬 파일.

```
Confluence 예시
Name: company-wiki / URL: https://company.atlassian.net/wiki
Space Keys: HR, ENGINEERING / Auth: API Token
```

### Step 2 — Knowledge Base 생성

| 설정 | 권장값 |
|------|--------|
| Embedding Model | bge-small-en(영어), bge-m3(다국어/한국어) |
| Chunk Size | FAQ 200–300 / 일반 400–600 / 기술문서 600–1000 (토큰) |
| Chunk Overlap | 50–100 |
| Indexing Schedule | Daily (권장) / Weekly / Manual |

PAIS가 자동으로 처리합니다: **수집 → 파싱 → 청킹 → 임베딩(Embedding Endpoint) → pgvector 저장 → 주기 갱신**.

### Step 3 — Agent 생성

| 설정 | 권장값 |
|------|--------|
| Model Endpoint | llama-3-1-8b-instruct |
| Temperature | 정확성 0.3 / 일반 0.7 |
| Max Tokens | 256–1024 |
| Knowledge Base | 용도별 KB |
| Similarity Cutoff | 0.6–0.8 |
| Number of Chunks | 3–7 |
| Chat History Length | 5–15 |
| **MCP 도구 (9.1)** | 필요 시 외부 데이터·도구 연동 → [문서 05](05-agents-mcp.md) |

System Prompt 예시:

```
당신은 회사 HR 정책 전문 어시스턴트입니다.
1. 제공된 문서 내용만 기반으로 답변하세요
2. 확실하지 않으면 "확인이 필요합니다"라고 말하세요
3. 답변은 3문장 이내로 간결하게
4. 출처 문서명을 항상 언급하세요
```

### Step 4 — PAIS Playground 테스트

Agent 생성 직후 **PAIS Playground**(Agent Builder 내장 테스트 UI)에서 즉시 대화형으로 검증하고, 검색된 청크를 확인하며 프롬프트를 반복 개선합니다. 화면에서 샘플 코드(curl 등)도 복사할 수 있습니다.

> "PAIS Playground"(UI 기능) ≠ "AI 플레이그라운드"(개념적 영역). [문서 01 §1.4](01-concepts.md#14-용어-혼동-주의-ai-플레이그라운드-vs-pais-playground) 참조.

---

## 3.5 Phase D: 앱 연동 (요약)

App Developer는 로컬 PC에서 전달받은 정보로 일반 REST API처럼 호출합니다.

```python
# 1) 토큰 획득 (OAuth Client Credentials)
token = requests.post(TOKEN_ENDPOINT, data={
    "grant_type":"client_credentials","client_id":CID,"client_secret":CSEC}).json()["access_token"]
# 2) Agent API 호출
r = requests.post(f"{BASE_URL}/v1/agents/{AGENT}/chat",
    headers={"Authorization": f"Bearer {token}"},
    json={"message":"연차 휴가는 며칠인가요?","session_id":"user-123"}, timeout=60)
# 3) 응답: {"response":"...","references":[{"source":"HR_Policy.pdf","content":"..."}]}
```

가이드라인: 세션 ID는 사용자별 고유 유지, 토큰 만료(보통 1시간) 전 자동 갱신, `references`에서 출처 추출, LLM 응답 지연 고려해 타임아웃 60초+(70B는 90초+). 상세 패턴은 [문서 04](04-dev-scenarios.md).

---

## 3.6 페르소나별 책임 요약

| Phase | VI Admin | Cloud Admin | Data Scientist | MLOps | App Dev | DevOps |
|-------|----------|-------------|----------------|-------|---------|--------|
| A. 인프라 | VCF, PAIF WD, vGPU | PAIS 설치, 카탈로그 | - | - | - | - |
| B. 모델 | - | - | 모델 평가/선택 | DLVM, Harbor Push, Endpoint | - | - |
| C. RAG/에이전트 | - | - | KB·Agent·프롬프트 | Embedding EP, MCP 연동 | - | - |
| D. 앱 | - | - | - | API 정보 전달 | 앱 코드 | VKS 배포, CI/CD |

---

[← 이전: 02 아키텍처 및 구축 순서](02-architecture.md) · [목차](../README.md) · [다음: 04 개발 시나리오 및 AI 앱 개발 →](04-dev-scenarios.md)

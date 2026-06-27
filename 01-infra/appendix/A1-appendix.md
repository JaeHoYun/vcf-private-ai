# A1 — FAQ·버전 매트릭스·용어집·참고 자료

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.

---

## A1.1 FAQ

### A1.1.1 기본 개념

**Q1. PAIF와 PAIS의 관계는?**
PAIS는 PAIF에 **포함된 관리형 AI 서비스 레이어**입니다. PAIF가 인프라(GPU·네트워크·스토리지)부터 서비스(Model Runtime·RAG·Agent·MCP)까지 전체를 묶고, 그중 서비스 부분이 PAIS(2.1)입니다.

**Q2. PAIF는 별도로 사야 하나요? (라이선스)**
아니요. **PAIF는 VCF 코어 구독에 포함**됩니다(별도 구매 불필요). 단 **NVIDIA AI Enterprise(NVAIE)** 는 NVIDIA에서 별도 구매해야 하며 vGPU 드라이버·NIM·NeMo 등을 포함합니다. GPU 하드웨어도 별도입니다. 또한 벡터 DB는 DSM 기반입니다. **DSM 자체는 별도 라이선스(Advanced Service)이지만, PAIS가 벡터 DB용 사용 권한을 포함**하므로 RAG 벡터 DB를 위해 DSM을 따로 살 필요는 없습니다(일반 DBaaS 확장 시에는 별도). → 9.0.x 일부 자료의 "PAIF = VCF Add-on" 서술은 부정확합니다. ([문서 01 §1.2](../docs/01-concepts.md#12-라이선스-구조-정확히))

**Q3. "AI 플레이그라운드"는 제품인가요?**
아니요. PAIF/PAIS 환경이 구축되면 형성되는 **개념적 영역**입니다. UI 기능인 "PAIS Playground"(Agent Builder 테스트 화면)와 다릅니다. ([문서 01 §1.4](../docs/01-concepts.md#14-용어-혼동-주의-ai-플레이그라운드-vs-pais-playground))

**Q4. Model Endpoint와 Agent의 차이는?**
Model Endpoint는 단일 모델 API, Agent는 RAG·세션·(9.1)도구사용까지 캡슐화합니다. 대부분 **Agent**가 간편합니다. ([문서 05 §5.1](../docs/05-agents-mcp.md#51-model-endpoint-vs-agent-복습))

### A1.1.2 9.1 신규

**Q5. 9.0에서 뭐가 가장 크게 바뀌었나요?**
① 외부 도구 연동 **MCP**, ② 에어갭 **Artifact Mirroring Tool**, ③ **CPU Completion 추론(llama.cpp)**, ④ **관측성**(모델·GPU 대시보드 + OTel), ⑤ **Enhanced DirectPath I/O**(NVAIE 없이 전용 GPU + vMotion), ⑥ **Blackwell GPU**, ⑦ 추론 엔진 대폭 상향(vLLM 0.11.2 등). ([문서 00](../docs/00-whats-new.md))

**Q6. `pais` CLI는 Deprecated 아닌가요?**
상태가 명확하지 않습니다. PAIF 9.1(NVIDIA) 릴리스 노트에는 `pais` CLI 1.0.0이 제공으로 표기되나, **PAIS 2.1 릴리스 노트에는 CLI 언급이 없습니다.** 따라서 9.0.x 가이드의 "제거 예정" 단정은 과하지만, "확정 제공"이라 단언하기도 어렵습니다. **모델 저장은 VCF Automation UI를 우선** 사용하고, CLI 사용 시 정확한 명칭·구문은 공식 문서로 확인하시기 바랍니다.

**Q7. DirectPath I/O는 vMotion이 안 된다던데요?**
9.1의 **Enhanced DirectPath I/O**는 NVAIE 없이 전용 GPU를 제공하면서 **vMotion 이점을 유지**합니다. 과거 "vMotion 제한" 서술은 폐기됐습니다. ([문서 02 §2.3](../docs/02-architecture.md#23-gpu-할당-방식-주의-91-변경))

**Q8. CPU만으로 LLM 추론이 되나요?**
9.1부터 **llama.cpp(b7739)** 로 **Completion 추론도 CPU**로 가능합니다(소규모·테스트·비용 절감). Embedding은 기존처럼 Infinity로 CPU 가능. 대규모·실시간은 GPU(vLLM 0.11.2).

**Q9. MCP로 무엇을 붙일 수 있나요?**
Oracle·MS SQL·PostgreSQL(DB), ServiceNow(ITSM), GitHub(코드), Slack(메신저) 등을 커스텀 커넥터 없이 표준 연동합니다. 거버넌스(권한·범위·감사)가 전제입니다. ([문서 05](../docs/05-agents-mcp.md))

### A1.1.3 기술/구성

**Q10. 어떤 LLM을 선택하나요?**

| 모델 | 파라미터 | GPU | 용도 |
|------|---------|------|------|
| Llama 3.1 8B | 8B | A100 40GB x1 | 일반 Q&A·요약 (권장 시작점) |
| Llama 3.1 70B | 70B | A100 80GB x2+ | 복잡 추론·고품질 |
| Mistral 7B | 7B | A100 40GB x1 | 빠른 응답·코드 |
| Qwen 2.5 | 7B/72B | 다양 | 다국어·아시아 언어 |

한국어는 Qwen·bge-m3(임베딩) 또는 한국어 파인튜닝 모델을 평가하세요.

**Q11. Knowledge Base 인덱싱 시간은?**
100개(10MB) 수 분 / 1,000개(100MB) 10–30분 / 10,000개(1GB) 1–2시간. PDF 파싱·Chunk 크기·Embedding 모델·Replica 수에 좌우. 대규모는 업무 외 시간 + 증분 인덱싱.

**Q12. Model Endpoint 생성이 실패합니다.**

| 증상 | 원인 | 해결 |
|------|------|------|
| Pending 지속 | GPU 부족 | 네임스페이스 GPU 쿼터 확인 |
| ImagePullBackOff | Harbor 인증 | 프로젝트 권한·Secret 확인 |
| CrashLoopBackOff | 모델 로딩 실패 | GPU 메모리 vs 모델 크기 |
| OOMKilled | 메모리 부족 | 더 작은/양자화 모델 |

```bash
kubectl get pods -n <ns> -l app=model-endpoint
kubectl describe pod <pod> -n <ns>
kubectl logs <pod> -n <ns>
```

**Q13. GPU 메모리 부족(vLLM)?**
`--gpu-memory-utilization 0.8`, 더 작은/양자화(GPTQ·AWQ) 모델, `--tensor-parallel-size`로 다중 GPU 분산, `--max-model-len` 축소. 참고: 8B(FP16) ≈ 16GB, 70B(FP16) ≈ 140GB(A100 80GB x2).

### A1.1.4 라이선스·비용

**Q14. GPU 비용 최적화?**
가장 큰 영향은 **모델 크기 선택**(8B로 충분하면 70B 금지 — 요구량 10배+). 그 외 자동 스케일링, 개발/프로덕션 분리, Embedding·소규모 Completion **CPU(llama.cpp)**, 야간/주말 Replica 축소.

---

## A1.2 버전 호환성 매트릭스

### A1.2.1 VCF / PAIF / PAIS

| VCF | PAIF | PAIS | DLVM | 비고 |
|-----|------|------|------|------|
| 9.0 / 9.0.1 / 9.0.2 | 9.0 | 2.0.89 | 9.0.x | 이전 라인 |
| **9.1** | **9.1** | **2.1** | VCF 9.1 호환 이미지 | **현재 권장** |

### A1.2.2 주요 컴포넌트 (9.1 / PAIS 2.1)

| 컴포넌트 | 버전 | 비고 |
|---------|------|------|
| vLLM | 0.11.2 | completions + embeddings |
| Infinity | 0.0.76 | embeddings |
| llama.cpp | b7739 | CPU completions + embeddings |
| VKr | 1.33 | ClusterClass builtin-generic-v3.2.0 |
| VKS | 3.5.0+ 권장 | — |
| GPU Operator | 25.10.1 | driver v580.x |
| PostgreSQL / pgvector | 16.8 / 0.8.0 | DSM 제공 |
| DLVM Conda | Miniforge3 24.3.0 | 9.0.x의 Miniconda 대체 |

### A1.2.3 9.0.x → 9.1 변경 요약

[문서 00 §0.4](../docs/00-whats-new.md#04-버전-매트릭스-변경-90x--91) 참조.

---

## A1.3 용어집

| 용어 | 정의 |
|------|------|
| **Adaptive Resync** | vSAN이 복구(resync) I/O와 VM(게스트) I/O의 대역폭을 동적으로 조절해 재동기화 중에도 워크로드 성능을 보호하는 기능 (문서 10 §10.5) |
| **Agent** | Model Endpoint + KB + Prompt (+9.1 MCP 도구)를 결합한 RAG/도구사용 캡슐화 |
| **Artifact Mirroring Tool** | 에어갭 환경에서 풀 AI 기능을 구동하기 위한 아티팩트 미러링 도구 (PAIS 2.1) |
| **Blackwell** | NVIDIA 차세대 GPU 아키텍처 (HGX B200, RTX PRO 4500/6000 등, 9.1 GA) |
| **Chunk** | 문서를 분할한 텍스트 조각 (RAG용) |
| **Cold Start** | 새 Replica 시작 시 모델 로딩으로 인한 초기 지연 |
| **DRA** | Dynamic Resource Allocation — Kubernetes 개방형 GPU 자원 할당 (K8s AI Conformance) |
| **DSM** | Data Services Manager — 관리형 데이터베이스(pgvector PostgreSQL) 서비스. 별도 라이선스 VCF Advanced Service이나, PAIS가 벡터 DB용 사용 권한 포함 |
| **DLVM** | Deep Learning VM — GPU 가속 개발 VM |
| **E2E 지연(End-to-End Latency)** | 요청 입력부터 최종 응답 완료까지의 전체 경과 시간. AI 서비스 SLI로 TTFT와 함께 추적 (문서 10 §10.4) |
| **Enhanced DirectPath I/O** | NVAIE 없이 전용 GPU 패스스루 + vMotion 유지 (9.1) |
| **ML API Gateway** | PAIS의 AI 전용 API 게이트웨이 (인증/인가·LB·OpenAI 호환·SSE 스트리밍) |
| **GPU-Accelerated Workload Domain** | GPU 호스트로 구성된 VCF AI 워크로드 도메인의 Broadcom 공식 표기. 본 문서는 가독성을 위해 **PAIF Workload Domain**으로 약칭(PAIF Workload Domain 항목 참조) |
| **GSLB** | Global Server Load Balancing — 지리 분산 사이트 트래픽 분배 (NSX ALB 등) |
| **Hallucination** | LLM이 사실이 아닌 내용을 생성하는 현상 |
| **Harbor** | 컨테이너 이미지/모델 레지스트리 |
| **Infinity** | Embedding 서빙 엔진 (CPU 지원) |
| **Knowledge Base** | 문서를 벡터화하여 저장하는 PAIS 관리형 저장소 |
| **LCM(Lifecycle Management)** | 플랫폼 컴포넌트의 설치·업그레이드·패치를 SDDC Manager 등으로 일관 관리하는 수명주기 관리 (문서 10 §10.1) |
| **llama.cpp** | CPU 기반 추론 엔진 (9.1, Completion CPU 추론 가능) |
| **MCP** | Model Context Protocol — 에이전트가 외부 데이터·도구를 표준 인터페이스로 연동 (PAIS 2.1) |
| **Model Endpoint** | PAIS 관리형 LLM/Embedding 서빙 API |
| **Network Policy** | 네임스페이스·파드 간 통신을 허용·차단하는 Kubernetes 네트워크 접근 제어 규칙 (문서 10 §10.5) |
| **NSX Edge** | 게이트웨이·로드밸런싱·NAT 등 north-south 네트워크 서비스를 제공하는 NSX 구성 요소 (문서 10 §10.5) |
| **NVAIE** | NVIDIA AI Enterprise — vGPU 드라이버·NIM·NeMo 등 포함, NVIDIA 별도 구매 |
| **OpenTelemetry (OTel)** | LLM 트레이싱·관측성 표준 (PAIS 2.1 LLM 트레이싱) |
| **PAIF** | Private AI Foundation with NVIDIA — VCF 코어 포함 AI 인프라 |
| **PAIF Workload Domain** | GPU 호스트로 구성된 VCF AI 워크로드 도메인. Broadcom 공식 표기는 **GPU-Accelerated Workload Domain**이며([TechDocs](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/design/design-library/private-ai-platform-detailed-design/private-ai-services.html)), 본 문서는 가독성을 위해 PAIF Workload Domain으로 약칭 |
| **PAIS** | Private AI Services — PAIF에 포함된 관리형 AI 서비스 레이어 |
| **pgvector** | PostgreSQL 벡터 검색 확장 |
| **RAG** | Retrieval-Augmented Generation — 검색 기반 응답 생성 |
| **RPO / RTO** | 데이터 손실 허용 시점 / 서비스 복구 허용 시간 |
| **SDDC Manager** | VCF 플랫폼의 수명주기·구성·인벤토리를 통합 관리하는 컨트롤 플레인. LCM·백업의 기준점 (문서 10 §10.1·§10.3) |
| **SLI(Service Level Indicator)** | 서비스 수준을 나타내는 측정 지표(예: TTFT·E2E 지연·가용성) (문서 10 §10.4) |
| **SLO(Service Level Objective)** | SLI에 대해 설정한 목표치(예: TTFT P95를 목표값 이내로). 알람·온콜의 기준 (문서 10 §10.4) |
| **SPBM(Storage Policy-Based Management)** | 스토리지 정책 기반 관리 — 가용성·성능 요구를 정책으로 정의해 vSAN에 적용 (문서 10 §10.5) |
| **Supervisor** | vSphere Kubernetes 컨트롤 플레인 |
| **Tool-calling** | LLM이 외부 도구를 호출해 작업을 수행하는 패턴 |
| **Trust Bundle** | PAIS가 신뢰하는 인증서 묶음 (OIDC·Harbor·DSM 인증서). 인증서 갱신 시 재구성 (문서 10 §10.3.3) |
| **TTFT(Time To First Token)** | 요청 후 첫 토큰이 생성되기까지의 지연. LLM 응답성 핵심 SLI (문서 10 §10.4) |
| **vGPU** | NVIDIA Virtual GPU — GPU 가상화/분할 공유 (NVAIE 필요) |
| **VKr / VKS / VKSM** | vSphere Kubernetes release / Service / Service Management |
| **vLLM** | LLM 추론 최적화 엔진 (PagedAttention) |
| **vSAN Effective Capacity** | vSAN 9.1의 운영·재구축 예비를 자동 산정해 안전하게 쓸 수 있는 용량을 보여 주는 뷰 (문서 10 §10.5) |
| **vSAN Skyline Health** | vSAN 클러스터·디바이스·네트워크 상태를 점검하고 문제를 진단·안내하는 건전성 점검 기능 (문서 10 §10.5) |
| **Workload Mobility** | VCF Operations의 워크로드 이동 기능. 다른 환경의 VM을 재부팅 없이 VCF로 전환(마이그레이션)할 때 활용 (문서 09) |
| **그린필드(Greenfield)** | 신규 인프라를 처음부터 구성해 PAIF 환경을 구축하는 출발 상황 (문서 09) |
| **마이그레이션(전환)** | 기존 가상화·경쟁 플랫폼에서 VCF로 워크로드를 옮겨 PAIF 환경을 구축하는 출발 상황. Workload Mobility 활용 (문서 09) |
| **브라운필드(Brownfield)** | 이미 운영 중인 VCF/vSphere 환경에 GPU 워크로드 도메인을 더해 PAIF를 얹는 구축 출발 상황 (문서 09) |

---

## A1.4 참고 자료

### 공식 문서
- [VMware Cloud Foundation 9.1 Release Notes](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/release-notes/vmware-cloud-foundation-9-1-0-0-release-notes.html)
- [VMware Private AI Foundation with NVIDIA 9.1 (TechDocs)](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1.html)
- [Requirements for Deploying PAIF with NVIDIA (9.1)](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1/deploying-private-ai-foundation-with-nvidia/requirements-for-deploying-private-ai-foundation-with-nvidia.html)
- [NVIDIA NGC Catalog](https://catalog.ngc.nvidia.com/) · [vLLM Docs](https://docs.vllm.ai/) · [LangChain Docs](https://python.langchain.com/)

### VCF 9.1 발표/분석
- [Announcing VCF 9.1 (VMware Cloud Foundation Blog)](https://blogs.vmware.com/cloud-foundation/2026/05/05/announcing-vcf-9-1-modern-private-cloud-built-for-efficiency-and-resilience/)
- [Streamline, Simplify and Protect all your AI workloads with VCF 9.1](https://blogs.vmware.com/cloud-foundation/2026/05/05/streamline-simplify-and-protect-all-your-ai-workloads-with-vcf-9-1/)
- [Broadcom Announces VCF 9.1 — Production AI (Broadcom News)](https://news.broadcom.com/releases/broadcom-announces-vmware-cloud-foundation-9-1)

### 호환성/지원
- [Broadcom Compatibility Guide (BCG)](https://www.broadcom.com/support/vmware/product-compatibility) — GPU/하드웨어 호환성 매번 확인
- Broadcom Support Portal — KB, 기술 지원

---

[← 이전: 11 GPU Enablement 핸즈온](../docs/11-gpu-enablement.md) · [목차](../README.md)

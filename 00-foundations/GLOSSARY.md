# 통합 용어집 (Glossary)

VCF Private AI 가이드 시리즈 전반에서 쓰이는 용어를 한곳에 모은 빠른 참조표입니다. 본편을 읽다 막히는 용어가 나오면 이 표로 되돌아오는 용도로 쓰십시오. 각 정의는 직관을 잡기 위한 짧은 설명이며, 정확한 정의는 본편과 공식 문서를 따릅니다.

표기 규칙: 영어 원문 유지가 관행인 용어는 영어로, 음차가 굳어진 용어는 한글로 적고 괄호에 원문을 병기합니다.

## AI·ML 기초

| 용어 | 한 줄 정의 |
|------|-----------|
| LLM (Large Language Model) | 방대한 텍스트로 학습해 다음 토큰을 예측하는 대규모 언어 모델. 입력 텍스트를 받아 출력 텍스트를 내는 "거대한 함수". |
| 토큰 (Token) | 모델이 텍스트를 다루는 최소 단위. 단어보다 작을 수 있다. 비용·지연·메모리가 토큰 수에 비례한다. |
| 컨텍스트 윈도우 (Context Window) | 모델이 한 번에 들고 처리할 수 있는 토큰의 최대 길이. "작업 메모리"에 해당. |
| 임베딩 (Embedding) | 텍스트의 의미를 숫자 배열(벡터)로 바꾼 것. 의미가 비슷하면 좌표도 가깝다. |
| 벡터 (Vector) | 임베딩의 결과인 숫자 배열. 유사도 검색의 대상. |
| 추론 (Inference) | 학습이 끝난 모델을 실제로 사용해 출력을 얻는 과정. 상시 서비스이며 사이징의 주 대상. |
| 학습 (Training) | 데이터로 모델의 가중치를 만들어 내는 과정. 대규모 GPU가 필요한 일회성·배치 작업. |
| 파인튜닝 (Fine-tuning) | 이미 학습된 모델을 특정 용도로 조금 더 다듬는 경량 학습. |
| RAG (Retrieval-Augmented Generation) | 외부 지식을 검색해 모델 입력에 덧붙여 답변 품질을 높이는 방식. 사내 데이터를 주입하는 대표 경로. |
| 에이전트 (Agent) | 모델이 도구를 호출하고 여러 단계를 거쳐 일을 수행하는 실행 형태. |
| MCP (Model Context Protocol) | 모델이 외부 도구·데이터에 표준 방식으로 연결되는 인터페이스. |
| 파라미터 (Parameter) | 모델이 학습으로 얻은 가중치 수. 모델 크기와 GPU 메모리 요구량을 좌우한다. |
| 양자화 (Quantization) | 모델 가중치의 정밀도를 낮춰 메모리·연산을 줄이는 기법. |

## 인프라·쿠버네티스

| 용어 | 한 줄 정의 |
|------|-----------|
| 컨테이너 (Container) | 애플리케이션과 의존성을 함께 패키징한 격리 실행 단위. VM보다 가볍고 빠르게 뜬다. |
| Pod | 쿠버네티스의 최소 배포 단위. 하나 이상의 컨테이너를 묶는다. |
| 노드 (Node) | Pod가 실제로 실행되는 워커 머신. ESXi 호스트에 대응되는 개념. |
| 쿠버네티스 (Kubernetes, K8S) | 컨테이너의 배포·확장·복구를 자동화하는 오케스트레이션 플랫폼. |
| GPU Operator | 쿠버네티스 위에서 NVIDIA 드라이버·런타임을 자동 설치·관리하는 컴포넌트. |
| vGPU | 물리 GPU를 여러 VM이 나눠 쓰도록 가상화한 것. |
| NVLink | GPU와 GPU를 직접 잇는 고속 연결(PCIe보다 빠름). 큰 모델을 여러 GPU에 쪼개 올릴 때(텐서 병렬) GPU끼리 매 토큰 계산값을 주고받아야 하므로, 이 연결이 빠를수록 성능이 유지된다. 노드 안의 GPU는 NVLink로 묶이지만 노드를 넘으면 일반 네트워크라 훨씬 느리다. |

## GPU·소프트웨어 스택

| 용어 | 한 줄 정의 |
|------|-----------|
| VRAM (GPU 메모리) | GPU에 붙은 전용 메모리. 모델 가중치와 KV 캐시가 올라가며, "이 모델이 올라가는가"를 먼저 가르는 1차 제약. |
| Passthrough | GPU 한 장을 통째로 VM 하나에 직접 붙이는 전용 할당 방식. |
| MIG (Multi-Instance GPU) | GPU 한 장을 하드웨어 수준에서 독립 인스턴스 여러 개로 쪼개는 분할 방식. 몫끼리 강하게 격리된다. |
| RDMA (InfiniBand·RoCE) | 노드를 넘어 GPU·서버를 잇는 저지연 고속 네트워크 기술. 멀티노드 GPU 통신에 쓰인다. |
| CUDA | GPU에 일반 연산을 시키기 위한 NVIDIA의 플랫폼·런타임. 상위 AI 소프트웨어 대부분이 이 위에서 동작한다. |
| cuDNN | CUDA 위에서 딥러닝 연산을 최적화해 둔 라이브러리. |
| NCCL | 여러 GPU 간 고속 통신을 담당하는 라이브러리. 멀티 GPU 학습·추론의 토대. |
| 추론 엔진 (Inference Engine) | 완성된 모델을 실제로 실행하고 API로 내보내는 소프트웨어 계층. |
| vLLM | GPU 기반 운영 추론의 표준 엔진. 높은 동시 처리량을 낸다(상세는 ③). |
| llama.cpp | CPU에서 양자화 모델을 돌리는 추론 엔진. 소규모·테스트·저부하용. |
| Infinity | 임베딩(검색용 벡터) 생성 전용 엔진(CPU). |
| 오픈웨이트 (Open-weight) | 가중치가 공개되어 받아서 사내 GPU에서 직접 실행할 수 있는 모델(Llama·Mistral·Qwen 등). |
| safetensors | 모델 가중치의 표준 저장 형식. |
| GGUF | llama.cpp용으로 양자화된 단일 파일 모델 형식. |
| NIM (NVIDIA Inference Microservices) | NVIDIA의 추론 컨테이너 런타임/모델 포맷. |
| NVIDIA AI Enterprise (NVAIE) | GPU 소프트웨어 스택을 검증·인증해 묶고 상용 지원을 붙인 NVIDIA의 소프트웨어 구독. |
| Harbor | VCF에서 컨테이너 이미지·AI 아티팩트를 보관하는 사내 레지스트리. |
| Artifact Mirroring Tool | 폐쇄망(air-gapped)에 모델·이미지 등 AI 아티팩트를 들여 완전한 Private AI 기능을 구동하게 하는 PAIS 2.1 도구. |
| Model Gallery / Runtime / Endpoint | PAIS의 모델 흐름. 반입(Gallery) → 엔진 실행(Runtime) → OpenAI 호환 API 서빙(Endpoint). |

## VCF·제품 계층

| 용어 | 한 줄 정의 |
|------|-----------|
| VCF (VMware Cloud Foundation) | 컴퓨트·스토리지·네트워크·쿠버네티스를 묶는 프라이빗 클라우드 플랫폼. Private AI의 바닥. |
| VKS | VCF가 제공하는 관리형 쿠버네티스 서비스. vSphere Supervisor 위에서 동작. |
| PAIF (Private AI Foundation with NVIDIA) | VCF 위에서 GPU·드라이버·모델·RAG를 표준화하는 AI 인프라 계층. |
| PAIS (Private AI Services) | 모델 서빙·RAG·에이전트(Agent Builder)·MCP를 관리형으로 올리는 서비스 계층. |
| DSM (Data Services Manager) | VCF에서 PostgreSQL 등 데이터 서비스를 관리형으로 제공하는 컴포넌트. RAG용 벡터 DB의 토대. |
| pgvector | PostgreSQL에서 벡터 유사도 검색을 지원하는 확장. RAG의 벡터 저장소로 쓰인다. |

"""
VCF Private AI 사이징과 TCO 계산 워크북 생성기.
입력 시트의 파란 셀을 바꾸면 동시성, GPU, 호스트, 노드, 스토리지, TCO 수량이 수식으로 다시 계산된다.
출처: https://github.com/JaeHoYun/vcf-private-ai/tree/main/06-sizing-cost
"""
import os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation

ARIAL = "Arial"
BLUE = "0000FF"     # 입력(사용자가 바꾸는 값)
BLACK = "000000"    # 수식과 계산
GREEN = "008000"    # 다른 시트 참조
HDR_FILL = PatternFill("solid", fgColor="1F3864")
SEC_FILL = PatternFill("solid", fgColor="D9E1F2")
YEL = PatternFill("solid", fgColor="FFFF00")
OUT_FILL = PatternFill("solid", fgColor="E2EFDA")
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def hdr(cell, text):
    cell.value = text
    cell.font = Font(name=ARIAL, bold=True, color="FFFFFF", size=12)
    cell.fill = HDR_FILL
    cell.alignment = Alignment(vertical="center")


def section(ws, row, text, span=5):
    c = ws.cell(row=row, column=1, value=text)
    c.font = Font(name=ARIAL, bold=True, color="1F3864")
    c.fill = SEC_FILL
    for col in range(2, span + 1):
        ws.cell(row=row, column=col).fill = SEC_FILL


wb = Workbook()

# ---------- 표지 ----------
cover = wb.active
cover.title = "표지"
cover.sheet_view.showGridLines = False
cover.column_dimensions["A"].width = 2
cover.column_dimensions["B"].width = 110
hdr(cover.cell(row=2, column=2), "VCF Private AI 사이징과 TCO 계산 워크북")
notes = [
    "",
    "목적: 입력 시트의 값을 채우면 동시성, GPU, 호스트, VKS 노드, 스토리지, TCO 수량이 수식으로 산출됩니다.",
    "",
    "[중요]",
    "- 성능 작동점(요청 동시성, 첫 토큰 시간, 토큰 간 지연)의 기본값은 공개 측정값이며, 자사 PoC 실측으로 바꿔야 합니다(가이드 06 6.5절).",
    "- 1인당 질의 수와 피크/평균비의 기본값은 근거 없는 가정값입니다. 자사 로그로 실측하세요(부록 A2.1).",
    "- 금액은 싣지 않습니다. TCO 시트는 수량까지 계산하고, 단가 칸은 견적으로 채웁니다(부록 A3).",
    "",
    "[시트 구성]",
    "- 입력: 자사 상황에 맞춰 정하는 값(파란 글씨)",
    "- 상수: 플랫폼 규칙과 보수 계수. 특별한 사유가 없으면 바꾸지 않습니다",
    "- 산정: 계산 결과와 점검 결과",
    "- TCO: 라이선스와 하드웨어 수량, 견적 단가 입력 칸",
    "",
    "[색상 약속]",
    "- 파란 글씨 = 입력, 검은 글씨 = 수식(직접 수정 금지), 노란 배경 = 실측이나 견적으로 바꿀 값",
    "",
    "[적용 범위]",
    "- 모델 하나를 복제본 여러 개로 서빙하는 대화형 추론(사내 문서 RAG 등)의 1차 산정 도구입니다.",
    "- 여러 모델 동시 서빙, 학습과 파인튜닝, MIG 세부 분할, 멀티테넌트 합산은 범위 밖입니다.",
    "",
    "[기본 예시] 가이드 docs/08 레퍼런스 시나리오와 같은 입력입니다(1인당 질의 10회 경우).",
    "",
    "출처: https://github.com/JaeHoYun/vcf-private-ai/tree/main/06-sizing-cost  (라이선스 CC BY 4.0)",
    "비공식 문서이며 벤더 공식 입장이 아닙니다. 모든 수치는 어림이며 실측과 견적으로 다시 확인하세요.",
]
r = 4
for line in notes:
    c = cover.cell(row=r, column=2, value=line)
    bold = line.startswith("[") or line.startswith("목적")
    c.font = Font(name=ARIAL, bold=bold, size=11, color="C00000" if line == "[중요]" else BLACK)
    c.alignment = Alignment(wrap_text=True, vertical="top")
    r += 1

# ---------- 입력, 상수 공통 ----------
REF = {}


def make_param_sheet(title, header):
    ws = wb.create_sheet(title)
    ws.sheet_view.showGridLines = False
    for col, w in zip("ABCDE", (4, 40, 16, 12, 60)):
        ws.column_dimensions[col].width = w
    hdr(ws.cell(row=1, column=2), header)
    for col in (3, 4, 5):
        ws.cell(row=1, column=col).fill = HDR_FILL
    return ws


class ParamWriter:
    def __init__(self, ws):
        self.ws = ws
        self.row = 2

    def section(self, text):
        section(self.ws, self.row, text)
        self.row += 1

    def add(self, key, label, value, unit="", note="", highlight=False, pct=False, fmt=None):
        ws = self.ws
        ws.cell(row=self.row, column=2, value=label).font = Font(name=ARIAL)
        c = ws.cell(row=self.row, column=3, value=value)
        c.font = Font(name=ARIAL, color=BLUE, bold=True)
        c.border = BORDER
        if highlight:
            c.fill = YEL
        if pct:
            c.number_format = "0%"
        elif fmt:
            c.number_format = fmt
        ws.cell(row=self.row, column=4, value=unit).font = Font(name=ARIAL, italic=True, color="808080")
        ws.cell(row=self.row, column=5, value=note).font = Font(name=ARIAL, italic=True, color="808080")
        REF[key] = f"'{ws.title}'!$C${self.row}"
        self.row += 1
        return c


inp = make_param_sheet("입력", "입력값 (자사 상황에 맞춰 파란 셀을 변경)")
P = ParamWriter(inp)

P.section("워크로드 (부록 A2.1)")
P.add("N_users", "도구를 배포받는 인원", 5000, "명")
P.add("dau", "일 활성 비율", 0.30, "", "배포 인원 기준 업무일 평균. 참고 범위와 구하는 법은 A2.1", pct=True)
P.add("q_day", "활성 사용자 1인당 업무일 질의", 10, "회", "가정값. 공개 근거 없음, 관리 콘솔이나 게이트웨이 로그로 실측", highlight=True)
P.add("hours", "업무시간", 8, "시간", "대화형 트래픽의 업무시간 집중(A2.1)")
P.add("peak_ratio", "피크/평균비", 3, "", "공개 근거 없는 보수 가정. 시간 단위 피크 계수를 실측", highlight=True)
P.add("burst", "버스트 헤드룸", 0.30, "", "A2.1", pct=True)

P.section("토큰 (부록 A2.2)")
P.add("sys_tok", "시스템 프롬프트", 500, "토큰")
P.add("question_tok", "사용자 질문", 100, "토큰")
P.add("history_tok", "대화 이력", 400, "토큰")
P.add("chunk_tok", "청크 크기", 512, "토큰")
P.add("topk", "최종 검색 결과 개수(리랭크 후)", 6, "개")
P.add("out_tok", "출력 토큰", 500, "토큰", "보수 산정. 평균 산정이면 250–300")
P.add("ko_factor", "한국어 토큰 팽창 계수", 1.0, "배", "위 토큰을 한국어로 이미 셌으면 1.0, 영어 기준 어림이면 1.3–1.7(A2.2)", fmt="0.00")

P.section("모델 (부록 A2.4, A2.5)")
P.add("model_label", "모델 설명", "70B dense (예: Llama 3.1 70B)", "", "산정에는 아래 숫자만 쓰임")
P.add("params", "총 파라미터 수", 70, "B(십억)")
P.add("prec_w", "가중치 정밀도 바이트", 1, "byte", "FP8=1, FP16/BF16=2, 4비트=0.5")
P.add("layers", "레이어 수", 80, "", "config.json num_hidden_layers")
P.add("kv_heads", "KV 헤드 수", 8, "", "config.json num_key_value_heads")
P.add("head_dim", "head_dim", 128, "", "config.json head_dim 또는 hidden_size ÷ 어텐션 헤드 수")
P.add("prec_kv", "KV 캐시 정밀도 바이트", 2, "byte", "BF16 KV=2, FP8 KV=1")

P.section("성능 작동점 (PoC 실측으로 교체, 부록 A2.3)")
P.add("perf_isl", "측정 조건: 입력 토큰", 5000, "토큰", "아래 값을 잰 조건", highlight=True)
P.add("perf_osl", "측정 조건: 출력 토큰", 500, "토큰", "", highlight=True)
P.add("safe_conc", "지연 목표를 지키는 복제본당 동시성", 50, "요청", "기본값: NVIDIA NIM 공개 측정, 70B FP8, H100 4장, 동시성 50", highlight=True)
P.add("ttft_ms", "그 동시성에서 첫 토큰 시간", 952, "ms", "동 측정 952.43ms", highlight=True)
P.add("itl_ms", "그 동시성에서 토큰 간 지연", 40.13, "ms", "동 측정 40.13ms", highlight=True, fmt="0.00")
P.add("ttft_target", "지연 목표: 첫 토큰 시간", 2000, "ms", "A2.3")
P.add("itl_target", "지연 목표: 토큰 간 지연", 100, "ms", "A2.3 (초당 10토큰 이상)")

P.section("GPU와 호스트 (가이드 02, 04)")
P.add("gpu_mem", "GPU 메모리", 80, "GB")
P.add("gpu_per_rep", "복제본당 GPU", 4, "장", "텐서 병렬 수. 호스트 안에서 NVLink로 묶임")
P.add("gpus_per_host", "호스트당 장착 GPU", 4, "장")
P.add("embed_gpu", "임베딩과 리랭커용 GPU", 1, "장", "CPU로 돌리면 0 (04 4.3절 N3)")
P.add("na_plus", "가용성 추가 복제본(N+1)", 1, "")
c_alloc = P.add("alloc_mode", "GPU 할당 방식", "DirectPath", "", "DirectPath 또는 vGPU (07 7.2절)")
c_nim = P.add("nim_used", "NIM 등 NVAIE 소프트웨어 사용", "예", "", "예 또는 아니오. 기본 성능 작동점이 NIM 측정값이라 기본값은 예")
c_deploy = P.add("deploy", "클러스터 배치", "통합형", "", "통합형 또는 분리형 (04 4.1절)")
P.add("sep_hosts", "분리형일 때 비GPU 호스트 수", 3, "대")
P.add("cores_host", "호스트당 물리 코어", 64, "코어", "서버 사양")
P.add("sockets", "호스트당 소켓 수", 2, "")

P.section("스토리지 (가이드 05)")
P.add("corpus_gb", "문서 원문 저장 용량", 100, "GB", "원문 저장 산정용. 벡터 수 추정에는 쓰지 않음")
P.add("vec_count", "벡터 수", 2800000, "건", "색인 범위 시나리오와 표본 실측(05 5.2절)", highlight=True, fmt="#,##0")
P.add("vec_dim", "벡터 차원", 1536, "", "임베딩 모델 사양")
P.add("ver_keep", "모델 보존 버전 수", 3, "", "05 5.1절")
P.add("img_gb", "컨테이너 이미지", 50, "GB", "확인 필요", highlight=True)
P.add("logs_gb", "로그와 관측(보존 기간분)", 30, "GB", "보존 정책 의존")

for cell, opts in ((c_alloc, '"DirectPath,vGPU"'), (c_nim, '"아니오,예"'), (c_deploy, '"통합형,분리형"')):
    dv = DataValidation(type="list", formula1=opts, allow_blank=False)
    inp.add_data_validation(dv)
    dv.add(cell.coordinate)

const = make_param_sheet("상수", "상수 (플랫폼 규칙과 보수 계수. 특별한 사유가 없으면 그대로)")
K = ParamWriter(const)
K.section("GPU 메모리 (가이드 02)")
K.add("gpu_util", "gpu_memory_utilization", 0.9, "", "vLLM 기본값 (02 2.1절)", pct=True)
K.add("overhead_gpu", "GPU당 활성화와 오버헤드", 4, "GB", "어림")
K.add("mem_rule", "GPU 메모리 ÷ 가중치 점검값", 2.5, "배", "VCF 9.1 설계 PAIF-ACC-RCMD-001")
K.section("가용성과 클러스터 (가이드 04)")
K.add("min_replicas", "모델 엔드포인트 최소 복제본", 2, "", "VCF 9.1 PAIS 설계 PAIS-021")
K.add("paif_min", "PAIF 최소 GPU 호스트", 3, "대", "PAIF 9.1 요건 (01 1.1절)")
K.add("cp_nodes", "컨트롤 플레인 노드", 3, "", "운영 환경 3 (04 4.1절)")
K.add("gen_workers", "일반 워커 노드", 3, "", "HA")
K.add("node_head", "GPU 노드 오토스케일 헤드룸", 0.20, "", "04 4.4절", pct=True)
K.add("clusters", "클러스터 수", 1, "", "격리 요구 시 증가 (04 4.5절)")
K.add("sup_cl_lim", "Supervisor 클러스터 한도", 500, "", "04 4.5절")
K.add("sup_node_lim", "Supervisor 노드 한도", 4000, "", "04 4.5절")
K.section("스토리지 (가이드 05)")
K.add("vec_bytes", "벡터 float 바이트", 4, "byte", "pgvector float32")
K.add("hnsw_mult", "HNSW 인덱스 배수", 2, "배", "원시 벡터 대비 1.5–3배 (05 5.2절)")
K.add("corpus_mult", "원문 전처리 사본 배수", 1.5, "배", "05 5.1절")
K.add("rag_ratio_hi", "RAG 벡터 DB 저장 공식 비율 상한", 10, "배", "원문의 5–10배, VCF 9.1 설계 PAIF-ACC-RCMD-010")
K.add("prot", "vSAN 보호 오버헤드 배수", 1.5, "배", "Auto-RAID (05 5.3절)")
K.add("dedup", "압축과 중복제거 절감 배수", 1.0, "배", "보수적으로 1.0")
K.section("라이선스 (부록 A3)")
K.add("core_min", "소켓당 코어 최소수량", 16, "코어", "견적으로 확인", highlight=True)


def V(key):
    return REF[key]


# ---------- 산정 ----------
calc = wb.create_sheet("산정")
calc.sheet_view.showGridLines = False
for col, w in zip("ABCDE", (4, 44, 18, 10, 56)):
    calc.column_dimensions[col].width = w
hdr(calc.cell(row=1, column=2), "사이징 산정 (검은 셀은 수식, 수정 금지)")
for col in (3, 4, 5):
    calc.cell(row=1, column=col).fill = HDR_FILL

S = {}
crow = 2


def add_calc(key, label, formula, unit="", note="", numfmt="#,##0.0", emphasize=False):
    global crow
    calc.cell(row=crow, column=2, value=label).font = Font(name=ARIAL, bold=emphasize)
    c = calc.cell(row=crow, column=3, value=formula)
    c.font = Font(name=ARIAL, color=BLACK, bold=emphasize)
    c.border = BORDER
    c.number_format = numfmt
    if emphasize:
        c.fill = OUT_FILL
    calc.cell(row=crow, column=4, value=unit).font = Font(name=ARIAL, italic=True, color="808080")
    calc.cell(row=crow, column=5, value=note).font = Font(name=ARIAL, italic=True, color="808080")
    S[key] = f"C{crow}"
    crow += 1


def add_calc_section(text):
    global crow
    section(calc, crow, text)
    crow += 1


def C(key):
    return S[key]


GEN = "General"

add_calc_section("토큰 (A2.2)")
add_calc("in_tok", "요청당 입력 토큰", f"=({V('sys_tok')}+{V('question_tok')}+{V('history_tok')}+{V('chunk_tok')}*{V('topk')})*{V('ko_factor')}", "토큰", numfmt="#,##0")
add_calc("out_eff", "요청당 출력 토큰", f"={V('out_tok')}*{V('ko_factor')}", "토큰", numfmt="#,##0")
add_calc("ctx", "요청당 전체 토큰", f"={C('in_tok')}+{C('out_eff')}", "토큰", numfmt="#,##0")
add_calc("chk_isl", "측정 조건 대비 입력 길이", f'=IF({C("in_tok")}>{V("perf_isl")}*1.1,"측정 조건보다 김: 처리 시간이 짧게 잡혔을 수 있음","측정 조건 이내")', numfmt=GEN)
add_calc("chk_osl", "측정 조건 대비 출력 길이", f'=IF({C("out_eff")}>{V("perf_osl")}*1.1,"측정 조건보다 김: 토큰 간 지연이 커질 수 있음","측정 조건 이내")', numfmt=GEN)

add_calc_section("지연과 처리 시간 (A2.3)")
add_calc("t_req", "요청당 처리 시간", f"=({V('ttft_ms')}+{V('itl_ms')}*MAX({C('out_eff')}-1,0))/1000", "초", "첫 토큰 시간 + 토큰 간 지연 × 출력 토큰")
add_calc("chk_sla", "지연 목표 점검", f'=IF(AND({V("ttft_ms")}<={V("ttft_target")},{V("itl_ms")}<={V("itl_target")}),"충족","미충족: 작동점 동시성을 낮춰 다시 측정")', numfmt=GEN)

add_calc_section("워크로드에서 동시성으로 (A2.1)")
add_calc("dau_v", "일 활성 사용자", f"={V('N_users')}*{V('dau')}", "명", numfmt="#,##0")
add_calc("req_day", "일 요청 수", f"={C('dau_v')}*{V('q_day')}", "건", numfmt="#,##0")
add_calc("peakqps", "피크 초당 요청", f"={C('req_day')}/({V('hours')}*3600)*{V('peak_ratio')}", "req/s", numfmt="#,##0.00")
add_calc("conc_raw", "피크 동시 요청", f"={C('peakqps')}*{C('t_req')}", "요청", "피크 초당 요청 × 요청당 처리 시간")
add_calc("conc_design", "설계 동시성", f"=ROUNDUP({C('conc_raw')}*(1+{V('burst')}),0)", "요청", numfmt="#,##0", emphasize=True)

add_calc_section("복제본 하나의 GPU 메모리 (가이드 02)")
add_calc("w_gb", "가중치 메모리", f"={V('params')}*{V('prec_w')}", "GB")
add_calc("avail_rep", "복제본 가용 메모리", f"={V('gpu_per_rep')}*{V('gpu_mem')}*{V('gpu_util')}-{V('gpu_per_rep')}*{V('overhead_gpu')}", "GB", "GPU 수 × 메모리 × utilization − 오버헤드")
add_calc("fit", "모델 적재 가능", f'=IF({C("w_gb")}<={C("avail_rep")},"예","아니오: 복제본당 GPU를 늘리거나 양자화")', numfmt=GEN)
add_calc("mem_ratio", "GPU 메모리 ÷ 가중치", f"={V('gpu_per_rep')}*{V('gpu_mem')}/{C('w_gb')}", "배", "점검값 2.5 이상 권장", numfmt="0.0")
add_calc("kv_tok", "토큰당 KV 캐시", f"=2*{V('layers')}*{V('kv_heads')}*{V('head_dim')}*{V('prec_kv')}/1073741824", "GiB", numfmt="0.000000")
add_calc("kv_req", "요청당 KV 캐시", f"={C('kv_tok')}*{C('ctx')}", "GiB", numfmt="0.00")
add_calc("conc_mem", "메모리로 담을 수 있는 동시성 상한", f"=IF({C('w_gb')}>={C('avail_rep')},0,FLOOR(({C('avail_rep')}-{C('w_gb')})/{C('kv_req')},1))", "요청", numfmt="#,##0")
add_calc("chk_mem", "작동점 동시성 메모리 점검", f'=IF({V("safe_conc")}<={C("conc_mem")},"정상","작동점 동시성이 메모리 상한을 넘음")', numfmt=GEN)

add_calc_section("복제본과 GPU (가이드 02 2.5절)")
add_calc("rep_base", "부하를 받는 복제본", f"=ROUNDUP({C('conc_design')}/{V('safe_conc')},0)", "", "설계 동시성 ÷ 복제본당 동시성", numfmt="#,##0")
add_calc("rep_total", "총 복제본", f"=MAX({C('rep_base')}+{V('na_plus')},{V('min_replicas')})", "", "N+1과 최소 복제본 2 중 큰 값", numfmt="#,##0", emphasize=True)
add_calc("gpu_llm", "추론 GPU", f"={C('rep_total')}*{V('gpu_per_rep')}", "장", numfmt="#,##0")
add_calc("gpu_total", "사용 GPU 합계", f"={C('gpu_llm')}+{V('embed_gpu')}", "장", numfmt="#,##0", emphasize=True)

add_calc_section("물리 호스트 (가이드 04 4.1절)")
add_calc("chk_tp", "복제본당 GPU와 호스트당 GPU", f'=IF({V("gpu_per_rep")}<={V("gpus_per_host")},"정상","복제본이 호스트를 넘음: 호스트 간 병렬 필요")', numfmt=GEN)
add_calc("hosts_gpu", "GPU 호스트", f"=MAX(ROUNDUP({C('gpu_total')}/{V('gpus_per_host')},0),{V('paif_min')})", "대", "PAIF 최소 3대 반영", numfmt="#,##0", emphasize=True)
add_calc("gpu_installed", "장착 GPU", f"={C('hosts_gpu')}*{V('gpus_per_host')}", "장", "하드웨어와 전력 산정 기준", numfmt="#,##0")
add_calc("hosts_total", "물리 호스트 합계", f'={C("hosts_gpu")}+IF({V("deploy")}="분리형",{V("sep_hosts")},0)', "대", numfmt="#,##0", emphasize=True)
add_calc("ram_lo", "GPU 호스트당 RAM 출발값(하한)", f"={V('gpus_per_host')}*{V('gpu_mem')}*2", "GB", "GPU 메모리 합의 2–3배 (03 3.1절)", numfmt="#,##0")
add_calc("ram_hi", "GPU 호스트당 RAM 출발값(상한)", f"={V('gpus_per_host')}*{V('gpu_mem')}*3", "GB", numfmt="#,##0")

add_calc_section("VKS 노드 (가이드 04)")
add_calc("gpu_nodes", "GPU 워커 노드", f"={C('rep_total')}+IF({V('embed_gpu')}>0,1,0)", "VM", "복제본당 1노드 + 임베딩 노드", numfmt="#,##0")
add_calc("gpu_nodes_max", "GPU 워커 노드(오토스케일 상한)", f"=ROUNDUP({C('gpu_nodes')}*(1+{V('node_head')}),0)", "VM", numfmt="#,##0")
add_calc("cluster_nodes", "클러스터 노드 합계", f"={C('gpu_nodes_max')}+{V('gen_workers')}+{V('cp_nodes')}", "VM", numfmt="#,##0", emphasize=True)
add_calc("total_nodes", "전체 노드(전 클러스터)", f"={C('cluster_nodes')}*{V('clusters')}", "VM", numfmt="#,##0")
add_calc("chk_cl", "Supervisor 클러스터 한도", f'=IF({V("clusters")}<={V("sup_cl_lim")},"여유","초과")', numfmt=GEN)
add_calc("chk_node", "Supervisor 노드 한도", f'=IF({C("total_nodes")}<={V("sup_node_lim")},"여유","초과")', numfmt=GEN)

add_calc_section("스토리지 (가이드 05)")
add_calc("st_model", "모델 아티팩트", f"={C('w_gb')}*{V('ver_keep')}", "GB", numfmt="#,##0")
add_calc("st_corpus", "원문과 전처리 사본", f"={V('corpus_gb')}*{V('corpus_mult')}", "GB", numfmt="#,##0")
add_calc("st_vec", "벡터 인덱스(원시 + HNSW)", f"={V('vec_count')}*{V('vec_dim')}*{V('vec_bytes')}/1073741824*(1+{V('hnsw_mult')})", "GB", numfmt="#,##0")
add_calc("st_rag_ratio", "공식 비율로 본 RAG 저장 상한", f"={V('corpus_gb')}*{V('rag_ratio_hi')}", "GB", "원문 × 10 (05 5.5절 교차 점검)", numfmt="#,##0")
add_calc("st_logical", "논리 합계(구성요소 합산)", f"={C('st_model')}+{V('img_gb')}+{C('st_corpus')}+{C('st_vec')}+{V('logs_gb')}", "GB", numfmt="#,##0")
add_calc("st_logical_up", "논리 합계(공식 비율 상한 적용)", f"={C('st_model')}+{V('img_gb')}+MAX({C('st_corpus')}+{C('st_vec')},{C('st_rag_ratio')})+{V('logs_gb')}", "GB", numfmt="#,##0")
add_calc("st_avail", "필요 가용 용량(구성요소 합산)", f"={C('st_logical')}*{V('prot')}/{V('dedup')}", "GB", numfmt="#,##0", emphasize=True)
add_calc("st_avail_up", "필요 가용 용량(예산 상한)", f"={C('st_logical_up')}*{V('prot')}/{V('dedup')}", "GB", "두 값이 크게 다르면 원문과 벡터 수를 표본 실측", numfmt="#,##0", emphasize=True)

# ---------- TCO ----------
tco = wb.create_sheet("TCO")
tco.sheet_view.showGridLines = False
for col, w in zip("ABCDEF", (4, 34, 16, 18, 22, 44)):
    tco.column_dimensions[col].width = w
hdr(tco.cell(row=1, column=2), "TCO 수량 골격 (금액은 견적 단가로 채움, 부록 A3)")
for col in (3, 4, 5, 6):
    tco.cell(row=1, column=col).fill = HDR_FILL

trow = 2


def t_calc(label, formula, unit="", note="", numfmt="#,##0"):
    global trow
    tco.cell(row=trow, column=2, value=label).font = Font(name=ARIAL)
    c = tco.cell(row=trow, column=3, value=formula)
    c.font = Font(name=ARIAL, color=BLACK)
    c.number_format = numfmt
    c.border = BORDER
    tco.cell(row=trow, column=4, value=unit).font = Font(name=ARIAL, italic=True, color="808080")
    tco.cell(row=trow, column=5, value=note).font = Font(name=ARIAL, italic=True, color="808080")
    ref = f"C{trow}"
    trow += 1
    return ref


def X(key):
    return f"'산정'!{S[key]}"


section(tco, trow, "수량 산정")
trow += 1
r_coreph = t_calc("호스트당 라이선스 코어", f"=MAX({V('cores_host')},{V('sockets')}*{V('core_min')})", "코어", "MAX(실제 코어, 소켓 × 최소수량)")
r_cores = t_calc("총 라이선스 코어", f"={X('hosts_total')}*{r_coreph}", "코어", "물리 호스트 합계 기준 (07 7.2절)")
r_nvaie = t_calc("NVAIE 대상 GPU", f'=IF(OR({V("alloc_mode")}="vGPU",{V("nim_used")}="예"),{X("gpu_installed")},0)', "장", "vGPU나 NIM을 쓰면 장착 GPU 전수, DirectPath와 오픈소스 스택이면 0 (07 7.2절)")

trow += 1
section(tco, trow, "비용 항목 (노란 칸에 견적 단가를 넣으면 소계 계산)")
trow += 1
for col, txt in zip((2, 3, 4, 5, 6), ("항목", "수량", "단가(견적 입력)", "소계", "메모")):
    cc = tco.cell(row=trow, column=col, value=txt)
    cc.font = Font(name=ARIAL, bold=True)
    cc.fill = SEC_FILL
trow += 1


def cost_row(label, qty_formula, note=""):
    global trow
    tco.cell(row=trow, column=2, value=label).font = Font(name=ARIAL)
    q = tco.cell(row=trow, column=3, value=qty_formula)
    q.font = Font(name=ARIAL, color=BLACK)
    q.number_format = "#,##0"
    q.border = BORDER
    p = tco.cell(row=trow, column=4)
    p.fill = YEL
    p.border = BORDER
    p.number_format = "#,##0"
    sub = tco.cell(row=trow, column=5, value=f'=IF(D{trow}="","견적 입력 필요",C{trow}*D{trow})')
    sub.font = Font(name=ARIAL)
    sub.number_format = "#,##0"
    sub.border = BORDER
    tco.cell(row=trow, column=6, value=note).font = Font(name=ARIAL, italic=True, color="808080")
    trow += 1


cost_row("VCF 코어 구독", f"={r_cores}", "코어/년, PAIF 포함(이중 계상 금지)")
cost_row("NVAIE(GPU당)", f"={r_nvaie}", "GPU/년, NVIDIA 별도. 0이면 불필요")
cost_row("DSM", "=1", "VCF 권한 조건 확인 (A3.1)")
cost_row("GPU", f"={X('gpu_installed')}", "장착 GPU 기준, 상각연수로 나눔 (07 7.3절)")
cost_row("GPU 서버", f"={X('hosts_gpu')}", "물리 서버 수, 상각연수로 나눔")
cost_row("비GPU 서버", f'=IF({V("deploy")}="분리형",{V("sep_hosts")},0)', "분리형일 때만")
cost_row("스토리지(GB)", f"={X('st_avail_up')}", "예산 상한 기준 (05 5.5절)")
cost_row("네트워크와 스위치", "=1", "토폴로지 (05 5.4절)")
cost_row("전력(연)", f"={X('gpu_installed')}", "GPU 소비전력 × PUE (07 7.5절)")
cost_row("유지보수와 지원", "=1", "계약")
cost_row("인력(선택)", "=0", "국내는 보통 제외. 넣을 때는 온프레미스와 클라우드에 같은 기준 적용")
cost_row("도입과 이행", "=1", "일회성")

note_c = tco.cell(row=trow + 1, column=2,
                  value="단가(노란 칸)는 이 워크북이 제시하지 않습니다. 부록 A3 견적 요청 체크리스트로 채우고 출처를 기록하세요.")
note_c.font = Font(name=ARIAL, italic=True, color="C00000")

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sizing-workbook.xlsx")
wb.save(out)
print("SAVED:", out)

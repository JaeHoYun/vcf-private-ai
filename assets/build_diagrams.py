"""저장소 Markdown 문서에 수록하는 다이어그램을 라이트, 다크 SVG 2종으로 생성한다.

실행: python3 assets/build_diagrams.py
문서는 <picture> 요소로 GitHub 테마에 맞는 파일(-light.svg, -dark.svg)을 표시한다.
문구나 배치를 고칠 때는 SVG를 직접 수정하지 않고 이 스크립트를 수정한 뒤 다시 실행한다.
"""
import os
from xml.sax.saxutils import escape

OUT = os.path.dirname(os.path.abspath(__file__))

# GitHub Primer 색상 기준
THEMES = {
    "light": dict(
        bg="#ffffff", text="#1f2328", muted="#59636e", arrow="#59636e", frame="#afb8c1",
        neutral_fill="#f6f8fa", neutral_stroke="#d0d7de", neutral_accent="#59636e",
        blue_fill="#ddf4ff", blue_stroke="#54aeff", blue_accent="#0969da",
        purple_fill="#fbefff", purple_stroke="#c297ff", purple_accent="#8250df",
        green_fill="#dafbe1", green_stroke="#4ac26b", green_accent="#1a7f37",
        orange_fill="#fff1e5", orange_stroke="#fb8f44", orange_accent="#bc4c00",
    ),
    "dark": dict(
        bg="#0d1117", text="#f0f6fc", muted="#9198a1", arrow="#9198a1", frame="#484f58",
        neutral_fill="#151b23", neutral_stroke="#3d444d", neutral_accent="#9198a1",
        blue_fill="#11284a", blue_stroke="#1f6feb", blue_accent="#4493f8",
        purple_fill="#231c35", purple_stroke="#8957e5", purple_accent="#ab7df8",
        green_fill="#122a1c", green_stroke="#2f9e4f", green_accent="#3fb950",
        orange_fill="#2d1c0f", orange_stroke="#bd561d", orange_accent="#f0883e",
    ),
}
FONT = ("-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Apple SD Gothic Neo', 'Malgun Gothic', "
        "'Noto Sans KR', 'Noto Sans CJK KR', Helvetica, Arial, sans-serif")

# 줄 스타일: 글자 크기, 굵기, 색상 토큰, 줄 높이
STY = {
    "big": (18, 700, "text", 24),
    "title": (15, 700, "text", 21),
    "sub": (13, 400, "muted", 18),
    "body": (13, 400, "text", 18),
}


def text_width(s, size):
    """배지 폭 계산용 근사치."""
    return sum(size * (1.0 if ord(c) > 0x2E80 else 0.6) for c in s)


class Diagram:
    def __init__(self, w, h, title, desc, t):
        self.w, self.h, self.t = w, h, t
        self.title, self.desc = title, desc
        self.o = []

    def c(self, key):
        return self.t.get(key, key)

    def text(self, x, y, s, size=13, weight=400, color="text", anchor="start", halo=False):
        attrs = f' font-size="{size}"'
        if weight != 400:
            attrs += f' font-weight="{weight}"'
        if anchor != "start":
            attrs += f' text-anchor="{anchor}"'
        attrs += f' fill="{self.c(color)}"'
        if halo:
            attrs += f' stroke="{self.t["bg"]}" stroke-width="4" stroke-linejoin="round" paint-order="stroke"'
        self.o.append(f'<text x="{x:g}" y="{y:g}"{attrs}>{escape(s)}</text>')

    def badge(self, x, y, s, kind, anchor="start"):
        """(x, y)는 배지 왼쪽 위. anchor가 middle이면 x가 중심."""
        bw = text_width(s, 12) + 14
        if anchor == "middle":
            x -= bw / 2
        self.o.append(f'<rect x="{x:g}" y="{y:g}" width="{bw:g}" height="20" rx="10" fill="{self.c(kind + "_accent")}"/>')
        self.text(x + bw / 2, y + 14.5, s, 12, 700, self.t["bg"], "middle")
        return bw

    def lines(self, x, y, w, h, lines, align="middle", badge=None, kind="neutral"):
        """lines: [(문자열, 스타일)]. badge가 있으면 가운데 정렬은 첫 줄 위에, 왼쪽 정렬은 첫 줄 앞에 표시."""
        total = sum(STY[st][3] for _, st in lines)
        if badge and align == "middle":
            total += 26
        cy = y + (h - total) / 2
        if badge and align == "middle":
            self.badge(x + w / 2, cy, badge, kind, "middle")
            cy += 26
        for i, (s, st) in enumerate(lines):
            size, wt, col, lh = STY[st]
            base = cy + lh * 0.74
            if align == "middle":
                self.text(x + w / 2, base, s, size, wt, col, "middle")
            else:
                tx = x + 14
                if badge and i == 0:
                    tx += self.badge(tx, base - 15, badge, kind) + 8
                self.text(tx, base, s, size, wt, col)
            cy += lh

    def box(self, x, y, w, h, lines, kind="neutral", dashed=False, align="middle", badge=None, fill=True):
        da = ' stroke-dasharray="6 4"' if dashed else ""
        f = self.c(kind + "_fill") if fill else "none"
        self.o.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="8" fill="{f}" '
                      f'stroke="{self.c(kind + "_stroke")}" stroke-width="1.5"{da}/>')
        self.lines(x, y, w, h, lines, align, badge, kind)

    def cyl(self, x, y, w, h, lines, kind="green"):
        ry = 8
        f, s = self.c(kind + "_fill"), self.c(kind + "_stroke")
        self.o.append(f'<path d="M{x:g},{y + ry:g} A{w / 2:g},{ry} 0 0 1 {x + w:g},{y + ry:g} V{y + h - ry:g} '
                      f'A{w / 2:g},{ry} 0 0 1 {x:g},{y + h - ry:g} Z" fill="{f}" stroke="{s}" stroke-width="1.5"/>')
        self.o.append(f'<path d="M{x:g},{y + ry:g} A{w / 2:g},{ry} 0 0 0 {x + w:g},{y + ry:g}" '
                      f'fill="none" stroke="{s}" stroke-width="1.5"/>')
        self.lines(x, y + 2 * ry, w, h - 2 * ry, lines)

    def frame(self, x, y, w, h, title=None, dashed=False, kind=None, note=None, tx=None):
        """kind가 있으면 해당 색상의 테두리, note는 제목 줄 오른쪽 끝에 표시. tx는 제목 시작 x(화살표 회피용)."""
        da = ' stroke-dasharray="6 4"' if dashed else ""
        stroke = self.c(kind + "_stroke") if kind else self.t["frame"]
        sw = 2 if kind else 1.5
        self.o.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="10" fill="none" '
                      f'stroke="{stroke}" stroke-width="{sw}"{da}/>')
        if title:
            self.text(tx if tx is not None else x + 14, y + 22, title, 13, 700, (kind + "_accent") if kind else "muted")
        if note:
            self.text(x + w - 14, y + 22, note, 13, 700, (kind + "_accent") if kind else "muted", "end")

    def arrow(self, pts, dashed=False, both=False, head=True):
        d = "M" + " L".join(f"{x:g},{y:g}" for x, y in pts)
        attrs = ' stroke-dasharray="5 4"' if dashed else ""
        if head:
            attrs += ' marker-end="url(#ah)"'
        if both:
            attrs += ' marker-start="url(#ah)"'
        self.o.append(f'<path d="{d}" fill="none" stroke="{self.t["arrow"]}" stroke-width="1.5"{attrs}/>')

    def label(self, x, y, lines, anchor="start", step=None):
        """화살표 설명. step이 있으면 번호 원을 앞에 표시(왼쪽 정렬 전용)."""
        if isinstance(lines, str):
            lines = [lines]
        if step is not None:
            self.o.append(f'<circle cx="{x + 9:g}" cy="{y - 4.5:g}" r="9" fill="{self.t["blue_accent"]}" '
                          f'stroke="{self.t["bg"]}" stroke-width="2"/>')
            self.text(x + 9, y, str(step), 11, 700, self.t["bg"], "middle")
            x += 22
        for i, s in enumerate(lines):
            self.text(x, y + i * 17, s, 12, 400, "muted", anchor, halo=True)

    def legend(self, x, y, items):
        """items: [(kind, 설명)]. kind가 dashed면 점선 사각형, line-dashed면 점선 화살표."""
        for kind, s in items:
            if kind == "title":
                self.text(x, y, s, 13, 700, "muted")
                x += text_width(s, 13) + 24
                continue
            if kind == "dashed":
                self.o.append(f'<rect x="{x:g}" y="{y - 12:g}" width="18" height="14" rx="3" fill="none" '
                              f'stroke="{self.t["frame"]}" stroke-width="1.5" stroke-dasharray="4 3"/>')
            elif kind == "line-dashed":
                self.arrow([(x, y - 5), (x + 18, y - 5)], dashed=True)
            else:
                self.o.append(f'<rect x="{x:g}" y="{y - 12:g}" width="18" height="14" rx="3" '
                              f'fill="{self.c(kind + "_fill")}" stroke="{self.c(kind + "_stroke")}" stroke-width="1.5"/>')
            self.text(x + 26, y, s, 12, 400, "muted")
            x += 26 + text_width(s, 12) + 24

    def render(self):
        head = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" font-family="{FONT}" role="img" aria-labelledby="t d">',
            f'<title id="t">{escape(self.title)}</title>',
            f'<desc id="d">{escape(self.desc)}</desc>',
            '<defs><marker id="ah" viewBox="0 0 10 10" refX="10" refY="5" markerUnits="userSpaceOnUse" '
            f'markerWidth="10" markerHeight="10" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
            f'fill="{self.t["arrow"]}"/></marker></defs>',
        ]
        return "\n".join(head + self.o + ["</svg>"]) + "\n"


# README: 시리즈 4계층 구조
def series_layers(t):
    d = Diagram(968, 536, "VCF Private AI 4계층 구조",
                "위에서 아래로 실행(Agents, MCP), 서비스(PAIS), AI 인프라(PAIF 코어 기능 계층), 플랫폼(VCF)의 4계층. "
                "보안과 거버넌스(⑤), 사이징, 용량, 비용(⑥)은 전 계층에 공통으로 적용되고, "
                "통합 설계(⑦)가 이 결정을 하나의 플랫폼 설계로 종합한다.", t)
    sx, sw, rh, gap, y0 = 132, 544, 88, 12, 52
    x5, xw = sx + sw + 16, 116
    x6 = x5 + xw + 12
    rows = [
        ("실행", "Agents, MCP", "실행 계층, 시리즈 본편 범위 밖", "모델이 사내 데이터와 도구에 연결되어 업무 수행", "앱 가이드", True),
        ("서비스", "PAIS", "Private AI Services", "모델 서빙, RAG, Agent Builder, MCP (관리형)", "시리즈 ③④", False),
        ("AI 인프라", "PAIF 코어 기능 계층", "Private AI Foundation with NVIDIA", "GPU, 드라이버, 모델, 벡터 DB 표준화", "시리즈 ①②", False),
        ("플랫폼", "VCF", "VMware Cloud Foundation", "컴퓨트, 스토리지, 네트워크, 쿠버네티스(VKS)", "시리즈 ①", False),
    ]
    d.text(sx, 34, "4계층 (상위 계층은 하위 계층을 기반으로 동작)", 13, 600, "muted")
    d.text(x5, 34, "전 계층 공통", 13, 600, "muted")
    for i, (role, name, sub, desc, chip, ext) in enumerate(rows):
        y = y0 + i * (rh + gap)
        d.text(sx - 16, y + rh / 2 + 5, role, 14, 600, "muted", "end")
        d.box(sx, y, sw, rh, [], dashed=ext, fill=not ext)
        d.text(sx + 20, y + 30, name, 18, 700)
        d.text(sx + 20, y + 52, sub, 13, 400, "muted")
        d.text(sx + 20, y + 73, desc, 14)
        cw = 96
        cx, cy = sx + sw - 16 - cw, y + 14
        d.o.append(f'<rect x="{cx}" y="{cy}" width="{cw}" height="26" rx="13" fill="{t["blue_fill"]}"/>')
        d.text(cx + cw / 2, cy + 18, chip, 13, 600, "blue_accent", "middle")
    bh = 4 * rh + 3 * gap
    for x, num, ls in ((x5, "⑤", ["보안,", "거버넌스"]), (x6, "⑥", ["사이징,", "용량, 비용"])):
        d.box(x, y0, xw, bh, [], "purple")
        cx, cy = x + xw / 2, y0 + bh / 2
        d.text(cx, cy - 22, num, 24, 700, "purple_accent", "middle")
        for j, s in enumerate(ls):
            d.text(cx, cy + 10 + j * 22, s, 15, 600, "text", "middle")
    dy = y0 + bh + 20
    d.text(sx - 16, dy + 33, "종합", 14, 600, "muted", "end")
    d.box(sx, dy, x6 + xw - sx, 56, [], "green")
    d.o.append(f'<text x="{sx + 20}" y="{dy + 34}" font-size="16" fill="{t["text"]}">'
               f'<tspan font-weight="700" fill="{t["green_accent"]}">⑦ 통합 설계</tspan>'
               f'<tspan dx="14">4계층과 ⑤⑥의 결정을 하나의 플랫폼 설계로 종합</tspan></text>')
    return d


# ④ 01: RAG 엔드투엔드 레퍼런스 아키텍처
def rag_reference_architecture(t):
    d = Diagram(1120, 784, "RAG 엔드투엔드 레퍼런스 아키텍처",
                "왼쪽은 인덱싱 타임(배치), 오른쪽은 쿼리 타임(요청마다)의 4-Tier 앱 계층, 아래는 VCF 9.1.1, PAIS 3.0 플랫폼. "
                "인덱싱은 사내 문서를 로딩, 청킹, 태깅한 뒤 임베딩 모델로 벡터화해 pgvector에 적재한다. "
                "쿼리는 오케스트레이션이 PAIS API Gateway로 질문을 보내면 질문 임베딩, 권한 필터를 선적용한 검색, "
                "리랭킹, 프롬프트 조립과 생성을 거쳐 출처 포함 답변을 스트리밍으로 반환한다.", t)
    # 인덱싱 타임
    d.frame(24, 24, 516, 340, "인덱싱 타임, 배치 (02)")
    d.box(48, 60, 240, 72, [("사내 문서", "title"), ("PDF, Office, 위키, 티켓, 보호 문서", "sub")])
    d.box(336, 60, 180, 72, [("보호 문서 복호화 존", "title"), ("격리, 서비스 신원,", "sub"),
                             ("문서 단위 권한 확인", "sub")], "purple")
    d.box(48, 172, 240, 60, [("로딩, 청킹", "title"), ("메타데이터, ACL 태깅", "sub")])
    d.box(48, 280, 240, 60, [("임베딩 (배치)", "title"), ("청크를 벡터로 변환", "sub")])
    d.arrow([(288, 96), (336, 96)])
    d.label(312, 88, "암호문", "middle")
    d.arrow([(168, 132), (168, 172)])
    d.label(176, 157, "평문")
    d.arrow([(426, 132), (426, 202), (288, 202)])
    d.arrow([(168, 232), (168, 280)])
    # 쿼리 타임 앱 계층
    d.frame(580, 24, 516, 340, "쿼리 타임, 요청마다: 4-Tier 앱 계층 (05)")
    d.box(680, 60, 392, 56, [("클라이언트", "title"), ("웹, 모바일, 메신저 봇", "sub")], "blue")
    d.box(680, 148, 392, 56, [("BFF, 게이트웨이", "title"), ("인증, 세션, 요청 속도 제한", "sub")], "blue")
    d.box(680, 236, 392, 108, [("RAG 오케스트레이션", "title"), ("검색(03) + 추론(04)", "sub"),
                               ("경로 A: Agent 호출, 경로 B: 직접 조립", "sub")], "blue")
    d.arrow([(876, 116), (876, 148)])
    d.arrow([(876, 204), (876, 236)])
    # 플랫폼
    d.frame(24, 400, 1072, 360)
    d.frame(36, 456, 1048, 252, dashed=True)
    d.box(48, 470, 196, 80, [("임베딩 모델", "title"), ("vLLM, Infinity", "sub")], "orange")
    d.cyl(284, 466, 196, 88, [("DSM PostgreSQL", "title"), ("+ pgvector", "sub")])
    d.box(580, 470, 196, 80, [("리랭커 모델", "title")], "orange")
    d.box(816, 470, 196, 80, [("완성(LLM) 모델", "title"), ("vLLM", "sub")], "orange")
    d.box(48, 640, 1024, 52, [("PAIS API Gateway (OpenAI 호환), MCP Tools Registry", "title")], "blue")
    # 인덱싱 흐름
    d.arrow([(150, 340), (150, 470)], both=True)
    d.label(160, 388, "임베딩 호출, 벡터 반환")
    d.arrow([(288, 310), (382, 310), (382, 466)])
    d.label(392, 388, "벡터, 원문, 메타데이터 적재")
    # 쿼리 흐름
    d.arrow([(1052, 344), (1052, 640)])
    d.label(984, 388, "질문", step=1)
    d.arrow([(146, 640), (146, 550)])
    d.label(156, 600, "질문 임베딩", step=2)
    d.arrow([(382, 640), (382, 554)])
    d.label(392, 592, ["유사도, 하이브리드 검색", "권한 필터 선적용"], step=3)
    d.arrow([(480, 510), (580, 510)])
    d.label(490, 500, "후보 청크", step=4)
    d.arrow([(678, 550), (678, 640)])
    d.label(688, 600, "top-k 근거", step=5)
    d.arrow([(914, 640), (914, 550)])
    d.label(924, 592, ["질문 + 근거", "프롬프트"], step=6)
    d.arrow([(914, 470), (914, 344)])
    d.label(738, 388, "출처 포함 답변 (스트리밍)", step=7)
    d.legend(48, 738, [("title", "VCF 9.1.1, PAIS 3.0 플랫폼"),
                       ("orange", "GPU 노드, PAIS Model Runtime (③)"),
                       ("green", "데이터 계층 (②)"),
                       ("dashed", "경로 A에서 Agent Builder가 대신 수행하는 범위")])
    return d


# ⑤ 00: 요청 경로상의 통제 지점
def security_control_points(t):
    d = Diagram(1020, 830, "요청 경로상의 통제 지점",
                "사용자 요청은 CP1 0계층 경계, CP2 1계층 AI 게이트웨이(선택), CP3 앱 BFF, CP4 오케스트레이션과 에이전트를 지난다. "
                "CP4에서 CP5 도구 게이트웨이를 거쳐 사내 시스템과 MCP 서버로, CP6 검색단 권한 필터를 거쳐 지식베이스로, "
                "CP7 2계층 PAIS 서빙 게이트웨이를 거쳐 Model Runtime으로 갈라진다. 원격 모델 호출은 CP8 반출 경계를 지나고, "
                "응답은 CP9 출력 가드를 거쳐 CP3으로 반환된다. CP3, CP4, CP7은 CP10 트레이스와 감사로 기록을 보낸다.", t)
    c1, c2, c3, cw = 34, 314, 594, 250
    xb, bw = 880, 124
    rows = [24, 108, 216, 324, 432, 564, 672]
    h = 72
    d.box(c2, rows[0], cw, 48, [("사용자와 클라이언트", "title")])
    d.box(c2, rows[1], cw, h, [("0계층 경계", "title"), ("Avi L7, WAF, TLS, 기존 API 관리", "body")],
          "blue", align="start", badge="CP1")
    d.box(c2, rows[2], cw, h, [("1계층 AI 게이트웨이", "title"), ("키와 팀 예산, 레이트리밋, 라우팅", "body")],
          "blue", dashed=True, align="start", badge="CP2")
    d.box(c2, rows[3], cw, h, [("앱 BFF", "title"), ("사용자 인증, 세션, 입력 가드", "body")],
          "blue", align="start", badge="CP3")
    d.box(c2, rows[4], cw, h, [("오케스트레이션과 에이전트", "title"), ("자율성 상한, 승인 게이트", "body")],
          "blue", align="start", badge="CP4")
    d.box(c1, rows[3], cw, h, [("출력 가드", "title"), ("PII, 누출, 유해 출력", "body")],
          "blue", align="start", badge="CP9")
    d.box(c1, rows[5], cw, h, [("도구 게이트웨이", "title"), ("MCP 승인 목록, 호출 단위 인가", "body")],
          "blue", align="start", badge="CP5")
    d.box(c2, rows[5], cw, h, [("검색단 권한 필터", "title"), ("권한 밖 문서를 프롬프트에서 제외", "body")],
          "blue", align="start", badge="CP6")
    d.box(c3, rows[5], cw, h, [("PAIS 서빙 게이트웨이", "title"), ("2계층, 토큰 검증, 모델 라우팅", "body")],
          "blue", align="start", badge="CP7")
    d.box(c1, rows[6], cw, 60, [("사내 시스템, MCP 서버", "title")])
    d.cyl(c2, rows[6] - 4, cw, 68, [("지식베이스, pgvector", "title")])
    d.box(c3, rows[6], cw, 60, [("Model Runtime", "title"), ("로컬, 공유, 원격", "sub")], "orange")
    d.box(xb, rows[6], bw, 60, [("원격 모델", "title"), ("반출 경계", "title")], "blue", dashed=True)
    d.badge(xb + bw / 2, rows[6] - 26, "CP8", "blue", "middle")
    d.box(xb, rows[3], bw, rows[5] + h - rows[3],
          [("트레이스와", "title"), ("감사", "title"), ("OTel,", "sub"), ("VCF Operations,", "sub"), ("SIEM", "sub")],
          "purple", badge="CP10")
    mx = c2 + cw / 2
    # 요청 경로
    for a, b in ((rows[0] + 48, rows[1]), (rows[1] + h, rows[2]), (rows[2] + h, rows[3]), (rows[3] + h, rows[4])):
        d.arrow([(mx, a), (mx, b)])
    fy = rows[4] + h + 30
    d.arrow([(mx, rows[4] + h), (mx, rows[5])])
    d.arrow([(mx, fy), (c1 + cw / 2, fy), (c1 + cw / 2, rows[5])])
    d.arrow([(mx, fy), (c3 + cw / 2, fy), (c3 + cw / 2, rows[5])])
    for cx in (c1, c2, c3):
        d.arrow([(cx + cw / 2, rows[5] + h), (cx + cw / 2, rows[6] - (4 if cx == c2 else 0))])
    # 원격 반출
    d.arrow([(c3 + cw, rows[6] + 30), (xb, rows[6] + 30)], dashed=True)
    # 응답 경로
    ry = rows[6] + 60 + 36
    d.arrow([(c3 + cw / 2 - 40, rows[6] + 60), (c3 + cw / 2 - 40, ry), (16, ry), (16, rows[3] + 36), (c1, rows[3] + 36)])
    d.label(c2 + cw / 2, ry - 8, "응답 경로: Model Runtime에서 CP9를 거쳐 CP3으로 반환", "middle")
    d.arrow([(c1 + cw, rows[3] + 36), (c2, rows[3] + 36)])
    # 감사 수집
    d.arrow([(c2 + cw, rows[3] + 36), (xb, rows[3] + 36)], dashed=True)
    d.arrow([(c2 + cw, rows[4] + 36), (xb, rows[4] + 36)], dashed=True)
    d.arrow([(c3 + cw, rows[5] + 36), (xb, rows[5] + 36)], dashed=True)
    d.legend(34, 818, [("blue", "통제 지점(CP)"), ("dashed", "선택 구성 또는 경계"),
                       ("line-dashed", "감사 기록 수집, 원격 반출")])
    return d


# ⑦ 02: 중(Standard) 블루프린트 논리 토폴로지
def design_standard_blueprint(t):
    d = Diagram(1000, 714, "중(Standard) 블루프린트 논리 토폴로지",
                "관리 도메인(vCenter, NSX Manager, VCF Automation, Operations)과 워크로드 도메인(표준 토폴로지, D1)을 분리한다. "
                "사내 사용자와 앱의 요청은 AVI 로드밸런서(D6)를 거쳐 VKS 클러스터(D3)의 PAIS API Gateway로 들어가고, "
                "Gateway는 MIG로 분할한 GPU 노드 풀(D2)의 PAIS Model Runtime(D4)과 DSM PostgreSQL, pgvector(D8)를 호출한다. "
                "외부 IdP(D11)가 인증을, 이그레스 프록시(D12)가 외부 모델 허브 연결을, vSAN(D7)이 가중치, 캐시, 데이터 저장을, "
                "NSX가 오버레이, VPC, 마이크로세그멘테이션 경계(D5, D10)를 맡는다.", t)
    # 외부
    d.box(510, 24, 200, 56, [("사내 사용자, 앱", "title")])
    d.box(740, 24, 236, 56, [("외부 IdP", "title"), ("페더레이션 (D11)", "sub")])
    # 관리 도메인
    d.frame(24, 120, 196, 260, "관리 도메인")
    d.box(40, 156, 164, 48, [("vCenter", "title")])
    d.box(40, 226, 164, 48, [("NSX Manager", "title")])
    d.box(40, 296, 164, 60, [("VCF Automation,", "title"), ("Operations", "title")])
    d.box(24, 440, 196, 64, [("이그레스 프록시 (D12)", "title"), ("→ 외부 모델 허브", "sub")])
    # 워크로드 도메인
    d.frame(340, 120, 636, 570, "워크로드 도메인, 표준 토폴로지 (D1)")
    d.box(510, 164, 200, 48, [("AVI 로드밸런서 (D6)", "title")], "blue")
    d.frame(364, 248, 588, 312, "VKS 클러스터 (D3)")
    d.box(510, 284, 200, 56, [("PAIS API Gateway", "title"), ("OpenAI 호환", "sub")], "blue")
    d.frame(388, 392, 252, 148, "GPU 노드 풀, MIG 분할 (D2)")
    d.box(408, 432, 212, 88, [("PAIS Model Runtime", "title"), ("vLLM (+NIM, D4)", "sub")], "orange")
    d.cyl(700, 420, 228, 100, [("DSM PostgreSQL", "title"), ("+ pgvector (D8)", "sub")])
    d.cyl(450, 600, 320, 68, [("vSAN 스토리지 (D7)", "title")], "neutral")
    # 흐름
    d.arrow([(610, 80), (610, 164)])
    d.arrow([(610, 212), (610, 284)])
    d.arrow([(590, 340), (590, 432)])
    d.arrow([(680, 340), (680, 380), (814, 380), (814, 420)])
    d.arrow([(858, 80), (858, 312), (710, 312)], dashed=True)
    d.label(866, 200, "인증")
    d.arrow([(408, 472), (220, 472)])
    d.arrow([(514, 520), (514, 600)], dashed=True)
    d.label(506, 584, "가중치, 캐시", "end")
    d.arrow([(814, 520), (814, 634), (770, 634)], dashed=True)
    d.label(822, 584, "데이터")
    d.arrow([(204, 250), (340, 250)], dashed=True)
    d.label(272, 205, ["오버레이, VPC,", "마이크로세그 경계", "(D5, D10)"], "middle")
    d.arrow([(204, 326), (364, 326)], dashed=True)
    d.label(284, 316, "프로비저닝, 정책", "middle")
    return d


# ⑦ 04: 게이트웨이 3계층
def design_gateway_tiers(t):
    d = Diagram(1022, 410, "게이트웨이 3계층",
                "앱과 BFF의 요청은 0계층 경계(Avi VIP, WAF, TLS 종단 또는 기존 API 관리 플랫폼), "
                "1계층 AI 게이트웨이(선택), 2계층 PAIS 서빙 게이트웨이를 거쳐 GPU 워커 노드의 Model Runtime에 도달한다. "
                "1계층이 없으면 0계층이 2계층에 직결하고 호출 빈도 통제는 앱이 맡는다. "
                "원격 클라우드 모델은 1계층에서 InferenceGatewayRoute를 거쳐 호출하며 NSX egress 허용이 필요하다.", t)
    y, h = 100, 150
    d.box(20, y, 140, h, [("앱, BFF", "title"), ("VKS 앱", "sub"), ("네임스페이스", "sub")])
    d.box(188, y, 190, h, [("경계", "title"), ("Avi VIP, WAF,", "body"), ("TLS 종단, 또는 기존", "body"),
                           ("API 관리 플랫폼", "body")], "blue", badge="0계층")
    d.box(406, y, 210, h, [("AI 게이트웨이 (선택)", "title"), ("GPU 없는 VKS 네임스페이스,", "body"),
                           ("레플리카 2+", "body"), ("키와 팀 예산, 별칭 라우팅,", "body"), ("캐시, 가드레일 훅", "body")],
          "blue", dashed=True, badge="1계층")
    d.box(644, y, 190, h, [("PAIS 서빙 게이트웨이", "title"), ("인증과 인가,", "body"), ("복제본 LB, mTLS", "body")],
          "blue", badge="2계층")
    d.box(862, y, 140, h, [("Model Runtime", "title"), ("GPU 워커 노드", "sub")], "orange")
    for a, b in ((160, 188), (378, 406), (616, 644), (834, 862)):
        d.arrow([(a, y + h / 2), (b, y + h / 2)])
    d.arrow([(283, y), (283, 56), (739, 56), (739, y)], dashed=True)
    d.label(511, 46, "1계층이 없으면 직결, 호출 빈도 통제는 앱", "middle")
    d.box(406, 330, 210, 56, [("원격 클라우드 모델", "title")])
    d.arrow([(511, y + h), (511, 330)], dashed=True)
    d.label(521, 284, ["InferenceGatewayRoute 경유,", "NSX egress 허용 필요"])
    return d



# ① 02: PAIF 논리 계층 구조
def infra_paif_layers(t):
    d = Diagram(1120, 836, "PAIF 논리 계층 구조",
                "위에서 아래로 고객 AI 앱, PAIS 서비스 계층, PAIF 코어 기능 계층, VCF 플랫폼의 논리 계층이다. "
                "고객 AI 앱은 PAIF 밖에서 PAIS의 OpenAI 호환 API를 호출해 소비한다. "
                "PAIF(솔루션)는 PAIF 코어 기능 계층과 PAIS 서비스 계층으로 구성되고, PAIS는 코어와 별도로 설치하는 Supervisor 서비스 패키지다. "
                "코어 기능 계층은 GPU enablement, 필수 공유 서비스(Harbor, DSM), 관리와 오케스트레이션(VCF Automation, VCF Operations), "
                "DLVM 이미지로 구성되고, 그 기반은 VCF 9.1의 GPU 가속 워크로드 도메인이다.", t)
    lx, lw = 108, 992          # 계층 박스
    ix, iw = lx + 20, lw - 40  # 계층 안쪽 영역
    cw5, g5 = 182, 10          # 5열 구성요소 폭, 간격
    col = [ix + i * (cw5 + g5) for i in range(5)]

    def layer(y, h, role, name, sub, ext=False):
        d.text(lx - 24, y + 30, role, 14, 600, "muted", "end")
        d.box(lx, y, lw, h, [], dashed=ext, fill=not ext)
        d.text(lx + 20, y + 30, name, 18, 700)
        # 설명은 오른쪽 끝에 정렬해 왼쪽 열을 지나는 화살표와 겹치지 않게 한다.
        d.text(lx + lw - 20, y + 30, sub, 13, 400, "muted", "end")

    d.text(lx, 34, "논리 계층 (상위 계층은 하위 계층을 기반으로 동작)", 13, 600, "muted")

    # 고객 AI 앱 (PAIF 밖)
    ay = 52
    layer(ay, 128, "앱", "고객 AI 앱", "PAIF 밖, PAIS API(OpenAI 호환)를 호출해 소비", ext=True)
    d.box(col[0], ay + 48, cw5, 60, [("Backend", "title"), ("FastAPI 등", "sub")], "blue")
    d.box(col[1], ay + 48, cw5, 60, [("Frontend", "title"), ("React, Vue", "sub")], "blue")

    # PAIF (솔루션) 프레임
    fy = 212
    d.frame(lx - 12, fy, lw + 24, 400, "PAIF (솔루션)", tx=col[0] + cw5 / 2 + 16,
            note="PAIF(솔루션) = PAIF 코어 기능 계층 + PAIS 서비스 계층")

    # PAIS 서비스 계층
    py = 248
    layer(py, 140, "서비스", "PAIS", "서비스 계층, Supervisor 서비스 패키지(코어와 별도 설치)")
    cy, ch = py + 48, 72
    d.box(col[0], cy, cw5, ch, [("ML API Gateway", "title"), ("OpenAI 호환 API", "sub")], "blue")
    d.box(col[1], cy, cw5, ch, [("Model Runtime,", "title"), ("Model Gallery", "title")], "orange")
    d.box(col[2], cy, cw5, ch, [("Data Indexing", "title"), ("& Retrieval", "title")], "green")
    d.box(col[3], cy, cw5, ch, [("Agent Builder,", "title"), ("MCP", "title")], "blue")
    d.box(col[4], cy, cw5, ch, [("관측성", "title"), ("모델, GPU 메트릭,", "sub"), ("OTel 트레이싱", "sub")], "purple")

    # 앱 → Gateway
    gx = col[0] + cw5 / 2
    d.arrow([(gx, ay + 108), (gx, cy)])
    d.label(gx + 10, 204, "OpenAI 호환 요청")

    # PAIF 코어 기능 계층
    ky = 400
    layer(ky, 188, "AI 인프라", "PAIF 코어 기능 계층", "PAIF core functionality")
    capy, by, bh = ky + 66, ky + 76, 92
    gw, hw, mw = 236, 136, 220
    x1 = ix
    x2 = x1 + gw + 20
    x3 = x2 + 2 * hw + 8 + 20
    x4 = x3 + mw + 20
    w4 = ix + iw - x4
    for x, s in ((x1, "GPU enablement"), (x2, "공유 서비스 (필수)"), (x3, "관리, 오케스트레이션"), (x4, "개발 평면")):
        d.text(x, capy, s, 12, 600, "muted")
    d.box(x1, by, gw, bh, [("vGPU 드라이버, GPU Operator", "body"), ("MIG, EDPIO", "body"),
                           ("DLS 라이선싱, DRA", "body")], "orange")
    d.box(x2, by, hw, bh, [("Harbor", "title"), ("Supervisor Service,", "sub"), ("모델, 컨테이너 저장", "sub")], "green")
    d.cyl(x2 + hw + 8, by, hw, bh, [("DSM", "title"), ("pgvector 벡터 DB", "sub")])
    mh = (bh - 8) / 2
    d.box(x3, by, mw, mh, [("VCF Automation", "title"), ("셀프서비스 카탈로그", "sub")], fill=False)
    d.box(x3, by + mh + 8, mw, mh, [("VCF Operations", "title"), ("GPU 관측, 쇼백/차지백", "sub")], fill=False)
    d.box(x4, by, w4, bh, [("DLVM 이미지", "title"), ("딥러닝용 VM 이미지", "sub")], fill=False)

    # VCF 플랫폼
    vy = 636
    layer(vy, 140, "플랫폼", "VCF", "VMware Cloud Foundation 9.1 기반 플랫폼")
    d.text(ix, vy + 66, "GPU 가속 워크로드 도메인", 12, 600, "muted")
    vb = vy + 76
    for i, (a, b) in enumerate((("GPU-enabled", "ESXi 호스트"), ("Supervisor", None), ("NSX Edge, VPC", None),
                                ("vSAN", None), ("VKS", "Kubernetes"))):
        ls = [(a, "title")] + ([(b, "sub")] if b else [])
        d.box(col[i], vb, cw5, 48, ls, "orange" if i == 0 else "neutral", fill=(i == 0))

    d.legend(lx, 816, [("blue", "앱, 게이트웨이, 에이전트"), ("orange", "GPU, 모델 런타임"),
                       ("green", "데이터, 레지스트리"), ("purple", "관측성"), ("dashed", "PAIF 밖")])
    return d


# ① 02: PAIS 서비스 아키텍처의 세 평면
def infra_pais_planes(t):
    d = Diagram(1120, 800, "PAIS 서비스 아키텍처의 세 평면",
                "클라이언트(고객 AI 앱)의 OpenAI 호환 요청은 제어 평면의 ML API Gateway가 인증, 인가한 뒤 "
                "추론(데이터) 평면의 Completion Endpoint, Embedding Endpoint, Agent로 라우팅한다. "
                "엔드포인트는 모델 런타임을 호출하고, Agent는 Knowledge Base 검색과 모델 호출, 외부 도구(MCP)를 결합한다. "
                "인입(인덱싱) 평면은 Data Source의 문서를 파싱, 청킹, 임베딩해 pgvector에 적재하고 소스 변경을 자동 갱신하며, "
                "이 데이터가 Knowledge Base로 사용된다. 관측성은 제어와 추론 평면에서 모델 메트릭, GPU 메트릭, OTel 트레이스를 수집한다.", t)
    px, pw = 48, 812          # 평면 프레임
    ix = 72
    cw, cg = 236, 28
    cols = [ix + i * (cw + cg) for i in range(3)]   # 72, 336, 600
    cx = [c + cw / 2 for c in cols]                 # 190, 454, 718

    # 클라이언트
    d.box(cx[1] - 120, 24, 240, 56, [("클라이언트", "title"), ("고객 AI 앱", "sub")], "blue")
    d.frame(24, 120, 1072, 640, "PAIS 3.0")

    # 제어 평면
    d.frame(px, 156, pw, 100, "제어 평면")
    d.box(cx[1] - 300, 186, 600, 56, [("ML API Gateway", "title"),
                                      ("인증과 인가, 라우팅, 로드밸런싱, OpenAI 호환 인터페이스", "sub")], "blue")
    d.arrow([(cx[1], 80), (cx[1], 186)])
    d.label(cx[1] + 10, 108, "OpenAI 호환 요청")

    # 추론(데이터) 평면
    iy = 300
    d.frame(px, iy, pw, 266, "추론(데이터) 평면", tx=cx[0] + 24)
    by = 278
    d.arrow([(cx[1], 242), (cx[1], 340)])
    for x in (cx[0], cx[2]):
        d.arrow([(cx[1], by), (x, by), (x, 340)])
    d.label(cx[1] + 10, by - 6, "라우팅")
    ey, eh = 340, 80
    d.box(cols[0], ey, cw, eh, [("Completion Endpoint", "title"), ("vLLM 0.20.0 (GPU)", "body"),
                                ("llama.cpp b9309 (CPU)", "body")], "blue")
    d.box(cols[1], ey, cw, eh, [("Embedding Endpoint", "title"), ("Infinity 0.0.76", "body"),
                                ("CPU 실행 가능", "body")], "blue")
    d.box(cols[2], ey, cw, eh, [("Agent", "title"), ("RAG, Tool-calling", "body"),
                                ("MCP (외부 도구)", "body")], "blue")
    ry, rh = 470, 72
    rx2 = 540
    d.box(ix, ry, rx2 - ix, rh, [("모델 런타임", "title"), ("vLLM, llama.cpp, Infinity", "sub")], "orange")
    d.arrow([(cx[0], ey + eh), (cx[0], ry)])
    d.arrow([(cx[1], ey + eh), (cx[1], ry)])
    ax = cols[2] + 30
    d.arrow([(ax, ey + eh), (ax, ry + rh / 2), (rx2, ry + rh / 2)])
    d.label((ax + rx2) / 2, ry + rh / 2 - 8, "모델 호출", "middle")
    kx, kw = 680, 146
    kc = kx + kw / 2
    d.cyl(kx, 462, kw, 84, [("Knowledge Base", "title"), ("검색 대상", "sub")])
    d.arrow([(kc, ey + eh), (kc, 462)])
    d.label(kc + 8, 446, "검색")

    # 인입(인덱싱) 평면
    gy = 590
    d.frame(px, gy, pw, 140, "인입(인덱싱) 평면")
    sy, sh = 630, 56
    bw, step = 120, 152
    names = [("Data Source", None), ("파싱", None), ("청킹", None), ("임베딩", None)]
    for i, (a, _) in enumerate(names):
        x = ix + i * step
        d.box(x, sy, bw, sh, [(a, "title")])
        d.arrow([(x + bw, sy + sh / 2), (x + step if i < 3 else kx, sy + sh / 2)])
    d.cyl(kx, sy - 6, kw, sh + 12, [("pgvector 적재", "title"), ("DSM", "sub")])
    d.arrow([(kc, sy - 6), (kc, 546)])
    d.label(kc + 8, 582, "Knowledge Base로 사용")
    ly = sy + sh + 24
    d.arrow([(kc, sy + sh + 6), (kc, ly), (ix + bw / 2, ly), (ix + bw / 2, sy + sh)])
    d.label((ix + bw / 2 + kc) / 2, ly - 6, "소스 변경 시 자동 갱신", "middle")

    # 관측성
    ox = 900
    d.box(ox, 156, 172, 410, [("관측성", "title"), ("제어, 추론 평면 횡단", "sub"), ("", "body"),
                              ("모델 메트릭", "body"), ("(캐시, 토큰, 지연)", "sub"), ("", "body"),
                              ("GPU 메트릭", "body"), ("", "body"), ("OTel 트레이싱", "body")], "purple")
    d.arrow([(cx[1] + 300, 214), (ox, 214)], dashed=True)
    d.arrow([(px + pw, 433), (ox, 433)], dashed=True)

    d.legend(48, 784, [("blue", "앱, 게이트웨이, 엔드포인트"), ("orange", "모델 런타임"),
                       ("green", "데이터 계층"), ("purple", "관측성"), ("line-dashed", "메트릭, 트레이스 수집")])
    return d


# ① 02: 구축 Phase 개요
def infra_install_phases(t):
    d = Diagram(1100, 460, "PAIF 구축 Phase 개요",
                "구축은 Phase 1 VCF 인프라(VCF 9.1, PAIF Workload Domain, Supervisor), "
                "Phase 2 지원 서비스(Harbor, DSM, 권장 구성인 VCF Automation), "
                "Phase 3 PAIS 3.0 설치와 활성화(UI 또는 CLI), Phase 4 개발과 운영(DLVM, VKS, 앱) 순서로 진행한다. "
                "Phase 1과 2는 VI Admin이 각각 2-3일, 1일, Phase 3은 Cloud/Org Admin이 1일, "
                "Phase 4는 DevOps와 데이터 사이언티스트가 지속적으로 담당한다.", t)
    fw, gap, x0, y0 = 236, 40, 24, 24
    fh = 392
    phases = [
        ("Phase 1", "VCF 인프라", "neutral", [
            ([("VCF 9.1", "title"), ("배포", "sub")], "neutral", False),
            ([("PAIF Workload Domain", "title"), ("GPU 호스트 3대 이상", "sub"), ("vGPU 호스트 드라이버", "sub")], "orange", False),
            ([("Supervisor", "title"), ("NSX VPC, vGPU VM Class", "sub")], "neutral", False),
        ], "VI Admin", "2-3일"),
        ("Phase 2", "지원 서비스", "green", [
            ([("Harbor", "title"), ("컨테이너 이미지,", "sub"), ("Model Gallery", "sub")], "green", False),
            ([("DSM", "title"), ("pgvector PostgreSQL", "sub")], "green", False),
            ([("VCF Automation", "title"), ("권장, 셀프서비스 카탈로그", "sub")], "neutral", True),
        ], "VI Admin", "1일"),
        ("Phase 3", "PAIS 설치", "blue", [
            ([("PAIS 3.0", "title"), ("Supervisor Service 설치", "sub")], "blue", False),
            ([("Trust Bundle,", "title"), ("PAISConfiguration", "title")], "neutral", False),
            ([("활성화 (UI 또는 CLI)", "title"), ("VCF Automation 또는 kubectl", "sub")], "neutral", False),
        ], "Cloud/Org Admin", "1일"),
        ("Phase 4", "개발/운영", "orange", [
            ([("DLVM", "title"), ("AI Workstation", "sub")], "orange", False),
            ([("VKS", "title"), ("AI Kubernetes Cluster", "sub")], "neutral", False),
            ([("Apps", "title"), ("PAIS API를 소비하는 앱", "sub")], "blue", False),
        ], "DevOps/DS", "지속"),
    ]
    bh, bg, by0 = 66, 12, y0 + 84
    for i, (ph, title, kind, items, owner, period) in enumerate(phases):
        x = x0 + i * (fw + gap)
        d.frame(x, y0, fw, fh)
        d.badge(x + fw / 2, y0 + 16, ph, "neutral", "middle")
        d.text(x + fw / 2, y0 + 66, title, 15, 700, "text", "middle")
        for j, (ls, k, dashed) in enumerate(items):
            d.box(x + 16, by0 + j * (bh + bg), fw - 32, bh, ls, k, dashed=dashed, fill=not dashed)
        fy = by0 + 3 * bh + 2 * bg + 20
        d.o.append(f'<line x1="{x + 16:g}" y1="{fy:g}" x2="{x + fw - 16:g}" y2="{fy:g}" '
                   f'stroke="{t["frame"]}" stroke-width="1"/>')
        for k2, (lab, val) in enumerate((("담당", owner), ("기간", period))):
            ty = fy + 26 + k2 * 24
            d.text(x + 20, ty, lab, 13, 600, "muted")
            d.text(x + 64, ty, val, 13, 700)
        if i < 3:
            ay = by0 + bh * 1.5 + bg
            d.arrow([(x + fw, ay), (x + fw + gap, ay)])
    d.legend(x0, 448, [("orange", "GPU 자원"), ("green", "데이터, 레지스트리"), ("blue", "PAIS, 앱"),
                       ("dashed", "권장 구성(선택)")])
    return d


# ① 04: AI 애플리케이션 구조
def infra_ai_app_structure(t):
    d = Diagram(1000, 676, "AI 애플리케이션 구조",
                "사용자의 HTTP Request는 일반 웹앱과 같은 3-Tier인 Frontend(Presentation, React/Vue), "
                "Backend(BFF/Business, FastAPI), Database(Data, PostgreSQL)를 거친다. "
                "AI 앱은 여기에 AI Services(PAIS) 계층이 추가된다. Backend가 Agent API를 호출하면 "
                "Agent API가 인증과 인가를 거쳐 질문 이해, 문서 검색(Knowledge Base), 답변 생성(LLM), "
                "출처 제공의 RAG 파이프라인을 자동 처리하고, 답변을 Backend에 스트리밍으로 반환한다.", t)
    # 사용자
    d.box(40, 24, 250, 44, [("사용자", "title")])
    d.arrow([(165, 68), (165, 136)])
    d.label(175, 84, "HTTP Request")
    # 3-Tier
    d.frame(24, 92, 952, 172, note="일반 웹앱과 같은 3-Tier")
    y, h = 136, 108
    d.box(40, y, 250, h, [("Frontend", "title"), ("React/Vue", "sub"), ("채팅 UI, 대화 이력", "body")],
          "blue", badge="Presentation")
    d.box(375, y, 250, h, [("Backend", "title"), ("FastAPI", "sub"), ("파일 업로드", "body")],
          "blue", badge="BFF/Business")
    d.cyl(710, y - 4, 250, h + 8, [])
    d.lines(710, y + 12, 250, h - 8, [("Database", "title"), ("PostgreSQL", "sub"), ("사용자 정보, 세션", "body")],
            badge="Data", kind="green")
    d.arrow([(290, y + h / 2), (375, y + h / 2)])
    d.arrow([(625, y + h / 2), (710, y + h / 2)])
    # AI 서비스 계층
    d.frame(24, 316, 952, 308, "AI Services (PAIS)", note="AI 앱에 추가된 계층")
    d.box(48, 360, 904, 56, [("Agent API", "title"), ("인증, 인가", "sub")], "blue")
    d.arrow([(470, y + h), (470, 360)])
    d.label(460, 300, "AI API 호출", "end")
    d.arrow([(530, 360), (530, y + h)])
    d.label(540, 300, "스트리밍 응답")
    d.frame(48, 444, 904, 156, "RAG 파이프라인, Agent API가 자동 처리", dashed=True, tx=200)
    bx, bw, by, bh, gap = 72, 178, 492, 84, 48
    stages = [
        ([("질문 이해", "title")], "neutral"),
        ([("문서 검색", "title"), ("Knowledge Base", "sub")], "green"),
        ([("답변 생성", "title"), ("LLM", "sub")], "orange"),
        ([("출처 제공", "title"), ("답변과 참조 문서", "sub")], "neutral"),
    ]
    for i, (ls, kind) in enumerate(stages):
        x = bx + i * (bw + gap)
        d.box(x, by, bw, bh, ls, kind)
        if i:
            d.arrow([(x - gap, by + bh / 2), (x, by + bh / 2)])
    d.arrow([(bx + bw / 2, 416), (bx + bw / 2, by)])
    d.arrow([(bx + 3 * (bw + gap) + bw / 2, by), (bx + 3 * (bw + gap) + bw / 2, 416)])
    d.legend(40, 656, [("blue", "앱, API 계층"), ("green", "데이터 계층"), ("orange", "모델 추론")])
    return d


# ① 04: AI 앱 배포 아키텍처
def infra_ai_app_deployment(t):
    d = Diagram(1140, 664, "AI 앱 배포 아키텍처",
                "AI 플레이그라운드(PAIF/PAIS) 안의 VKS Cluster(프로젝트)에 앱을 배포한다. "
                "외부 사용자의 HTTPS 요청은 Ingress Controller(L7 로드밸런싱, TLS 종료)를 거쳐 Frontend Pod(React, Nginx)로, "
                "다시 Backend Pod(FastAPI, 인증 처리, AI API 중계)로 전달되고, Backend Pod가 PAIS Services"
                "(Agent API, Model Endpoints, Knowledge Base)를 호출한다. 공유 서비스로 Harbor가 컨테이너 이미지를, "
                "DSM PostgreSQL이 앱 데이터와 사용자 정보를 보관한다.", t)
    # 외부 사용자
    d.box(299, 24, 190, 44, [("외부 사용자", "title")])
    d.arrow([(394, 68), (394, 180)])
    d.label(404, 92, "HTTPS")
    # 플레이그라운드
    d.frame(24, 108, 740, 500, "AI 플레이그라운드 (PAIF/PAIS)")
    d.frame(48, 144, 692, 268, "VKS Cluster (프로젝트)")
    d.box(72, 180, 644, 56, [("Ingress Controller", "title"), ("L7 로드밸런싱, TLS 종료", "sub")], "blue")
    py, ph = 280, 108
    d.box(72, py, 280, ph, [("Frontend Pod(s)", "title"), ("React, Nginx", "body")], "blue")
    d.box(436, py, 280, ph, [("Backend Pod(s)", "title"), ("FastAPI", "body"), ("인증 처리, AI API 중계", "body")],
          "blue")
    d.arrow([(212, 236), (212, py)])
    d.arrow([(352, py + ph / 2), (436, py + ph / 2)])
    # PAIS
    d.frame(48, 460, 692, 124, "PAIS Services")
    sx, sw, sy, sh = 72, 196, 500, 60
    d.box(sx, sy, sw, sh, [("Agent API", "title")], "blue")
    d.box(sx + 224, sy, sw, sh, [("Model Endpoints", "title")], "orange")
    d.box(sx + 448, sy, sw, sh, [("Knowledge Base", "title")], "green")
    d.arrow([(576, py + ph), (576, 460)])
    d.label(586, 440, "PAIS API 호출")
    # 공유 서비스
    d.frame(840, 108, 276, 500, "공유 서비스")
    d.box(864, 140, 228, 72, [("Harbor", "title"), ("컨테이너 이미지 저장소", "sub")])
    d.cyl(864, py - 6, 228, ph + 12, [("DSM", "title"), ("PostgreSQL", "sub"), ("앱 데이터, 사용자 정보", "sub")])
    d.arrow([(864, 162), (740, 162)], dashed=True)
    d.label(802, 154, "앱 이미지", "middle")
    d.arrow([(716, py + ph / 2), (864, py + ph / 2)], dashed=True)
    d.label(802, py + ph / 2 - 8, "앱 데이터", "middle")
    d.legend(40, 644, [("blue", "앱, API 계층"), ("green", "데이터 계층"), ("orange", "모델 추론"),
                       ("line-dashed", "공유 서비스 사용")])
    return d


# ① 05: Agent 구성 요소
def infra_agent_composition(t):
    d = Diagram(1060, 448, "Agent 구성 요소",
                "System Prompt, Model Endpoint, Knowledge Base, MCP Tools, Session Config의 5개 구성 요소가 결합해 "
                "하나의 Agent를 구성한다. Agent를 구성하면 REST API 엔드포인트 POST /v1/agents/{name}/chat이 자동 생성된다.", t)
    x0, bw, bh, gap, y0 = 24, 456, 60, 14, 64
    rows = [
        ("System Prompt", ["규칙, 톤, 제약"], "blue"),
        ("Model Endpoint", ["Llama 3.1 8B 등", "Temperature, Max Tokens"], "orange"),
        ("Knowledge Base", ["RAG 데이터", "Similarity Cutoff, Chunk 수"], "green"),
        ("MCP Tools", ["외부 데이터, 도구", "DB, ITSM, 메신저, 코드"], "neutral"),
        ("Session Config", ["Chat History, 만료 시간"], "blue"),
    ]
    d.text(x0, 44, "구성 요소", 13, 700, "muted")
    total = len(rows) * bh + (len(rows) - 1) * gap
    ax, aw = 572, 180
    rx, rw = 832, 204
    for i, (name, desc, kind) in enumerate(rows):
        y = y0 + i * (bh + gap)
        d.box(x0, y, bw, bh, [], kind)
        d.text(x0 + 18, y + bh / 2 + 5, name, 15, 700)
        n = len(desc)
        for j, s in enumerate(desc):
            d.text(x0 + 206, y + bh / 2 + 5 + (j - (n - 1) / 2) * 18, s, 13, 400, "muted" if j else "text")
        d.arrow([(x0 + bw, y + bh / 2), (ax, y + bh / 2)])
    d.text(ax, 44, "결합", 13, 700, "muted")
    d.box(ax, y0, aw, total, [("Agent", "big"), ("5개 구성 요소를", "sub"), ("하나로 결합", "sub")], "blue")
    d.text(rx, 44, "자동 생성", 13, 700, "muted")
    ry = y0 + total / 2 - 50
    d.box(rx, ry, rw, 100, [("REST API", "title"), ("POST", "body"), ("/v1/agents/{name}/chat", "body")], "blue")
    d.arrow([(ax + aw, y0 + total / 2), (rx, y0 + total / 2)])
    return d


# ② 03: VCF 기반 pgvector 워크로드 구성
def vectordb_dsm_topology(t):
    d = Diagram(1160, 676, "VCF 기반 pgvector 워크로드 구성",
                "VCF 관리 도메인에는 vCenter Server, SDDC Manager, DSM Appliance(컨트롤 플레인), "
                "VCF Automation(셀프서비스 카탈로그), VCF Operations(DSM Management Pack)가 있다. "
                "DSM은 Infrastructure Policy로 정의한 컴퓨트, 스토리지, 네트워크에 데이터베이스를 배포한다. "
                "VCF 워크로드 도메인의 vSphere Cluster A에서는 Anti-Affinity Rule에 따라 PG Primary, PG Replica, "
                "PG Monitor가 서로 다른 ESXi 호스트에서 실행되고, RAG App VM은 Primary에서 검색하고 Replica로 읽기를 분산한다. "
                "클러스터의 저장은 vSAN ESA가, 격리와 로드밸런싱은 NSX가 맡는다. "
                "Private AI 구성 시 DLVM, Model Runtime, 임베딩 서비스의 GPU 워크로드는 별도의 PAIF 워크로드 도메인에서 실행된다.", t)
    # 관리 도메인
    d.frame(24, 24, 1112, 124, "VCF 관리 도메인")
    bx, by, bw, bh = 40, 60, 200, 64
    d.box(bx, by, bw, bh, [("vCenter Server", "title")])
    d.box(bx + 220, by, bw, bh, [("SDDC Manager", "title")])
    d.box(bx + 440, by, bw, bh, [("DSM Appliance", "title"), ("컨트롤 플레인, vCenter 플러그인", "sub")], "green")
    d.box(bx + 660, by, bw, bh, [("VCF Automation", "title"), ("셀프서비스 카탈로그", "sub")])
    d.box(bx + 880, by, bw, bh, [("VCF Operations", "title"), ("DSM Management Pack", "sub")])
    # 워크로드 도메인
    d.frame(24, 212, 784, 440, "VCF 워크로드 도메인")
    d.frame(40, 248, 752, 388, "vSphere Cluster A")
    hx, hy, hw, hh = 56, 284, 232, 218
    for i in range(3):
        d.frame(hx + i * 248, hy, hw, hh, f"ESXi Host {i + 1}")
    vx, vw = hx + 14, hw - 28
    r1, r2, rh = 320, 422, 64
    d.cyl(vx, r1 - 4, vw, rh + 8, [("PG Primary", "title"), ("+ pgvector", "sub")])
    d.box(vx, r2, vw, rh, [("RAG App VM", "title"), ("LangChain", "sub")], "blue")
    d.cyl(vx + 248, r1 - 4, vw, rh + 8, [("PG Replica", "title"), ("+ pgvector, 읽기 전용", "sub")])
    d.box(vx + 496, r1, vw, rh, [("PG Monitor", "title"), ("pg_auto_failover, HA 제어", "sub")], "green")
    d.text(vx + 496 + vw / 2, r1 + rh + 26, "장애 감지와", 12, 400, "muted", "middle")
    d.text(vx + 496 + vw / 2, r1 + rh + 43, "자동 Failover 수행", 12, 400, "muted", "middle")
    # 복제, 검색 흐름
    d.arrow([(vx + vw, r1 + 40), (vx + 248, r1 + 40)])
    d.label(vx + vw + 22, r1 + 33, "복제", "middle")
    d.arrow([(vx + vw / 2, r2), (vx + vw / 2, r1 + rh + 4)])
    d.label(vx + vw / 2 + 8, r2 - 12, "벡터 검색")
    d.arrow([(vx + vw, r2 + 32), (vx + 248 + vw / 2, r2 + 32), (vx + 248 + vw / 2, r1 + rh + 4)])
    d.label(vx + 248 + vw / 2 + 8, r2 + 52, "읽기 분산")
    d.text(416, 526, "Anti-Affinity Rule로 Primary, Replica, Monitor를 서로 다른 호스트에 배치",
           12, 400, "muted", "middle")
    d.cyl(56, 544, 360, 76, [("vSAN ESA", "title"), ("RAID-5/6, 읽기 캐시 최적화", "sub")], "neutral")
    d.box(432, 548, 344, 68, [("NSX", "title"), ("마이크로세그멘테이션, 로드밸런싱", "sub")], "purple")
    # PAIF 워크로드 도메인 (선택)
    d.frame(832, 212, 304, 440, "PAIF 워크로드 도메인 (선택)", dashed=True)
    px, pw = 852, 264
    d.box(px, 252, pw, 64, [("DLVM", "title"), ("파인튜닝", "sub")], "orange")
    d.box(px, 332, pw, 64, [("Model Runtime", "title"), ("NVIDIA NIM", "sub")], "orange")
    d.box(px, 412, pw, 64, [("임베딩 서비스", "title")], "orange")
    d.text(px + pw / 2, 530, "Private AI Foundation 구성 시", 12, 400, "muted", "middle")
    d.text(px + pw / 2, 548, "임베딩 모델과 LLM 추론의", 12, 400, "muted", "middle")
    d.text(px + pw / 2, 566, "GPU 워크로드를 실행", 12, 400, "muted", "middle")
    # Infrastructure Policy
    d.arrow([(580, 124), (580, 248)])
    d.label(592, 172, ["Infrastructure Policy", "DB를 배포할 컴퓨트, 스토리지, 네트워크 정의"])
    return d


# ③ 02: PAIS 4대 모듈과 의존 관계
def serving_model_runtime(t):
    d = Diagram(1120, 652, "PAIS 4대 모듈과 의존 관계",
                "Model Gallery(Harbor, OCI)가 모델 아티팩트를 저장하고 접근통제, 버전관리, 메타데이터를 관리하며, "
                "Model Runtime이 모델 리비전을 가져와 배포한다. Runtime의 ML API Gateway는 모든 호출의 진입점으로 "
                "인증, 인가, 로드밸런싱, OpenAI 호환 경로, SSE를 처리하고 Completion Endpoint(vLLM, llama.cpp)와 "
                "Embedding Endpoint(Infinity, vLLM, llama.cpp)로 요청을 전달한다. Endpoint는 VKS 워커 노드 파드의 복제본으로 "
                "실행되어 ESXi 물리 GPU에 연결된다. Agent Builder는 Completion Endpoint를 내부에서 호출하고, "
                "Data Indexing & Retrieval은 Embedding Endpoint로 임베딩을 생성해 pgvector에 저장하며, 두 모듈은 서로 연동한다.", t)
    # Model Gallery
    d.box(200, 24, 560, 72, [("Model Gallery (Harbor, OCI)", "title"),
                             ("모델 아티팩트 저장, RBAC 접근통제, 버전관리, 메타데이터", "sub")])
    d.arrow([(480, 96), (480, 164)])
    d.label(490, 136, "모델 리비전을 가져와 배포", step=1)
    # Model Runtime
    d.frame(24, 164, 912, 284, "Model Runtime", kind="orange", note="stateless, 요청 간 상태 없음")
    d.box(48, 200, 864, 64, [("ML API Gateway (모든 호출의 진입점)", "title"),
                             ("인증, 인가, 로드밸런싱, OpenAI 호환 경로, SSE", "sub")], "blue")
    d.box(976, 200, 120, 64, [("앱", "title"), ("데이터 평면", "sub")])
    d.arrow([(976, 232), (912, 232)])
    cols = [
        (48, [("Completion Endpoint", "title"), ("vLLM (GPU)", "body"), ("llama.cpp (CPU)", "body")], False),
        (344, [("Embedding Endpoint", "title"), ("Infinity (CPU, GPU)", "body"), ("vLLM, llama.cpp", "body")], False),
        (640, [("복제본 N개", "title"), ("VKS 워커 노드 파드", "body"), ("ESXi 물리 GPU에 연결", "body")], True),
    ]
    for x, ls, dashed in cols:
        d.box(x, 304, 272, 120, ls, "orange", dashed=dashed)
        d.arrow([(x + 136, 264), (x + 136, 304)])
    # 소비 모듈
    d.box(48, 532, 340, 96, [("Agent Builder", "title"), ("RAG, 세션, MCP 도구를 결합해", "body"),
                             ("오케스트레이션, Agent API로 노출", "body")], "blue")
    d.box(452, 532, 460, 96, [("Data Indexing & Retrieval", "title"),
                              ("데이터 소스 → 파싱 → 청킹 → 임베딩", "body"),
                              ("pgvector에 저장 (Knowledge Base, 인덱스)", "body")], "green")
    d.arrow([(184, 424), (184, 532)], both=True)
    d.label(194, 492, "모델 호출(내부)")
    d.arrow([(480, 424), (480, 532)], both=True)
    d.label(490, 492, "임베딩 생성")
    d.arrow([(388, 580), (452, 580)], both=True)
    d.label(420, 570, "검색", "middle")
    return d


# ③ 02: 모델 한 개의 생애주기
def serving_model_pipeline(t):
    d = Diagram(1150, 340, "모델 한 개의 생애주기",
                "모델은 준비, 반입, 배포, 노출, 소비의 다섯 단계를 거쳐 사내 추론 API가 된다. "
                "PAIS 밖에서 준비한 외부 모델(NGC, Hugging Face) 또는 DLVM, 학습 산출물을 Model Gallery의 Harbor(OCI)에 "
                "리비전과 메타데이터와 함께 업로드한다(1). Model Runtime이 리비전으로 Endpoint를 만들어 추론 엔진 컨테이너를 "
                "VKS 워커 노드에 파드로 스케줄하고 ESXi 물리 GPU에 연결하며 복제본을 2개 이상 배치한다(2). "
                "ML API Gateway가 단일 URL로 노출하고 인증, 인가, 로드밸런싱을 처리하며(3), 앱은 base_url만 교체해 호출한다(4).", t)
    widths = [148, 148, 210, 160, 148]
    gap = 72
    xs = []
    x = 24
    for w in widths:
        xs.append(x)
        x += w + gap
    heads = [("준비", "PAIS 밖", "neutral"), ("반입", "Model Gallery", "neutral"), ("배포", "Model Runtime", "orange"),
             ("노출", "ML API Gateway", "blue"), ("소비", "앱, 에이전트", "blue")]
    for (s, loc, kind), x, w in zip(heads, xs, widths):
        d.badge(x + w / 2, 20, s, kind, "middle")
        d.text(x + w / 2, 62, loc, 13, 600, "muted", "middle")
    # PAIS 범위
    fx = xs[1] - 12
    d.frame(fx, 80, xs[3] + widths[3] + 12 - fx, 240, "PAIS")
    y, h = 120, 180
    d.box(xs[0], y, widths[0], h, [("외부 모델", "title"), ("NGC, Hugging Face", "body"),
                                   ("또는 DLVM,", "body"), ("학습 산출물", "body")], dashed=True)
    d.box(xs[1], y, widths[1], h, [("Harbor (OCI)", "title"), ("리비전,", "body"), ("메타데이터", "body")])
    d.box(xs[2], y, widths[2], h, [("추론 엔진 컨테이너", "title"), ("VKS 워커 노드에", "body"),
                                   ("파드로 스케줄", "body"), ("ESXi 물리 GPU에 연결", "body"),
                                   ("복제본 2개 이상", "body")], "orange")
    d.box(xs[3], y, widths[3], h, [("단일 URL", "title"), ("인증, 인가,", "body"), ("로드밸런싱", "body")], "blue")
    d.box(xs[4], y, widths[4], h, [("앱", "title"), ("base_url만 교체", "body")], "blue")
    labels = [["업로드"], ["Endpoint", "생성"], ["URL 노출"], ["API 호출"]]
    cy = y + h / 2
    for i in range(4):
        a, b = xs[i] + widths[i], xs[i + 1]
        m = (a + b) / 2
        d.arrow([(a, cy), (b, cy)])
        d.o.append(f'<circle cx="{m:g}" cy="{cy - 22:g}" r="9" fill="{t["blue_accent"]}" '
                   f'stroke="{t["bg"]}" stroke-width="2"/>')
        d.text(m, cy - 17.5, str(i + 1), 11, 700, t["bg"], "middle")
        for j, s in enumerate(labels[i]):
            d.text(m, cy + 22 + j * 17, s, 12, 400, "muted", "middle", halo=True)
    return d


# ④ 04: 추론 경로 B(Model Endpoint)와 경로 A(Agent)
def rag_inference_paths(t):
    d = Diagram(1120, 648, "RAG 추론 경로 B와 경로 A",
                "왼쪽 경로 B(Model Endpoint)는 앱이 검색을 통제한다. 앱이 질문을 받아 검색과 컨텍스트 조립(03)을 직접 수행하며 "
                "pgvector(②)를 검색하고, 질문과 조립된 근거를 Model Endpoint의 완성 모델(③)에 보내 스트리밍 답변을 받은 뒤 "
                "실제 검색 청크 메타데이터로 출처를 표기한다(4.5). 오른쪽 경로 A(Agent)는 플랫폼이 검색을 포함한다. "
                "앱은 질문만 전달하고, Agent(Agent Builder)가 검색 호출 여부와 검색어를 동적으로 판단해 MCP 도구로 "
                "pgvector(②)를 검색하고 근거를 받아 완성 생성(③)까지 수행한 뒤 답변과 근거를 앱에 반환한다.", t)
    # 경로 B
    d.frame(24, 24, 524, 600, "경로 B: Model Endpoint", note="앱이 검색을 통제")
    d.frame(40, 64, 330, 236, "앱이 직접 수행하는 범위", kind="blue")
    d.box(60, 100, 290, 56, [("앱, 오케스트레이션", "title")], "blue")
    d.box(60, 216, 290, 60, [("검색, 컨텍스트 조립 (03)", "title")], "blue")
    d.cyl(410, 202, 120, 88, [("pgvector", "title"), ("②", "sub")])
    d.box(60, 372, 290, 64, [("Model Endpoint", "title"), ("완성 모델 (③)", "sub")], "orange")
    d.box(60, 536, 470, 64, [("앱", "title"), ("출처는 실제 검색 청크 메타데이터로 표기 (4.5)", "sub")], "blue")
    d.arrow([(205, 156), (205, 216)])
    d.label(215, 191, "질문", step=1)
    d.arrow([(350, 246), (410, 246)], both=True)
    d.label(380, 238, "검색", "middle")
    d.arrow([(205, 276), (205, 372)])
    d.label(215, 326, ["질문 + 근거", "(조립된 컨텍스트)"], step=2)
    d.arrow([(205, 436), (205, 536)])
    d.label(215, 490, "답변 (스트리밍)", step=3)
    # 경로 A
    d.frame(572, 24, 524, 600, "경로 A: Agent", note="플랫폼이 검색을 포함")
    d.box(612, 100, 290, 56, [("앱", "title")], "blue")
    d.frame(596, 196, 326, 296, "Agent (Agent Builder)", dashed=True)
    d.box(612, 236, 290, 64, [("동적 판단", "title"), ("검색 호출 여부와 검색어 결정", "sub")])
    d.box(612, 340, 290, 56, [("KB 검색", "title"), ("Knowledge Base", "sub")])
    d.box(612, 428, 290, 48, [("완성 생성 (③)", "title")], "orange")
    d.cyl(966, 324, 114, 88, [("pgvector", "title"), ("②", "sub")])
    d.box(612, 536, 468, 64, [("앱", "title"), ("Agent 응답의 근거, 출처 필드 사용 (4.5)", "sub")], "blue")
    d.arrow([(840, 156), (840, 236)])
    d.label(850, 182, "질문만 전달")
    d.arrow([(757, 300), (757, 340)])
    d.label(767, 324, "검색이 필요할 때")
    d.arrow([(902, 358), (966, 358)])
    d.label(934, 350, "MCP 도구", "middle")
    d.arrow([(966, 382), (902, 382)])
    d.label(934, 398, "근거", "middle")
    d.arrow([(757, 396), (757, 428)])
    d.arrow([(757, 476), (757, 536)])
    d.label(767, 518, "답변 + 근거")
    return d


# ⑤ 02: 격리 계층 동심 구조
def security_isolation_layers(t):
    d = Diagram(940, 640, "격리 계층 동심 구조",
                "바깥에서 안쪽 순으로 멀티테넌트 경계(NSX Project, VCF Automation 조직과 쿼터), 네트워크 논리 격리(NSX VPC, 세그먼트, "
                "Transit Gateway), 동/서 마이크로세그(vDefend DFW, 분산 IDS/IPS), 컴퓨트(VKS 네임스페이스, 쿼터, GPU Reservation), "
                "GPU 하드웨어(NVIDIA MIG, vGPU 프로파일)가 중첩된다. 남/북 출입구(vDefend Gateway Firewall, URL/Geo-IP 필터링)는 "
                "가장 바깥 경계에서 외부와의 인그레스, 이그레스를 통제한다. 바깥 계층은 정책 설정으로 강제되어 설정 실수에 취약하고, "
                "안쪽 계층일수록 하드웨어가 분리를 강제한다.", t)
    x0, y0, w0 = 24, 150, 700
    inset, head, pad_b = 22, 64, 16
    layers = [
        ("멀티테넌트 경계", "NSX Project, VCF Automation 조직과 네임스페이스 쿼터", "관리와 정책 평면"),
        ("네트워크 (논리)", "NSX VPC, 세그먼트, 서브넷 접근 모드, Transit Gateway", "NSX 데이터플레인"),
        ("동/서 마이크로세그", "vDefend 분산 방화벽(DFW), 분산 IDS/IPS", "ESXi 커널(각 vNIC)"),
        ("컴퓨트", "VKS 네임스페이스, 쿼터, GPU Reservation", "Supervisor / vSphere"),
    ]
    n = len(layers)
    gh = 112
    gx, gy = x0 + n * inset, y0 + n * head
    gw = w0 - 2 * n * inset
    h0 = n * head + gh + n * pad_b
    rows = []
    for k, (name, comp, point) in enumerate(layers):
        x, y = x0 + k * inset, y0 + k * head
        w, h = w0 - 2 * k * inset, h0 - k * (head + pad_b)
        d.frame(x, y, w, h, kind="purple")
        d.text(x + 14, y + 26, name, 14, 700, "purple_accent")
        d.text(x + w - 14, y + 26, point, 12, 600, "muted", "end")
        d.text(x + 14, y + 48, comp, 13)
        rows.append((y + 21, name))
    # GPU 하드웨어
    d.box(gx, gy, gw, gh, [], "orange")
    d.text(gx + 14, gy + 28, "GPU 하드웨어", 14, 700, "orange_accent")
    d.text(gx + gw - 14, gy + 28, "GPU 실리콘", 12, 600, "muted", "end")
    d.text(gx + 14, gy + 52, "NVIDIA MIG, vGPU 프로파일", 13)
    d.text(gx + 14, gy + 86, "가장 민감한 테넌트 경계일수록 이 계층으로 격리를 강제", 13, 400, "muted")
    rows.append((gy + 23, "GPU 하드웨어"))
    # 남/북 출입구: 가장 바깥 경계에 위치
    bx, bw = 222, 340
    d.box(bx, y0 - 40, bw, 70, [("남/북 출입구", "title"), ("vDefend Gateway Firewall, URL/Geo-IP 필터링", "body"),
                                 ("T0 Edge / Provider Gateway", "sub")], "purple")
    d.box(bx + 50, 20, bw - 100, 50, [("외부", "title"), ("인터넷, 외부 모델 허브", "sub")])
    d.arrow([(bx + bw / 2, 70), (bx + bw / 2, y0 - 40)], both=True)
    d.label(bx + bw / 2 + 10, 96, "인그레스, 이그레스")
    # 강제 방식 축
    ax = 772
    top, bot = rows[0][0] - 4, rows[-1][0] + 4
    d.text(ax - 6, y0 - 56, "강제 방식", 13, 700, "muted")
    d.text(ax - 6, top - 34, "정책(설정)으로 강제", 13, 700, "purple_accent")
    d.text(ax - 6, top - 16, "설정 실수에 취약", 12, 400, "muted")
    d.o.append(f'<defs><linearGradient id="enf" x1="0" y1="0" x2="0" y2="1">'
               f'<stop offset="0" stop-color="{t["purple_accent"]}"/>'
               f'<stop offset="1" stop-color="{t["orange_accent"]}"/></linearGradient></defs>')
    d.o.append(f'<rect x="{ax:g}" y="{top:g}" width="10" height="{bot - top:g}" rx="5" fill="url(#enf)"/>')
    for y, name in rows:
        d.o.append(f'<circle cx="{ax + 5:g}" cy="{y - 4:g}" r="6" fill="{t["bg"]}" stroke="{t["muted"]}" stroke-width="1.5"/>')
        d.text(ax + 22, y, name, 12, 400, "text")
    d.text(ax - 6, bot + 28, "하드웨어로 강제", 13, 700, "orange_accent")
    d.text(ax - 6, bot + 45, "강격리, 설정 실수만으로", 12, 400, "muted")
    d.text(ax - 6, bot + 62, "경계가 해제되지 않음", 12, 400, "muted")
    d.text(x0, y0 + h0 + 30, "각 계층은 독립적으로 동작한다. 한 계층이 잘못 설정되어도 다른 계층이 침범을 차단한다.",
           13, 400, "muted")
    return d

DIAGRAMS = {
    "series-layers": series_layers,
    "rag-reference-architecture": rag_reference_architecture,
    "security-control-points": security_control_points,
    "design-standard-blueprint": design_standard_blueprint,
    "design-gateway-tiers": design_gateway_tiers,
    "infra-paif-layers": infra_paif_layers,
    "infra-pais-planes": infra_pais_planes,
    "infra-install-phases": infra_install_phases,
    "infra-ai-app-structure": infra_ai_app_structure,
    "infra-ai-app-deployment": infra_ai_app_deployment,
    "infra-agent-composition": infra_agent_composition,
    "vectordb-dsm-topology": vectordb_dsm_topology,
    "serving-model-runtime": serving_model_runtime,
    "serving-model-pipeline": serving_model_pipeline,
    "rag-inference-paths": rag_inference_paths,
    "security-isolation-layers": security_isolation_layers,
}

if __name__ == "__main__":
    for name, build in DIAGRAMS.items():
        for theme, t in THEMES.items():
            with open(os.path.join(OUT, f"{name}-{theme}.svg"), "w", encoding="utf-8") as f:
                f.write(build(t).render())

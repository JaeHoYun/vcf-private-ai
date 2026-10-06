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

    def frame(self, x, y, w, h, title=None, dashed=False):
        da = ' stroke-dasharray="6 4"' if dashed else ""
        self.o.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="10" fill="none" '
                      f'stroke="{self.t["frame"]}" stroke-width="1.5"{da}/>')
        if title:
            self.text(x + 14, y + 22, title, 13, 700, "muted")

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


DIAGRAMS = {
    "series-layers": series_layers,
    "rag-reference-architecture": rag_reference_architecture,
    "security-control-points": security_control_points,
    "design-standard-blueprint": design_standard_blueprint,
    "design-gateway-tiers": design_gateway_tiers,
}

if __name__ == "__main__":
    for name, build in DIAGRAMS.items():
        for theme, t in THEMES.items():
            with open(os.path.join(OUT, f"{name}-{theme}.svg"), "w", encoding="utf-8") as f:
                f.write(build(t).render())

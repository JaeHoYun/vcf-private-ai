"""README의 4계층 구조도(라이트, 다크 SVG 2종)를 생성한다. 실행: python3 assets/build_series_layers.py"""
import os
import sys
THEMES = {
  "light": dict(text="#1f2328", muted="#59636e", head="#59636e",
                layer_fill="#f6f8fa", layer_stroke="#d0d7de",
                chip_fill="#ddf4ff", chip_text="#0969da",
                x_fill="#fbefff", x_stroke="#c297ff", x_text="#8250df",
                d_fill="#dafbe1", d_stroke="#4ac26b", d_text="#1a7f37"),
  "dark": dict(text="#f0f6fc", muted="#9198a1", head="#9198a1",
               layer_fill="#151b23", layer_stroke="#3d444d",
               chip_fill="#11284a", chip_text="#4493f8",
               x_fill="#231c35", x_stroke="#8957e5", x_text="#ab7df8",
               d_fill="#122a1c", d_stroke="#2f9e4f", d_text="#3fb950"),
}
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Apple SD Gothic Neo', 'Malgun Gothic', 'Noto Sans KR', 'Noto Sans CJK KR', Helvetica, Arial, sans-serif"

W, H = 968, 536
SX, SW = 132, 544          # stack x, width
RH, GAP, Y0 = 88, 12, 52   # row height, gap, first row y
X5, X6, XW = SX + SW + 16, SX + SW + 16 + 128, 116

ROWS = [
  ("실행", "Agents, MCP", "실행 계층, 시리즈 본편 범위 밖", "모델이 사내 데이터와 도구에 연결되어 업무 수행", "앱 가이드", True),
  ("서비스", "PAIS", "Private AI Services", "모델 서빙, RAG, Agent Builder, MCP (관리형)", "시리즈 ③④", False),
  ("AI 인프라", "PAIF 코어 기능 계층", "Private AI Foundation with NVIDIA", "GPU, 드라이버, 모델, 벡터 DB 표준화", "시리즈 ①②", False),
  ("플랫폼", "VCF", "VMware Cloud Foundation", "컴퓨트, 스토리지, 네트워크, 쿠버네티스(VKS)", "시리즈 ①", False),
]

def svg(t):
  o = []
  a = o.append
  a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}" role="img" aria-labelledby="t d">')
  a('<title id="t">VCF Private AI 4계층 구조</title>')
  a('<desc id="d">위에서 아래로 실행(Agents, MCP), 서비스(PAIS), AI 인프라(PAIF 코어 기능 계층), 플랫폼(VCF)의 4계층. 보안과 거버넌스(⑤), 사이징, 용량, 비용(⑥)은 전 계층에 공통으로 적용되고, 통합 설계(⑦)가 이 결정을 하나의 플랫폼 설계로 종합한다.</desc>')
  # headers
  a(f'<text x="{SX}" y="34" font-size="13" font-weight="600" fill="{t["head"]}">4계층 (상위 계층은 하위 계층을 기반으로 동작)</text>')
  a(f'<text x="{X5}" y="34" font-size="13" font-weight="600" fill="{t["head"]}">전 계층 공통</text>')
  for i, (role, name, sub, desc, chip, ext) in enumerate(ROWS):
    y = Y0 + i * (RH + GAP)
    a(f'<text x="{SX-16}" y="{y+RH/2+5}" font-size="14" font-weight="600" text-anchor="end" fill="{t["muted"]}">{role}</text>')
    dash = ' stroke-dasharray="6 4"' if ext else ''
    fill = 'none' if ext else t["layer_fill"]
    a(f'<rect x="{SX}" y="{y}" width="{SW}" height="{RH}" rx="8" fill="{fill}" stroke="{t["layer_stroke"]}" stroke-width="1.5"{dash}/>')
    a(f'<text x="{SX+20}" y="{y+30}" font-size="18" font-weight="700" fill="{t["text"]}">{name}</text>')
    a(f'<text x="{SX+20}" y="{y+52}" font-size="13" fill="{t["muted"]}">{sub}</text>')
    a(f'<text x="{SX+20}" y="{y+73}" font-size="14" fill="{t["text"]}">{desc}</text>')
    cw = 96
    cx, cy = SX + SW - 16 - cw, y + 14
    a(f'<rect x="{cx}" y="{cy}" width="{cw}" height="26" rx="13" fill="{t["chip_fill"]}"/>')
    a(f'<text x="{cx+cw/2}" y="{cy+18}" font-size="13" font-weight="600" text-anchor="middle" fill="{t["chip_text"]}">{chip}</text>')
  # cross-cutting bars
  bh = 4 * RH + 3 * GAP
  for x, num, lines in ((X5, "⑤", ["보안,", "거버넌스"]), (X6, "⑥", ["사이징,", "용량, 비용"])):
    a(f'<rect x="{x}" y="{Y0}" width="{XW}" height="{bh}" rx="8" fill="{t["x_fill"]}" stroke="{t["x_stroke"]}" stroke-width="1.5"/>')
    cx, cy = x + XW / 2, Y0 + bh / 2
    a(f'<text x="{cx}" y="{cy-22}" font-size="24" font-weight="700" text-anchor="middle" fill="{t["x_text"]}">{num}</text>')
    for j, ln in enumerate(lines):
      a(f'<text x="{cx}" y="{cy+10+j*22}" font-size="15" font-weight="600" text-anchor="middle" fill="{t["text"]}">{ln}</text>')
  # synthesis bar
  dy = Y0 + bh + 20
  dw = X6 + XW - SX
  a(f'<text x="{SX-16}" y="{dy+33}" font-size="14" font-weight="600" text-anchor="end" fill="{t["muted"]}">종합</text>')
  a(f'<rect x="{SX}" y="{dy}" width="{dw}" height="56" rx="8" fill="{t["d_fill"]}" stroke="{t["d_stroke"]}" stroke-width="1.5"/>')
  a(f'<text x="{SX+20}" y="{dy+34}" font-size="16" fill="{t["text"]}"><tspan font-weight="700" fill="{t["d_text"]}">⑦ 통합 설계</tspan><tspan dx="14">4계층과 ⑤⑥의 결정을 하나의 플랫폼 설계로 종합</tspan></text>')
  a('</svg>')
  return "\n".join(o) + "\n"

out = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
for name, t in THEMES.items():
  open(f"{out}/series-layers-{name}.svg", "w").write(svg(t))

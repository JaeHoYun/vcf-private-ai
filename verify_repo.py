#!/usr/bin/env python3
"""VCF Private AI 가이드 저장소 검증 스크립트.

CONVENTIONS.md와 CLAUDE.md 가운데 기계로 판정할 수 있는 규칙을 검사한다.
표준 라이브러리만 사용한다. 위반이 하나라도 있으면 종료 코드 1을 반환한다.

검사 항목
  MIDDOT    가운뎃점(U+00B7) 사용 금지 (CONVENTIONS 7절)
  SECTION   절 기호(U+00A7) 사용 금지 (CONVENTIONS 7절)
  PILCROW   단락 기호(U+00B6) 사용 금지 (CONVENTIONS 7절)
  TILDE     물결(~) 사용 금지. 코드 블록과 코드 스팬은 제외 (CONVENTIONS 7절)
  EMOJI     이모지 사용 금지 (CONVENTIONS 7절)
  H1        docs/NN-*.md, appendix/AN-*.md의 H1 형식 `# NN — 제목` (CONVENTIONS 3절)
  LINK      상대 링크와 .md#앵커, 저장소 간 github.com/JaeHoYun 링크의 대상 존재
  DASH      두 구를 대시(—)로 잇는 구조 금지 (CLAUDE.md 문장 규칙 3)

사용법
  python3 verify_repo.py                  # 전체 검사
  python3 verify_repo.py --check LINK     # 특정 검사만 (여러 번 지정 가능)
  python3 verify_repo.py --siblings ..    # 형제 저장소 clone 위치(기본: 이 저장소의 상위 폴더)

형제 저장소(vcf-private-ai-apps, enterprise-ax-methodology)가 --siblings 위치에 clone돼
있으면 그 저장소를 가리키는 링크와 앵커도 검사하고, 없으면 건너뛴 수를 보고한다.
"""
import argparse
import os
import re
import sys
import urllib.parse

OWNER = "JaeHoYun"
THIS_REPO = "vcf-private-ai"
SIBLINGS = ("vcf-private-ai-apps", "enterprise-ax-methodology")
CHECKS = ("MIDDOT", "SECTION", "PILCROW", "TILDE", "EMOJI", "H1", "LINK", "DASH")
# 규칙 문서는 금지 대상 기호와 구조를 예시로 인용하므로 기호, 대시 검사에서 제외한다.
RULE_DOCS = {"CLAUDE.md", "CONVENTIONS.md"}

EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⭕]")
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
H1_FILE_RE = re.compile(r"(^|/)(docs|appendix)/([A-Z]?\d+)-[^/]+\.md$")
H1_RE = re.compile(r"^# [A-Z]?\d+ — \S")
GH_RE = re.compile(
    rf"^https://github\.com/{OWNER}/([^/#]+)(?:/(?:blob|tree)/([^/#]+)(/[^#]*)?)?/?(?:#(.*))?$"
)


def md_files(root):
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if not d.startswith(".")]
        for f in sorted(fn):
            if f.endswith(".md"):
                yield os.path.join(dp, f)


def prose_lines(text):
    """코드 블록 밖의 줄을 (줄 번호, 내용)으로 돌려준다."""
    in_fence = False
    for i, line in enumerate(text.split("\n"), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield i, line


def strip_code_spans(line):
    return re.sub(r"`[^`]*`", "", line)


def slug(heading):
    """GitHub 앵커 규칙: 소문자화, 문자, 숫자, 한글, 하이픈, 공백 외 제거, 공백은 하이픈."""
    h = re.sub(r"<[^>]+>", "", heading).strip().lower()
    h = re.sub(r"[^0-9a-z가-힣ㄱ-ㅎㅏ-ㅣ①-⑳\-_ ]", "", h)
    return h.replace(" ", "-")


_anchor_cache = {}


def anchors(path):
    if path not in _anchor_cache:
        found, count = set(), {}
        text = open(path, encoding="utf-8").read()
        for _, line in prose_lines(text):
            m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
            if m:
                base = slug(m.group(2))
                n = count.get(base, 0)
                count[base] = n + 1
                found.add(base if n == 0 else f"{base}-{n}")
        found.update(re.findall(r'<a\s+(?:name|id)="([^"]+)"', text))
        _anchor_cache[path] = found
    return _anchor_cache[path]


def check_target(path, anchor):
    if not os.path.exists(path):
        return "대상 파일 없음"
    if os.path.isdir(path):
        if not anchor:
            return None
        path = os.path.join(path, "README.md")
        if not os.path.exists(path):
            return "앵커가 있으나 폴더에 README.md 없음"
    if anchor and path.endswith(".md"):
        a = urllib.parse.unquote(anchor)
        if a not in anchors(path):
            return f"앵커 없음 #{a}"
    return None


def run(root, siblings_dir, enabled):
    roots = {THIS_REPO: root}
    for name in SIBLINGS:
        p = os.path.join(siblings_dir, name)
        if os.path.isdir(p):
            roots[name] = p
    errors, skipped, checked = [], 0, 0

    for path in md_files(root):
        rel = os.path.relpath(path, root)
        base = os.path.basename(path)
        text = open(path, encoding="utf-8").read()
        h1_target = bool(H1_FILE_RE.search(rel.replace(os.sep, "/")))
        h1_seen = False

        for no, line in prose_lines(text):
            loc = f"{rel}:{no}"
            plain = strip_code_spans(line)
            is_rule_doc = base in RULE_DOCS

            if not is_rule_doc:
                if "MIDDOT" in enabled and "·" in plain:
                    errors.append(("MIDDOT", loc, "가운뎃점(·)"))
                if "SECTION" in enabled and "§" in plain:
                    errors.append(("SECTION", loc, "절 기호(§)"))
                if "PILCROW" in enabled and "¶" in plain:
                    errors.append(("PILCROW", loc, "단락 기호(¶)"))
                if "TILDE" in enabled and "~" in re.sub(r"\]\([^)]*\)", "", plain):
                    errors.append(("TILDE", loc, "물결(~)"))
                if "EMOJI" in enabled and EMOJI_RE.search(plain):
                    errors.append(("EMOJI", loc, "이모지"))

            if "H1" in enabled and h1_target and line.startswith("# ") and not h1_seen:
                h1_seen = True
                if not H1_RE.match(line):
                    errors.append(("H1", loc, "H1 형식은 `# NN — 제목`"))

            if "DASH" in enabled and not is_rule_doc and "—" in plain:
                t = plain
                if re.match(r"^# [A-Z]?\d+ — ", t):
                    t = ""  # H1 번호 구분자
                # 외부 자료 링크 텍스트(원래 제목과 출처 표기)는 예외
                t = LINK_RE.sub(
                    lambda m: "" if m.group(2).startswith("http") and f"github.com/{OWNER}/" not in m.group(2) else m.group(0),
                    t,
                )
                # 값 없음을 뜻하는 단독 셀(| — |, LLM05 / — |)은 예외: 대시 한쪽에 내용이 없음
                if re.search(r"[^\s|]\s*—\s*[^\s|]", t):
                    errors.append(("DASH", loc, "두 구를 대시로 잇는 구조"))

            if "LINK" in enabled:
                for m in LINK_RE.finditer(line):
                    url = m.group(2)
                    gm = GH_RE.match(url)
                    if gm:
                        repo, ref, sub, anc = gm.groups()
                        if ref and ref != "main":
                            continue  # 태그와 커밋 고정 링크는 검사하지 않음
                        if repo not in roots:
                            skipped += 1
                            continue
                        target = roots[repo] + (urllib.parse.unquote(sub) if sub else "")
                        target = target.rstrip("/") or roots[repo]
                    elif re.match(r"^[a-z][a-z0-9+.-]*:", url):
                        continue  # 외부 URL과 mailto 등은 검사하지 않음
                    else:
                        part, _, anc = url.partition("#")
                        target = path if not part else os.path.normpath(
                            os.path.join(os.path.dirname(path), urllib.parse.unquote(part))
                        )
                    checked += 1
                    err = check_target(target, anc)
                    if err:
                        errors.append(("LINK", loc, f"{url} ({err})"))

    return errors, checked, skipped, sorted(roots)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="append", choices=CHECKS, help="실행할 검사(기본: 전체)")
    ap.add_argument("--siblings", default=None, help="형제 저장소 clone 위치(기본: 상위 폴더)")
    args = ap.parse_args()

    root = os.path.dirname(os.path.abspath(__file__))
    siblings_dir = os.path.abspath(args.siblings) if args.siblings else os.path.dirname(root)
    enabled = set(args.check or CHECKS)

    errors, checked, skipped, repos = run(root, siblings_dir, enabled)
    for kind, loc, msg in errors:
        print(f"{kind:8} {loc}  {msg}")

    counts = {k: sum(1 for e in errors if e[0] == k) for k in CHECKS if k in enabled}
    print("\n검사 결과: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    if "LINK" in enabled:
        print(f"링크 {checked}개 검사, 형제 저장소 미존재로 건너뜀 {skipped}개 (확인한 저장소: {', '.join(repos)})")
    print("통과" if not errors else f"위반 {len(errors)}건")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

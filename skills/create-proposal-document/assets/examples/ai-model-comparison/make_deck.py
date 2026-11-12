# -*- coding: utf-8 -*-
"""Example: a 17-slide editorial comparison deck (OpenAI GPT vs Anthropic Claude) built with python-pptx only.

SNAPSHOT of 2026-11-12. Every model name, price and rule below was read from the vendors' own documentation on that
date and changes often: re-verify with references/ai-vendor-comparison-playbook.md before reusing a number.

It demonstrates the design system in references/editorial-deck-design.md: a nine-step type scale, one content grid,
stacked text boxes, hairlines only where they carry structure, native charts, and the at-a-glance patterns
(head-to-head scoreboard, proportional bars, yes/no matrix, three-way triage, weight bar).

Usage:
    python make_deck.py out.pptx
    python ../../../scripts/tidy_audit.py out.pptx

Needs python-pptx and Pillow (requirements.txt). The fonts Noto Serif KR, Noto Sans KR and Georgia are used by name
and are not bundled; without them PowerPoint substitutes other fonts, so share a PDF. The cover and closing art is
generated in code (no stock images, no logos).
"""
import io, math, sys
from PIL import Image, ImageDraw, ImageFilter
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt
from lxml import etree

if len(sys.argv) != 2:
    raise SystemExit(__doc__)
OUT = sys.argv[1]
TOTAL = 17
# ---- fonts (5 families)
F_R, F_L, F_M, F_S, F_N = "Noto Sans KR", "Noto Sans KR Light", "Noto Sans KR Medium", "Noto Serif KR SemiBold", "Georgia"
# ---- type scale (9 sizes, nothing else is allowed)
T_FOOT, T_LABEL, T_BODY, T_H2, T_H1, T_NUM, T_TITLE, T_BIG, T_DISPLAY = 8.5, 9.5, 11, 13, 16, 24, 27, 34, 44
# ---- colors
def rgb(h): return RGBColor.from_string(h)
PAPER, WHITE, INK, SLATE, MUTED, HAIR = "FAF8F4", "FFFFFF", "14181F", "4B5563", "8A8F98", "DDD7CB"
NAVY, NAVY_2 = "0E1830", "1B2C52"
BRASS, BRASS_L, TINT = "A27F3E", "D2B67E", "F3EEE3"
BRASS_M, HAIR_L = "BFA46C", "E9E4D9"   # quieter numerals, fainter table rules
GPT, CLA = "0F7A68", "B4532F"
GREEN, AMBER = "2F7D5B", "B7791F"
# ---- grid
CX, CW = 0.85, 11.633
RIGHT = CX + CW
CT, CB = 2.25, 6.75               # every slide's content block starts at CT and ends at CB
COL2 = [CX, CX + 6.083]; W2 = 5.55
IDX = 0.8                          # index column of every numbered list (number | text)
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
PAGE = [0]
def I(v): return Inches(v)

def ys(n, top=CT, bottom=CB):
    p = (bottom - top) / n
    return [round(top + i * p, 3) for i in range(n)], round(p, 3)

# ------------------------------------------------------------------ primitives
def _strip_style(s):
    st = s._element.find(qn("p:style"))
    if st is not None: s._element.remove(st)

def set_fonts(rPr, name):
    lat = rPr.find(qn("a:latin"))
    if lat is None: lat = etree.SubElement(rPr, qn("a:latin"))
    lat.set("typeface", name)
    for tag in ("a:ea", "a:cs"):
        for old in rPr.findall(qn(tag)): rPr.remove(old)
    ea = etree.Element(qn("a:ea")); ea.set("typeface", name)
    cs = etree.Element(qn("a:cs")); cs.set("typeface", name)
    lat.addnext(ea); ea.addnext(cs)

def gradient(s, c1, c2, angle=0):
    s.fill.gradient(); s.fill.gradient_angle = angle
    g = s.fill.gradient_stops
    g[0].color.rgb = rgb(c1); g[0].position = 0
    g[1].color.rgb = rgb(c2); g[1].position = 1

def shape(sl, kind, x, y, w, h, fill=None, line=None, lw=0.75):
    s = sl.shapes.add_shape(kind, I(x), I(y), I(w), I(h)); _strip_style(s)
    if fill: s.fill.solid(); s.fill.fore_color.rgb = rgb(fill)
    else: s.fill.background()
    if line: s.line.color.rgb = rgb(line); s.line.width = Pt(lw)
    else: s.line.fill.background()
    return s

def rect(sl, x, y, w, h, fill=None, line=None, **k): return shape(sl, MSO_SHAPE.RECTANGLE, x, y, w, h, fill, line, **k)
def oval(sl, x, y, w, h, fill=None, line=None, **k): return shape(sl, MSO_SHAPE.OVAL, x, y, w, h, fill, line, **k)
def hair(sl, x, y, w, color=HAIR, t=0.012): return rect(sl, x, y, w, t, color)
def vhair(sl, x, y, h, color=HAIR, t=0.012): return rect(sl, x, y, t, h, color)

def P(t, size=T_BODY, font=F_R, color=INK, after=0, spc=None, align=None):
    o = {"size": size, "font": font, "color": color}
    if after: o["space_after"] = after
    if spc is not None: o["spc"] = spc
    if align: o["align"] = align
    return (t, o)

def text(sl, x, y, w, h, paras, size=T_BODY, color=INK, font=F_R, align="l", anchor="t", spacing=1.25, spc=None):
    tb = sl.shapes.add_textbox(I(x), I(y), I(w), I(h))
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}[anchor]
    if isinstance(paras, str): paras = [paras]
    first = True
    for p in paras:
        opts = {}
        if isinstance(p, tuple): p, opts = p
        para = tf.paragraphs[0] if first else tf.add_paragraph(); first = False
        para.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[opts.get("align", align)]
        para.line_spacing = opts.get("spacing", spacing)
        if "space_after" in opts: para.space_after = Pt(opts["space_after"])
        for t, ro in (p if isinstance(p, list) else [(p, {})]):
            r = para.add_run(); r.text = t; f = r.font
            f.size = Pt(ro.get("size", opts.get("size", size))); f.bold = False
            f.color.rgb = rgb(ro.get("color", opts.get("color", color)))
            rPr = r._r.get_or_add_rPr(); set_fonts(rPr, ro.get("font", opts.get("font", font)))
            sp = ro.get("spc", opts.get("spc", spc))
            if sp is not None: rPr.set("spc", str(sp))
    return tb

def label(sl, x, y, w, t, color=MUTED, align="l", h=0.25):
    return text(sl, x, y, w, h, [P(t, T_LABEL, F_M, color, spc=100, align=align)], anchor="m")

def index_row(sl, x, y, h, w, num, head, body, num_color=BRASS, head_w=None):
    """number | heading + body, all boxes share (y, h) so nothing drifts."""
    text(sl, x, y, IDX, h, [P(num, T_H1, F_N, BRASS_M)], anchor="m")
    text(sl, x + IDX, y, w - IDX, h, [P(head, T_H2, F_M, INK, after=3), P(body, T_BODY, F_R, SLATE)], anchor="m")

# ------------------------------------------------------------------ line icons
def _poly(sl, pts, x, y, s, color, w=1.2, close=False):
    fb = sl.shapes.build_freeform(I(x + pts[0][0] * s), I(y + pts[0][1] * s))
    fb.add_line_segments([(I(x + px * s), I(y + py * s)) for px, py in pts[1:]], close=close)
    sh = fb.convert_to_shape(); _strip_style(sh); sh.fill.background()
    sh.line.color.rgb = rgb(color); sh.line.width = Pt(w)

def icon(sl, kind, x, y, s=0.34, color=INK, w=1.2):
    if kind == "layers":
        _poly(sl, [(.5, .08), (.94, .3), (.5, .52), (.06, .3)], x, y, s, color, w, True)
        _poly(sl, [(.06, .5), (.5, .72), (.94, .5)], x, y, s, color, w)
        _poly(sl, [(.06, .7), (.5, .92), (.94, .7)], x, y, s, color, w)
    elif kind == "bolt":
        _poly(sl, [(.6, .04), (.2, .56), (.48, .56), (.4, .96), (.8, .4), (.52, .4)], x, y, s, color, w, True)
    elif kind == "nodes":
        for cx, cy in ((.2, .5), (.8, .2), (.8, .8)): oval(sl, x + (cx - .12) * s, y + (cy - .12) * s, .24 * s, .24 * s, None, color, lw=w)
        _poly(sl, [(.31, .45), (.69, .25)], x, y, s, color, w); _poly(sl, [(.31, .55), (.69, .75)], x, y, s, color, w)
    elif kind == "gear":   # target: two rings
        oval(sl, x + .1 * s, y + .1 * s, .8 * s, .8 * s, None, color, lw=w)
        oval(sl, x + .35 * s, y + .35 * s, .3 * s, .3 * s, None, color, lw=w)

# ------------------------------------------------------------------ frame
SECTIONS = ["sum", "dir", "lin", "pc", "sel", "app"]
SEC = {"sum": ("01", "핵심 요약"), "dir": ("02", "추구 방향"), "lin": ("03", "라인업·가격·사양"),
       "pc": ("04", "강점과 유의점"), "sel": ("05", "선택과 도입"), "app": ("A", "근거와 한계")}

def new_slide(sec, title, lead, source="", notes=""):
    sl = prs.slides.add_slide(BLANK); PAGE[0] += 1
    rect(sl, 0, 0, 13.333, 7.5, PAPER)
    no, name = SEC[sec]
    text(sl, CX, 0.4, 5, 0.26, [[(no, {"size": T_BODY, "font": F_N, "color": BRASS}), ("    " + name, {"size": T_LABEL, "font": F_M, "color": BRASS, "spc": 80})]], anchor="m")
    text(sl, CX, 0.8, CW, 0.6, [P(title, T_TITLE, F_S, INK, spc=-30)], anchor="m")
    text(sl, CX, 1.45, CW, 0.3, [P(lead, T_H2, F_L, SLATE)], anchor="m")
    if source: text(sl, CX, 7.06, 10.4, 0.26, [P(source, T_FOOT, F_R, MUTED)], anchor="m")
    text(sl, RIGHT - 1.2, 7.06, 1.2, 0.26, [P("%02d / %d" % (PAGE[0], TOTAL), T_FOOT, F_N, MUTED, align="r")], anchor="m")
    if notes: sl.notes_slide.notes_text_frame.text = notes
    return sl

# ------------------------------------------------------------------ tables
def cell_border(cell, color=HAIR, w=9525, sides=("b",)):
    tcPr = cell._tc.get_or_add_tcPr()
    for side in ("l", "r", "t", "b"):
        tag = qn("a:ln" + side.upper())
        for old in tcPr.findall(tag): tcPr.remove(old)
        ln = etree.SubElement(tcPr, tag)
        if side in sides:
            ln.set("w", str(w)); ln.set("cap", "flat"); ln.set("cmpd", "sng")
            sf = etree.SubElement(ln, qn("a:solidFill")); etree.SubElement(sf, qn("a:srgbClr")).set("val", color)
        else:
            ln.set("w", "0"); etree.SubElement(ln, qn("a:noFill"))
    for tag in ("a:solidFill", "a:noFill"):
        for el in tcPr.findall(qn(tag)):
            tcPr.remove(el); tcPr.append(el)

def table(sl, col_w, rows, heads, top=CT, bottom=CB, head_h=0.44, tint_rows=(), max_row=0.7):
    n = len(rows); row_h = min(max_row, (bottom - top - head_h) / n)
    gf = sl.shapes.add_table(n + 1, len(col_w), I(CX), I(top), I(sum(col_w)), I(head_h + row_h * n))
    tb = gf.table
    tb._tbl.tblPr.set("firstRow", "0"); tb._tbl.tblPr.set("bandRow", "0")
    sid = tb._tbl.tblPr.find(qn("a:tableStyleId"))
    if sid is not None: sid.text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"
    for i, cw in enumerate(col_w): tb.columns[i].width = I(cw)
    tb.rows[0].height = I(head_h)
    for r in range(1, n + 1): tb.rows[r].height = I(row_h)
    def put(cell, content, sz, color, font, fill, spc=None):
        cell.fill.solid(); cell.fill.fore_color.rgb = rgb(fill)
        cell.margin_left = I(0.0); cell.margin_right = I(0.18); cell.margin_top = cell.margin_bottom = I(0.04)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf = cell.text_frame; tf.word_wrap = True
        for k, ln in enumerate(content if isinstance(content, list) else [content]):
            p = tf.paragraphs[0] if k == 0 else tf.add_paragraph(); p.line_spacing = 1.15
            for t, ro in (ln if isinstance(ln, list) else [(ln, {})]):
                rn = p.add_run(); rn.text = t; f = rn.font
                f.size = Pt(ro.get("size", sz)); f.bold = False; f.color.rgb = rgb(ro.get("color", color))
                rPr = rn._r.get_or_add_rPr(); set_fonts(rPr, ro.get("font", font))
                if spc is not None: rPr.set("spc", str(spc))
    for c, (lab, col) in enumerate(heads):
        put(tb.cell(0, c), lab, T_LABEL, col, F_M, PAPER, spc=60)
        cell_border(tb.cell(0, c), col if col != MUTED else INK, 12700, ("b",))
    for r, row in enumerate(rows, start=1):
        for c, content in enumerate(row):
            put(tb.cell(r, c), content, T_BODY, SLATE if c == 0 else INK, F_M if c == 0 else F_R, TINT if (r - 1) in tint_rows else PAPER)
            cell_border(tb.cell(r, c), HAIR_L, 9525, ("b",))
    return top + head_h + row_h * n

def chart_font(ch, size, color=SLATE):
    ch.font.size = Pt(size); ch.font.color.rgb = rgb(color); set_fonts(ch.font._element, F_R)

# ------------------------------------------------------------------ generated art
def ribbon(seed, size=(1920, 1080)):
    W, H = size; S = 2
    big = Image.new("RGB", (W * S, H * S), (11, 20, 40)); d = ImageDraw.Draw(big, "RGBA")
    for yy in range(0, H * S, 4):
        t = yy / (H * S); d.line([(0, yy), (W * S, yy)], fill=(int(11 + 10 * t), int(20 + 14 * t), int(40 + 22 * t), 255), width=4)
    N = 96; teal, terra = (30, 170, 146), (214, 116, 78)
    for i in range(N):
        t = i / (N - 1); col = tuple(int(teal[k] + (terra[k] - teal[k]) * t) for k in range(3)); pts = []
        for xi in range(0, W * S + 8, 8):
            x = xi / (W * S)
            pinch = 0.22 + 0.78 * (0.5 + 0.5 * math.sin(x * 5.2 + seed * 0.7))
            cy = 0.52 + 0.13 * math.sin(x * 3.1 + seed) + 0.05 * math.sin(x * 9 + seed * 2)
            pts.append((x * W * S, (cy + (t - 0.5) * 0.46 * pinch) * H * S))
        d.line(pts, fill=col + (int(170 + 70 * math.sin(t * math.pi)),), width=3)
    img = big.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.5))
    fade = Image.linear_gradient("L").rotate(90).resize((W, H))
    mask = fade.point(lambda v: 0 if v < 75 else min(255, int((v - 75) * 1.7)))
    out = Image.composite(img, Image.new("RGB", (W, H), (11, 20, 40)), mask)
    buf = io.BytesIO(); out.save(buf, "JPEG", quality=92); buf.seek(0)
    return buf

# ------------------------------------------------------------------ data
MODELS = [("GPT-6 Astra", "g", 10, 50, 1.00), ("GPT-6.1 Sol", "g", 2, 10, 0.10), ("GPT-6.1 Terra", "g", 1, 5, 0.05),
          ("GPT-6 Luna", "g", 0.1, 0.5, 0.01), ("Claude Fable 5.2", "c", 8, 40, 0.20), ("Claude Opus 5.5", "c", 4, 20, 0.20),
          ("Claude Sonnet 5.5", "c", 2, 10, 0.10), ("Claude Haiku 5.5", "c", 0.10, 0.50, 0.01)]
VC = {"g": GPT, "c": CLA}
def money(v): return "$" + ("%.2f" % v).rstrip("0").rstrip(".")
N = ("✕", MUTED)
def mark(m, t): return [[(m[0], {"color": m[1], "size": T_H2}), ("   " + t, {})]]
Yg, Yc = ("●", GPT), ("●", CLA)

# ================================================================== 1 cover
sl = prs.slides.add_slide(BLANK); PAGE[0] += 1
sl.shapes.add_picture(ribbon(3), 0, 0, I(13.333), I(7.5))
text(sl, CX, 1.3, 8, 0.3, [P("OpenAI GPT(생성형 사전학습 모델)  ×  Anthropic Claude", T_BODY, F_M, BRASS_L, spc=120)], anchor="m")
rect(sl, CX, 1.85, 0.7, 0.03, BRASS_L)
text(sl, CX, 2.15, 7.4, 2.85, [P(t, T_DISPLAY, F_S, WHITE, spc=-40) for t in ("GPT와 Claude,", "무엇이 다르고", "어떻게 고를 것인가")], spacing=1.22)
text(sl, CX, 5.1, 6.3, 0.7, [P("추구 방향 · 라인업과 가격 · 강점과 유의점을 양사 공식 문서 기준으로 비교합니다", T_H2, F_L, "C5CEDD")], spacing=1.5)
for i, (k, v) in enumerate((("기준일", "2026-11-12"), ("작성", "Claude (Anthropic 모델)"), ("근거", "OpenAI · Anthropic 공식 문서"))):
    text(sl, CX + (0, 2.2, 5.1)[i], 6.3, 3.4, 0.6, [P(k, T_LABEL, F_M, BRASS_L, spc=100, after=4), P(v, T_BODY, F_R, "E6EBF3")])
g = rect(sl, 0, 7.4, 13.333, 0.1, GPT); gradient(g, GPT, CLA, 0)
sl.notes_slide.notes_text_frame.text = "작성 주체가 Anthropic의 Claude이므로 이해관계가 있을 수 있다. 이를 줄이기 위해 수치는 양사 공식 문서의 값만 사용했고 벤치마크 점수는 넣지 않았다."

# ================================================================== 2 agenda
sl = prs.slides.add_slide(BLANK); PAGE[0] += 1
rect(sl, 0, 0, 13.333, 7.5, PAPER); rect(sl, 0, 0, 4.5, 7.5, NAVY)
text(sl, CX, 0.9, 3.2, 1.6, [P("Contents", T_H1, F_N, BRASS_L, spc=80, after=6), P("목차", T_DISPLAY, F_S, WHITE, spc=-30)])
rect(sl, CX, 2.75, 0.5, 0.025, BRASS_L)
text(sl, CX, 3.05, 3.0, 1.2, [P("결론을 먼저 보고, 근거와 한계는 마지막에 확인합니다.", T_H2, F_L, "C5CEDD")], spacing=1.55)
ag = [("01", "핵심 요약", "10개 항목 한눈에 비교", "03"), ("02", "추구 방향", "미션과 제품 설계의 차이", "04"),
      ("03", "라인업·가격·사양", "사다리, 단가, 비용, 과금 규칙, 도구, 데이터 거주", "05–10"), ("04", "강점과 유의점", "GPT와 Claude 각각의 평가", "11–12"),
      ("05", "선택과 도입", "상황별 선택, 평가 절차, 위험", "13–15"), ("A", "근거와 한계", "출처와 확인하지 못한 것", "16")]
rows_y, pitch = ys(6, 0.9, 6.9)
for (n, h, d, pg), y in zip(ag, rows_y):
    text(sl, 5.3, y, IDX, 0.85, [P(n, T_NUM, F_N, BRASS)], anchor="m")
    text(sl, 5.3 + IDX, y, 4.9, 0.85, [P(h, T_H1, F_S, INK, after=3), P(d, T_BODY, F_R, SLATE)], anchor="m")
    text(sl, 11.3, y, 1.18, 0.85, [P(pg, T_BODY, F_N, MUTED, align="r")], anchor="m")
text(sl, RIGHT - 1.2, 7.06, 1.2, 0.26, [P("%02d / %d" % (PAGE[0], TOTAL), T_FOOT, F_N, MUTED, align="r")], anchor="m")

# ================================================================== 3 scoreboard
sl = new_slide("sum", "10개 항목 비교: 4 대 4, 나머지 2는 동일",
               "공식 문서의 사양·가격 기준입니다. 응답 품질 비교가 아니며, 유리는 낮은 가격이나 넓은 제공 범위를 뜻합니다.",
               source="출처: OpenAI·Claude 공식 모델·가격·데이터 문서 (2026-11-12 조회). 판정은 문서에 적힌 가격과 제공 범위 기준",
               notes="판정 기준: 가격은 낮은 쪽, 기능·제공 범위는 문서에서 확인된 쪽을 유리로 표시했다. 음성·전사 모델은 OpenAI 모델 문서에 전용 모델이 나열돼 있고 Claude 라인업에는 없다는 점을 기준으로 했다.")
GLX, GLW = CX, 2.9
GVX, GVW = CX + 2.95, 2.65
TRX, TRW = CX + 5.75, 1.8
CVX, CVW = CX + 7.7, 2.65
VDX, VDW = CX + 10.35, CW - 10.35
label(sl, GLX, CT, GLW, "항목", MUTED)
label(sl, GVX, CT, GVW, "OPENAI GPT", GPT, align="r")
label(sl, CVX, CT, CVW, "ANTHROPIC CLAUDE", CLA)
label(sl, VDX, CT, VDW, "문서 기준", MUTED, align="r")
hair(sl, CX, CT + 0.3, CW, INK, 0.014)
score = [("플래그십 입력 단가", "$10 (Astra)", "$8 (Fable 5.2)", "c"),
         ("경량 입력 단가", "$0.1 (Luna)", "$0.10 (Haiku 5.5)", "="),
         ("장문 컨텍스트 단가", "272K 초과 시 2배", "1M까지 동일", "c"),
         ("클라우드 공급 경로", "Bedrock · Google(프리뷰)", "자사 API + 4곳", "c"),
         ("모델 제공 기간 공개", "문서에 없음", "최소 시한 공개", "c"),
         ("검색·코드·컴퓨터 사용", "지원", "지원", "="),
         ("속도 옵션", "Fast · Ultrafast", "Fast 모드 (2개 모델)", "g"),
         ("이미지 생성 도구", "있음", "없음", "g"),
         ("음성·전사 전용 모델", "있음", "라인업에 없음", "g"),
         ("한국 내 저장", "가능", "불가", "g")]
assert [x[3] for x in score].count("g") == 4 and [x[3] for x in score].count("c") == 4 and [x[3] for x in score].count("=") == 2
rows_y, pitch = ys(10, CT + 0.38, CB)
for (lab, gv, cv, win), y in zip(score, rows_y):
    h_ = pitch - 0.04
    yc = y + h_ / 2
    text(sl, GLX, y, GLW, h_, [P(lab, T_BODY, F_M, INK)], anchor="m")
    text(sl, GVX, y, GVW, h_, [P(gv, T_BODY, F_M if win == "g" else F_R, INK if win == "g" else SLATE, align="r")], anchor="m")
    text(sl, CVX, y, CVW, h_, [P(cv, T_BODY, F_M if win == "c" else F_R, INK if win == "c" else SLATE)], anchor="m")
    rect(sl, TRX + 0.1, yc - 0.006, TRW - 0.2, 0.012, HAIR)
    for key, dx, col in (("g", 0.25, GPT), ("=", TRW / 2, INK), ("c", TRW - 0.25, CLA)):
        d = 0.22 if win == key else 0.08
        oval(sl, TRX + dx - d / 2, yc - d / 2, d, d, col if win == key else HAIR)
    verdict = {"g": ("GPT 유리", GPT), "c": ("Claude 유리", CLA), "=": ("동일", MUTED)}[win]
    text(sl, VDX, y, VDW, h_, [P(verdict[0], T_BODY, F_M, verdict[1], align="r")], anchor="m")
    hair(sl, CX, y + pitch - 0.02, CW, HAIR_L)

# ================================================================== 4 direction
sl = new_slide("dir", "추구 방향이 다르면 제품 설계도 달라집니다",
               "미션과 제품 설계는 공식 소개와 문서에서 확인되는 사실만 정리했습니다.",
               source="출처: anthropic.com/company, openai.com/our-structure, OpenAI·Claude 모델·가격 문서. 미션·구조는 각사 공식 소개 기준",
               notes="미션 문구는 각사 공식 소개를 의역했다. 제품 항목은 모델·가격 문서에서 확인한 사실이다.")
panels = [("OpenAI GPT", "AGI(범용 인공지능)가 모든 인류에게 혜택이 되도록", GPT,
           [("nodes", "구조", "비영리 Foundation + 영리 Group, 같은 미션"),
            ("layers", "제품", "웹·파일 검색, 컴퓨터 사용, 이미지 생성 등 10종"),
            ("bolt", "속도·가격", "Standard · Batch · Fast · Ultrafast"),
            ("gear", "운영", "4단 라인업, 계정 등급별 한도")]),
          ("Anthropic Claude", "첨단 AI의 책임 있는 개발, 장기적 인류 이익", CLA,
           [("nodes", "구조", "공익법인(PBC) + Long-Term Benefit Trust"),
            ("layers", "제품", "장시간 에이전트·코딩·지식 업무"),
            ("bolt", "가격·운영", "1M 단일 단가 · 배치 50%"),
            ("gear", "운영", "모델별 최소 제공 시한 공개")])]
rows_y, pitch = ys(4, 3.5, CB)
for x, (name, mission, col, rows) in zip(COL2, panels):
    rect(sl, x, CT, W2, 0.02, col)
    text(sl, x, CT + 0.15, W2, 0.95, [P(name, T_NUM, F_S, INK, spc=-20, after=4), P("미션  " + mission, T_BODY, F_M, col)])
    for (ic, kw, desc), y in zip(rows, rows_y):
        icon(sl, ic, x, y + 0.2, 0.34, col)
        text(sl, x + 0.6, y, 1.6, pitch - 0.08, [P(kw, T_H2, F_M, INK)], anchor="m")
        text(sl, x + 2.2, y, W2 - 2.2, pitch - 0.08, [P(desc, T_BODY, F_R, SLATE)], anchor="m")

# ================================================================== 5 ladder
sl = new_slide("lin", "라인업은 4단 사다리로 대응합니다",
               "순서대로 짝지었을 뿐 성능이 같다는 뜻은 아닙니다. 단가는 100만 토큰당 입력 / 출력입니다.",
               source="출처: OpenAI 모델 문서, Claude 모델 개요 (2026-11-12 조회). Mythos 5.2는 검증된 조직 전용이라 제외",
               notes="Fable 5.2는 모든 고객에게 열린 가장 높은 등급이다. Mythos 5.2는 검증된 조직에만 제공되어 표에서 제외했다.")
LX, LW, MX, MW, RX = CX, 4.95, CX + 5.15, 1.33, CX + 6.68
label(sl, LX, CT, LW, "OPENAI GPT", GPT); rect(sl, LX, CT + 0.32, LW, 0.02, GPT)
label(sl, RX, CT, LW, "ANTHROPIC CLAUDE", CLA); rect(sl, RX, CT + 0.32, LW, 0.02, CLA)
ladder = [("1", "플래그십", ("GPT-6 Astra", "$10 / $50", "가장 어려운 작업용 · 추론·코딩·리서치"), ("Claude Fable 5.2", "$8 / $40", "까다로운 추론·장시간 에이전트 작업")),
          ("2", "고성능", ("GPT-6.1 Sol", "$2 / $10", "Astra에 근접한 성능, 낮은 비용"), ("Claude Opus 5.5", "$4 / $20", "장시간 에이전트 코딩·지식 업무")),
          ("3", "균형", ("GPT-6.1 Terra", "$1 / $5", "빠르고 효율적 · 시각 추론·글쓰기"), ("Claude Sonnet 5.5", "$2 / $10", "속도와 지능의 균형 · 코딩·분석")),
          ("4", "경량", ("GPT-6 Luna", "$0.1 / $0.5", "집중된 대량 작업용 최저가"), ("Claude Haiku 5.5", "$0.10 / $0.50부터", "분류·추출·라우팅, 대량 처리"))]
rows_y, pitch = ys(4, CT + 0.5, CB)
for (no, tier, g_, c_), y in zip(ladder, rows_y):
    for (name, price, desc), x, col in ((g_, LX, GPT), (c_, RX, CLA)):
        text(sl, x, y, 3.2, 0.4, [P(name, T_H1, F_S, INK)], anchor="m")
        text(sl, x + 3.0, y, LW - 3.0, 0.4, [P(price, T_H2, F_N, col, align="r")], anchor="m")
        text(sl, x, y + 0.45, LW, 0.3, [P(desc, T_BODY, F_R, SLATE)], anchor="m")
    rect(sl, MX, y, MW, 0.76, PAPER)
    text(sl, MX, y, MW, 0.76, [P(no, T_NUM, F_N, BRASS, align="c"), P(tier, T_BODY, F_M, INK, align="c")], anchor="m", spacing=1.1)

# ================================================================== 6 price charts
sl = new_slide("lin", "단가는 플래그십·중간·경량 세 구간입니다",
               "모델을 쌍으로 묶지 않고 단가 순으로 나열했습니다. 단위는 100만 토큰당 달러입니다.",
               source="출처: OpenAI·Claude 가격 문서 (2026-11-12 조회). 정가. Haiku 5.5는 프롬프트 100K 이하 기준",
               notes="모델을 쌍으로 묶지 않고 단가 순으로 정렬해 대응 관계의 오해를 피했다.")
order = sorted(MODELS, key=lambda m: -m[2])
def hbar(sl, x, idx, title, vmax):
    w, h = W2, 3.45
    label(sl, x, CT, 3.5, title, INK)
    oval(sl, x + w - 2.0, CT + 0.075, 0.1, 0.1, GPT); text(sl, x + w - 1.84, CT, 0.8, 0.25, [P("OpenAI", T_LABEL, F_R, SLATE)], anchor="m")
    oval(sl, x + w - 0.95, CT + 0.075, 0.1, 0.1, CLA); text(sl, x + w - 0.79, CT, 0.8, 0.25, [P("Claude", T_LABEL, F_R, SLATE)], anchor="m")
    hair(sl, x, CT + 0.32, w, INK, 0.014)
    cd = CategoryChartData(); cd.categories = [m[0] for m in order]; cd.add_series("단가", [m[idx] for m in order])
    gf = sl.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, I(x - 0.05), I(CT + 0.4), I(w + 0.05), I(h - 0.4), cd)
    ch = gf.chart; ch.has_legend = False; ch.has_title = False; chart_font(ch, T_LABEL)
    pl = ch.plots[0]; pl.gap_width = 90; pl.vary_by_categories = False
    ca, va = ch.category_axis, ch.value_axis
    ca.reverse_order = True; ca.format.line.color.rgb = rgb(HAIR); ca.has_major_gridlines = False; ca.tick_labels.font.size = Pt(T_LABEL)
    va.visible = False; va.has_major_gridlines = False; va.maximum_scale = vmax; va.minimum_scale = 0
    for i, m in enumerate(order):
        pt = pl.series[0].points[i]; pt.format.fill.solid(); pt.format.fill.fore_color.rgb = rgb(VC[m[1]])
        dl = pt.data_label; dl.position = XL_LABEL_POSITION.OUTSIDE_END
        dl.text_frame.text = money(m[idx]); r0 = dl.text_frame.paragraphs[0].runs[0]
        r0.font.size = Pt(T_BODY); r0.font.color.rgb = rgb(INK); set_fonts(r0._r.get_or_add_rPr(), F_N)
hbar(sl, COL2[0], 2, "입력 단가", 12.5)
hbar(sl, COL2[1], 3, "출력 단가", 62)
calls = [("플래그십", GPT, "Astra가 Fable 5.2보다 입력·출력 모두 25% 높음"),
         ("같은 단가", INK, "Sol = Sonnet 5.5, Luna = Haiku 5.5"),
         ("빈 구간", CLA, "GPT에는 Opus 5.5($4/$20)급 중간 모델이 없음")]
W3 = 3.61
for i, (h_, col, b) in enumerate(calls):
    x = CX + i * (W3 + 0.4)
    text(sl, x, 6.02, W3, 0.75, [P(h_, T_LABEL, F_M, col, spc=100, after=4), P(b, T_BODY, F_R, SLATE)])

# ================================================================== 7 cost scenario
sl = new_slide("lin", "출력 토큰이 총비용의 3분의 2 안팎입니다",
               "월 입력 1억 토큰(캐시 적중 80%)과 출력 1천만 토큰을 정가로 계산했습니다.",
               source="출처: 공식 가격 문서의 정가로 계산. 캐시 기록 비용, 배치·Fast 등 할인·가산, 데이터 거주 가산은 제외",
               notes="계산식: 비캐시 입력 20M x 입력가 + 캐시 적중 80M x 캐시 읽기가 + 출력 10M x 출력가. 캐시 읽기가는 각 벤더 가격 문서 기준.")
rows7 = []
for name, v, i_, o_, c_ in MODELS:
    non, hit, out = 20 * i_, 80 * c_, 10 * o_
    rows7.append((name, v, non, hit, out, non + hit + out))
shares = [r[4] / r[5] for r in rows7]
assert 0.64 <= min(shares) and max(shares) <= 0.695, shares
rows7.sort(key=lambda r: -r[5])
LW7 = 7.4
label(sl, CX, CT, 5, "월 정가 비용 (USD)", INK); hair(sl, CX, CT + 0.32, LW7, INK, 0.014)
cd = CategoryChartData(); cd.categories = ["%s   %s" % (r[0], money(round(r[5], 1))) for r in rows7]
cd.add_series("입력 (캐시 미적중)", [r[2] for r in rows7]); cd.add_series("입력 (캐시 적중)", [r[3] for r in rows7]); cd.add_series("출력", [r[4] for r in rows7])
gf = sl.shapes.add_chart(XL_CHART_TYPE.BAR_STACKED, I(CX - 0.05), I(CT + 0.4), I(LW7 + 0.1), I(CB - CT - 0.4), cd)
ch = gf.chart; ch.has_title = False; ch.has_legend = True; chart_font(ch, T_LABEL)
ch.legend.include_in_layout = False; ch.legend.font.size = Pt(T_LABEL); ch.legend.position = XL_LEGEND_POSITION.BOTTOM
pl = ch.plots[0]; pl.gap_width = 70; pl.overlap = 100
ch.category_axis.reverse_order = True; ch.category_axis.format.line.color.rgb = rgb(HAIR); ch.category_axis.tick_labels.font.size = Pt(T_LABEL)
ch.value_axis.visible = False; ch.value_axis.has_major_gridlines = False
for ser, col in zip(pl.series, ("B8AE98", "DDD5C3", NAVY)):
    ser.format.fill.solid(); ser.format.fill.fore_color.rgb = rgb(col)
for i, r in enumerate(rows7):
    if r[5] >= 250:
        dl = pl.series[2].points[i].data_label; dl.position = XL_LABEL_POSITION.CENTER
        dl.text_frame.text = "출력 %d%%" % round(100 * r[4] / r[5]); r0 = dl.text_frame.paragraphs[0].runs[0]
        r0.font.size = Pt(T_LABEL); r0.font.color.rgb = rgb(WHITE); set_fonts(r0._r.get_or_add_rPr(), F_M)
RX7 = CX + 8.0; RW7 = CW - 8.0
label(sl, RX7, CT, RW7, "계산 가정", BRASS); hair(sl, RX7, CT + 0.32, RW7, BRASS_L, 0.014)
text(sl, RX7, CT + 0.5, RW7, 1.2, [P(t, T_BODY, F_R, SLATE, after=4) for t in ("월 입력 1억 토큰, 이 중 80%가 캐시 적중", "월 출력 1천만 토큰", "정가 기준, 캐시 기록 비용·할인 제외")])
rect(sl, RX7, 4.2, RW7, CB - 4.2, NAVY)
text(sl, RX7 + 0.3, 4.2, RW7 - 0.6, CB - 4.2, [P("읽는 법", T_LABEL, F_M, BRASS_L, spc=100, after=6), P("64–69%", T_DISPLAY, F_N, WHITE, spc=-30, after=2),
     P("총액에서 출력 토큰이 차지하는 비중", T_BODY, F_R, "9FB0CE", after=10), P("8개 모델 모두 같은 패턴입니다. 응답 길이와 출력 형식을 줄이는 설계가 단가 협상만큼 중요합니다.", T_BODY, F_R, "DCE4F2")], anchor="m")

# ================================================================== 8 billing rules
sl = new_slide("lin", "과금 규칙은 장문 구간에서만 크게 갈립니다",
               "272K 토큰을 넘으면 GPT만 단가가 오르고, 나머지 규칙은 양사가 비슷합니다.",
               source="출처: OpenAI·Claude 가격 문서 (2026-11-12 조회). OpenAI는 할증이 요청 전체에 적용되는지 초과분에만 적용되는지 문서에 불명확",
               notes="Claude Haiku 5.5는 프롬프트 100K 초과 시 단가가 오른다. OpenAI 지역 처리 가산은 모델 출시일 조건이 있어 이 모델들에 적용되는지 미확인.")
BX, BW = CX + 1.6, CW - 1.6
SC = BW / 1.05
label(sl, CX, CT, 6, "요청 길이별 입력 단가 (표준 단가 = 1배)", INK)
ya, yb = CT + 0.55, CT + 1.4
text(sl, CX, ya, 1.5, 0.55, [P("OpenAI", T_H2, F_S, GPT)], anchor="m")
text(sl, CX, yb, 1.5, 0.55, [P("Claude", T_H2, F_S, CLA)], anchor="m")
rect(sl, BX, ya, 0.272 * SC, 0.55, GPT)
text(sl, BX, ya, 0.272 * SC, 0.55, [P("1배", T_H2, F_M, WHITE, align="c")], anchor="m")
rect(sl, BX + 0.272 * SC, ya, BW - 0.272 * SC, 0.55, "0A4F42")
text(sl, BX + 0.272 * SC, ya, BW - 0.272 * SC, 0.55, [P("입력 2배 · 출력 1.5배", T_H2, F_M, WHITE, align="c")], anchor="m")
rect(sl, BX, yb, 1.0 * SC, 0.55, CLA)
text(sl, BX, yb, 1.0 * SC, 0.55, [P("1M까지 입력·출력 모두 1배", T_H2, F_M, WHITE, align="c")], anchor="m")
text(sl, BX + 0.1 * SC, yb + 0.6, 4.5, 0.25, [P("▲ Haiku 5.5만 100K 초과 시 단가 상향", T_LABEL, F_R, MUTED)], anchor="m")
hair(sl, BX, CT + 2.35, BW, INK, 0.014)
for tok, frac in (("0", 0.0), ("272K", 0.272), ("1M", 1.0)):
    vhair(sl, BX + frac * SC - 0.006, CT + 2.35, 0.08, INK)
    text(sl, BX + frac * SC - 0.6, CT + 2.47, 1.2, 0.25, [P(tok, T_LABEL, F_N, SLATE, align="c")], anchor="m")
tiles = [("배치 처리", "50%", "50%"), ("캐시 읽기 (입력가 대비)", "5–10%", "2.5–10%"),
         ("속도 프리미엄", "2배 · 6배", "2배 (2개 모델)"), ("데이터 지역 가산", "10%", "10% (미국 한정)")]
TW = (CW - 3 * 0.3) / 4
for i, (lab, g, c) in enumerate(tiles):
    x = CX + i * (TW + 0.3)
    label(sl, x, 5.05, TW, lab, BRASS)
    hair(sl, x, 5.36, TW, BRASS_L, 0.014)
    for k, (nm, v, col) in enumerate((("OpenAI", g, GPT), ("Claude", c, CLA))):
        yy = 5.5 + k * 0.55
        oval(sl, x, yy + 0.2, 0.1, 0.1, col)
        text(sl, x + 0.2, yy, 0.9, 0.5, [P(nm, T_LABEL, F_R, SLATE)], anchor="m")
        text(sl, x + 0.9, yy, TW - 0.9, 0.5, [P(v, T_H2, F_M, INK, align="r")], anchor="m")

# ================================================================== 9 capability matrix
sl = new_slide("lin", "도구는 많이 겹치고 이미지 생성에서 갈립니다",
               "공식 문서에서 확인된 항목만 표시했습니다. 확인하지 못한 항목은 비워 두었습니다.",
               source="출처: OpenAI GPT-6 Astra 모델 페이지, Claude 모델 개요·모델 API 문서 (2026-11-12). ●: 문서에서 확인, ✕: 해당 라인업 범위 밖",
               notes="Azure에서의 OpenAI 모델 제공 여부와 Claude의 MCP(Model Context Protocol) 지원 범위는 이번 조사에서 확인하지 못했다.")
r9 = [("입력 형식", mark(Yg, "텍스트·이미지"), mark(Yc, "텍스트·이미지")), ("출력 형식", mark(Yg, "텍스트"), mark(Yc, "텍스트")),
      ("웹 검색 도구", mark(Yg, "Responses API 내장"), mark(Yc, "서버 도구로 제공")), ("코드 실행", mark(Yg, "코드 인터프리터"), mark(Yc, "코드 실행 도구")),
      ("컴퓨터 사용", mark(Yg, "지원"), mark(Yc, "지원 (Opus·Fable급)")), ("이미지 생성 도구", mark(Yg, "Responses API 도구"), mark(N, "출력이 텍스트 전용")),
      ("추론 강도 조절", mark(Yg, "low~max 5단계"), mark(Yc, "effort 파라미터")),
      ("클라우드 공급", [[("Bedrock, Google Cloud(비공개 프리뷰)", {})]], [[("자사 API, Bedrock, Google Cloud, Foundry", {})]])]
table(sl, [2.4, 4.6, 4.633], [list(r) for r in r9], [("항목", MUTED), ("OPENAI GPT-6 ASTRA", GPT), ("ANTHROPIC CLAUDE", CLA)], tint_rows=(5,))

# ================================================================== 10 data residency
sl = new_slide("lin", "한국 기준: 저장은 OpenAI만, 국내 추론은 둘 다 없음",
               "자사 API 기준입니다. 한국에 저장 지역을 두는 곳은 OpenAI뿐이고 추론은 양사 모두 국외입니다.",
               source="출처: OpenAI 데이터 관리 가이드, Claude 데이터 거주 문서 (2026-11-12). Bedrock·Google Cloud 경유 시 지역은 각 클라우드 규칙을 따르며 미확인",
               notes="OpenAI: 한국은 지역 저장 가능, 지역 처리 불가. 미국·유럽·아랍에미리트는 처리도 지역 내이며 일부 지역은 특정 모델만 지원하고 제로 데이터 보관이 필요하다. Claude: inference_geo는 us 또는 global, 워크스페이스 저장 지역은 현재 us만 가능. 법률 자문이 아니며 국외 이전 해당 여부는 법무 검토가 필요하다.")
MXL, MXW = CX, 6.3
c1, c2 = MXL + 3.0, MXL + 5.2
label(sl, c1 - 1.0, CT, 2.0, "OPENAI", GPT, align="c")
label(sl, c2 - 1.0, CT, 2.0, "CLAUDE", CLA, align="c")
hair(sl, MXL, CT + 0.3, MXW, INK, 0.014)
cells = [("한국 내 저장", (True, "kr.api.openai.com"), (False, "저장은 미국만")),
         ("한국 내 추론", (False, "처리는 지역 밖"), (False, "us 또는 global"))]
for k, (lab, g, c) in enumerate(cells):
    yc = CT + 1.35 + k * 1.95
    text(sl, MXL, yc - 0.5, 2.3, 1.0, [P(lab, T_H1, F_S, INK)], anchor="m")
    for cx_, (ok, cap) in ((c1, g), (c2, c)):
        oval(sl, cx_ - 0.42, yc - 0.62, 0.84, 0.84, GREEN if ok else "BDB6A8")
        text(sl, cx_ - 0.42, yc - 0.62, 0.84, 0.84, [P("✓" if ok else "✕", T_NUM, F_M, WHITE, align="c")], anchor="m")
        text(sl, cx_ - 1.0, yc + 0.32, 2.0, 0.3, [P(cap, T_LABEL, F_R, SLATE, align="c")], anchor="m")
    if k == 0:
        hair(sl, MXL, yc + 0.95, MXW, HAIR_L)
FX, FW = CX + 7.0, CW - 7.0
label(sl, FX, CT, FW, "그 밖의 규칙", BRASS)
hair(sl, FX, CT + 0.3, FW, BRASS_L, 0.014)
facts = [("지역 내 추론", "미국·유럽 등", "미국(us)"), ("지역 가산", "10%", "1.1배"), ("제로 데이터 보관", "승인 고객만", "적격"), ("기본 보관", "로그 30일", "미확인")]
text(sl, FX + 1.65, CT + 0.4, 1.4, 0.25, [P("OpenAI", T_LABEL, F_M, GPT)], anchor="m")
text(sl, FX + 3.15, CT + 0.4, 1.4, 0.25, [P("Claude", T_LABEL, F_M, CLA)], anchor="m")
rows_y, pitch = ys(4, CT + 0.75, CT + 3.3)
for (lab, g, c), y in zip(facts, rows_y):
    text(sl, FX, y, 1.6, pitch - 0.05, [P(lab, T_BODY, F_M, INK)], anchor="m")
    text(sl, FX + 1.65, y, 1.45, pitch - 0.05, [P(g, T_BODY, F_R, SLATE)], anchor="m")
    text(sl, FX + 3.15, y, 1.45, pitch - 0.05, [P(c, T_BODY, F_R, MUTED if c == "미확인" else SLATE)], anchor="m")
    hair(sl, FX, y + pitch - 0.02, FW, HAIR_L)
rect(sl, FX, 5.8, FW, CB - 5.8, TINT)
text(sl, FX + 0.25, 5.8, FW - 0.5, CB - 5.8, [P("이 자료는 법률 자문이 아닙니다. 개인정보 국외 이전 해당 여부는 법무 검토가 필요합니다.", T_BODY, F_R, SLATE)], anchor="m")

# ================================================================== 11 / 12 pros & cons
def pros_cons(title, lead, pros, cons, source, notes):
    sl = new_slide("pc", title, lead, source=source, notes=notes)
    rows_y, pitch = ys(4, CT + 0.6, CB)
    for x, (head, items, hc) in zip(COL2, (("강점", pros, GREEN), ("유의점", cons, AMBER))):
        text(sl, x, CT, W2, 0.4, [P(head, T_H1, F_S, hc)], anchor="m")
        rect(sl, x, CT + 0.45, W2, 0.02, hc)
        for j, ((h, b), y) in enumerate(zip(items, rows_y)):
            index_row(sl, x, y, pitch - 0.1, W2, "%02d" % (j + 1), h, b)

pros_cons("GPT는 도구 폭이 강점, 장문 할증이 변수입니다",
          "도구 폭과 속도 옵션이 강점이고, 장문 구간 과금과 모델 수명 정보는 확인이 필요합니다.",
          [("도구 10종을 한 API에서", "웹·파일 검색, 컴퓨터 사용, 코드 실행, 이미지 생성 등"),
           ("Fast 2배 · Ultrafast 6배", "응답 속도를 단가로 선택"),
           ("경량 Luna는 $0.1/$0.5", "배치로 쓰면 $0.05/$0.25"),
           ("한국 저장 지역 선택 가능", "kr.api.openai.com, 처리는 지역 밖")],
          [("272K 초과 시 입력 2배·출력 1.5배", "적용 범위는 문서에 불명확"),
           ("플래그십은 Fable 5.2보다 25% 비쌈", "Astra $10/$50 대 $8/$40"),
           ("폐기 일정이 문서에 없음", "계약 시 모델 수명 확인 필요"),
           ("클라우드 경로가 좁음", "Google Cloud는 비공개 프리뷰, Azure는 미확인")],
          "출처: OpenAI 모델 문서, GPT-6 Astra 모델 페이지, OpenAI 가격·데이터 관리 문서 (2026-11-12 조회)",
          "Astra 분당 토큰 한도는 Build 100만, Launch 400만, Grow 4천만이다. 도구 10종: 웹 검색, 파일 검색, 컴퓨터 사용, MCP, 도구 검색, 이미지 생성, 코드 인터프리터, 호스티드 셸, apply patch, skills.")
pros_cons("Claude는 장문·예측성이 강점, 출력 형태가 한계",
          "장문 단가와 운영 예측성이 강점이고, 출력 형태와 한국 저장 지역이 한계입니다.",
          [("1M 토큰까지 같은 단가", "장문도 할증 없음 (Haiku 5.5 제외)"),
           ("effort로 지능·지연·비용 조절", "모델 조합 가이드도 제공"),
           ("4개 경로 + 제공 시한 공개", "Opus 5.5는 2027-09-22 이전 종료 없음"),
           ("캐시 읽기는 입력가의 2.5~10%", "Fable 5.2는 $0.20")],
          [("출력은 텍스트만", "이미지 생성·음성은 라인업 밖"),
           ("Fable 5.2는 $8/$40", "Fast 모드는 $16/$80"),
           ("한국 저장 지역 없음", "저장은 미국만, 추론은 us 또는 global"),
           ("모델 전환 시 변경 사항 점검", "tool_choice 강제·사고 끄기 사용 시")],
          "출처: Claude 모델 개요·모델 선택 가이드·가격·데이터 거주 문서 (2026-11-12 조회)",
          "Claude 최소 제공 시한은 모델별로 다르다. Fable 5.2는 2027-11-09, Opus 5.5는 2027-09-22이다. Sonnet 5.5는 2027-09-28, Haiku 5.5는 2027-10-07이다.")

# ================================================================== 13 selection guide
sl = new_slide("sel", "상황별로 먼저 볼 모델이 달라집니다",
               "공식 사양과 가격에 근거한 판단입니다. 최종 선택은 자체 평가로 합니다.",
               source="출처: 앞 장의 공식 사양에 근거한 작성자 판단. Claude 모델 선택 가이드(선택 매트릭스) 참고",
               notes="판단 근거는 모두 공식 문서의 사양과 가격이다. 성능 우열은 판단하지 않았고 최종 선택은 자사 평가로 한다.")
cols = [("OPENAI 먼저", "GPT-6 Astra · Sol", GPT, [("이미지 생성까지 한 번에 쓰는 서비스", "Responses API에 이미지 생성 포함"),
                                                   ("한국 내 저장이 필요한 데이터", "한국 저장 지역은 OpenAI만 제공")]),
        ("CLAUDE 먼저", "Opus 5.5 → Fable 5.2", CLA, [("수 시간 이어지는 에이전트·대규모 코딩", "공식 선택 매트릭스가 지목"),
                                                    ("수십만 토큰 문서를 반복 처리", "1M까지 동일 단가, GPT는 272K 초과 할증")]),
        ("둘 다 평가", "병행 평가", INK, [("대량 분류·추출·라우팅", "Luna와 Haiku 5.5 단가 동일, 실측 필요"),
                                      ("Amazon Bedrock(AWS) 계약 환경", "양쪽 모두 Bedrock 제공"),
                                      ("어느 쪽도 확신이 서지 않을 때", "자사 업무 샘플로 비교")])]
for i, (head, models, col, items) in enumerate(cols):
    x = CX + i * (W3 + 0.4)
    label(sl, x, CT, W3, head, col)
    text(sl, x, CT + 0.3, W3, 0.5, [P(models, T_H1, F_S, INK)], anchor="m")
    rect(sl, x, CT + 0.95, W3, 0.02, col)
    rows_y, pitch = ys(3, CT + 1.2, CB)
    for (sit, why), y in zip(items, rows_y):
        oval(sl, x, y + 0.08, 0.12, 0.12, col)
        text(sl, x + 0.3, y, W3 - 0.3, pitch - 0.1, [P(sit, T_H2, F_M, INK, after=3), P(why, T_BODY, F_R, SLATE)])

# ================================================================== 14 evaluation
sl = new_slide("sel", "벤더 설명 대신 자사 업무로 평가합니다",
               "벤치마크 순위 대신, 같은 조건의 자체 평가로 품질·지연·비용을 비교합니다.",
               source="출처: Claude 모델 선택 가이드(자체 평가셋 권고) 및 작성자 제안. 가중치는 예시이며 조직 기준에 맞게 조정",
               notes="가중치 50/20/30은 예시값이다. 업무 특성에 따라 바꾼다.")
steps = [("01", "평가셋 구성", "실제 업무 입력 모음\n정답 기준 사전 합의"), ("02", "조건 통일", "같은 프롬프트·도구\n추론 강도(effort) 맞춤"),
         ("03", "병행 실행", "두 후보를 같은 날 실행\n실패 사례 별도 기록"), ("04", "채점·결정", "품질·지연·비용 점수화\n모델 교체 시 재평가")]
hair(sl, CX, CT + 0.95, CW, BRASS_L, 0.014)
for i, (no, h_, b) in enumerate(steps):
    x = CX + i * (CW / 4)
    text(sl, x, CT, 2.6, 0.7, [P(no, T_NUM, F_N, BRASS)], anchor="m")
    oval(sl, x, CT + 0.87, 0.16, 0.16, NAVY)
    text(sl, x, CT + 1.2, 2.6, 1.0, [P(h_, T_H2, F_M, INK, after=4)] + [P(t, T_BODY, F_R, SLATE) for t in b.split("\n")])
label(sl, CX, 4.6, 6, "채점 가중치 예시", BRASS)
segs = [("품질", 50, NAVY, "정답 기준 대비 채점, 실패 사례 분류"), ("응답 시간", 20, BRASS, "첫 토큰·완료 시간의 중앙값"),
        ("비용", 30, "7C8798", "작업당 토큰 x 단가 (캐시·배치 반영)")]
bx = CX
for nm, pct, col, desc in segs:
    w = CW * pct / 100
    rect(sl, bx, 4.95, w - 0.04, 0.7, col)
    text(sl, bx, 4.95, w - 0.04, 0.7, [P("%s  %d%%" % (nm, pct), T_H2, F_M, WHITE, align="c")], anchor="m")
    text(sl, bx, 5.8, w - 0.15, 0.7, [P(desc, T_BODY, F_R, SLATE)])
    bx += w

# ================================================================== 15 risks
sl = new_slide("sel", "도입 전에 확인할 위험 다섯 가지",
               "모델 교체와 가격 변동은 상수입니다. 위험마다 미리 정해 둘 대응이 있습니다.",
               source="출처: Claude 모델 개요·가격·데이터 거주 문서, OpenAI 모델·가격·데이터 관리 문서 (2026-11-12 조회)",
               notes="Claude 최소 제공 시한은 Anthropic이 운영하는 플랫폼 기준이다. 파트너 플랫폼은 자체 일정을 정한다.")
label(sl, CX + IDX, CT, 3, "위험", MUTED)
label(sl, CX + 4.4, CT, 3, "대응", BRASS)
hair(sl, CX, CT + 0.3, CW, INK, 0.014)
risks = [("모델 수명", "계약 전에 폐기 일정을 확인"), ("가격 변동", "견적서에 기준일을 명시"),
         ("전환 호환성", "Opus 5.5·Fable 5.2 전환 전 변경 사항 점검"), ("벤더 종속", "프롬프트·도구 정의를 중립 계층으로 분리, 평가셋 공용"),
         ("데이터 지역", "저장·처리 지역은 법무 검토 후 결정")]
rows_y, pitch = ys(5, CT + 0.4, CB)
for (i, (h_, b)), y in zip(enumerate(risks), rows_y):
    text(sl, CX, y, IDX, pitch - 0.05, [P("%02d" % (i + 1), T_H1, F_N, BRASS_M)], anchor="m")
    text(sl, CX + IDX, y, 3.2, pitch - 0.05, [P(h_, T_H2, F_M, INK)], anchor="m")
    text(sl, CX + 3.95, y, 0.4, pitch - 0.05, [P("→", T_H1, F_N, BRASS_L)], anchor="m")
    text(sl, CX + 4.4, y, CW - 4.4, pitch - 0.05, [P(b, T_BODY, F_R, SLATE)], anchor="m")
    if i < 4:
        hair(sl, CX, y + pitch - 0.025, CW, HAIR_L)

# ================================================================== 16 sources & limits
sl = new_slide("app", "수치는 공식 문서만 썼고 한계가 있습니다",
               "모든 수치는 2026-11-12에 확인한 공식 문서 기준이며 정가입니다.",
               source="모든 조회일 2026-11-12. 가격은 정가이며 협상가·약정 할인은 반영하지 않음",
               notes="2차 블로그는 버전과 가격이 서로 달라 사용하지 않았다.")
srcs = [("Claude 문서", "모델 개요·가격·선택 가이드·데이터 거주", "platform.claude.com/docs"),
        ("OpenAI 문서", "모델·Astra 페이지·가격·데이터 관리", "developers.openai.com"),
        ("Anthropic 소개", "미션과 법인 구조", "anthropic.com/company"),
        ("OpenAI 소개", "미션과 구조 (검색 요약 기반)", "openai.com/our-structure")]
lims = [("작성 주체", "Claude가 작성해 이해관계 가능성이 있어, 수치는 공식 문서로 제한했습니다."),
        ("제외", "벤치마크 점수, 소비자 앱 요금제, 2차 블로그 가격은 뺐습니다."),
        ("미확인", "Azure의 OpenAI 제공, 장문 할증 적용 범위, Claude의 MCP(Model Context Protocol) 지원, ChatGPT 구독 요금제"),
        ("읽기 경로", "OpenAI 문서는 요약 도구를 거쳐 읽었습니다. 발표 전 원문 대조를 권합니다.")]
rows_y, pitch = ys(4, CT + 0.6, CB)
for x, (head, col) in zip(COL2, (("사용한 출처", INK), ("한계와 처리", AMBER))):
    text(sl, x, CT, W2, 0.4, [P(head, T_H1, F_S, col)], anchor="m"); rect(sl, x, CT + 0.45, W2, 0.02, col)
for j, y in enumerate(rows_y):
    h_, b, u = srcs[j]
    text(sl, COL2[0], y, W2, pitch - 0.1, [P(h_, T_LABEL, F_M, BRASS, spc=100, after=3), P(b, T_H2, F_M, INK, after=2), P(u, T_LABEL, F_N, MUTED)])
    h2, b2 = lims[j]
    text(sl, COL2[1], y, W2, pitch - 0.1, [P(h2, T_LABEL, F_M, BRASS, spc=100, after=3), P(b2, T_BODY, F_R, SLATE)])

# ================================================================== 17 closing
sl = prs.slides.add_slide(BLANK); PAGE[0] += 1
sl.shapes.add_picture(ribbon(9), 0, 0, I(13.333), I(7.5))
text(sl, CX, 0.95, 5, 0.3, [P("Summary", T_H1, F_N, BRASS_L, spc=100)], anchor="m")
rect(sl, CX, 1.42, 0.7, 0.03, BRASS_L)
text(sl, CX, 1.7, 11, 1.9, [P(t, T_DISPLAY, F_S, WHITE, spc=-40) for t in ("하나를 고르기보다", "용도별 포트폴리오로 운영합니다")], spacing=1.25)
nxt = [("01", "후보 좁히기", "용도와 과금 구조로 2~3개 모델을 추립니다."),
       ("02", "자체 평가", "실제 업무 샘플로 품질·지연·비용을 같은 조건에서 비교합니다."),
       ("03", "분기 점검", "모델 교체와 가격 변동에 맞춰 재평가합니다.")]
for i, (n, h_, b) in enumerate(nxt):
    x = CX + i * (W3 + 0.4)
    rect(sl, x, 4.15, W3, 0.015, BRASS_L)
    text(sl, x, 4.3, W3, 2.2, [P(n, T_NUM, F_N, BRASS_L, after=10), P(h_, T_H1, F_S, WHITE, after=8), P(b, T_BODY, F_R, "C5CEDD")])
text(sl, CX, 6.75, 11, 0.3, [P("모델명과 가격은 2026-11-12 기준이며 수시로 바뀝니다.", T_BODY, F_R, "8FA0BA")], anchor="m")
g = rect(sl, 0, 7.4, 13.333, 0.1, GPT); gradient(g, GPT, CLA, 0)

cp = prs.core_properties
cp.title = "GPT와 Claude 비교 리포트"; cp.author = "Claude (Anthropic 모델)"; cp.last_modified_by = "Claude (Anthropic 모델)"
cp.comments = ""; cp.subject = "OpenAI GPT vs Anthropic Claude"; cp.keywords = ""
assert PAGE[0] == TOTAL, PAGE[0]
prs.save(OUT)
print("saved", OUT, "slides:", len(prs.slides))

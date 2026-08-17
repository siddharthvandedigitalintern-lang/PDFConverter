# -*- coding: utf-8 -*-
import html
from data import UNITS
from config import CONFIG

DARK = "#00875F"    # dark teal (from logo)
MINT = "#00D9A0"    # bright mint (from logo)
INK  = "#161616"    # near-black (from logo text)
PAPER = "#FFFFFF"
MUTED = "#5B6260"

def esc(s):
    return html.escape(s, quote=False)

def render_paras(paras):
    return "".join(f'<p class="para">{p}</p>' for p in paras)

def render_bullets(items):
    lis = "".join(f'<li>{it}</li>' for it in items)
    return f'<ul class="bullets">{lis}</ul>'

def render_numbered(items):
    lis = "".join(f'<li>{it}</li>' for it in items)
    return f'<ol class="numbered">{lis}</ol>'

def render_section(sec):
    out = [f'<h3 class="sec-heading">{esc(sec["heading"])}</h3>']
    if "paras" in sec:
        out.append(render_paras(sec["paras"]))
    if "bullets" in sec:
        out.append(render_bullets(sec["bullets"]))
    if "numbered" in sec:
        out.append(render_numbered(sec["numbered"]))
    if "subsections" in sec:
        for sub in sec["subsections"]:
            out.append(f'<h4 class="sub-heading">{esc(sub["sub"])}</h4>')
            if "paras" in sub:
                out.append(render_paras(sub["paras"]))
            if "bullets" in sub:
                out.append(render_bullets(sub["bullets"]))
            if "numbered" in sub:
                out.append(render_numbered(sub["numbered"]))
    return "".join(out)

def render_summary_box(points, title):
    lis = "".join(f'<li>{p}</li>' for p in points)
    return f'''
    <div class="summary-box">
      <div class="summary-title">{esc(title)}</div>
      <ul class="summary-list">{lis}</ul>
    </div>'''

def render_glossary(terms, layout="list"):
    if layout == "table":
        rows = [[f'<b>{esc(term)}</b>', defn] for term, defn in terms]
        return render_table(["Term", "Definition"], rows)
    items = "".join(
        f'<div class="glossary-item"><span class="glossary-term">{esc(term)}:</span> {defn}</div>'
        for term, defn in terms
    )
    return f'<div class="glossary-list">{items}</div>'

def render_table(headers, rows):
    thead = "".join(f'<th>{esc(h)}</th>' for h in headers)
    trs = "".join(
        '<tr>' + "".join(f'<td>{cell}</td>' for cell in row) + '</tr>'
        for row in rows
    )
    return f'''
    <div class="table-wrap">
      <table class="brand-table">
        <thead><tr>{thead}</tr></thead>
        <tbody>{trs}</tbody>
      </table>
    </div>'''

def render_images(items):
    figs = []
    for it in items:
        src = it["src"]
        caption = it.get("caption", "")
        width = it.get("width", "150mm")
        cap_html = f'<div class="figure-caption">{esc(caption)}</div>' if caption else ""
        figs.append(f'<div class="figure" style="width:{width};"><img src="{src}">{cap_html}</div>')
    return f'<div class="figure-row">{"".join(figs)}</div>'

LETTERS = ["A","B","C","D","E","F"]

def render_mcqs(mcqs):
    cards = []
    for i, (q, opts, ans) in enumerate(mcqs, start=1):
        opt_html = "".join(
            f'<span class="opt{" opt-correct" if LETTERS[j]==ans else ""}">'
            f'<span class="opt-letter">{LETTERS[j]}</span>{esc(o)}</span>'
            for j, o in enumerate(opts)
        )
        cards.append(f'''
        <div class="mcq-card">
          <div class="mcq-q"><span class="mcq-num">{i}.</span>{esc(q)}</div>
          <div class="mcq-opts">{opt_html}</div>
          <div class="mcq-ans">Answer: <b>{ans}</b></div>
        </div>''')
    return f'<div class="mcq-grid">{"".join(cards)}</div>'

def render_short_qs(items):
    blocks = []
    for i, (q, a) in enumerate(items, start=1):
        blocks.append(f'''
        <div class="qa-block">
          <div class="qa-q"><span class="qa-tag">Q{i}</span>{esc(q)}</div>
          <div class="qa-a"><span class="qa-tag qa-tag-a">Ans</span>{a}</div>
        </div>''')
    return "".join(blocks)

def render_long_q(lq):
    parts = [f'<div class="long-q-title">{esc(lq["q"])}</div>']
    parts.append(f'<p class="para">{lq["intro"]}</p>')
    if "extra_para_heading" in lq:
        parts.append(f'<h5 class="mini-heading">{esc(lq["extra_para_heading"])}</h5>')
        parts.append(f'<p class="para">{lq["extra_para"]}</p>')
    if "extra_para_heading2" in lq:
        parts.append(f'<h5 class="mini-heading">{esc(lq["extra_para_heading2"])}</h5>')
        parts.append(f'<p class="para">{lq["extra_para2"]}</p>')
    if "numbered_heading" in lq:
        parts.append(f'<h5 class="mini-heading">{esc(lq["numbered_heading"])}</h5>')
    if "numbered" in lq:
        parts.append(render_numbered(lq["numbered"]))
    parts.append(f'<p class="para outro">{lq["outro"]}</p>')
    return f'<div class="long-q-box">{"".join(parts)}</div>'

# ------------------------------------------------------------------
# BLOCK DISPATCH — this is what makes the kit "structure-agnostic".
# Every unit is just an ordered list of blocks; each block has a
# "type" that decides how it renders. Add/remove/reorder blocks
# freely per unit/subject — nothing else needs to change.
# ------------------------------------------------------------------

DEFAULT_LABELS = {
    "notes":    "Deep-Dive Notes",
    "summary":  "Quick-Hit Revision \u2014 Key Points",
    "glossary": "Key Glossary Terms",
    "mcq":      "Multiple Choice Questions",
    "short_qa": "Short Answer Questions",
    "long_qa":  "Long Answer Question",
    "table":    "",
    "image":    "",
    "custom":   "",
}

def content_block(label, body_html):
    parts = ['<div class="content-block">']
    if label:
        parts.append(f'<div class="block-label">{label}</div>')
    parts.append(body_html)
    parts.append('</div>')
    return "".join(parts)

def render_block(block):
    t = block["type"]
    label = block.get("label", DEFAULT_LABELS.get(t, ""))

    if t in ("notes", "custom"):
        body = "".join(render_section(s) for s in block["sections"])
        return content_block(esc(label) if label else "", body)

    if t == "summary":
        # Summary box carries its own internal title; no extra outer label needed.
        return content_block("", render_summary_box(block["points"], label))

    if t == "glossary":
        layout = block.get("layout", "list")   # "list" or "table"
        return content_block(esc(label), render_glossary(block["terms"], layout))

    if t == "mcq":
        count = len(block["items"])
        full_label = f'{esc(label)} <span class="block-count">({count} MCQs)</span>'
        return content_block(full_label, render_mcqs(block["items"]))

    if t == "short_qa":
        return content_block(esc(label), render_short_qs(block["items"]))

    if t == "long_qa":
        body = "".join(render_long_q(item) for item in block["items"])
        return content_block(esc(label), body)

    if t == "table":
        return content_block(esc(label) if label else "", render_table(block["headers"], block["rows"]))

    if t == "image":
        return content_block(esc(label) if label else "", render_images(block["items"]))

    # Unknown type -> skip safely rather than crash a whole build
    return ""

def render_unit(u):
    out = []
    out.append(f'''
    <section class="unit-cover">
      <div class="unit-tag">UNIT {u["num"]}</div>
      <div class="unit-title">{esc(u["title"])}</div>
      <div class="unit-rule"></div>
    </section>''')

    for block in u["blocks"]:
        out.append(render_block(block))

    return "".join(out)


# CSS for the cover page (standalone, no margins, no footer)
CSS_COVER = f'''
@page {{
  size: A4;
  margin: 0;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: 'Liberation Sans', 'DejaVu Sans', sans-serif;
  color: {INK};
  font-size: 10.6pt;
  line-height: 1.55;
}}
h1, h2, h3, h4, h5, .unit-tag, .unit-title, .cover-title, .cover-kicker, .cover-sub,
.block-label, .mcq-ans, .qa-tag, .cover-footer {{
  font-family: 'Poppins', 'Liberation Sans', sans-serif;
}}
.cover-page {{
  width: 210mm;
  height: 297mm;
  position: relative;
  background: {PAPER};
  overflow: hidden;
}}
.cover-top-bar {{
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 8mm;
  background: linear-gradient(90deg, {DARK}, {MINT});
}}
.cover-bottom-bar {{
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 8mm;
  background: linear-gradient(90deg, {MINT}, {DARK});
}}'''

# CSS for content pages (with margins; footer is stamped via post-processing in build.py)
CSS = f'''
@page {{
  size: A4;
  margin: 16mm 18mm 18mm 18mm;
}}
* {{ box-sizing: border-box; }}
body {{
  font-family: 'Liberation Sans', 'DejaVu Sans', sans-serif;
  color: {INK};
  font-size: 10.6pt;
  line-height: 1.55;
}}
h1, h2, h3, h4, h5, .unit-tag, .unit-title, .cover-title, .cover-kicker, .cover-sub,
.block-label, .mcq-ans, .qa-tag, .cover-footer {{
  font-family: 'Poppins', 'Liberation Sans', sans-serif;
}}
/* cover-page styles kept for compat but cover is now a separate HTML */
.cover-page {{
  width: 210mm;
  height: 297mm;
  position: relative;
  background: {PAPER};
  overflow: hidden;
}}
.cover-top-bar {{
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 8mm;
  background: linear-gradient(90deg, {DARK}, {MINT});
}}
.cover-bottom-bar {{
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 8mm;
  background: linear-gradient(90deg, {MINT}, {DARK});
}}
.cover-blob-1 {{
  position: absolute;
  top: -60mm; right: -55mm;
  width: 140mm; height: 140mm;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, {MINT} 0%, {DARK} 75%);
  opacity: 0.12;
}}
.cover-blob-2 {{
  position: absolute;
  bottom: -50mm; left: -50mm;
  width: 110mm; height: 110mm;
  border-radius: 50%;
  background: radial-gradient(circle at 65% 65%, {DARK} 0%, {MINT} 75%);
  opacity: 0.10;
}}
.cover-inner {{
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  padding: 20mm;
}}
.cover-card {{
  background: {PAPER};
  border: 1px solid #e7ece9;
  border-radius: 10px;
  padding: 22mm 16mm;
  width: 150mm;
  box-shadow: 0 10px 34px rgba(0,60,40,0.10);
}}
.cover-logo {{
  width: 78mm;
  margin-bottom: 10mm;
}}
.cover-kicker {{
  font-size: 10.5pt;
  letter-spacing: 3px;
  color: {DARK};
  font-weight: 700;
  text-transform: uppercase;
  margin-bottom: 4mm;
}}
.cover-title {{
  font-size: 21pt;
  font-weight: 800;
  color: {INK};
  line-height: 1.25;
  margin-bottom: 6mm;
}}
.cover-sub {{
  font-size: 12pt;
  color: {DARK};
  font-weight: 700;
  margin-bottom: 10mm;
}}
.cover-pill-row {{
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 6px;
  margin-bottom: 10mm;
}}
.cover-pill {{
  background: rgba(0,135,95,0.08);
  border: 1px solid rgba(0,135,95,0.35);
  color: {DARK};
  font-size: 8.3pt;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: 20px;
}}
.cover-meta {{
  font-size: 9.3pt;
  color: {MUTED};
  border-top: 1px solid #e2e2e2;
  padding-top: 6mm;
  margin-top: 2mm;
}}
.cover-meta b {{ color: {INK}; }}

/* Unit cover strip */
.unit-cover {{
  page-break-before: always;
  padding: 2mm 0 3mm 0;
  margin-bottom: 3mm;
}}
.unit-tag {{
  display: inline-block;
  background: {DARK};
  color: white;
  font-size: 9pt;
  font-weight: 700;
  letter-spacing: 2px;
  padding: 3px 10px;
  border-radius: 3px;
  margin-bottom: 2.5mm;
}}
.unit-title {{
  font-size: 17pt;
  font-weight: 800;
  color: {INK};
}}
.unit-rule {{
  height: 4px;
  background: linear-gradient(90deg, {DARK}, {MINT});
  width: 100%;
  margin-top: 3mm;
  border-radius: 2px;
}}

.content-block {{ margin-bottom: 3mm; }}
.block-label {{
  font-size: 12.5pt;
  font-weight: 800;
  color: {DARK};
  border-bottom: 2px solid {MINT};
  padding-bottom: 1.5mm;
  margin-bottom: 3mm;
  letter-spacing: 0.3px;
}}
.block-count {{
  font-weight: 500;
  font-size: 9.5pt;
  color: {MUTED};
}}

.sec-heading {{
  font-size: 12pt;
  font-weight: 700;
  color: {INK};
  margin: 3.5mm 0 1.8mm 0;
  padding-left: 2.5mm;
  border-left: 3px solid {DARK};
}}
.sub-heading {{
  font-size: 10.8pt;
  font-weight: 700;
  color: {DARK};
  margin: 2.5mm 0 1.3mm 0;
}}
.mini-heading {{
  font-size: 10.5pt;
  font-weight: 700;
  color: {DARK};
  margin: 2.5mm 0 1mm 0;
}}
.para {{
  margin: 0 0 1.8mm 0;
  text-align: justify;
  orphans: 3;
  widows: 3;
}}
.outro {{
  font-style: italic;
  color: #333;
}}
ul.bullets, ol.numbered {{
  margin: 0.5mm 0 2mm 0;
  padding-left: 5mm;
}}
ul.bullets li, ol.numbered li {{
  margin-bottom: 1.2mm;
  text-align: justify;
}}
ul.bullets li::marker {{ color: {DARK}; }}
ol.numbered li::marker {{ color: {DARK}; font-weight: 700; }}
b {{ color: {INK}; }}

/* Summary box */
.summary-box {{
  background: #F2FBF8;
  border: 1px solid rgba(0,135,95,0.25);
  border-left: 4px solid {DARK};
  border-radius: 6px;
  padding: 4mm 5.5mm;
}}
.summary-title {{
  font-size: 11.5pt;
  font-weight: 800;
  color: {DARK};
  margin-bottom: 2mm;
}}
.summary-list {{
  margin: 0;
  padding-left: 5mm;
}}
.summary-list li {{
  margin-bottom: 1.3mm;
}}
.summary-list li::marker {{ color: {MINT}; font-size: 1.1em; }}

/* MCQ grid */
.mcq-grid {{
  display: block;
  column-count: 1;
}}
.mcq-card {{
  break-inside: avoid;
  page-break-inside: avoid;
  border: 1px solid #e3e3e3;
  border-radius: 5px;
  padding: 2.6mm 4mm;
  margin-bottom: 2mm;
  background: #FCFDFD;
}}
.mcq-q {{
  font-weight: 700;
  font-size: 10.2pt;
  margin-bottom: 1.3mm;
  color: {INK};
}}
.mcq-num {{
  color: {DARK};
  margin-right: 1.2mm;
}}
.mcq-opts {{
  display: flex;
  flex-wrap: wrap;
  gap: 1.3mm 4mm;
  margin-bottom: 1.3mm;
}}
.opt {{
  font-size: 9.4pt;
  color: #3a3a3a;
}}
.opt-letter {{
  display: inline-block;
  font-weight: 700;
  color: {DARK};
  margin-right: 1mm;
}}
.opt-correct {{
  color: {DARK};
  font-weight: 700;
}}
.mcq-ans {{
  font-size: 9pt;
  color: white;
  background: {DARK};
  display: inline-block;
  padding: 1px 8px;
  border-radius: 10px;
  font-weight: 600;
}}

/* Short Q&A */
.qa-block {{
  break-inside: avoid;
  page-break-inside: avoid;
  margin-bottom: 2.8mm;
  padding-bottom: 2.5mm;
  border-bottom: 1px dashed #dcdcdc;
}}
.qa-q {{
  font-weight: 700;
  font-size: 10.5pt;
  margin-bottom: 1.3mm;
  color: {INK};
}}
.qa-a {{
  font-size: 10pt;
  text-align: justify;
  color: #2c2c2c;
}}
.qa-tag {{
  display: inline-block;
  background: {DARK};
  color: white;
  font-size: 8pt;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 3px;
  margin-right: 2.2mm;
  vertical-align: middle;
}}
.qa-tag-a {{
  background: {MINT};
  color: {INK};
}}

/* Glossary */
.glossary-list {{
  margin: 0;
}}
.glossary-item {{
  margin-bottom: 1.6mm;
  padding-bottom: 1.6mm;
  border-bottom: 1px dotted #e2e2e2;
  text-align: justify;
}}
.glossary-term {{
  color: {DARK};
  font-weight: 700;
  margin-right: 1mm;
}}

/* Long answer */
.long-q-box {{
  background: #FAFFFD;
  border: 1px solid rgba(0,135,95,0.2);
  border-radius: 6px;
  padding: 4mm 5.5mm;
  margin-bottom: 3mm;
}}
.long-q-box:last-child {{ margin-bottom: 0; }}
.long-q-title {{
  font-size: 11.5pt;
  font-weight: 800;
  color: {DARK};
  margin-bottom: 2.5mm;
  padding-bottom: 1.5mm;
  border-bottom: 1px solid rgba(0,135,95,0.2);
}}

/* Tables (glossary-as-table, comparison tables, any tabular data) */
.table-wrap {{
  margin-bottom: 2mm;
  overflow-x: auto;
}}
table.brand-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 9.6pt;
}}
table.brand-table thead {{
  display: table-header-group;   /* repeat header if table spans pages */
}}
table.brand-table thead th {{
  background: {DARK};
  color: white;
  text-align: left;
  padding: 2.2mm 3mm;
  font-weight: 700;
  font-family: 'Poppins', 'Liberation Sans', sans-serif;
}}
table.brand-table tbody td {{
  padding: 2mm 3mm;
  border-bottom: 1px solid #e6e6e6;
  vertical-align: top;
  text-align: justify;
}}
table.brand-table tbody tr {{
  break-inside: avoid;
  page-break-inside: avoid;
}}
table.brand-table tbody tr:nth-child(even) {{
  background: #F5FBF9;
}}

/* Images / Diagrams */
.figure-row {{
  display: flex;
  flex-wrap: wrap;
  gap: 5mm;
  justify-content: flex-start;
}}
.figure {{
  break-inside: avoid;
  page-break-inside: avoid;
  text-align: center;
}}
.figure img {{
  width: 100%;
  height: auto;
  display: block;
  border: 1px solid #e3e3e3;
  border-radius: 5px;
  padding: 2mm;
  background: white;
  box-sizing: border-box;
}}
.figure-caption {{
  font-size: 8.5pt;
  color: {MUTED};
  margin-top: 1.3mm;
  font-style: italic;
}}

.page-break {{ page-break-before: always; }}

/* Footer brand strip on cover */
.cover-footer {{
  position: absolute;
  bottom: 14mm;
  left: 0; right: 0;
  text-align: center;
  color: {DARK};
  font-size: 9pt;
  letter-spacing: 1.5px;
  font-weight: 700;
}}
'''

def build_cover_html(pills_html):
    """Return the cover page HTML (standalone, zero-margin, no footer)."""
    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{CSS_COVER}
.cover-blob-1 {{
  position: absolute;
  top: -60mm; right: -55mm;
  width: 140mm; height: 140mm;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, {MINT} 0%, {DARK} 75%);
  opacity: 0.12;
}}
.cover-blob-2 {{
  position: absolute;
  bottom: -50mm; left: -50mm;
  width: 110mm; height: 110mm;
  border-radius: 50%;
  background: radial-gradient(circle at 65% 65%, {DARK} 0%, {MINT} 75%);
  opacity: 0.10;
}}
.cover-inner {{
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  padding: 20mm;
}}
.cover-card {{
  background: {PAPER};
  border: 1px solid #e7ece9;
  border-radius: 10px;
  padding: 22mm 16mm;
  width: 150mm;
  box-shadow: 0 10px 34px rgba(0,60,40,0.10);
}}
.cover-logo {{
  width: 78mm;
  margin-bottom: 10mm;
}}
.cover-kicker {{
  font-size: 10.5pt;
  letter-spacing: 3px;
  color: {DARK};
  font-weight: 700;
  text-transform: uppercase;
  margin-bottom: 4mm;
  font-family: 'Poppins', 'Liberation Sans', sans-serif;
}}
.cover-title {{
  font-size: 21pt;
  font-weight: 800;
  color: {INK};
  line-height: 1.25;
  margin-bottom: 6mm;
  font-family: 'Poppins', 'Liberation Sans', sans-serif;
}}
.cover-sub {{
  font-size: 12pt;
  color: {DARK};
  font-weight: 700;
  margin-bottom: 10mm;
  font-family: 'Poppins', 'Liberation Sans', sans-serif;
}}
.cover-pill-row {{
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 6px;
  margin-bottom: 10mm;
}}
.cover-pill {{
  background: rgba(0,135,95,0.08);
  border: 1px solid rgba(0,135,95,0.35);
  color: {DARK};
  font-size: 8.3pt;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: 20px;
  font-family: 'Poppins', 'Liberation Sans', sans-serif;
}}
.cover-meta {{
  font-size: 9.3pt;
  color: {MUTED};
  border-top: 1px solid #e2e2e2;
  padding-top: 6mm;
  margin-top: 2mm;
  font-family: 'Liberation Sans', 'DejaVu Sans', sans-serif;
}}
.cover-meta b {{ color: {INK}; }}
.cover-footer {{
  position: absolute;
  bottom: 14mm;
  left: 0; right: 0;
  text-align: center;
  color: {DARK};
  font-size: 9pt;
  letter-spacing: 1.5px;
  font-weight: 700;
  font-family: 'Poppins', 'Liberation Sans', sans-serif;
}}
</style>
</head>
<body>
<div class="cover-page">
  <div class="cover-top-bar"></div>
  <div class="cover-bottom-bar"></div>
  <div class="cover-blob-1"></div>
  <div class="cover-blob-2"></div>
  <div class="cover-inner">
    <div class="cover-card">
      <img class="cover-logo" src="{CONFIG['logo_path']}">
      <div class="cover-kicker">{CONFIG['kicker']}</div>
      <div class="cover-title">{CONFIG['title']}</div>
      <div class="cover-sub">{CONFIG['subtitle']}</div>
      <div class="cover-pill-row">
        {pills_html}
      </div>
      <div class="cover-meta">
        Institution: <b>{CONFIG['institution']}</b><br>
        Prepared by: <b>{CONFIG['prepared_by']}</b>
      </div>
    </div>
  </div>
  <div class="cover-footer">NOTESNINJA.IN</div>
</div>
</body>
</html>'''


def build_html():
    """Generate cover.html and content.html for two-pass PDF build."""
    units_html = "".join(render_unit(u) for u in UNITS)
    pills_html = "".join(f'<span class="cover-pill">{p}</span>' for p in CONFIG["pills"])

    # --- cover.html (zero-margin, no footer) ---
    cover_doc = build_cover_html(pills_html)
    with open("cover.html", "w", encoding="utf-8") as f:
        f.write(cover_doc)

    # --- content.html (normal margins; footer stamped by build.py post-process) ---
    content_doc = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{CSS}</style>
</head>
<body>
{units_html}
</body>
</html>'''
    with open("content.html", "w", encoding="utf-8") as f:
        f.write(content_doc)

    # Legacy single-file output for compatibility
    combined_doc = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{CSS}</style>
</head>
<body>
{units_html}
</body>
</html>'''
    with open("notes.html", "w", encoding="utf-8") as f:
        f.write(combined_doc)


if __name__ == "__main__":
    build_html()
    print("HTML built -> cover.html + content.html + notes.html")

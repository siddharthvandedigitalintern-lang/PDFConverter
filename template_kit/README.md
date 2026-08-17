# Notes Ninja — PDF Template Kit (Reusable)

Ye kit use karo jab bhi tumhe **same design/layout** mein naya notes PDF banana ho —
is baar guaranteed identical output milega, kyunki design ka code (HTML/CSS) bilkul
same rehta hai, sirf content change hota hai.

## Files
```
template_kit/
├── config.py     ← Cover page / footer / output filename settings (chhota, easy)
├── data.py       ← YAHAN NOTES CONTENT DAALTE HO (units, MCQs, Q&A, etc.)
├── generate.py   ← Design engine (HTML+CSS). ISKO MAT CHHEDO.
├── build.py      ← Isko run karo — ye PDF bana dega
└── assets/
    └── logo_trans.png   ← Notes Ninja logo (transparent bg)
```

## Har naye subject/notes ke liye kya karna hai

### Step 1 — `data.py` edit karo
- Ab ye **fully flexible / structure-agnostic** hai — har unit sirf ek ordered
  list hai "blocks" ki, aur tum jitne aur jaise blocks chaho utne use kar sakte ho,
  **jis order mein chaho**. Har unit ka structure alag ho sakta hai.
- Supported block types: `notes` (deep-dive), `summary` (quick revision),
  `glossary` (key terms — list OR table layout), `mcq`, `short_qa`,
  `long_qa` (ek ya multiple), `table` (koi bhi tabular data/comparison),
  `image` (diagrams/figures, ek ya multiple side-by-side), aur `custom`
  (kuch bhi extra jo upar wale types mein fit nahi hota).
- Poora schema aur ek **fully working example (4 real units)** upar comment
  aur code mein diya hai — bas copy-paste karke apna content daalo.
- Agar kisi PDF mein glossary nahi hai, bas wo block mat daalo. Agar kisi PDF
  mein 2 long-answer questions hain, `long_qa` ke `items` list mein dono daal do.
  Agar structure hi kuch alag hai (jaise "Case Study" ya "Formulas"), `custom`
  type use karo apne label ke saath.
- **Tables**: koi bhi comparison table ya tabular data ho to `table` block use
  karo (headers + rows). Glossary bhi table jaisa dikhana ho to glossary block
  mein `"layout": "table"` add kar do.
- **Diagrams/Images**: agar source PDF mein diagrams hain, unhe pehle image
  files ke roop mein `assets/` folder mein daal do (PDF se crop/export karke),
  phir `image` block use karo (`src`, `caption`, optional `width`). Ek block
  mein multiple images bhi daal sakte ho (side-by-side dikhte hain).

### Step 2 — `config.py` edit karo
Sirf ye cheezein badlo:
- `title`, `subtitle` (course/semester/units)
- `pills` (cover ke badge tags)
- `institution`, `prepared_by`
- `footer_subject` (footer mein subject ka naam)
- `output_filename` (final PDF ka naam)

### Step 3 — Build karo
```bash
pip install pypdf reportlab --break-system-packages   # (ek baar hi install karna hai)
# wkhtmltopdf bhi chahiye — Linux: sudo apt install wkhtmltopdf
python3 build.py
```
Output: same folder mein `<output_filename>.pdf` ban jayega — bilkul same design,
sirf naya content ke saath.

**Build process (v2 — bugfixed):**
- `build.py` pehle `cover.html` aur `content.html` alag-alag generate karta hai
- `cover.pdf` zero-margin ke saath build hota hai (full-bleed bars, koi footer nahi)
- `content.pdf` standard margins ke saath build hota hai
- reportlab se footer (page number) har content page par stamp hota hai (page 2 se)
- pypdf se dono merge hokar final PDF ban jaati hai

## Important
- **`generate.py` mat badalna** — yahi file hai jo guarantee karti hai ki design/colors/
  spacing/layout har baar EXACT same rahe.
- Agar kabhi design hi change karwana ho (colors, spacing, cover style, etc.), tabhi
  `generate.py` ke CSS section mein jaake edit karna — warna touch mat karo.
- Logo change karna ho to `assets/logo_trans.png` replace kar dena aur `config.py` mein
  `logo_path` update kar dena (agar naam alag rakha ho).

## Design Specs (reference)
- Colors: Dark teal `#00875F`, Mint `#00D9A0`, Ink `#161616`, Muted `#5B6260`
- Fonts: Poppins (headings), Liberation Sans (body)
- Page: A4, margins 16mm/18mm/16mm/18mm
- Layout: **Cover page → straight into Unit 1 content** (no Table of Contents page)
- **Structure-agnostic**: every unit is an ordered list of "blocks" (notes,
  summary, glossary, table, image, mcq, short_qa, long_qa, custom) — mix/match/
  reorder freely per unit, no fixed template of sections required.
- Rule: sirf naya UNIT shuru hone par hi naya page — baaki sab blocks
  continuously flow karte hain same unit ke andar.

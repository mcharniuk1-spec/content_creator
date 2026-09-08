#!/usr/bin/env python3
"""
type-metrics.py -- IBM Plex type-scale measurement for M2 Lab Instagram canvases.

All numbers below come from real font metrics read with fontTools (hmtx advance
widths, glyf/OS2 vertical metrics, cmap coverage) plus the fixed canvas/frame
numbers given in the brief. No widths or heights are guessed -- everything is
computed and printed, then dumped to type-metrics.json.

Run: python3 type-metrics.py
"""
import json
import math
from pathlib import Path
from fontTools.ttLib import TTFont

FONT_DIR = Path("/Users/mihailampleev/Desktop/m2lab-brand/assets/fonts/ttf")
OUT_JSON = Path("/Users/mihailampleev/Desktop/m2lab-brand/research/type-metrics.json")

FONT_PATHS = {
    "hook_condensed_bold": FONT_DIR / "IBMPlexSansCondensed-Bold.ttf",
    "body_regular": FONT_DIR / "IBMPlexSans-Regular.ttf",
    "body_semibold": FONT_DIR / "IBMPlexSans-SemiBold.ttf",
    "label_mono_medium": FONT_DIR / "IBMPlexMono-Medium.ttf",
}

CANVAS_W = 1080
PAD_X = 96
TEXT_COL = CANVAS_W - 2 * PAD_X  # 888

# ---------------------------------------------------------------- font wrapper

class FontMetrics:
    def __init__(self, path):
        self.name = path.name
        self.font = TTFont(str(path))
        self.upm = self.font["head"].unitsPerEm
        self.hmtx = self.font["hmtx"]
        self.cmap = self.font.getBestCmap()  # codepoint -> glyph name
        self.glyf = self.font["glyf"] if "glyf" in self.font else None
        hhea = self.font["hhea"]
        self.ascent = hhea.ascent
        self.descent = hhea.descent  # negative
        self.linegap = hhea.lineGap
        os2 = self.font["OS/2"]
        self.cap_height_u = getattr(os2, "sCapHeight", 0) or self._glyph_ymax("H")
        self.x_height_u = getattr(os2, "sxHeight", 0) or self._glyph_ymax("x")

    def _glyph_ymax(self, ch):
        if not self.glyf or ord(ch) not in self.cmap:
            return None
        g = self.glyf[self.cmap[ord(ch)]]
        return getattr(g, "yMax", None)

    def has_char(self, ch):
        return ord(ch) in self.cmap

    def advance_units(self, ch):
        gname = self.cmap.get(ord(ch))
        if gname is None:
            # fall back to space-width average for unmapped chars (should not
            # happen for the ASCII test corpus used here)
            gname = self.cmap.get(ord(" "))
        return self.hmtx[gname][0]

    def text_width_px(self, text, size_px, tracking_em=0.0):
        units = sum(self.advance_units(c) for c in text)
        base_px = units / self.upm * size_px
        tracking_px = tracking_em * size_px * len(text)
        return base_px + tracking_px

    def avg_char_width_px(self, corpus, size_px, tracking_em=0.0):
        total_chars = sum(len(line) for line in corpus)
        total_px = sum(self.text_width_px(line, size_px, tracking_em) for line in corpus)
        return total_px / total_chars

    def natural_line_height_px(self, size_px):
        return (self.ascent - self.descent + self.linegap) / self.upm * size_px

    def cap_height_px(self, size_px):
        return self.cap_height_u / self.upm * size_px if self.cap_height_u else None

    def x_height_px(self, size_px):
        return self.x_height_u / self.upm * size_px if self.x_height_u else None


def wrap_greedy(fm, text, size_px, max_width_px, tracking_em=0.0):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = w if not cur else cur + " " + w
        if fm.text_width_px(trial, size_px, tracking_em) <= max_width_px or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- test corpus
# 30 hook lines, 6-8 words, AI-for-business niche (written for this test, not
# copied from any real M2 Lab post).
HOOK_CORPUS = [
    "We tested this AI agent on invoices",
    "This tool cut our reporting time in half",
    "Most founders waste hours on manual data entry",
    "Here is how we automated support",
    "Your team can ship this today",
    "This AI agent reads contracts faster than lawyers",
    "We replaced three spreadsheets with one AI agent",
    "Small teams are shipping AI tools this week",
    "This automation saved us hours weekly",
    "We built a bot that writes invoices",
    "AI agents are replacing junior analysts now",
    "This workflow turns emails into tracked tasks",
    "We tested five AI tools this week",
    "Our support bot closed forty tickets overnight",
    "This prompt saves our team six hours",
    "We fired our first AI teammate today",
    "This dashboard replaced four weekly status meetings",
    "Your inbox can run itself by tonight",
    "We automated onboarding for every new client",
    "This agent drafts our proposals in minutes",
    "We cut customer response time by eighty percent",
    "This tool reads receipts faster than an intern",
    "We let AI handle our weekly reporting",
    "This bot answers support tickets while we sleep",
    "We tested AI against our best analyst",
    "This workflow builds decks while you sleep",
    "We automated the part nobody wanted to do",
    "This agent reviews every contract before you sign",
    "We built this in a single weekend",
    "This tool turns meetings into action items fast",
]

BODY_CORPUS = [
    "Most teams still copy numbers from one tool into another by hand every single week.",
    "We ran the same task through four models and timed every single step of the process.",
    "The agent reads the inbox, drafts a reply, and waits for a human to approve it.",
    "None of this replaces a person, it just removes the parts nobody wanted to do anyway.",
    "We logged every failure so the next version of this workflow does not repeat it.",
]

LABELS = ["M2 RADAR", "M2 BUILDS", "M2 TEARDOWN", "KEEP", "KILL", "TEST", "WAS", "NOW", "SAVED"]

CYRILLIC_RANGE = [chr(c) for c in range(0x0410, 0x044F + 1)]

# ---------------------------------------------------------------- main

def main():
    fm = {k: FontMetrics(p) for k, p in FONT_PATHS.items()}
    out = {}

    print("=" * 100)
    print("0. FONT METRICS (raw, from head/hhea/OS2, unitsPerEm-normalised)")
    print("=" * 100)
    print(f"{'font':24}{'upm':>6}{'ascent':>8}{'descent':>8}{'lineGap':>8}{'capH_u':>8}{'xH_u':>8}")
    font_meta = {}
    for k, f in fm.items():
        print(f"{k:24}{f.upm:6}{f.ascent:8}{f.descent:8}{f.linegap:8}{f.cap_height_u or 0:8}{f.x_height_u or 0:8}")
        font_meta[k] = dict(file=f.name, unitsPerEm=f.upm, ascent=f.ascent, descent=f.descent,
                             lineGap=f.linegap, capHeight_units=f.cap_height_u, xHeight_units=f.x_height_u)
    out["font_meta"] = font_meta

    # word-count check on the corpus (must be 6-8 words per brief)
    counts = [len(l.split()) for l in HOOK_CORPUS]
    print(f"\nHook corpus: {len(HOOK_CORPUS)} lines, word counts min={min(counts)} max={max(counts)} "
          f"avg={sum(counts)/len(counts):.2f}")

    # ------------------------------------------------------------ TASK 1
    print("\n" + "=" * 100)
    print("1. HOOK -- chars/line into 888px column, lines needed for a 6- and 8-word hook")
    print("=" * 100)
    hook_font = fm["hook_condensed_bold"]
    tracking_hook = -0.01
    hook_sizes = [90, 96, 104]
    task1 = {"tracking_em": tracking_hook, "text_column_px": TEXT_COL, "sizes": {}}

    six_word = [l for l in HOOK_CORPUS if len(l.split()) == 6]
    eight_word = [l for l in HOOK_CORPUS if len(l.split()) == 8]
    sample6 = six_word[0]
    sample8 = eight_word[0]
    print(f"6-word sample: \"{sample6}\"")
    print(f"8-word sample: \"{sample8}\"\n")

    print(f"{'size':>6}{'avg_char_w_px':>16}{'chars/line(888px)':>20}{'6w lines':>10}{'8w lines':>10}"
          f"{'corpus avg lines':>18}{'corpus max lines':>18}")
    for size in hook_sizes:
        avg_w = hook_font.avg_char_width_px(HOOK_CORPUS, size, tracking_hook)
        chars_per_line = math.floor(TEXT_COL / avg_w)
        lines6 = len(wrap_greedy(hook_font, sample6, size, TEXT_COL, tracking_hook))
        lines8 = len(wrap_greedy(hook_font, sample8, size, TEXT_COL, tracking_hook))
        all_line_counts = [len(wrap_greedy(hook_font, l, size, TEXT_COL, tracking_hook)) for l in HOOK_CORPUS]
        avg_lines = sum(all_line_counts) / len(all_line_counts)
        max_lines = max(all_line_counts)
        print(f"{size:>6}{avg_w:16.2f}{chars_per_line:20}{lines6:10}{lines8:10}{avg_lines:18.2f}{max_lines:18}")
        task1["sizes"][size] = dict(avg_char_width_px=round(avg_w, 3), chars_per_line_888=chars_per_line,
                                     lines_6word_sample=lines6, lines_8word_sample=lines8,
                                     corpus_avg_lines=round(avg_lines, 3), corpus_max_lines=max_lines)
    out["task1_hook_line_wrap"] = task1

    # ------------------------------------------------------------ body chars/line too (context for task 6b)
    body_font = fm["body_regular"]
    body_sizes = [52, 46, 42]
    task1b = {"sizes": {}}
    print(f"\nBody (Regular, tracking 0): chars/line into 888px")
    print(f"{'size':>6}{'avg_char_w_px':>16}{'chars/line(888px)':>20}")
    for size in body_sizes:
        avg_w = body_font.avg_char_width_px(BODY_CORPUS, size, 0.0)
        chars_per_line = math.floor(TEXT_COL / avg_w)
        print(f"{size:>6}{avg_w:16.2f}{chars_per_line:20}")
        task1b["sizes"][size] = dict(avg_char_width_px=round(avg_w, 3), chars_per_line_888=chars_per_line)
    out["task1b_body_chars_per_line"] = task1b

    # ------------------------------------------------------------ TASK 2
    print("\n" + "=" * 100)
    print("2. VERTICAL FOOTPRINT")
    print("=" * 100)
    leading_hook = 1.03
    leading_body = 1.35
    leading_label = 1.0
    gap = 48
    reel_band = 1920 - 180 - 320   # 1420
    ratio45_band = 1350 - 180 - 320  # 850

    task2 = {"leading": {"hook": leading_hook, "body": leading_body, "label": leading_label},
             "gap_px": gap, "bands": {"reel_1920": reel_band, "ratio_4x5_1350": ratio45_band},
             "hook_block_heights": {}, "body_block_heights": {}, "label_line_heights": {}}

    print(f"Safe vertical band -- Reels(1920): {reel_band}px, 4:5(1350): {ratio45_band}px\n")
    print("Hook block heights (n_lines * size * 1.03):")
    print(f"{'size':>6}" + "".join(f"{n}L:>10" for n in (2, 3, 4)))
    for size in hook_sizes:
        row = {}
        cells = []
        for n in (2, 3, 4):
            h = n * size * leading_hook
            cells.append(h)
            row[str(n)] = round(h, 1)
        print(f"{size:>6}  2L={cells[0]:7.1f}  3L={cells[1]:7.1f}  4L={cells[2]:7.1f}")
        task2["hook_block_heights"][size] = row

    print("\nBody paragraph (3 lines, leading 1.35):")
    for size in body_sizes:
        h = 3 * size * leading_body
        print(f"  {size}px -> {h:.1f}px")
        task2["body_block_heights"][size] = round(h, 1)

    print("\nLabel line height (1 line, leading 1.0):")
    for size in (32, 25):
        h = size * leading_label
        print(f"  {size}px -> {h:.1f}px")
        task2["label_line_heights"][size] = round(h, 1)

    # what fits: hook(default 96, N lines) + gap + body(default 46, M lines) <= band
    print("\nMax hook+body combo (hook @96px, body @46px, gap 48px) per band:")
    hook96 = task2["hook_block_heights"][96]
    body46 = task2["body_block_heights"][46]
    combos = {}
    for band_name, band in (("reel_1920", reel_band), ("ratio_4x5_1350", ratio45_band)):
        best = None
        for n_hook in (2, 3, 4):
            for n_body_lines in range(0, 8):
                body_h = n_body_lines * 46 * leading_body
                total = hook96[str(n_hook)] + (gap + body_h if n_body_lines > 0 else 0)
                if total <= band:
                    if best is None or (n_hook, n_body_lines) > (best[0], best[1]):
                        best = (n_hook, n_body_lines, total)
        combos[band_name] = dict(max_hook_lines=best[0], max_body_lines=best[1], used_px=round(best[2], 1),
                                  band_px=band, slack_px=round(band - best[2], 1))
        print(f"  {band_name} ({band}px): hook {best[0]}L + body {best[1]}L = {best[2]:.1f}px used, "
              f"{band - best[2]:.1f}px slack")
    task2["max_fit_combo"] = combos
    out["task2_vertical_footprint"] = task2

    # ------------------------------------------------------------ TASK 3
    print("\n" + "=" * 100)
    print("3. MINIMUM LEGIBLE SIZE (reel-in-feed phone view, and profile grid tile)")
    print("=" * 100)
    reel_scale = 390 / 1080
    grid_scale = 125 / 1080
    print(f"reel_scale (390/1080) = {reel_scale:.4f}")
    print(f"grid_scale (125/1080) = {grid_scale:.4f}\n")

    all_sizes = {
        "hook_90": (hook_font, 90), "hook_96": (hook_font, 96), "hook_104": (hook_font, 104),
        "body_52": (body_font, 52), "body_46": (body_font, 46), "body_42": (body_font, 42),
        "label_32": (fm["label_mono_medium"], 32), "label_25": (fm["label_mono_medium"], 25),
    }
    task3 = {"reel_scale": round(reel_scale, 4), "grid_scale": round(grid_scale, 4), "sizes": {}}
    print(f"{'role_size':14}{'css_px(reel)':>14}{'pt(reel)':>10}{'phys_px@3x':>12}{'illegible<12css':>16}"
          f"{'capH_css(grid)':>16}{'grid_survive>=9':>16}")
    for label, (font, size) in all_sizes.items():
        css_px = size * reel_scale
        pt = css_px * 0.75  # 96 css-px/in, 72 pt/in
        phys_px_3x = css_px * 3
        illegible = css_px < 12
        cap_h_px_at_size = font.cap_height_px(size) or 0
        cap_h_css_grid = cap_h_px_at_size * grid_scale
        survives_grid = cap_h_css_grid >= 9
        print(f"{label:14}{css_px:14.2f}{pt:10.2f}{phys_px_3x:12.2f}{str(illegible):>16}"
              f"{cap_h_css_grid:16.2f}{str(survives_grid):>16}")
        task3["sizes"][label] = dict(size_px=size, css_px_reel=round(css_px, 2), pt_reel=round(pt, 2),
                                      physical_px_at_3x=round(phys_px_3x, 2), illegible_below_12css=illegible,
                                      cap_height_units=font.cap_height_u, cap_height_css_grid=round(cap_h_css_grid, 2),
                                      survives_grid_9css_cap=survives_grid)
    out["task3_min_legible"] = task3

    # ------------------------------------------------------------ TASK 4
    print("\n" + "=" * 100)
    print("4. CYRILLIC COVERAGE (U+0410-U+044F, from cmap)")
    print("=" * 100)
    task4 = {}
    for k, f in fm.items():
        missing = [c for c in CYRILLIC_RANGE if not f.has_char(c)]
        covers = len(missing) == 0
        print(f"{k:24} {f.name:32} covers full range: {covers}  (missing {len(missing)}/{len(CYRILLIC_RANGE)})")
        task4[k] = dict(file=f.name, covers_full_range=covers, missing_count=len(missing),
                         range_size=len(CYRILLIC_RANGE))
    out["task4_cyrillic"] = task4

    # ------------------------------------------------------------ TASK 5
    print("\n" + "=" * 100)
    print("5. MONO LABEL WIDTHS (+0.16em tracking)")
    print("=" * 100)
    mono = fm["label_mono_medium"]
    tracking_label = 0.16
    task5 = {"tracking_em": tracking_label, "sizes": {}}
    for size in (32, 25):
        print(f"\nsize {size}px:")
        widths = {}
        for lbl in LABELS:
            w = mono.text_width_px(lbl, size, tracking_label)
            widths[lbl] = round(w, 2)
            print(f"  {lbl:12} {w:8.2f}px")
        task5["sizes"][size] = widths
    out["task5_mono_labels"] = task5

    chip_labels = ["KEEP", "KILL", "TEST"]
    chip_reco = {}
    for size in (32, 25):
        max_w = max(task5["sizes"][size][l] for l in chip_labels)
        chip_reco[size] = dict(max_label_width_px=max_w, recommended_chip_pad_x=24,
                                recommended_chip_width_px=round(max_w + 2 * 24, 1))
        print(f"\nchip @ {size}px: widest of KEEP/KILL/TEST = {max_w:.2f}px -> "
              f"fixed chip width {max_w + 48:.1f}px (24px pad each side)")
    task5["chip_recommendation"] = chip_reco
    out["task5_mono_labels"] = task5

    # ------------------------------------------------------------ TASK 6
    print("\n" + "=" * 100)
    print("6. RECOMMENDATIONS")
    print("=" * 100)
    # 6a: 4:5 hook size test -- does 96px 3-line hook fit 850px band with body?
    band45 = ratio45_band
    hook_h_96_3L = task2["hook_block_heights"][96]["3"]
    hook_h_84_3L = 3 * 84 * leading_hook
    hook_h_84_4L = 4 * 84 * leading_hook
    print(f"4:5 band = {band45}px. Hook@96 3L = {hook_h_96_3L:.1f}px, "
          f"leaves {band45 - hook_h_96_3L - gap:.1f}px after a {gap}px gap for body.")
    print(f"Hook@84 3L = {hook_h_84_3L:.1f}px, Hook@84 4L = {hook_h_84_4L:.1f}px")
    body_46_1L = 46 * leading_body
    body_46_2L = 2 * 46 * leading_body
    fits_96_with_1L_body = (hook_h_96_3L + gap + body_46_1L) <= band45
    fits_96_with_2L_body = (hook_h_96_3L + gap + body_46_2L) <= band45
    fits_84_4L_with_1L_body = (hook_h_84_4L + gap + body_46_1L) <= band45
    print(f"96px/3L hook + gap + 1L body(46) fits 4:5 band: {fits_96_with_1L_body} "
          f"({hook_h_96_3L+gap+body_46_1L:.1f} vs {band45})")
    print(f"96px/3L hook + gap + 2L body(46) fits 4:5 band: {fits_96_with_2L_body} "
          f"({hook_h_96_3L+gap+body_46_2L:.1f} vs {band45})")
    print(f"84px/4L hook + gap + 1L body(46) fits 4:5 band: {fits_84_4L_with_1L_body} "
          f"({hook_h_84_4L+gap+body_46_1L:.1f} vs {band45})")

    # 6b: lint chars/line -- take the smallest chars_per_line across the sizes actually used
    hook_min_chars = min(task1["sizes"][s]["chars_per_line_888"] for s in hook_sizes)
    body_min_chars = min(task1b["sizes"][s]["chars_per_line_888"] for s in body_sizes)
    print(f"\nLint max-chars-per-line (worst case = biggest size in role): "
          f"hook <= {hook_min_chars}, body <= {body_min_chars}")

    # 6c: caption size for burned-in subtitles, Plex Sans SemiBold, >=14 css px on 390-wide phone
    caption_font = fm["body_semibold"]
    min_caption_px = 14 / reel_scale
    caption_candidates = [34, 36, 38, 40, 42]
    print(f"\nCaption min size for >=14 css px @ reel_scale {reel_scale:.4f}: {min_caption_px:.2f}px (raw)")
    task6 = {
        "ratio_4x5": dict(band_px=band45, hook96_3L_px=round(hook_h_96_3L, 1),
                           hook84_3L_px=round(hook_h_84_3L, 1), hook84_4L_px=round(hook_h_84_4L, 1),
                           fits_96_3L_plus_1L_body=fits_96_with_1L_body,
                           fits_96_3L_plus_2L_body=fits_96_with_2L_body,
                           fits_84_4L_plus_1L_body=fits_84_4L_with_1L_body),
        "lint_max_chars_per_line": dict(hook=hook_min_chars, body=body_min_chars),
        "caption": dict(font="IBMPlexSans-SemiBold", min_size_px_raw=round(min_caption_px, 2),
                         candidates_css_px={}),
    }
    print(f"{'candidate_px':14}{'css_px(reel)':>14}{'ok>=14css':>12}")
    for c in caption_candidates:
        css = c * reel_scale
        ok = css >= 14
        print(f"{c:14}{css:14.2f}{str(ok):>12}")
        task6["caption"]["candidates_css_px"][c] = dict(css_px=round(css, 2), ok_ge_14=ok)
    out["task6_recommendations"] = task6

    OUT_JSON.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {OUT_JSON}")


if __name__ == "__main__":
    main()

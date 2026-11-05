"""Render a validated Team Status tree to one accessible static page.

The renderer does not rewrite status text, dates, or the as-of sentence.
Tone values are exposed as text for assistive technology and as color.
"""

from __future__ import annotations

import html

from jsx_subset import Element

_TONE_WORD = {
    "danger": "danger",
    "warning": "warning",
    "success": "success",
    "info": "note",
}

_CSS = """
:root {
  color-scheme: light dark;
  --bg: #f6f6f4;
  --ink: #1c1917;
  --muted: #44403c;
  --line: #d6d3d1;
  --paper: #ffffff;
  --danger: #9f1239;
  --warning: #92400e;
  --success: #166534;
  --info: #1e3a8a;
  --callout-bg: #fffbeb;
  --callout-ink: #1c1917;
  --focus: #1d4ed8;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #141413;
    --ink: #f5f5f4;
    --muted: #d6d3d1;
    --line: #44403c;
    --paper: #1c1c1a;
    --danger: #fecdd3;
    --warning: #fde68a;
    --success: #bbf7d0;
    --info: #bfdbfe;
    --callout-bg: #292524;
    --callout-ink: #f5f5f4;
    --focus: #93c5fd;
  }
}
* { box-sizing: border-box; }
html { scroll-behavior: auto; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font: 1rem/1.5 system-ui, -apple-system, "Segoe UI", sans-serif;
}
a { color: inherit; }
a:hover { text-decoration-thickness: 2px; }
:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
.skip {
  position: absolute;
  left: 0.75rem;
  top: 0.75rem;
  padding: 0.4rem 0.7rem;
  background: var(--paper);
  color: var(--ink);
  border: 1px solid var(--line);
  transform: translateY(-200%);
}
.skip:focus { transform: none; }
main { margin: 0 auto; padding: 2rem 1.25rem 3rem; }
main[data-width="column"] { max-width: 43.75rem; }
main[data-width="wide"] { max-width: 80rem; }
main[data-width="full"] { max-width: none; }
h1 { font-size: 1.75rem; line-height: 1.2; margin: 0 0 0.75rem; }
h2 { font-size: 1.3rem; line-height: 1.3; margin: 0 0 0.75rem; }
h3 { font-size: 1.05rem; line-height: 1.35; margin: 0; }
.summary { margin: 0 0 1.25rem; font-size: 1.05rem; }
nav ol { display: flex; flex-wrap: wrap; gap: 0.5rem 1rem; padding: 0; margin: 0 0 2rem; list-style: none; }
nav a { color: var(--ink); }
.section { margin: 0 0 2.5rem; }
.caption { margin: 0.75rem 0 0; color: var(--muted); }
.rows { display: flex; flex-direction: column; }
.row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto auto;
  column-gap: 0.75rem;
  row-gap: 0.35rem;
  align-items: baseline;
  padding: 0.9rem 0;
  border-top: 1px solid var(--line);
}
.row.no-lead { grid-template-columns: minmax(0, 1fr) auto auto; }
.lead { margin: 0; color: var(--muted); font-variant-numeric: tabular-nums; }
.title { margin: 0; }
.detail { grid-column: 2 / -1; margin: 0; }
.row.no-lead .detail { grid-column: 1 / -1; }
.meta { margin: 0; color: var(--muted); text-align: right; }
.status { margin: 0; font-weight: 600; white-space: nowrap; }
.status[data-tone="danger"] { color: var(--danger); }
.status[data-tone="warning"] { color: var(--warning); }
.status[data-tone="success"] { color: var(--success); }
.callout {
  margin: 0 0 1rem;
  padding: 0.9rem 1rem;
  background: var(--callout-bg);
  color: var(--callout-ink);
  border-left: 4px solid var(--line);
}
.callout[data-tone="warning"] { border-left-color: var(--warning); }
.callout[data-tone="danger"] { border-left-color: var(--danger); }
.callout[data-tone="success"] { border-left-color: var(--success); }
.callout[data-tone="info"] { border-left-color: var(--info); }
.callout p { margin: 0.4rem 0 0; }
.callout p:first-child { margin-top: 0; }
.kicker { font-weight: 700; }
.prose { margin: 0.9rem 0 0; }
.scroll-hint { margin: 0 0 0.4rem; color: var(--muted); font-size: 0.9rem; }
.table-scroll {
  overflow-x: auto;
  border: 1px solid var(--line);
  background: var(--paper);
}
table { border-collapse: collapse; width: 100%; min-width: 52rem; }
th, td {
  border-bottom: 1px solid var(--line);
  padding: 0.55rem 0.7rem;
  text-align: left;
  vertical-align: top;
}
th { font-weight: 600; }
tbody th { font-weight: 600; }
tr:last-child th, tr:last-child td { border-bottom: 0; }
td[data-tone="danger"], th[data-tone="danger"] { color: var(--danger); font-weight: 600; }
td[data-tone="warning"], th[data-tone="warning"] { color: var(--warning); font-weight: 600; }
td[data-tone="success"], th[data-tone="success"] { color: var(--success); font-weight: 600; }
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
@media (max-width: 640px) {
  .row, .row.no-lead { grid-template-columns: auto minmax(0, 1fr); }
  .status, .meta, .row.no-lead .status, .row.no-lead .meta { grid-column: 2; text-align: left; }
  .detail, .row.no-lead .detail { grid-column: 2; }
  .row.no-lead .title { grid-column: 1 / -1; }
  .status { white-space: normal; }
}
@media (min-width: 801px) {
  .scroll-hint { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0, 0, 0, 0); }
}
@media print {
  body { background: #fff; color: #000; }
  .skip, nav { display: none; }
  .table-scroll { overflow: visible; }
  table { min-width: 0; }
  a { text-decoration: none; }
}
"""


def _esc(text: str) -> str:
    return html.escape(text, quote=False)


def _attr(text: str) -> str:
    return html.escape(text, quote=True)


def _slug(text: str) -> str:
    lowered = text.lower()
    out = []
    dash = False
    for char in lowered:
        if char.isascii() and char.isalnum():
            out.append(char)
            dash = False
        elif not dash:
            out.append("-")
            dash = True
    slug = "".join(out).strip("-")
    return slug or "section"


class _Renderer:
    def __init__(self) -> None:
        self._used: dict[str, int] = {}

    def unique_slug(self, text: str) -> str:
        base = _slug(text)
        seen = self._used.get(base, 0) + 1
        self._used[base] = seen
        if seen == 1:
            return base
        return f"{base}-{seen}"

    def render(self, page: Element) -> str:
        title = page.props["title"]
        summary = page.props.get("summary", "")
        width = page.props.get("width", "column")
        lang = page.props.get("lang", "en")
        sections = [child for child in page.children if isinstance(child, Element)]
        nav = []
        body = []
        for child in sections:
            if child.name == "Section" and child.props.get("heading"):
                slug = self.unique_slug(child.props["heading"])
            elif child.name == "Section":
                slug = self.unique_slug("section")
            else:
                slug = ""
            if child.name == "Section" and child.props.get("heading"):
                nav.append((slug, child.props["heading"]))
            body.append(self.block(child, slug))
        nav_html = ""
        if nav:
            items = "".join(
                f'<li><a href="#{_attr(slug)}">{_esc(label)}</a></li>'
                for slug, label in nav
            )
            nav_html = f'<nav aria-label="Sections"><ol>{items}</ol></nav>'
        summary_html = f'<p class="summary">{_esc(summary)}</p>' if summary else ""
        return (
            "<!DOCTYPE html>\n"
            f'<html lang="{_attr(lang)}">\n'
            "<head>\n"
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"<title>{_esc(title)}</title>\n"
            + (f'<meta name="description" content="{_attr(summary)}">\n' if summary else "")
            + '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src \'self\' data:; base-uri \'none\'; form-action \'none\'; frame-ancestors \'none\'">\n'
            f"<style>{_CSS}</style>\n"
            "</head>\n"
            "<body>\n"
            '<a class="skip" href="#content">Skip to content</a>\n'
            f'<main id="content" data-width="{_attr(width)}">\n'
            "<header>\n"
            f"<h1>{_esc(title)}</h1>\n"
            f"{summary_html}\n"
            "</header>\n"
            f"{nav_html}\n"
            f"{''.join(body)}"
            "</main>\n"
            "</body>\n"
            "</html>\n"
        )

    def block(self, el: Element, slug: str) -> str:
        if el.name == "Section":
            return self.section(el, slug)
        if el.name == "Text":
            return self.text(el)
        if el.name == "Callout":
            return self.callout(el)
        if el.name == "Rows":
            return self.rows(el)
        if el.name == "Table":
            return self.table(el, "")
        raise RuntimeError(el.name)

    def section(self, el: Element, slug: str) -> str:
        heading = el.props.get("heading", "")
        anchor = el.props.get("id") or slug or self.unique_slug(heading or "section")
        heading_id = f"{anchor}-heading"
        head = ""
        if heading:
            head = f'<h2 id="{_attr(heading_id)}">{_esc(heading)}</h2>\n'
        caption = el.props.get("caption", "")
        blocks = []
        caption_placed = False
        saw_table = False
        for child in el.children:
            if child.name == "Table":
                saw_table = True
                blocks.append(self.table(child, heading_id if heading else ""))
                if caption and not caption_placed:
                    blocks.append(f'<p class="caption">{_esc(caption)}</p>\n')
                    caption_placed = True
                continue
            rendered = self.block(child, "")
            blocks.append(rendered)
        if caption and not caption_placed:
            # No table: the caption is the heading subtitle and stays with the heading.
            head += f'<p class="caption">{_esc(caption)}</p>\n'
            caption_placed = True
        if caption and not caption_placed and not saw_table:
            blocks.append(f'<p class="caption">{_esc(caption)}</p>\n')
        labelled = f' aria-labelledby="{_attr(heading_id)}"' if heading else ""
        return (
            f'<section class="section" id="{_attr(anchor)}"{labelled}>\n'
            f"{head}{''.join(blocks)}</section>\n"
        )

    def text(self, el: Element) -> str:
        parts = "".join(_esc(child) for child in el.children)
        return f'<p class="prose">{parts}</p>\n'

    def callout(self, el: Element) -> str:
        tone = el.props.get("tone", "")
        bits = []
        if tone:
            bits.append(f'<p class="kicker">{_esc(_TONE_WORD[tone].capitalize())}</p>')
        if el.props.get("lead"):
            bits.append(f'<p class="kicker">{_esc(el.props["lead"])}</p>')
        for child in el.children:
            if isinstance(child, str):
                bits.append(f"<p>{_esc(child)}</p>")
            else:
                inner = "".join(_esc(part) for part in child.children)
                bits.append(f"<p>{inner}</p>")
        tone_attr = f' data-tone="{_attr(tone)}"' if tone else ""
        return f'<aside class="callout" role="note"{tone_attr}>{"".join(bits)}</aside>\n'

    def rows(self, el: Element) -> str:
        items = []
        for row in el.props["rows"]:
            classes = ["row"]
            lead = row.get("lead", "")
            if not lead:
                classes.append("no-lead")
            bits = []
            if lead:
                bits.append(f'<p class="lead"><span class="sr-only">Item </span>{_esc(lead)}</p>')
            bits.append(f'<h3 class="title">{_esc(row["title"])}</h3>')
            status = row.get("status")
            if status:
                tone = status.get("tone", "")
                tone_attr = f' data-tone="{_attr(tone)}"' if tone else ""
                spoken = "Status"
                if tone:
                    spoken += f", {tone}"
                bits.append(
                    f'<p class="status"{tone_attr}><span class="sr-only">{_esc(spoken)}. </span>{_esc(status["label"])}</p>'
                )
            if row.get("meta"):
                bits.append(f'<p class="meta">{_esc(row["meta"])}</p>')
            if row.get("detail"):
                bits.append(f'<p class="detail">{_esc(row["detail"])}</p>')
            items.append(f'<article class="{" ".join(classes)}">{"".join(bits)}</article>\n')
        return f'<div class="rows">{"".join(items)}</div>\n'

    def table(self, el: Element, heading_id: str) -> str:
        columns = list(el.props["columns"])
        rows = el.props["rows"]
        width = max(len(columns), max(len(row) for row in rows))
        while len(columns) < width:
            columns.append("")
        align = list(el.props.get("align") or [])
        head_cells = []
        for index, column in enumerate(columns):
            style = _align_style(align, index)
            head_cells.append(f'<th scope="col"{style}>{_esc(column)}</th>')
        body = []
        for row in rows:
            cells = []
            padded = list(row) + [""] * (width - len(row))
            for index, cell in enumerate(padded):
                text, tone = _cell_parts(cell)
                style = _align_style(align, index)
                if tone:
                    style += f' data-tone="{_attr(tone)}"'
                if index == 0:
                    spoken = f'<span class="sr-only">{_esc(tone)}. </span>' if tone else ""
                    cells.append(f'<th scope="row"{style}>{spoken}{_esc(text)}</th>')
                else:
                    spoken = f'<span class="sr-only">{_esc(tone)}. </span>' if tone else ""
                    cells.append(f"<td{style}>{spoken}{_esc(text)}</td>")
            body.append("<tr>" + "".join(cells) + "</tr>")
        labelled = f' aria-labelledby="{_attr(heading_id)}"' if heading_id else ""
        return (
            '<p class="scroll-hint">This table scrolls sideways on a narrow screen. Every column is in the page.</p>\n'
            f'<div class="table-scroll" tabindex="0">\n'
            f"<table{labelled}>\n<thead><tr>{''.join(head_cells)}</tr></thead>\n"
            f"<tbody>{''.join(body)}</tbody>\n</table>\n</div>\n"
        )


def _cell_parts(cell) -> tuple[str, str]:
    if isinstance(cell, str):
        return cell, ""
    if cell == "":
        return "", ""
    return cell.get("text", ""), cell.get("tone", "")


def _align_style(align: list, index: int) -> str:
    if index >= len(align) or align[index] in ("", "auto", "start"):
        return ""
    if align[index] == "end":
        return ' style="text-align:right"'
    return ""


def render_team_status(page: Element) -> str:
    return _Renderer().render(page)

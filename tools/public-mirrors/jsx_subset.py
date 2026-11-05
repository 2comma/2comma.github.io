"""Fail-closed parser for the Team Status JSX subset.

The supported module shape is a single grok/canvas import and a default App
function that returns one element tree. Expressions may only be string
literals, arrays, and objects of those values. Comments, spreads, identifiers,
calls, and any component or prop this renderer does not know are errors.
Nothing in the tree is skipped.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from common import MirrorError

ALLOWED_COMPONENTS = {"Page", "Section", "Rows", "Table", "Callout", "Text"}
PAGE_PROPS = {"title", "summary", "width", "lang"}
SECTION_PROPS = {"heading", "id", "caption"}
ROWS_PROPS = {"rows"}
TABLE_PROPS = {"columns", "rows", "align"}
CALLOUT_PROPS = {"tone", "lead"}
TEXT_PROPS: set[str] = set()
ROW_KEYS = {"lead", "title", "detail", "meta", "status"}
STATUS_KEYS = {"label", "tone"}
STATUS_TONES = {"success", "warning", "danger"}
CALLOUT_TONES = STATUS_TONES | {"info"}
WIDTHS = {"column", "wide", "full"}
ALIGNS = {"auto", "start", "end"}
PAGE_CHILD = {"Section", "Text", "Callout", "Rows", "Table"}
SECTION_CHILD = {"Section", "Text", "Callout", "Rows", "Table"}


@dataclass
class Element:
    name: str
    props: dict
    children: list = field(default_factory=list)


class Parser:
    def __init__(self, src: str):
        self.s = src
        self.i = 0
        self.n = len(src)

    def peek(self, k: int = 0) -> str:
        j = self.i + k
        return self.s[j] if j < self.n else ""

    def startswith(self, lit: str) -> bool:
        return self.s.startswith(lit, self.i)

    def err(self, msg: str) -> None:
        line = self.s.count("\n", 0, self.i) + 1
        last_nl = self.s.rfind("\n", 0, self.i)
        col = self.i - last_nl
        raise MirrorError(f"unexpected JSX: {msg} (line {line}, column {col})")

    def expect(self, lit: str) -> None:
        if not self.startswith(lit):
            self.err(f"expected {lit!r}")
        self.i += len(lit)

    def skip_ws(self) -> None:
        while self.peek() and self.peek().isspace():
            self.i += 1

    def skip_ws_code(self) -> None:
        self.skip_ws()
        if self.startswith("//") or self.startswith("/*") or self.startswith("{/*"):
            self.err("comment would be dropped")

    def parse_ident(self) -> str:
        c = self.peek()
        if not (c.isalpha() or c == "_"):
            self.err("expected an identifier")
        j = self.i + 1
        while j < self.n and (self.s[j].isalnum() or self.s[j] in "_$"):
            j += 1
        ident = self.s[self.i:j]
        self.i = j
        return ident

    def parse_string(self) -> str:
        quote = self.peek()
        if quote not in "\"'":
            self.err("expected a string")
        self.i += 1
        chars: list[str] = []
        while self.i < self.n:
            c = self.peek()
            if c == quote:
                self.i += 1
                return "".join(chars)
            if c == "\n":
                self.err("unterminated string")
            if c == "\\":
                self.i += 1
                esc = self.peek()
                mapping = {"n": "\n", "r": "\r", "t": "\t", "\\": "\\", "'": "'", '"': '"', "/": "/"}
                if esc in mapping:
                    chars.append(mapping[esc])
                    self.i += 1
                    continue
                if esc == "u":
                    self.i += 1
                    hex_digits = self.s[self.i:self.i + 4]
                    if len(hex_digits) != 4 or any(d not in "0123456789abcdefABCDEF" for d in hex_digits):
                        self.err("bad unicode escape")
                    chars.append(chr(int(hex_digits, 16)))
                    self.i += 4
                    continue
                self.err("unsupported string escape")
            chars.append(c)
            self.i += 1
        self.err("unterminated string")
        return ""

    def parse_template(self) -> str:
        self.expect("`")
        chars: list[str] = []
        while self.i < self.n:
            if self.startswith("${"):
                self.err("template interpolation is not supported")
            c = self.peek()
            if c == "`":
                self.i += 1
                return "".join(chars)
            if c == "\\":
                self.i += 1
                esc = self.peek()
                if esc in "`\\$":
                    chars.append(esc)
                    self.i += 1
                    continue
                self.err("unsupported template escape")
            chars.append(c)
            self.i += 1
        self.err("unterminated template")
        return ""

    def parse_expr(self):
        self.skip_ws_code()
        c = self.peek()
        if c in "\"'":
            return self.parse_string()
        if c == "`":
            return self.parse_template()
        if c == "[":
            return self.parse_array()
        if c == "{":
            return self.parse_object()
        if c.isdigit() or (c == "-" and self.peek(1).isdigit()):
            self.err("numeric literal is not supported; keep values as strings so text is not reformatted")
        if self._keyword("true") or self._keyword("false") or self._keyword("null"):
            self.err("boolean and null literals are not supported")
        if c.isalpha() or c == "_":
            self.err("identifier expression would be evaluated; only literal data is accepted")
        if c == ".":
            self.err("spread would hide or inject properties")
        self.err("unsupported expression")
        return None

    def _keyword(self, word: str) -> bool:
        if not self.startswith(word):
            return False
        nxt = self.peek(len(word))
        return not (nxt.isalnum() or nxt == "_")

    def parse_array(self) -> list:
        self.expect("[")
        items = []
        while True:
            self.skip_ws_code()
            if self.peek() == "]":
                self.i += 1
                return items
            items.append(self.parse_expr())
            self.skip_ws_code()
            if self.peek() == ",":
                self.i += 1
                continue
            if self.peek() == "]":
                self.i += 1
                return items
            self.err("expected a comma in an array")

    def parse_object(self) -> dict:
        self.expect("{")
        obj: dict = {}
        while True:
            self.skip_ws_code()
            if self.peek() == "}":
                self.i += 1
                return obj
            if self.startswith("..."):
                self.err("object spread would hide or inject properties")
            if self.peek() in "\"'":
                key = self.parse_string()
            else:
                key = self.parse_ident()
            if key in obj:
                self.err(f"duplicate object key {key!r}")
            self.skip_ws_code()
            self.expect(":")
            obj[key] = self.parse_expr()
            self.skip_ws_code()
            if self.peek() == ",":
                self.i += 1
                continue
            if self.peek() == "}":
                self.i += 1
                return obj
            self.err("expected a comma in an object")

    def parse_braced_expr(self):
        if self.startswith("{/*"):
            self.err("JSX comment would be dropped")
        self.expect("{")
        self.skip_ws_code()
        if self.startswith("..."):
            self.err("spread would hide or inject properties")
        value = self.parse_expr()
        self.skip_ws_code()
        self.expect("}")
        return value

    def parse_element(self) -> Element:
        self.expect("<")
        if self.peek() in ">/" :
            self.err("JSX fragment is not supported")
        name = self.parse_ident()
        props: dict = {}
        while True:
            self.skip_ws_code()
            if self.startswith("/>"):
                self.i += 2
                return Element(name, props, [])
            if self.startswith(">"):
                self.i += 1
                children = self.parse_children(name)
                return Element(name, props, children)
            if self.startswith("{") or self.startswith("..."):
                self.err("expression prop is not supported")
            key = self.parse_ident()
            self.skip_ws_code()
            if self.peek() != "=":
                self.err(f"boolean prop {key!r} is not supported")
            self.expect("=")
            self.skip_ws_code()
            if key in props:
                self.err(f"duplicate prop {key!r}")
            if self.peek() in "\"'":
                props[key] = self.parse_string()
            elif self.peek() == "{":
                props[key] = self.parse_braced_expr()
            else:
                self.err(f"expected a value for prop {key!r}")

    def parse_children(self, name: str) -> list:
        end = f"</{name}>"
        children: list = []
        buf: list[str] = []

        def flush() -> None:
            if not buf:
                return
            text = "".join(buf)
            buf.clear()
            if text.strip():
                children.append(text)

        while not self.startswith(end):
            if self.i >= self.n:
                self.err(f"unclosed <{name}>")
            if self.startswith("</"):
                self.err(f"closing tag does not match <{name}>")
            if self.startswith("{/*"):
                self.err("JSX comment would be dropped")
            if self.startswith("<"):
                flush()
                children.append(self.parse_element())
                continue
            if self.startswith("{"):
                flush()
                value = self.parse_braced_expr()
                if not isinstance(value, str):
                    self.err("JSX child expression must be a string literal")
                if value.strip():
                    children.append(value)
                elif value != "":
                    children.append(value)
                continue
            buf.append(self.peek())
            self.i += 1
        flush()
        self.expect(end)
        return children

    def parse_module(self) -> tuple[list[str], Element]:
        self.skip_ws_code()
        self.expect("import")
        self.skip_ws_code()
        self.expect("{")
        names: list[str] = []
        while True:
            self.skip_ws_code()
            if self.peek() == "}":
                self.i += 1
                break
            name = self.parse_ident()
            self.skip_ws_code()
            if self._keyword("as"):
                self.err("import aliases are not supported")
            if name in names:
                self.err(f"duplicate import {name!r}")
            names.append(name)
            self.skip_ws_code()
            if self.peek() == ",":
                self.i += 1
                continue
            if self.peek() == "}":
                self.i += 1
                break
            self.err("expected a comma in the import list")
        self.skip_ws_code()
        self.expect("from")
        self.skip_ws_code()
        module = self.parse_string()
        if module != "grok/canvas":
            self.err(f"import source {module!r} is not the supported literal export")
        self.skip_ws_code()
        self.expect(";")
        self.skip_ws_code()
        self.expect("export")
        self.skip_ws_code()
        self.expect("default")
        self.skip_ws_code()
        self.expect("function")
        self.skip_ws_code()
        fname = self.parse_ident()
        if fname != "App":
            self.err("expected function App")
        self.skip_ws_code()
        self.expect("(")
        self.skip_ws_code()
        self.expect(")")
        self.skip_ws_code()
        self.expect("{")
        self.skip_ws_code()
        self.expect("return")
        self.skip_ws_code()
        wrapped = False
        if self.peek() == "(":
            wrapped = True
            self.i += 1
            self.skip_ws_code()
        if self.peek() != "<":
            self.err("expected a JSX element")
        element = self.parse_element()
        self.skip_ws_code()
        if wrapped:
            self.expect(")")
            self.skip_ws_code()
        self.expect(";")
        self.skip_ws_code()
        self.expect("}")
        self.skip_ws_code()
        if self.i != self.n:
            self.err("trailing content after the component")
        if not names:
            self.err("empty import")
        return names, element


def parse_module(src: str) -> tuple[list[str], Element]:
    return Parser(src).parse_module()


def _require_str(props: dict, key: str, where: str, required: bool = False) -> None:
    if key not in props:
        if required:
            raise MirrorError(f"{where} is missing required string prop {key!r}")
        return
    if not isinstance(props[key], str) or props[key].strip() == "":
        raise MirrorError(f"{where} prop {key!r} must be a non-empty string")


def _reject_unknown_props(props: dict, allowed: set[str], where: str) -> None:
    unknown = sorted(set(props) - allowed)
    if unknown:
        raise MirrorError(
            f"{where} has unsupported prop {unknown[0]!r}. "
            "Refusing to drop it."
        )


def _check_status(status, where: str) -> None:
    if not isinstance(status, dict):
        raise MirrorError(f"{where} status must be an object")
    unknown = sorted(set(status) - STATUS_KEYS)
    if unknown:
        raise MirrorError(f"{where} status has unsupported field {unknown[0]!r}")
    label = status.get("label")
    if not isinstance(label, str) or label.strip() == "":
        raise MirrorError(f"{where} status is missing label")
    if "tone" in status and status["tone"] not in STATUS_TONES:
        raise MirrorError(f"{where} status tone {status['tone']!r} is not supported")


def _check_cell(cell, where: str) -> None:
    if isinstance(cell, str):
        return
    if isinstance(cell, dict):
        unknown = sorted(set(cell) - {"text", "tone"})
        if unknown:
            raise MirrorError(f"{where} cell has unsupported field {unknown[0]!r}")
        if not isinstance(cell.get("text"), str):
            raise MirrorError(f"{where} cell text must be a string")
        if "tone" in cell and cell["tone"] not in STATUS_TONES:
            raise MirrorError(f"{where} cell tone {cell['tone']!r} is not supported")
        return
    raise MirrorError(f"{where} cell is not a string or status object")


def _walk(el: Element, used: set[str], *, role: str) -> None:
    if not isinstance(el, Element):
        raise MirrorError("unexpected child; refusing to drop it")
    used.add(el.name)
    if el.name not in ALLOWED_COMPONENTS:
        raise MirrorError(f"unsupported component <{el.name}>. Refusing to drop it.")
    if el.name == "Page":
        if role != "root":
            raise MirrorError("nested Page is not supported")
        _reject_unknown_props(el.props, PAGE_PROPS, "Page")
        _require_str(el.props, "title", "Page", required=True)
        _require_str(el.props, "summary", "Page", required=False)
        if "width" in el.props and el.props["width"] not in WIDTHS:
            raise MirrorError(f"Page width {el.props['width']!r} is not supported")
        _require_str(el.props, "lang", "Page", required=False)
        if not el.children:
            raise MirrorError("Page has no children")
        for child in el.children:
            if isinstance(child, str):
                raise MirrorError("Page text child would need a block; refusing to drop it")
            if child.name not in PAGE_CHILD:
                raise MirrorError(f"Page cannot contain <{child.name}>")
            _walk(child, used, role="block")
        return
    if el.name == "Section":
        _reject_unknown_props(el.props, SECTION_PROPS, "Section")
        _require_str(el.props, "heading", "Section", required=False)
        _require_str(el.props, "caption", "Section", required=False)
        if "id" in el.props:
            anchor = el.props["id"]
            _require_str(el.props, "id", "Section", required=True)
            if not anchor.replace("-", "").replace("_", "").isalnum() or not anchor[0].isalpha():
                raise MirrorError(f"Section id {anchor!r} is not a plain anchor")
        if not el.children:
            raise MirrorError("Section has no children")
        for child in el.children:
            if isinstance(child, str):
                raise MirrorError("Section text must be a Text element; refusing to drop raw text")
            if child.name not in SECTION_CHILD:
                raise MirrorError(f"Section cannot contain <{child.name}>")
            _walk(child, used, role="block")
        return
    if el.name == "Text":
        _reject_unknown_props(el.props, TEXT_PROPS, "Text")
        if not el.children or any(not isinstance(child, str) for child in el.children):
            raise MirrorError("Text must contain only text")
        if not "".join(el.children).strip():
            raise MirrorError("Text is empty")
        return
    if el.name == "Callout":
        _reject_unknown_props(el.props, CALLOUT_PROPS, "Callout")
        _require_str(el.props, "lead", "Callout", required=False)
        if "tone" in el.props and el.props["tone"] not in CALLOUT_TONES:
            raise MirrorError(f"Callout tone {el.props['tone']!r} is not supported")
        texts: list[str] = []
        for child in el.children:
            if isinstance(child, str):
                texts.append(child)
                continue
            if isinstance(child, Element) and child.name == "Text":
                _walk(child, used, role="block")
                texts.append("x")
                continue
            raise MirrorError("Callout child is not text; refusing to drop it")
        if "lead" not in el.props and not any(part.strip() for part in texts):
            raise MirrorError("Callout has no content")
        return
    if el.name == "Rows":
        _reject_unknown_props(el.props, ROWS_PROPS, "Rows")
        if el.children:
            raise MirrorError("Rows children are not supported; put items in rows")
        rows = el.props.get("rows")
        if not isinstance(rows, list) or not rows:
            raise MirrorError("Rows is missing a non-empty rows array")
        for index, row in enumerate(rows, start=1):
            where = f"Rows item {index}"
            if not isinstance(row, dict):
                raise MirrorError(f"{where} must be an object")
            unknown = sorted(set(row) - ROW_KEYS)
            if unknown:
                raise MirrorError(f"{where} has unsupported field {unknown[0]!r}")
            _require_str(row, "title", where, required=True)
            for key in ("lead", "detail", "meta"):
                if key in row and (not isinstance(row[key], str)):
                    raise MirrorError(f"{where} field {key!r} must be a string")
            if "status" in row:
                _check_status(row["status"], where)
        return
    if el.name == "Table":
        _reject_unknown_props(el.props, TABLE_PROPS, "Table")
        if el.children:
            raise MirrorError("Table children are not supported; put values in rows")
        columns = el.props.get("columns")
        rows = el.props.get("rows")
        if not isinstance(columns, list) or not columns or not all(isinstance(col, str) for col in columns):
            raise MirrorError("Table columns must be a non-empty list of strings")
        if not isinstance(rows, list) or not rows:
            raise MirrorError("Table is missing a non-empty rows array")
        if "align" in el.props:
            align = el.props["align"]
            if not isinstance(align, list) or any(item not in ALIGNS for item in align):
                raise MirrorError("Table align contains an unsupported value")
        for rindex, row in enumerate(rows, start=1):
            if not isinstance(row, list) or not row:
                raise MirrorError(f"Table row {rindex} must be a non-empty list")
            for cell in row:
                _check_cell(cell, f"Table row {rindex}")
        return
    raise MirrorError(f"unsupported component <{el.name}>")


def validate_tree(names: list[str], root: Element) -> Element:
    unknown_imports = sorted(set(names) - ALLOWED_COMPONENTS)
    if unknown_imports:
        raise MirrorError(
            f"unsupported component import {unknown_imports[0]!r}. Refusing to drop it."
        )
    if root.name != "Page":
        raise MirrorError("root element must be Page")
    if root.props.get("title") != "Team Status":
        raise MirrorError(
            "page title is not 'Team Status'. Refusing an unknown target page."
        )
    used: set[str] = set()
    _walk(root, used, role="root")
    unused = sorted(set(names) - used)
    if unused:
        raise MirrorError(f"unused import {unused[0]!r} is not rendered")
    missing = sorted(used - set(names))
    if missing:
        raise MirrorError(f"component {missing[0]!r} is used but not imported")
    return root


def iter_strings(value) -> list[str]:
    found: list[str] = []

    def walk(node) -> None:
        if isinstance(node, str):
            found.append(node)
        elif isinstance(node, Element):
            for prop in node.props.values():
                walk(prop)
            for child in node.children:
                walk(child)
        elif isinstance(node, dict):
            for item in node.values():
                walk(item)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(value)
    return found

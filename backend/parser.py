from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum


class PrereqKind(StrEnum):
    PREREQ = "PREREQ"
    COREQ = "COREQ"
    RECOMMENDED = "RECOMMENDED"


@dataclass
class ParseResult:
    kind: PrereqKind
    groups: list[tuple[str, ...]] = field(default_factory=list)
    notes: str = ""
    confident: bool = True
    raw: str = ""


@dataclass
class Atom:
    code: str


@dataclass
class And:
    children: list[Node]


@dataclass
class Or:
    children: list[Node]


Node = Atom | And | Or


_COURSE_CODE_RE = re.compile(r"\b([A-Z]{2,5})\s+(\d+[A-Z]{0,3})\b")
_BARE_NUMBER_RE = re.compile(r"(?<![A-Za-z])(\d+[A-Z]{0,3})\b")
_COURSE_CODE_RE_LOOSE = re.compile(r"\b([A-Z]{2,5})\s+(\d+[A-Z]{0,3})\b", re.I)
_NON_DEPT_WORDS: frozenset[str] = frozenset(
    {"AND", "OR", "EITHER", "WITH", "FROM", "THE", "NOT", "MAY"}
)

_NOTE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"Students who have not completed listed prerequisites? may enroll[^.]*\.?",
            re.I,
        ),
        "may enroll with consent",
    ),
    (
        re.compile(r"Students may not receive credit for[^.]*\.?", re.I),
        "duplicate-credit notice",
    ),
    (
        re.compile(r"May not be (?:taken|received) for credit (?:after|if)[^.]*\.?", re.I),
        "duplicate-credit notice",
    ),
    (
        re.compile(r"\bRenumbered from [A-Z]{2,5}\s+\d+[A-Z]{0,3}\.?", re.I),
        "renumbered",
    ),
    (re.compile(r"\bconsent of instructor\b\.?", re.I), "consent of instructor"),
    (re.compile(r"\bconsent of (the )?department\b\.?", re.I), "consent of department"),
    (re.compile(r"\binstructor approval\b\.?", re.I), "instructor approval"),
    (re.compile(r"\bdepartment(al)? approval\b\.?", re.I), "department approval"),
    (re.compile(r"\bpermission of instructor\b\.?", re.I), "permission of instructor"),
)

_AP_SCORE_RE = (
    r"AP\s+(?:Calculus|Precalculus|Statistics|Physics|Chemistry|Biology)"
    r"(?:\s+[A-Z]{1,3})?"
    r"(?:\s+(?:score|subscore))?"
    r"(?:\s*\([^)]*\))?"
    r"(?:\s+of)?"
    r"\s+\d+"
    r"(?:\s*,\s*\d+)*"
    r"(?:\s*,?\s*or\s+(?:\d+|more|higher|above))?"
)
_SCORE_LIST_RE = (
    r"(?:a\s+)?(?:qualifying\s+)?(?:sub)?score"
    r"(?:\s*\([^)]*\))?"
    r"(?:\s+of)?"
    r"\s+\d+"
    r"(?:\s*,\s*\d+)*"
    r"(?:\s*,?\s*or\s+(?:\d+|more|higher|above))?"
)
_DROP_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"Math Placement Exam[^,;.]*", re.I),
    re.compile(_AP_SCORE_RE, re.I),
    re.compile(r"\(or\s+(?:its\s+)?equivalent[^)]*\)", re.I),
    re.compile(r"\bor\s+(?:its\s+)?equivalent(?:\s+experience)?\b", re.I),
    re.compile(_SCORE_LIST_RE, re.I),
    re.compile(r"\bwith a grade of[^,;.]*", re.I),
    re.compile(r"\bgrade of [a-d][+\-–]?(?: or better)?", re.I),
    re.compile(
        r"AP\s+(?:Calculus|Precalculus|Statistics|Physics|Chemistry|Biology)"
        r"(?:\s+[A-Z]{1,3})?",
        re.I,
    ),
    re.compile(r"\bor better\b", re.I),
    re.compile(r"\bhigher\b", re.I),
)


def _strip_notes(text: str) -> tuple[str, str]:
    notes: list[str] = []
    for pat, label in _NOTE_PATTERNS:
        if pat.search(text):
            notes.append(label)
            text = pat.sub("", text)
    return text, "; ".join(notes)


def _strip_drops(text: str) -> str:
    for pat in _DROP_PATTERNS:
        text = pat.sub("", text)
    while True:
        prev = text
        text = re.sub(r"\s*,\s*(?=,|\.|;|$)", "", text)
        text = re.sub(r"^\s*[,;]\s*", "", text)
        text = re.sub(r"^\s*(?:or|and)\b\s*", "", text, flags=re.I)
        text = re.sub(r"\s+(?:or|and)\s*(?=[.;]|$)", "", text, flags=re.I)
        text = re.sub(r"\s+", " ", text).strip()
        if text == prev:
            break
    return text


def _detect_kind(text: str) -> tuple[PrereqKind, str]:
    s = text.strip()
    if re.match(r"^Recommended preparation\s*:?\s*", s, re.I):
        return PrereqKind.RECOMMENDED, re.sub(
            r"^Recommended preparation\s*:?\s*", "", s, flags=re.I
        )
    if re.match(r"^Recommended\s*:?\s*", s, re.I) and "preparation" in s.lower()[:40]:
        return PrereqKind.RECOMMENDED, re.sub(r"^Recommended[^:]*:\s*", "", s, flags=re.I)
    if re.match(r"^(Corequisites?|Concurrent enrollment in|Concurrent registration)\s*:?\s*", s, re.I):
        return PrereqKind.COREQ, re.sub(
            r"^(Corequisites?|Concurrent enrollment in|Concurrent registration)\s*:?\s*",
            "",
            s,
            flags=re.I,
        )
    return PrereqKind.PREREQ, s


_EITHER_RE = re.compile(
    r"\beither\s+("
    r"[A-Z]{2,5}\s+\d+[A-Z]{0,3}"
    r"(?:\s+or\s+[A-Z]{2,5}\s+\d+[A-Z]{0,3})+"
    r")",
    re.I,
)
_SLASH_RE = re.compile(
    r"\b([A-Z]{2,5}\s+\d+[A-Z]{0,3})\s*/\s*([A-Z]{2,5}\s+\d+[A-Z]{0,3})",
    re.I,
)
_HYPHEN_SERIES_RE = re.compile(
    r"\b([A-Z]{2,5}\s+\d+)([A-Z])((?:-[A-Z])+)",
    re.I,
)
_AND_OR_CHAIN_RE = re.compile(
    r"\b([A-Z]{2,5}\s+\d+[A-Z]{0,3})"
    r"\s+and\s+"
    r"("
    r"[A-Z]{2,5}\s+\d+[A-Z]{0,3}"
    r"(?:\s+or\s+[A-Z]{2,5}\s+\d+[A-Z]{0,3})+"
    r")"
    r"(?=\s*[.;]|\s*$)",
    re.I,
)
_OR_AND_CHAIN_RE = re.compile(
    r"(^|[.;]\s*)"
    r"("
    r"[A-Z]{2,5}\s+\d+[A-Z]{0,3}"
    r"(?:\s+or\s+[A-Z]{2,5}\s+\d+[A-Z]{0,3}){2,}"
    r")"
    r"\s+and\s+",
    re.I,
)


def _wrap_and_or_chain(text: str) -> str:
    return _AND_OR_CHAIN_RE.sub(r"\1 and (\2)", text)


def _wrap_or_and_chain(text: str) -> str:
    return _OR_AND_CHAIN_RE.sub(r"\1(\2) and ", text)


def _expand_hyphen_series(text: str) -> str:
    def expand(m: re.Match[str]) -> str:
        prefix = m.group(1)
        first_letter = m.group(2)
        rest_letters = [letter for letter in m.group(3).split("-") if letter]
        letters = [first_letter, *rest_letters]
        return " and ".join(f"{prefix}{letter}" for letter in letters)

    return _HYPHEN_SERIES_RE.sub(expand, text)


def _wrap_grouping_hints(text: str) -> str:
    text = _expand_hyphen_series(text)
    text = _EITHER_RE.sub(r"(\1)", text)
    text = _SLASH_RE.sub(r"(\1 or \2)", text)
    text = _wrap_or_and_chain(text)
    text = _wrap_and_or_chain(text)
    return text


_BARE_NUMBER_TOKENIZER = re.compile(
    r"[A-Z]{2,5}\s+\d+[A-Z]{0,3}|\d+[A-Z]{0,3}|[^A-Z\d]+|."
)


def _normalize_course_codes(text: str) -> str:
    def _norm(m: re.Match[str]) -> str:
        dept = m.group(1).upper()
        if dept in _NON_DEPT_WORDS:
            return m.group(0)
        number = m.group(2).upper().lstrip("0")
        if not number or not number[0].isdigit():
            number = "0" + number
        return f"{dept} {number}"

    return _COURSE_CODE_RE_LOOSE.sub(_norm, text)


def _expand_bare_numbers(text: str) -> str:
    out: list[str] = []
    last_dept: str | None = None
    tokens = _BARE_NUMBER_TOKENIZER.findall(text)
    for tok in tokens:
        m = _COURSE_CODE_RE.fullmatch(tok)
        if m:
            last_dept = m.group(1)
            out.append(tok)
            continue
        bn = _BARE_NUMBER_RE.fullmatch(tok)
        if bn and last_dept:
            prev_blob = "".join(out[-3:]).rstrip().lower()
            if prev_blob.endswith((",", "or", "and", "(")):
                out.append(f"{last_dept} {tok}")
                continue
        out.append(tok)
    return "".join(out)


@dataclass
class _Tok:
    kind: str
    value: str = ""


def _tokenize(text: str) -> list[_Tok]:
    toks: list[_Tok] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch == "(":
            toks.append(_Tok("LPAREN"))
            i += 1
            continue
        if ch == ")":
            toks.append(_Tok("RPAREN"))
            i += 1
            continue
        if ch == ",":
            toks.append(_Tok("COMMA"))
            i += 1
            continue
        if ch == "/":
            toks.append(_Tok("OR"))
            i += 1
            continue
        m = _COURSE_CODE_RE.match(text, i)
        if m:
            code = f"{m.group(1).upper()} {m.group(2).upper()}"
            toks.append(_Tok("COURSE", code))
            i = m.end()
            continue
        rest_lower = text[i:].lower()
        if (rest_lower.startswith("and") and (len(rest_lower) == 3 or not rest_lower[3].isalpha())):
            toks.append(_Tok("AND"))
            i += 3
            continue
        if rest_lower.startswith("or") and (len(rest_lower) == 2 or not rest_lower[2].isalpha()):
            toks.append(_Tok("OR"))
            i += 2
            continue
        if rest_lower.startswith("either") and (len(rest_lower) == 6 or not rest_lower[6].isalpha()):
            i += 6
            continue
        i += 1
    return toks


def _resolve_commas(toks: list[_Tok]) -> list[_Tok]:
    collapsed: list[_Tok] = []
    for t in toks:
        if t.kind == "COMMA" and collapsed and collapsed[-1].kind == "COMMA":
            continue
        collapsed.append(t)
    toks = collapsed

    out: list[_Tok] = []
    i = 0
    while i < len(toks):
        t = toks[i]
        if t.kind == "COMMA" and i + 1 < len(toks) and toks[i + 1].kind in ("AND", "OR"):
            elevated = "TOP_AND" if toks[i + 1].kind == "AND" else "TOP_OR"
            out.append(_Tok(elevated))
            i += 2
            continue
        out.append(t)
        i += 1

    final: list[_Tok] = []
    for i, t in enumerate(out):
        if t.kind != "COMMA":
            final.append(t)
            continue

        prev_had_or = False
        depth_back = 0
        for j in range(i - 1, -1, -1):
            tj = out[j]
            if tj.kind == "RPAREN":
                depth_back += 1
            elif tj.kind == "LPAREN":
                depth_back -= 1
                if depth_back < 0:
                    break
            elif depth_back == 0:
                if tj.kind == "COMMA":
                    break
                if tj.kind in ("OR", "TOP_OR"):
                    prev_had_or = True
                    break
                if tj.kind in ("AND", "TOP_AND"):
                    break

        depth = 0
        next_conj: str | None = None
        for j in range(i + 1, len(out)):
            tj = out[j]
            if tj.kind == "LPAREN":
                depth += 1
            elif tj.kind == "RPAREN":
                depth -= 1
                if depth < 0:
                    break
            elif depth == 0 and tj.kind in ("AND", "OR", "TOP_AND", "TOP_OR"):
                next_conj = tj.kind
                break

        if prev_had_or and next_conj in ("OR", "TOP_OR"):
            final.append(_Tok("TOP_AND"))
        elif next_conj == "TOP_AND":
            final.append(_Tok("AND"))
        elif next_conj == "TOP_OR":
            final.append(_Tok("OR"))
        else:
            final.append(_Tok(next_conj or "AND"))
    return final


class _Parser:
    def __init__(self, toks: list[_Tok]) -> None:
        self.toks = toks
        self.i = 0

    def _peek(self) -> _Tok | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def _eat(self, kind: str) -> _Tok | None:
        t = self._peek()
        if t and t.kind == kind:
            self.i += 1
            return t
        return None

    def parse(self) -> Node | None:
        if not self.toks:
            return None
        return self._top_expr()

    def _top_expr(self) -> Node:
        left = self._or_expr()
        and_children: list[Node] = [left]
        or_children: list[Node] = [left]
        last_top: str | None = None
        while self._peek() and self._peek().kind in ("TOP_AND", "TOP_OR"):  # type: ignore[union-attr]
            t = self._peek()
            assert t is not None
            self.i += 1
            rhs = self._or_expr()
            if t.kind == "TOP_AND":
                if last_top == "TOP_OR":
                    and_children = [Or(or_children), rhs]
                    or_children = [And(and_children)]
                else:
                    and_children.append(rhs)
                    or_children = [And(and_children)]
            else:
                if last_top == "TOP_AND":
                    or_children = [And(and_children), rhs]
                    and_children = [Or(or_children)]
                else:
                    or_children.append(rhs)
                    and_children = [Or(or_children)]
            last_top = t.kind
        if last_top == "TOP_AND":
            return And(and_children) if len(and_children) > 1 else and_children[0]
        if last_top == "TOP_OR":
            return Or(or_children) if len(or_children) > 1 else or_children[0]
        return left

    def _or_expr(self) -> Node:
        left = self._and_expr()
        children: list[Node] = [left]
        while self._peek() and self._peek().kind == "OR":  # type: ignore[union-attr]
            self._eat("OR")
            children.append(self._and_expr())
        return Or(children) if len(children) > 1 else children[0]

    def _and_expr(self) -> Node:
        left = self._term()
        children: list[Node] = [left]
        while self._peek() and self._peek().kind == "AND":  # type: ignore[union-attr]
            self._eat("AND")
            children.append(self._term())
        return And(children) if len(children) > 1 else children[0]

    def _term(self) -> Node:
        t = self._peek()
        if t is None:
            return Atom("")
        if t.kind == "COURSE":
            self.i += 1
            return Atom(t.value)
        if t.kind == "LPAREN":
            self.i += 1
            node = self._top_expr()
            self._eat("RPAREN")
            return node
        if t.kind in ("AND", "OR", "TOP_AND", "TOP_OR", "COMMA", "RPAREN"):
            self.i += 1
            return Atom("")
        self.i += 1
        return Atom("")


def _to_dnf(node: Node | None) -> list[frozenset[str]]:
    if node is None:
        return []
    if isinstance(node, Atom):
        return [frozenset({node.code})] if node.code else []
    if isinstance(node, Or):
        result: list[frozenset[str]] = []
        for c in node.children:
            result.extend(_to_dnf(c))
        return result
    products: list[frozenset[str]] = [frozenset()]
    for c in node.children:
        c_dnf = _to_dnf(c)
        if not c_dnf:
            continue
        new_products: list[frozenset[str]] = []
        for p in products:
            for q in c_dnf:
                new_products.append(p | q)
        products = new_products
    return [p for p in products if p]


def _dedupe_groups(groups: list[frozenset[str]]) -> list[tuple[str, ...]]:
    seen: set[frozenset[str]] = set()
    ordered: list[tuple[str, ...]] = []
    for g in groups:
        if g in seen or not g:
            continue
        seen.add(g)
        ordered.append(tuple(sorted(g)))
    return ordered


def parse(text: str) -> ParseResult:
    raw = text or ""
    if not raw.strip():
        return ParseResult(kind=PrereqKind.PREREQ, raw=raw)

    kind, body = _detect_kind(raw)
    body = _normalize_course_codes(body)
    body, notes = _strip_notes(body)
    body = _strip_drops(body)
    body = _expand_bare_numbers(body)
    body = _wrap_grouping_hints(body)

    if not _COURSE_CODE_RE.search(body):
        return ParseResult(kind=kind, groups=[], notes=notes, confident=True, raw=raw)

    toks = _tokenize(body)
    toks = _resolve_commas(toks)
    ast = _Parser(toks).parse()
    dnf = _to_dnf(ast)
    groups = _dedupe_groups(dnf)

    extracted = {c for g in groups for c in g}
    found_in_text = {
        f"{m.group(1).upper()} {m.group(2).upper()}"
        for m in _COURSE_CODE_RE.finditer(body)
    }
    confident = bool(groups) and extracted == found_in_text

    return ParseResult(kind=kind, groups=groups, notes=notes, confident=confident, raw=raw)

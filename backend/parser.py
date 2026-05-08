"""Parse UCSD prerequisite prose into structured AND/OR groups.

The output schema mirrors the `prereqs` table:
    Within a `group_id`: AND (all required).
    Across `group_id`s for the same course: OR (any group satisfies).

A clean prereq string like:
    "MATH 20A and MATH 20B, or MATH 10A and MATH 10B"
parses to two groups:
    [{20A, 20B}, {10A, 10B}]

Strategy (rule-based, pragmatic):
  1. Detect type prefix: "Recommended preparation" / "Corequisite" / default Prerequisite.
  2. Strip non-blocking notes ("consent of instructor", etc.) into a separate notes string.
  3. Strip non-course atoms (Math Placement, AP scores, grade qualifiers).
  4. Expand bare course numbers using the most recent department prefix.
  5. Tokenize: COURSE | AND | OR | LPAREN | RPAREN | COMMA.
  6. Resolve commas: list-final conjunction ("and"/"or") propagates to all commas.
  7. Recursive-descent parse to an AST of And / Or / Atom nodes.
  8. DNF-expand to list of frozensets (each = one group).

If parsing leaves unconsumed content or yields zero groups for a non-empty string,
we set `confident=False` so callers can route to an LLM fallback.
"""

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
    # List of groups; each group is a sorted tuple of course codes (AND within).
    # Across groups: OR.
    groups: list[tuple[str, ...]] = field(default_factory=list)
    notes: str = ""
    confident: bool = True
    raw: str = ""


# ---------- AST -------------------------------------------------------------


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


# ---------- Preprocessing ---------------------------------------------------


# Course code regex. Case-sensitive: by the time it runs, `_normalize_course_codes`
# has uppercased every real course code in the body. Keeping it case-sensitive avoids
# false positives like "and 20C" where a 3-letter conjunction looks like a dept code.
_COURSE_CODE_RE = re.compile(r"\b([A-Z]{2,5})\s+(\d+[A-Z]{0,3})\b")
_BARE_NUMBER_RE = re.compile(r"(?<![A-Za-z])(\d+[A-Z]{0,3})\b")

# Loose, case-insensitive variant used only by `_normalize_course_codes` to find
# course codes regardless of the catalog's mixed case ("Math 20D"). The callback
# filters out matches whose "dept" is actually an English keyword.
_COURSE_CODE_RE_LOOSE = re.compile(r"\b([A-Z]{2,5})\s+(\d+[A-Z]{0,3})\b", re.I)
_NON_DEPT_WORDS: frozenset[str] = frozenset(
    {"AND", "OR", "EITHER", "WITH", "FROM", "THE", "NOT", "MAY"}
)

# Notes/non-blocking phrases. Stripped to the `notes` field.
_NOTE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"Students who have not completed listed prerequisites? may enroll[^.]*\.?",
            re.I,
        ),
        "may enroll with consent",
    ),
    # Duplicate-credit warnings — "Students may not receive credit for X and Y"
    # and "May not be taken for credit after X". These mention course codes but
    # are policy notes, not prereqs. Strip them so they don't pollute groups.
    (
        re.compile(
            r"Students may not receive credit for[^.]*\.?",
            re.I,
        ),
        "duplicate-credit notice",
    ),
    (
        re.compile(
            r"May not be (?:taken|received) for credit (?:after|if)[^.]*\.?",
            re.I,
        ),
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

# Non-course atoms removed entirely (placement exam, AP scores, "or equivalent").
# AP / score patterns swallow full "score of 3, 4, or 5" lists including the comma chain.
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
    r"(?:\s*\([^)]*\))?"  # tolerate "(or subscore)"
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
    # Catch any AP fragment that survives (e.g. "AP Calculus AB" without a score).
    re.compile(
        r"AP\s+(?:Calculus|Precalculus|Statistics|Physics|Chemistry|Biology)"
        r"(?:\s+[A-Z]{1,3})?",
        re.I,
    ),
    # Trailing fragments left after the above:
    re.compile(r"\bor better\b", re.I),
    re.compile(r"\bhigher\b", re.I),
)


def _strip_notes(text: str) -> tuple[str, str]:
    """Pull non-blocking phrases out of the prereq text into a `notes` string."""
    notes: list[str] = []
    for pat, label in _NOTE_PATTERNS:
        if pat.search(text):
            notes.append(label)
            text = pat.sub("", text)
    return text, "; ".join(notes)


def _strip_drops(text: str) -> str:
    for pat in _DROP_PATTERNS:
        text = pat.sub("", text)
    # Iteratively clean up dangling commas/conjunctions/whitespace until stable.
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
    """Strip leading 'Recommended preparation:' / 'Corequisite:' marker, return kind + body."""
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
# Hyphenated course series, e.g. 'PHYS 4A-B' or 'MATH 20A-B-C'. The catalog uses
# this shorthand to mean a hard AND of the listed series. Expand to explicit ANDs.
_HYPHEN_SERIES_RE = re.compile(
    r"\b([A-Z]{2,5}\s+\d+)([A-Z])((?:-[A-Z])+)",
    re.I,
)
# Catalog convention: 'X and Y or Z [or W ...]' at the end of a clause means
# 'X and (Y or Z [or W ...])'. Strict logical precedence (AND tighter than OR)
# would give '(X and Y) or Z' instead, which lets a student take just Z alone
# — almost never the prereq author's intent. We add explicit parens around
# the OR-chain when (a) the chain is preceded by exactly one AND and a course,
# and (b) the chain is at a clause boundary (period, semicolon, or end). The
# clause-boundary requirement avoids breaking 'X and Y or Z and W' which is
# genuinely '(X and Y) or (Z and W)'.
_AND_OR_CHAIN_RE = re.compile(
    r"\b([A-Z]{2,5}\s+\d+[A-Z]{0,3})"                # X
    r"\s+and\s+"
    r"("
    r"[A-Z]{2,5}\s+\d+[A-Z]{0,3}"                    # Y
    r"(?:\s+or\s+[A-Z]{2,5}\s+\d+[A-Z]{0,3})+"       # or Z [or W ...]
    r")"
    r"(?=\s*[.;]|\s*$)",                              # at clause end
    re.I,
)
# Mirror heuristic for the leading position: '... or X or Y or Z and W ...' at
# clause start means '(... or X or Y or Z) and W'. Require 2+ ORs (3+ courses)
# in the chain to avoid bad rewrites of single-OR patterns whose intent is
# genuinely ambiguous.
_OR_AND_CHAIN_RE = re.compile(
    r"(^|[.;]\s*)"                                    # clause start
    r"("
    r"[A-Z]{2,5}\s+\d+[A-Z]{0,3}"                     # X
    r"(?:\s+or\s+[A-Z]{2,5}\s+\d+[A-Z]{0,3}){2,}"    # 2+ 'or Z'
    r")"
    r"\s+and\s+",
    re.I,
)


def _wrap_and_or_chain(text: str) -> str:
    """Wrap trailing OR-chains so AND binds looser than the chain — matches
    catalog convention where the foundational prereq comes first and a list
    of acceptable alternatives for the second slot follows."""
    return _AND_OR_CHAIN_RE.sub(r"\1 and (\2)", text)


def _wrap_or_and_chain(text: str) -> str:
    """Mirror of _wrap_and_or_chain for leading OR-chains: '(X or Y or Z) and W'.
    Requires 3+ courses in the OR chain to be conservative."""
    return _OR_AND_CHAIN_RE.sub(r"\1(\2) and ", text)


def _expand_hyphen_series(text: str) -> str:
    """'PHYS 4A-B' -> 'PHYS 4A and PHYS 4B'; 'MATH 20A-B-C' -> 'MATH 20A and 20B and 20C'."""
    def expand(m: re.Match[str]) -> str:
        prefix = m.group(1)  # 'PHYS 4'
        first_letter = m.group(2)
        rest_letters = [letter for letter in m.group(3).split("-") if letter]
        letters = [first_letter, *rest_letters]
        return " and ".join(f"{prefix}{letter}" for letter in letters)

    return _HYPHEN_SERIES_RE.sub(expand, text)


def _wrap_grouping_hints(text: str) -> str:
    """Convert implicit groupings ('either', slash, hyphen series, trailing
    OR-chain) into explicit AND/OR.

    'either X or Y or Z'     -> '(X or Y or Z)'
    'X/Y'                    -> '(X or Y)'
    'PHYS 4A-B'              -> 'PHYS 4A and PHYS 4B'
    'X and Y or Z or W.'     -> 'X and (Y or Z or W).'

    This way the existing parser uses correct precedence without special cases.
    """
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
    """Uppercase the dept + number portion of every course code occurrence
    and strip leading zeros from the number ('MAE 08' -> 'MAE 8').

    Catalog text occasionally uses 'Math 20D' (lowercase dept). After this pass
    the tokenizer can stay case-sensitive without missing those — and we avoid
    case-insensitive course-code matching that would swallow 'and 20C'/'or 20D'
    (English conjunctions) as fake dept codes.

    The leading-zero strip mirrors what the scraper does to course codes in
    the courses table — MAE's course-name listing uses 'MAE 08' while prereq
    prose uses 'MAE 8'. Both must agree so the loader doesn't drop edges.
    """
    def _norm(m: re.Match[str]) -> str:
        dept = m.group(1).upper()
        if dept in _NON_DEPT_WORDS:
            return m.group(0)  # leave a non-dept match alone
        number = m.group(2).upper().lstrip("0")
        # Don't reduce "0" -> "" (no real course is just zero, but be safe).
        if not number or not number[0].isdigit():
            number = "0" + number
        return f"{dept} {number}"

    return _COURSE_CODE_RE_LOOSE.sub(_norm, text)


def _expand_bare_numbers(text: str) -> str:
    """Inside a span like 'MATH 20A, 20B, and 20C', prefix bare numbers with the most recent dept."""
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


# ---------- Tokenizer / parser ---------------------------------------------


@dataclass
class _Tok:
    kind: str  # COURSE | AND | OR | LPAREN | RPAREN | COMMA
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
        # Stray slash that survived `_wrap_grouping_hints` (e.g. between non-course tokens).
        if ch == "/":
            toks.append(_Tok("OR"))
            i += 1
            continue
        # Course code?
        m = _COURSE_CODE_RE.match(text, i)
        if m:
            code = f"{m.group(1).upper()} {m.group(2).upper()}"
            toks.append(_Tok("COURSE", code))
            i = m.end()
            continue
        # Word "and"/"or"/"either"? Match on word boundary.
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
            # "either" is a hint that what follows is OR-grouped, but for tokenization we drop it.
            i += 6
            continue
        # Skip unknown char (parser will mark non-confident if anything important is left).
        i += 1
    return toks


def _resolve_commas(toks: list[_Tok]) -> list[_Tok]:
    """Resolve COMMAs into operator tokens.

    Rules:
      * Adjacent COMMAs collapse to a single COMMA (handles malformed ", , and X").
      * COMMA followed immediately by AND/OR -> drop COMMA AND elevate the operator
        to TOP_AND/TOP_OR. This captures English scope-marking commas:
        "X or Y, and Z"  -> (X or Y) and Z   (TOP_AND binds looser than OR)
      * Bare COMMA (no immediate conjunction) -> look ahead at the next conjunction
        token and become its kind. If that conjunction is TOP_*, become regular
        AND/OR (Oxford comma list, no scope elevation needed).
    """
    # Pre-pass: collapse adjacent COMMAs.
    collapsed: list[_Tok] = []
    for t in toks:
        if t.kind == "COMMA" and collapsed and collapsed[-1].kind == "COMMA":
            continue
        collapsed.append(t)
    toks = collapsed

    out: list[_Tok] = []
    # First pass: drop ", and" / ", or" and elevate to TOP_*.
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

    # Second pass: bare COMMA -> next conjunction kind, mapped down from TOP_*.
    # If the surrounding clauses both contain OR (i.e. parallel OR-clauses
    # separated only by a comma, e.g. "A or B , C or D"), elevate the COMMA
    # to TOP_AND. The natural reading of that pattern is (A|B) AND (C|D).
    final: list[_Tok] = []
    for i, t in enumerate(out):
        if t.kind != "COMMA":
            final.append(t)
            continue

        # Look back: did the current clause contain OR?
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

        # Look forward: what's the next conjunction in the next clause?
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
            # Two parallel OR clauses joined by a bare comma -> AND.
            final.append(_Tok("TOP_AND"))
        elif next_conj == "TOP_AND":
            final.append(_Tok("AND"))
        elif next_conj == "TOP_OR":
            final.append(_Tok("OR"))
        else:
            final.append(_Tok(next_conj or "AND"))
    return final


class _Parser:
    """Recursive descent: expr := and_expr ("or" and_expr)*
                          and_expr := term ("and" term)*
                          term := COURSE | "(" expr ")"
    """

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
        """top := or_expr ((TOP_AND | TOP_OR) or_expr)*

        TOP_* binds looser than OR/AND. They model the comma-elevated
        conjunctions ("X or Y, and Z" -> (X or Y) and Z).
        """
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
                    # Mixed top-level: bind left associatively as encountered.
                    and_children = [Or(or_children), rhs]
                    or_children = [And(and_children)]
                else:
                    and_children.append(rhs)
                    or_children = [And(and_children)]
            else:  # TOP_OR
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
        # Stray operator at the start of a term position — emit empty atom but DO NOT
        # consume the token, so the parent expr loop can handle it. To prevent infinite
        # recursion the parent must check that progress is being made; we rely on the
        # parent loops only running when they see their own operator.
        if t.kind in ("AND", "OR", "TOP_AND", "TOP_OR", "COMMA", "RPAREN"):
            # Skip this token to make progress, return empty atom.
            self.i += 1
            return Atom("")
        self.i += 1
        return Atom("")


def _to_dnf(node: Node | None) -> list[frozenset[str]]:
    """Convert AST to disjunctive normal form: list of conjunction-sets."""
    if node is None:
        return []
    if isinstance(node, Atom):
        return [frozenset({node.code})] if node.code else []
    if isinstance(node, Or):
        result: list[frozenset[str]] = []
        for c in node.children:
            result.extend(_to_dnf(c))
        return result
    # And: cartesian product of children's DNFs (union sets)
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
    """Parse a prerequisite prose string into a structured `ParseResult`."""
    raw = text or ""
    if not raw.strip():
        return ParseResult(kind=PrereqKind.PREREQ, raw=raw)

    kind, body = _detect_kind(raw)
    # Normalize first so every later regex can be case-sensitive without missing
    # mixed-case catalog entries like "Math 20D".
    body = _normalize_course_codes(body)
    body, notes = _strip_notes(body)
    body = _strip_drops(body)
    # Expand bare numbers BEFORE grouping hints — the AND-OR-chain heuristic
    # needs to see fully-qualified course codes (e.g. 'ECON 1 and MATH 10C or
    # 20C or 31BH' must already read as 'ECON 1 and MATH 10C or MATH 20C or
    # MATH 31BH' for the OR chain to be detected).
    body = _expand_bare_numbers(body)
    body = _wrap_grouping_hints(body)

    # Quick check: any course codes survived?
    if not _COURSE_CODE_RE.search(body):
        # Could be a placement-exam-only prereq, or unrecognized prose.
        return ParseResult(kind=kind, groups=[], notes=notes, confident=True, raw=raw)

    toks = _tokenize(body)
    toks = _resolve_commas(toks)
    ast = _Parser(toks).parse()
    dnf = _to_dnf(ast)
    groups = _dedupe_groups(dnf)

    # Confidence: at least one group + no leftover course tokens missed.
    extracted = {c for g in groups for c in g}
    found_in_text = {
        f"{m.group(1).upper()} {m.group(2).upper()}"
        for m in _COURSE_CODE_RE.finditer(body)
    }
    confident = bool(groups) and extracted == found_in_text

    return ParseResult(kind=kind, groups=groups, notes=notes, confident=confident, raw=raw)

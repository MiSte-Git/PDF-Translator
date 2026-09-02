"""AND/OR/parenthesized boolean query matching for the document search
feature (02.09.2026, extended 02.09.2026).

History: originally (Michael: "Dann sollte im Suchfeld auch die
Möglichkeit einer ODER und UND Verknüpfung der Suchbegriffe bestehen.")
deliberately kept to exactly one operator per query - no mixing, no
parentheses/precedence (confirmed via AskUserQuestion, 02.09.2026).

Extended the same day when Michael actually needed more: "Ich habe jetzt
gerade doch den Fall von einer Kombinierten Suche die so aussehen würde
'StellarRussia ODER (The UND Korolev UND Directive)'. Aktuell werden nur
die 'StellarRussia' PDFs gefunden." - a real query that mixes both
operators, disambiguated with parentheses exactly like every other search
tool's boolean syntax. This module now parses a full, arbitrarily nested
AND/OR/parenthesis expression instead of only ever splitting on one
operator kind:

    expr     := or_expr
    or_expr  := and_expr (OR and_expr)*
    and_expr := atom (AND atom)*
    atom     := '(' expr ')' | TERM

Standard precedence applies when parentheses are omitted: AND binds
tighter than OR (e.g. "A UND B ODER C" == "(A UND B) ODER C"), matching
how most search tools (Lucene, Google, ...) treat unparenthesized mixed
queries - this is a strict improvement over the previous "degrades to a
flat OR, silently ignoring the AND part" fallback, not just an addition.

A query with unbalanced/misplaced parentheses or a dangling operator
never raises - matches_query() must never crash a folder scan just
because of an unusual query - it falls back to treating the ENTIRE typed
text as one literal substring, exactly this feature's original,
pre-02.09.2026 behavior for anything with no recognized operators.

Both German (UND/ODER) and English (AND/OR) keywords are recognized,
case-insensitively, so the app's own language toggle (ui/i18n.py) doesn't
also have to translate what the user types into a search field.

Shared between ui/merge_search.py (local scan) and ui/drive_search.py
(Google Drive scan), and both dialogs' PDF/DOCX callers - matching itself
has nothing PDF- or DOCX-specific about it, see ui/search_scopes.py for
where the per-format/per-scope extractor selection happens instead.
"""
from __future__ import annotations

import re

# \b (word boundary) keeps a term like "Sandra" from being split on the
# "and" it happens to contain - \bAND\b only matches "AND" surrounded by
# non-word characters (or string start/end), never mid-word. Parentheses
# and both operator keywords are tokenized in one pass so a term may still
# contain, say, a literal "(" only if it's never actually balanced/used as
# grouping - see _tokenize()'s fallback behavior below for that case.
_SPLIT_RE = re.compile(r"\(|\)|\b(?:UND|AND|ODER|OR)\b", re.IGNORECASE)
_AND_WORD_RE = re.compile(r"^(?:UND|AND)$", re.IGNORECASE)

# A node is either ("term", text) or ("and"/"or", [child, child, ...]).
QueryNode = tuple  # (str, Union[str, list["QueryNode"]]) - see module docstring's grammar.

_Token = tuple[str, str]  # (kind, text) - kind is one of TERM/AND/OR/LPAREN/RPAREN.


def _tokenize(query: str) -> list[_Token]:
    tokens: list[_Token] = []
    pos = 0
    for match in _SPLIT_RE.finditer(query):
        term = query[pos:match.start()].strip()
        if term:
            tokens.append(("TERM", term))
        raw = match.group()
        if raw == "(":
            tokens.append(("LPAREN", raw))
        elif raw == ")":
            tokens.append(("RPAREN", raw))
        elif _AND_WORD_RE.match(raw):
            tokens.append(("AND", raw))
        else:
            tokens.append(("OR", raw))
        pos = match.end()
    tail = query[pos:].strip()
    if tail:
        tokens.append(("TERM", tail))
    return tokens


class _ParseError(ValueError):
    """Internal only - always caught by parse_query(), never escapes it."""


class _Parser:
    def __init__(self, tokens: list[_Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    def _peek(self) -> _Token | None:
        return self._tokens[self._pos] if self._pos < len(self._tokens) else None

    def _advance(self) -> _Token:
        token = self._tokens[self._pos]
        self._pos += 1
        return token

    def parse(self) -> QueryNode:
        node = self._or_expr()
        if self._peek() is not None:
            raise _ParseError(f"unexpected trailing token: {self._peek()}")
        return node

    def _or_expr(self) -> QueryNode:
        children = [self._and_expr()]
        while self._peek() is not None and self._peek()[0] == "OR":
            self._advance()
            children.append(self._and_expr())
        return children[0] if len(children) == 1 else ("or", children)

    def _and_expr(self) -> QueryNode:
        children = [self._atom()]
        while self._peek() is not None and self._peek()[0] == "AND":
            self._advance()
            children.append(self._atom())
        return children[0] if len(children) == 1 else ("and", children)

    def _atom(self) -> QueryNode:
        token = self._peek()
        if token is None:
            raise _ParseError("unexpected end of query")
        kind, text = token
        if kind == "LPAREN":
            self._advance()
            node = self._or_expr()
            closing = self._peek()
            if closing is None or closing[0] != "RPAREN":
                raise _ParseError("missing closing parenthesis")
            self._advance()
            return node
        if kind == "TERM":
            self._advance()
            return ("term", text)
        raise _ParseError(f"unexpected token: {text}")


def parse_query(query: str) -> QueryNode | None:
    """Parses `query` into a QueryNode tree, or None for an empty/
    whitespace-only query (meaning "match everything" - see
    matches_query()). Never raises: a malformed boolean expression (a
    stray/unbalanced parenthesis, an operator with nothing on one side,
    ...) falls back to a single ("term", query) node - the whole typed
    text as one literal substring, exactly like a query with no
    recognized operators has always behaved.
    """
    query = (query or "").strip()
    if not query:
        return None
    tokens = _tokenize(query)
    if not tokens:
        return None
    try:
        return _Parser(tokens).parse()
    except _ParseError:
        return ("term", query)


def _evaluate(node: QueryNode, haystack: str) -> bool:
    kind, payload = node
    if kind == "term":
        return payload.lower() in haystack
    children: list[QueryNode] = payload
    if kind == "and":
        return all(_evaluate(child, haystack) for child in children)
    return any(_evaluate(child, haystack) for child in children)  # "or"


def matches_query(text: str | None, query: str) -> bool:
    """Whether `text` matches `query`, per parse_query()'s grammar -
    nested AND/OR/parentheses, each leaf term a case-insensitive substring
    check (the same primitive this feature always used, just now
    possibly combined into a tree instead of a single flat pass).

    `text=None` (nothing extractable for the file/selected scope(s), e.g.
    a non-ICO document with "ICO Format" as the only checked scope) never
    matches a real query. An empty/whitespace-only `query` matches
    unconditionally - both find_matching() and find_drive_matching()
    already special-case an empty query as "list everything" before an
    extractor is even called, but this function agrees with that
    convention for any other caller too.
    """
    node = parse_query(query)
    if node is None:
        return True
    if text is None:
        return False
    return _evaluate(node, text.lower())

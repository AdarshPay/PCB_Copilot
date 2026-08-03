"""Lossless KiCad S-expression AST parsing.

Days 3–5 will implement full `.kicad_sch` parsing. This module defines the
public surface and a minimal recursive descent placeholder.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SExprNode:
    """Node in a lossless S-expression AST."""

    head: str | None = None
    children: list[Any] = field(default_factory=list)
    atom: str | None = None

    @property
    def is_atom(self) -> bool:
        return self.atom is not None


class ParseError(ValueError):
    pass


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch in "()":
            tokens.append(ch)
            i += 1
            continue
        if ch == '"':
            i += 1
            start = i
            while i < n and text[i] != '"':
                if text[i] == "\\" and i + 1 < n:
                    i += 2
                    continue
                i += 1
            if i >= n:
                raise ParseError("Unterminated string literal")
            tokens.append('"' + text[start:i] + '"')
            i += 1
            continue
        start = i
        while i < n and not text[i].isspace() and text[i] not in "()":
            i += 1
        tokens.append(text[start:i])
    return tokens


def _parse_tokens(tokens: list[str], index: int = 0) -> tuple[SExprNode, int]:
    if index >= len(tokens):
        raise ParseError("Unexpected end of input")
    tok = tokens[index]
    if tok == "(":
        index += 1
        if index >= len(tokens):
            raise ParseError("Unterminated list")
        head_tok = tokens[index]
        if head_tok in "()":
            raise ParseError("Expected list head symbol")
        head = head_tok.strip('"')
        index += 1
        children: list[Any] = []
        while index < len(tokens) and tokens[index] != ")":
            if tokens[index] == "(":
                child, index = _parse_tokens(tokens, index)
                children.append(child)
            else:
                atom = tokens[index]
                if atom.startswith('"') and atom.endswith('"'):
                    children.append(SExprNode(atom=atom[1:-1]))
                else:
                    children.append(SExprNode(atom=atom))
                index += 1
        if index >= len(tokens) or tokens[index] != ")":
            raise ParseError("Unterminated list")
        return SExprNode(head=head, children=children), index + 1
    raise ParseError(f"Expected '(', got {tok!r}")


def parse_schematic_sexpr(source: str | Path) -> SExprNode:
    """Parse a KiCad S-expression document into a lossless AST."""
    text = Path(source).read_text(encoding="utf-8") if isinstance(source, Path) else source
    tokens = tokenize(text)
    node, index = _parse_tokens(tokens, 0)
    if index != len(tokens):
        raise ParseError("Trailing tokens after root expression")
    return node

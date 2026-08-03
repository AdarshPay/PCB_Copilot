"""Lossless KiCad S-expression AST parsing and serialization."""

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

    def find(self, head: str) -> SExprNode | None:
        for child in self.children:
            if isinstance(child, SExprNode) and child.head == head:
                return child
        return None

    def find_all(self, head: str) -> list[SExprNode]:
        return [
            child
            for child in self.children
            if isinstance(child, SExprNode) and child.head == head
        ]

    def atom_at(self, index: int = 0) -> str | None:
        if index < 0 or index >= len(self.children):
            return None
        child = self.children[index]
        if isinstance(child, SExprNode) and child.is_atom:
            return child.atom
        return None


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
            buf: list[str] = []
            while i < n and text[i] != '"':
                if text[i] == "\\" and i + 1 < n:
                    buf.append(text[i + 1])
                    i += 2
                    continue
                buf.append(text[i])
                i += 1
            if i >= n:
                raise ParseError("Unterminated string literal")
            tokens.append('"' + "".join(buf) + '"')
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
        if head_tok.startswith('"') and head_tok.endswith('"'):
            head = head_tok[1:-1]
        else:
            head = head_tok
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
    if not tokens:
        raise ParseError("Empty input")
    node, index = _parse_tokens(tokens, 0)
    if index != len(tokens):
        raise ParseError("Trailing tokens after root expression")
    return node


def _needs_quotes(atom: str) -> bool:
    if atom == "":
        return True
    if any(ch.isspace() for ch in atom):
        return True
    if any(ch in atom for ch in "()\"'\\"):
        return True
    # Preserve numeric / identifier atoms unquoted when safe.
    return False


def _escape_atom(atom: str) -> str:
    return atom.replace("\\", "\\\\").replace('"', '\\"')


def serialize_sexpr(node: SExprNode, *, indent: int = 0) -> str:
    """Serialize an AST node to a KiCad-style S-expression string."""
    if node.is_atom:
        assert node.atom is not None
        if _needs_quotes(node.atom):
            return f'"{_escape_atom(node.atom)}"'
        return node.atom

    assert node.head is not None
    pad = "  " * indent
    inner_pad = "  " * (indent + 1)
    if not node.children:
        return f"({node.head})"

    # Compact single-line form for shallow scalar lists.
    if all(isinstance(c, SExprNode) and c.is_atom for c in node.children) and len(node.children) <= 4:
        parts = [serialize_sexpr(c) for c in node.children]
        return f"({node.head} {' '.join(parts)})"

    lines = [f"({node.head}"]
    for child in node.children:
        if isinstance(child, SExprNode):
            child_text = serialize_sexpr(child, indent=indent + 1)
            for line in child_text.splitlines() or [child_text]:
                lines.append(f"{inner_pad}{line}" if indent >= 0 else line)
        else:
            lines.append(f"{inner_pad}{child}")
    lines.append(f"{pad})")
    return "\n".join(lines)


def dump_schematic_sexpr(node: SExprNode, destination: Path | None = None) -> str:
    """Serialize a root AST; optionally write UTF-8 text to disk."""
    text = serialize_sexpr(node) + "\n"
    if destination is not None:
        destination.write_text(text, encoding="utf-8")
    return text

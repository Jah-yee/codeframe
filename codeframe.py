#!/usr/bin/env python3
"""
codeframe — Beautiful code screenshots from your terminal.

Usage:
    codeframe input.py -o output.svg
    codeframe input.js --theme dracula -o output.svg
    cat code.py | codeframe --lang python -o output.svg
"""

import argparse
import html as html_mod
import os
import sys

try:
    from pygments import lex
    from pygments.lexers import get_lexer_for_filename, get_lexer_by_name, TextLexer
    from pygments.token import Token
    HAS_PYGMENTS = True
except ImportError:
    HAS_PYGMENTS = False

__version__ = "0.1.0"

# ---
# 5

# ═══════════════════════════════════════════════════════════════
# THEMES
# ═══════════════════════════════════════════════════════════════

THEMES = {
    "github-dark": {
        "bg": "#0d1117", "fg": "#e6edf3", "chrome": "#161b22",
        "border": "#30363d", "gutter": "#484f58", "title": "#8b949e",
        "kw": "#ff7b72", "str": "#a5d6ff", "cmt": "#8b949e",
        "fn": "#d2a8ff", "num": "#79c0ff", "cls": "#f0883e",
        "dec": "#d2a8ff", "op": "#ff7b72", "bi": "#ffa657",
        "dots": ("#ff5f57", "#febc2e", "#28c840"),
    },
    "one-dark": {
        "bg": "#282c34", "fg": "#abb2bf", "chrome": "#21252b",
        "border": "#3e4451", "gutter": "#495162", "title": "#636d83",
        "kw": "#c678dd", "str": "#98c379", "cmt": "#5c6370",
        "fn": "#61afef", "num": "#d19a66", "cls": "#e5c07b",
        "dec": "#c678dd", "op": "#56b6c2", "bi": "#e5c07b",
        "dots": ("#ff5f57", "#febc2e", "#28c840"),
    },
    "dracula": {
        "bg": "#282a36", "fg": "#f8f8f2", "chrome": "#21222c",
        "border": "#44475a", "gutter": "#6272a4", "title": "#6272a4",
        "kw": "#ff79c6", "str": "#f1fa8c", "cmt": "#6272a4",
        "fn": "#50fa7b", "num": "#bd93f9", "cls": "#ffb86c",
        "dec": "#50fa7b", "op": "#ff79c6", "bi": "#8be9fd",
        "dots": ("#ff5555", "#f1fa8c", "#50fa7b"),
    },
    "nord": {
        "bg": "#2e3440", "fg": "#d8dee9", "chrome": "#272c36",
        "border": "#3b4252", "gutter": "#4c566a", "title": "#616e88",
        "kw": "#81a1c1", "str": "#a3be8c", "cmt": "#616e88",
        "fn": "#88c0d0", "num": "#b48ead", "cls": "#ebcb8b",
        "dec": "#b48ead", "op": "#81a1c1", "bi": "#8fbcbb",
        "dots": ("#bf616a", "#ebcb8b", "#a3be8c"),
    },
    "github-light": {
        "bg": "#ffffff", "fg": "#1f2328", "chrome": "#f6f8fa",
        "border": "#d0d7de", "gutter": "#afb8c1", "title": "#656d76",
        "kw": "#cf222e", "str": "#0a3069", "cmt": "#6e7781",
        "fn": "#8250df", "num": "#0550ae", "cls": "#953800",
        "dec": "#8250df", "op": "#cf222e", "bi": "#953800",
        "dots": ("#ff5f57", "#febc2e", "#28c840"),
    },
}


# ═══════════════════════════════════════════════════════════════
# TOKEN MAPPING
# ═══════════════════════════════════════════════════════════════

def token_color(tok_type, theme):
    """Map Pygments token type to theme color."""
    T = Token
    checks = [
        ([T.Keyword, T.Keyword.Namespace, T.Keyword.Constant, T.Keyword.Declaration], "kw"),
        ([T.Keyword.Type], "bi"),
        ([T.Name.Function, T.Name.Function.Magic], "fn"),
        ([T.Name.Class], "cls"),
        ([T.Name.Decorator], "dec"),
        ([T.Name.Builtin, T.Name.Builtin.Pseudo], "bi"),
        ([T.Literal.String, T.Literal.String.Doc, T.Literal.String.Single,
          T.Literal.String.Double, T.Literal.String.Backtick,
          T.Literal.String.Interpol, T.Literal.String.Regex], "str"),
        ([T.Literal.String.Affix, T.Literal.String.Escape], "kw"),
        ([T.Literal.Number, T.Literal.Number.Integer, T.Literal.Number.Float,
          T.Literal.Number.Hex, T.Literal.Number.Oct], "num"),
        ([T.Comment, T.Comment.Single, T.Comment.Multiline, T.Comment.Hashbang,
          T.Comment.Special], "cmt"),
        ([T.Operator, T.Punctuation], "op"),
        ([T.Operator.Word], "kw"),
    ]
    for types, key in checks:
        if tok_type in types:
            return theme[key]
    # Walk up the token hierarchy
    for types, key in checks:
        for t in types:
            if tok_type is t or str(tok_type).startswith(str(t)):
                return theme[key]
    return theme["fg"]


# ═══════════════════════════════════════════════════════════════
# SVG RENDERING
# ═══════════════════════════════════════════════════════════════

MONO = "'SF Mono','Cascadia Code','JetBrains Mono','Fira Code',Consolas,monospace"
FONT_SIZE = 14
LINE_H = 22
CHAR_W = 8.4
PAD_X = 24
PAD_Y = 16
CHROME_H = 40
GUTTER_W = 44


def escape_xml(text):
    return html_mod.escape(text)


def render(code, filename="untitled", theme_name="github-dark", show_lines=True):
    """Render code string to SVG."""
    theme = THEMES.get(theme_name, THEMES["github-dark"])
    code = code.expandtabs(4).rstrip("\n")
    lines = code.split("\n")
    n_lines = len(lines)
    max_len = max((len(l) for l in lines), default=0)

    gutter = GUTTER_W if show_lines else 0
    code_x = PAD_X + gutter
    width = max(int(code_x + max_len * CHAR_W + PAD_X + 16), 480)
    width = min(width, 920)
    height = int(CHROME_H + PAD_Y + n_lines * LINE_H + PAD_Y)

    # Tokenize
    tokens_by_line = [[] for _ in range(n_lines)]
    if HAS_PYGMENTS:
        try:
            lexer = get_lexer_for_filename(filename, stripall=True)
        except Exception:
            try:
                ext = filename.rsplit(".", 1)[-1] if "." in filename else "text"
                lexer = get_lexer_by_name(ext, stripall=True)
            except Exception:
                lexer = TextLexer()
        line_idx = 0
        for tok_type, tok_value in lex(code, lexer):
            parts = tok_value.split("\n")
            for pi, part in enumerate(parts):
                if pi > 0:
                    line_idx += 1
                if line_idx < n_lines and part:
                    color = token_color(tok_type, theme)
                    tokens_by_line[line_idx].append((part, color))
    else:
        for i, line in enumerate(lines):
            tokens_by_line[i] = [(line, theme["fg"])]

    # Build SVG
    s = []
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" fill="none">')
    s.append(f'  <style>.m{{font-family:{MONO};font-size:{FONT_SIZE}px;white-space:pre}}</style>')

    # Shadow (simulated with offset rect)
    s.append(f'  <rect fill="#00000033" x="4" y="4" width="{width}" height="{height}" rx="10"/>')

    # Main background
    s.append(f'  <rect fill="{theme["bg"]}" width="{width}" height="{height}" rx="10"/>')

    # Chrome bar
    s.append(f'  <rect fill="{theme["chrome"]}" width="{width}" height="{CHROME_H}" rx="10"/>')
    s.append(f'  <rect fill="{theme["chrome"]}" y="10" width="{width}" height="{CHROME_H - 10}"/>')

    # Traffic light dots
    dc, dm, dx = theme["dots"]
    s.append(f'  <circle fill="{dc}" cx="{PAD_X}" cy="20" r="6"/>')
    s.append(f'  <circle fill="{dm}" cx="{PAD_X + 22}" cy="20" r="6"/>')
    s.append(f'  <circle fill="{dx}" cx="{PAD_X + 44}" cy="20" r="6"/>')

    # Filename
    s.append(f'  <text class="m" fill="{theme["title"]}" x="{width // 2}" y="25" text-anchor="middle" font-size="12">{escape_xml(filename)}</text>')

    # Chrome/code border
    s.append(f'  <line x1="0" y1="{CHROME_H}" x2="{width}" y2="{CHROME_H}" stroke="{theme["border"]}" stroke-width="1"/>')

    # Code lines
    for i in range(n_lines):
        y = CHROME_H + PAD_Y + (i + 1) * LINE_H - 5

        # Line numbers
        if show_lines:
            s.append(f'  <text class="m" fill="{theme["gutter"]}" x="{PAD_X + gutter - 10}" y="{y}" text-anchor="end" font-size="13">{i + 1}</text>')

        # Tokens
        if tokens_by_line[i]:
            tspans = []
            for text, color in tokens_by_line[i]:
                esc = escape_xml(text)
                if color == theme["fg"]:
                    tspans.append(esc)
                else:
                    tspans.append(f'<tspan fill="{color}">{esc}</tspan>')
            joined = "".join(tspans)
            s.append(f'  <text class="m" fill="{theme["fg"]}" x="{code_x}" y="{y}" xml:space="preserve">{joined}</text>')

    s.append("</svg>")
    return "\n".join(s)


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    p = argparse.ArgumentParser(
        description="codeframe — Beautiful code screenshots from your terminal.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  codeframe hello.py -o hello.svg\n"
               "  codeframe app.js --theme dracula -o app.svg\n"
               "  cat main.rs | codeframe --lang rust -o main.svg\n",
    )
    p.add_argument("input", nargs="?", help="Input source file")
    p.add_argument("-o", "--output", default="-", help="Output SVG file (default: stdout)")
    p.add_argument("-t", "--theme", default="github-dark", choices=list(THEMES.keys()),
                   help="Color theme (default: github-dark)")
    p.add_argument("-l", "--lang", help="Language hint (for stdin input)")
    p.add_argument("--no-lines", action="store_true", help="Hide line numbers")
    p.add_argument("--list-themes", action="store_true", help="List available themes")
    p.add_argument("--version", action="version", version=f"codeframe {__version__}")
    args = p.parse_args()

    if args.list_themes:
        for name in THEMES:
            print(f"  {name}")
        return

    if args.input:
        with open(args.input) as f:
            code = f.read()
        filename = os.path.basename(args.input)
    elif not sys.stdin.isatty():
        code = sys.stdin.read()
        filename = f"stdin.{args.lang}" if args.lang else "untitled"
    else:
        p.print_help()
        sys.exit(1)

    svg = render(code, filename=filename, theme_name=args.theme, show_lines=not args.no_lines)

    if args.output == "-":
        sys.stdout.write(svg)
    else:
        with open(args.output, "w") as f:
            f.write(svg)
        print(f"✓ {args.output} ({len(svg):,} bytes)", file=sys.stderr)


if __name__ == "__main__":
    main()

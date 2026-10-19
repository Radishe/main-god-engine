"""Extract full conversation text from a saved DeepSeek chat HTML export.

The saved page is a rendered DOM: each turn lives in a container carrying
`data-virtual-list-item-key="N"`. User turns hold their text in a plain
<span>; assistant turns contain one or more `ds-markdown` blocks (THINK,
TOOL_SEARCH, RESPONSE) plus the main answer marked
`ds-assistant-message-main-content`.
"""

import html
import re
import sys
from pathlib import Path

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "DeepSeek - 探索未至之境.html")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "_chat_full.txt")


def strip_tags(fragment: str) -> str:
    """Turn an HTML fragment into readable text."""
    # Preserve block structure before dropping tags.
    s = fragment
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</(p|div|li|h[1-6]|tr|blockquote)>", "\n", s)
    s = re.sub(r"(?i)</t[dh]>", " | ", s)
    s = re.sub(r"(?i)<li[^>]*>", "- ", s)
    s = re.sub(r"(?i)<h([1-6])[^>]*>", lambda m: "\n" + "#" * int(m.group(1)) + " ", s)
    # Drop scripts/styles entirely.
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = s.replace("\u00a0", " ")
    # Drop the per-code-block UI chrome ("text" / 复制 / 下载 buttons).
    s = re.sub(r"(?m)^\s*(text|复制|下载)\s*$\n?", "", s)
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def balanced_div(html_text: str, start: int) -> str:
    """Return the inner HTML of the <div> whose '<div' begins at `start`."""
    depth = 0
    i = start
    while i < len(html_text):
        nxt = html_text.find("<div", i)
        close = html_text.find("</div>", i)
        if close == -1:
            break
        if nxt != -1 and nxt < close:
            depth += 1
            i = nxt + 4
        else:
            depth -= 1
            i = close + 6
            if depth == 0:
                return html_text[start:i]
    return html_text[start:]


def main() -> None:
    raw = SRC.read_text(encoding="utf-8")

    # Split the transcript into per-turn chunks.
    keys = list(re.finditer(r'data-virtual-list-item-key="(\d+)"', raw))
    chunks = []
    for idx, m in enumerate(keys):
        end = keys[idx + 1].start() if idx + 1 < len(keys) else len(raw)
        chunks.append((int(m.group(1)), raw[m.end():end]))

    out = []
    for key, chunk in sorted(chunks):
        # Assistant answers carry this marker; user turns do not.
        is_assistant = "ds-assistant-message-main-content" in chunk

        if not is_assistant:
            # User text: first non-empty span inside the collapsible block.
            body = ""
            m = re.search(r'<div class="ds-collapsible-text".*?</div>', chunk, re.S)
            if m:
                body = strip_tags(m.group(0))
            if not body:
                body = strip_tags(chunk)
            out.append(f"===== [turn {key}] USER =====\n{body}\n")
            continue

        # Assistant: collect the main answer block(s).
        answers = []
        for m in re.finditer(r'class="ds-markdown ds-assistant-message-main-content"', chunk):
            # Back up to the opening '<div' of this block.
            start = chunk.rfind("<div", 0, m.start())
            if start == -1:
                continue
            answers.append(strip_tags(balanced_div(chunk, start)))
        if not answers:
            # Fallback: any ds-markdown block that is not think/search content.
            for m in re.finditer(r'class="ds-markdown"', chunk):
                start = chunk.rfind("<div", 0, m.start())
                if start == -1:
                    continue
                block = balanced_div(chunk, start)
                if "ds-think-content" in chunk[max(0, start - 400):start]:
                    continue
                answers.append(strip_tags(block))
        body = "\n\n".join(a for a in answers if a.strip())
        out.append(f"===== [turn {key}] ASSISTANT =====\n{body}\n")

    text = "\n".join(out)
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"[OK] turns={len(chunks)} chars={len(text)} -> {OUT}")
    print(f"     user turns={sum(1 for o in out if 'USER =====' in o)} "
          f"assistant turns={sum(1 for o in out if 'ASSISTANT =====' in o)}")


if __name__ == "__main__":
    main()
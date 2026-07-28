"""Minimal .po → .mo compiler (no gettext tooling required)."""

from __future__ import annotations

import struct
from pathlib import Path


def parse_po(text: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    msgid: str | None = None
    msgstr: str | None = None
    mode: str | None = None

    def flush() -> None:
        nonlocal msgid, msgstr
        # Keep the empty msgid header (charset metadata) and normal entries.
        if msgid is not None and msgstr is not None:
            entries.append((msgid, msgstr))
        msgid = None
        msgstr = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("msgid "):
            flush()
            mode = "id"
            msgid = _unquote(line[6:].strip())
            msgstr = None
        elif line.startswith("msgstr "):
            mode = "str"
            msgstr = _unquote(line[7:].strip())
        elif line.startswith('"') and mode:
            frag = _unquote(line)
            if mode == "id":
                msgid = (msgid or "") + frag
            else:
                msgstr = (msgstr or "") + frag
    flush()
    return entries


def _unquote(value: str) -> str:
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    return (
        value.replace("\\n", "\n")
        .replace('\\"', '"')
        .replace("\\\\", "\\")
    )


def write_mo(entries: list[tuple[str, str]], dest: Path) -> None:
    ids = b"\x00".join(msgid.encode("utf-8") for msgid, _ in entries) + b"\x00"
    strs = b"\x00".join(msgstr.encode("utf-8") for _, msgstr in entries) + b"\x00"
    keystart = 7 * 4 + 16 * len(entries)
    valuestart = keystart + len(ids)

    koffsets: list[tuple[int, int]] = []
    offset = 0
    for msgid, _ in entries:
        raw = msgid.encode("utf-8")
        koffsets.append((len(raw), keystart + offset))
        offset += len(raw) + 1

    voffsets: list[tuple[int, int]] = []
    offset = 0
    for _, msgstr in entries:
        raw = msgstr.encode("utf-8")
        voffsets.append((len(raw), valuestart + offset))
        offset += len(raw) + 1

    output = struct.pack(
        "Iiiiiii",
        0x950412DE,
        0,
        len(entries),
        7 * 4,
        7 * 4 + 8 * len(entries),
        0,
        keystart,
    )
    for length, off in koffsets:
        output += struct.pack("ii", length, off)
    for length, off in voffsets:
        output += struct.pack("ii", length, off)
    output += ids + strs
    dest.write_bytes(output)


def main() -> None:
    po_path = Path(__file__).with_name("th") / "LC_MESSAGES" / "django.po"
    mo_path = po_path.with_suffix(".mo")
    entries = parse_po(po_path.read_text(encoding="utf-8"))
    write_mo(entries, mo_path)
    print(f"Wrote {mo_path} ({len(entries)} entries)")


if __name__ == "__main__":
    main()

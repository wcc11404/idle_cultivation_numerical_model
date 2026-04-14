import re
from pathlib import Path
from typing import Dict


def save_realms_numeric_fields_preserve_format(path: Path, old_data: Dict, new_data: Dict) -> None:
    text = path.read_text(encoding="utf-8")
    updated_text = _update_realms_section_text(
        text=text,
        realm_order=old_data["realm_order"],
        old_realms=old_data["realms"],
        new_realms=new_data["realms"],
    )
    path.write_text(updated_text, encoding="utf-8")


def _update_realms_section_text(text: str, realm_order: list[str], old_realms: Dict, new_realms: Dict) -> str:
    realms_key = '"realms": {'
    start = text.find(realms_key)
    if start == -1:
        raise ValueError("realms section not found")

    brace_start = text.find("{", start)
    brace_end = _find_matching_brace(text, brace_start)

    prefix = text[: brace_start + 1]
    realms_body = text[brace_start + 1 : brace_end]
    suffix = text[brace_end:]

    updated_body = realms_body
    cursor = 0
    for realm_name in realm_order:
        old_levels = old_realms[realm_name]["levels"]
        new_levels = new_realms[realm_name]["levels"]

        realm_pattern = re.compile(rf'"{re.escape(realm_name)}"\s*:\s*\{{')
        match = realm_pattern.search(updated_body, cursor)
        if not match:
            raise ValueError(f"realm block not found: {realm_name}")

        block_brace_start = match.end() - 1
        block_brace_end = _find_matching_brace(updated_body, block_brace_start)
        block_text = updated_body[block_brace_start : block_brace_end + 1]
        replaced_block = _replace_level_numbers(block_text, old_levels, new_levels)

        updated_body = (
            updated_body[:block_brace_start] + replaced_block + updated_body[block_brace_end + 1 :]
        )
        cursor = block_brace_start + len(replaced_block)

    return prefix + updated_body + suffix


def _replace_level_numbers(block_text: str, old_levels: Dict, new_levels: Dict) -> str:
    result = block_text
    for level in sorted(old_levels.keys(), key=int):
        old_cost = int(old_levels[level]["spirit_energy_cost"])
        old_max = int(old_levels[level]["max_spirit_energy"])
        new_cost = int(new_levels[level]["spirit_energy_cost"])
        new_max = int(new_levels[level]["max_spirit_energy"])

        pattern = re.compile(
            rf'("{re.escape(level)}"\s*:\s*\{{[^{{}}]*?"spirit_energy_cost"\s*:\s*){old_cost}'
            rf'([^{{}}]*?"max_spirit_energy"\s*:\s*){old_max}'
        )

        def _repl(m: re.Match) -> str:
            return f"{m.group(1)}{new_cost}{m.group(2)}{new_max}"

        result, count = pattern.subn(_repl, result, count=1)
        if count != 1:
            raise ValueError(f"failed to replace numbers for level {level}")

    return result


def _find_matching_brace(text: str, start_idx: int) -> int:
    if start_idx < 0 or start_idx >= len(text) or text[start_idx] != "{":
        raise ValueError("invalid brace start index")
    depth = 0
    for idx in range(start_idx, len(text)):
        ch = text[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return idx
    raise ValueError("matching brace not found")

#!/usr/bin/env python3
import os, subprocess, sys, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "last_changes.md"
REPORT.parent.mkdir(parents=True, exist_ok=True)

def sh(cmd, cwd=None):
    return subprocess.check_output(cmd, cwd=cwd, text=True).strip()

def main():
    event = os.getenv("GITHUB_EVENT_NAME", "")
    head  = os.getenv("GITHUB_SHA", "") or sh(["git","rev-parse","HEAD"])
    base  = os.getenv("GITHUB_BASE_SHA", "")
    pr_head = os.getenv("GITHUB_HEAD_SHA", "")

    # Определяем диапазон сравнения
    if event == "pull_request" and base and pr_head:
        frm, to = base, pr_head
        title = f"PR diff: {base[:7]}..{pr_head[:7]}"
    else:
        # push: сравниваем с предыдущим коммитом
        frm = sh(["git","rev-parse","HEAD^"]) if sh(["git","rev-list","--count","HEAD"]) != "1" else head
        to  = head
        title = f"Push diff: {frm[:7]}..{to[:7]}"

    changed = sh(["git","diff","--name-status", f"{frm}..{to}"])
    files = [line.split("\t")[-1] for line in changed.splitlines()] if changed else []

    # Сводка
    lines = []
    lines.append("# 📝 Last Changes Digest")
    lines.append("")
    lines.append(f"- Generated: {datetime.datetime.utcnow().isoformat()}Z")
    lines.append(f"- Range: `{title}`")
    lines.append(f"- Files changed: **{len(files)}**")
    lines.append("")
    if not files:
        lines.append("_No changes detected._")
    else:
        lines.append("## Changed files")
        lines.append("")
        lines.append("```text")
        lines.append(changed)
        lines.append("```")
        lines.append("")

        # Короткие диффы по каждому файлу (без контекста, чтобы не раздувать отчёт)
        lines.append("## Diffs (unified=0)")
        for f in files:
            lines.append(f"\n<details><summary>{f}</summary>\n")
            try:
                diff = sh(["git","diff","--unified=0", f"{frm}..{to}", "--", f])
                if diff.strip():
                    # Чуть урежем очень большие диффы
                    parts = diff.splitlines()
                    if len(parts) > 800:
                        parts = parts[:800] + ["... (truncated)"]
                    lines.append("```diff")
                    lines.extend(parts)
                    lines.append("```")
                else:
                    lines.append("_No textual diff (binary or rename)._")
            except subprocess.CalledProcessError as e:
                lines.append(f"_Error diffing {f}: {e}_")
            lines.append("\n</details>")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REPORT}")

if __name__ == "__main__":
    main()

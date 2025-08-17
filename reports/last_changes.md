# 📝 Last Changes Digest

- Generated: 2025-08-17T13:39:46.518110Z
- Range: `Push diff: 5f20454..7e1911f`
- Files changed: **11**

## Changed files

```text
A	.github/ISSUE_TEMPLATE/bug_report.md
A	.github/ISSUE_TEMPLATE/feature_request.md
A	.github/PULL_REQUEST_TEMPLATE.md
A	.github/workflows/change-digest.yml
A	README.md
A	app/modules/ui_analyzer/__init__.py
A	app/modules/ui_analyzer/analyzer.py
A	patches/analyzer-compat.patch
A	patches/logger-fix.patch
A	patches/ui-analyzer-wire.patch
A	scripts/diff_digest.py
```

## Diffs (unified=0)

<details><summary>.github/ISSUE_TEMPLATE/bug_report.md</summary>

```diff
diff --git a/.github/ISSUE_TEMPLATE/bug_report.md b/.github/ISSUE_TEMPLATE/bug_report.md
new file mode 100644
index 0000000..d6fb0ae
--- /dev/null
+++ b/.github/ISSUE_TEMPLATE/bug_report.md
@@ -0,0 +1,24 @@
+---
+name: Bug report
+about: Сообщить об ошибке
+labels: bug
+---
+
+**Что происходит?**
+Кратко опишите баг.
+
+**Шаги для воспроизведения**
+1. …
+2. …
+3. …
+
+**Ожидаемое поведение**
+…
+
+**Логи/скриншоты**
+…
+
+**Окружение**
+- OS:
+- Python:
+- Версия Aideon:
```

</details>

<details><summary>.github/ISSUE_TEMPLATE/feature_request.md</summary>

```diff
diff --git a/.github/ISSUE_TEMPLATE/feature_request.md b/.github/ISSUE_TEMPLATE/feature_request.md
new file mode 100644
index 0000000..3354511
--- /dev/null
+++ b/.github/ISSUE_TEMPLATE/feature_request.md
@@ -0,0 +1,21 @@
+---
+name: Feature request
+about: Предложить фичу/модуль
+labels: enhancement
+---
+
+**Проблема / возможность**
+Что хотим улучшить и зачем?
+
+**Предлагаемое решение**
+Коротко про архитектуру/интерфейсы.
+
+**Альтернативы**
+…
+
+**Риски**
+…
+
+**Критерии принятия**
+- [ ] …
+- [ ] …
```

</details>

<details><summary>.github/PULL_REQUEST_TEMPLATE.md</summary>

```diff
diff --git a/.github/PULL_REQUEST_TEMPLATE.md b/.github/PULL_REQUEST_TEMPLATE.md
new file mode 100644
index 0000000..4267310
--- /dev/null
+++ b/.github/PULL_REQUEST_TEMPLATE.md
@@ -0,0 +1,18 @@
+## Что сделано
+- …
+
+## Почему
+- …
+
+## Как тестировать
+- …
+
+## Чек-лист
+- [ ] Нет изменений в “ядре” без отдельного согласования
+- [ ] Добавлены/обновлены метасаммари при необходимости
+- [ ] Обновлены тесты/документация (если нужно)
+- [ ] Локально проверено, что UI не ломается
+
+## Ссылки
+Issue: #...
+Digest: `reports/last_changes.md`
```

</details>

<details><summary>.github/workflows/change-digest.yml</summary>

```diff
diff --git a/.github/workflows/change-digest.yml b/.github/workflows/change-digest.yml
new file mode 100644
index 0000000..d96a28b
--- /dev/null
+++ b/.github/workflows/change-digest.yml
@@ -0,0 +1,50 @@
+name: Change Digest
+
+on:
+  push:
+    branches: [ "main", "*" ]
+  pull_request:
+
+permissions:
+  contents: write
+
+jobs:
+  digest:
+    runs-on: ubuntu-latest
+    steps:
+      - name: Checkout (full history)
+        uses: actions/checkout@v4
+        with:
+          fetch-depth: 0
+
+      - name: Setup Python
+        uses: actions/setup-python@v5
+        with:
+          python-version: "3.11"
+
+      - name: Generate digest
+        env:
+          GITHUB_EVENT_NAME: ${{ github.event_name }}
+          GITHUB_SHA: ${{ github.sha }}
+          GITHUB_BASE_SHA: ${{ github.event.pull_request.base.sha }}
+          GITHUB_HEAD_SHA: ${{ github.event.pull_request.head.sha }}
+        run: |
+          python scripts/diff_digest.py
+          echo "----"; ls -l reports/; echo "----"
+          head -n 50 reports/last_changes.md || true
+
+      - name: Upload artifact (PRs)
+        if: ${{ github.event_name == 'pull_request' }}
+        uses: actions/upload-artifact@v4
+        with:
+          name: last_changes
+          path: reports/last_changes.md
+
+      - name: Commit digest (pushes)
+        if: ${{ github.event_name == 'push' }}
+        run: |
+          git config user.name "github-actions[bot]"
+          git config user.email "github-actions[bot]@users.noreply.github.com"
+          git add reports/last_changes.md
+          git commit -m "ci: update last_changes.md" || echo "No changes to commit"
+          git push
```

</details>

<details><summary>README.md</summary>

```diff
diff --git a/README.md b/README.md
new file mode 100644
index 0000000..deee731
--- /dev/null
+++ b/README.md
@@ -0,0 +1,6 @@
+# Aideon 5.0
+
+Авто-метасаммари: ![Meta Summary](https://github.com/backtoback11/aideon/actions/workflows/meta-summary.yml/badge.svg)
+
+- Автообзор: см. `SUMMARY.md`
+- Полный JSON: `reports/meta_summary.json`
```

</details>

<details><summary>app/modules/ui_analyzer/__init__.py</summary>

```diff
diff --git a/app/modules/ui_analyzer/__init__.py b/app/modules/ui_analyzer/__init__.py
new file mode 100644
index 0000000..2bc230b
--- /dev/null
+++ b/app/modules/ui_analyzer/__init__.py
@@ -0,0 +1 @@
+# UI Analyzer module (scaffold)
```

</details>

<details><summary>app/modules/ui_analyzer/analyzer.py</summary>

```diff
diff --git a/app/modules/ui_analyzer/analyzer.py b/app/modules/ui_analyzer/analyzer.py
new file mode 100644
index 0000000..213d6de
--- /dev/null
+++ b/app/modules/ui_analyzer/analyzer.py
@@ -0,0 +1,32 @@
+"""
+UI Analyzer (scaffold)
+
+Задача: анализ UI-слоёв (Qt-панели), сбор метрик взаимодействия и рекомендации.
+Пока только каркас: интерфейс + заглушки.
+"""
+from dataclasses import dataclass
+from typing import List, Dict, Any
+
+@dataclass
+class UIEvent:
+    when: float
+    widget: str
+    action: str
+    meta: Dict[str, Any]
+
+class UIAnalyzer:
+    def __init__(self):
+        self.events: List[UIEvent] = []
+
+    def track(self, event: UIEvent) -> None:
+        self.events.append(event)
+
+    def snapshot(self) -> Dict[str, Any]:
+        return {
+            "events_count": len(self.events),
+            "widgets": sorted({e.widget for e in self.events})
+        }
+
+    def recommend(self) -> List[str]:
+        # TODO: сюда позже добавим интеллект + запросы к GPT на базе метасаммери
+        return ["(scaffold) Недостаточно данных для рекомендаций"]
```

</details>

<details><summary>patches/analyzer-compat.patch</summary>

```diff
diff --git a/patches/analyzer-compat.patch b/patches/analyzer-compat.patch
new file mode 100644
index 0000000..b768c22
--- /dev/null
+++ b/patches/analyzer-compat.patch
@@ -0,0 +1,190 @@
+*** a/app/modules/analyzer.py
+--- b/app/modules/analyzer.py
+@@
+-import json
+-import openai
+-
+-from app.utils import load_api_key
+-from app.core.file_manager import FileManager
++import json
++import time
++from typing import List, Dict, Any, Optional
++
++from app.utils import load_api_key
++from app.core.file_manager import FileManager
++
++# Совместимость с openai 0.x/1.x
++try:
++    from openai import OpenAI  # >=1.0
++    _OPENAI_V1 = True
++except Exception:
++    _OPENAI_V1 = False
++    import openai  # type: ignore
+@@
+ class CodeAnalyzer:
+@@
+-        self.model_mode = "ChatGPT"
+-        self.api_key = load_api_key(self.config)
+-        self.openai_model = self.config.get("model_name", "gpt-4o")
+-        self.temperature = self.config.get("temperature", 0.7)
+-        self.max_context_tokens = self.config.get("max_context_tokens", 8192)
+-
+-        print("✅ Используется ChatGPT (OpenAI).")
++        self.model_mode = "ChatGPT"
++        self.api_key = load_api_key(self.config)
++        self.openai_model = self.config.get("model_name", "gpt-4o")
++        self.temperature = float(self.config.get("temperature", 0.7))
++        self.max_context_tokens = int(self.config.get("max_context_tokens", 8192))
++        self.request_timeout = int(self.config.get("openai_timeout_sec", 60))
++        self.retry_attempts = int(self.config.get("openai_retries", 2))
++
++        if _OPENAI_V1:
++            self._client = OpenAI(api_key=self.api_key)
++        else:
++            openai.api_key = self.api_key  # legacy
++
++        print("✅ Используется ChatGPT (OpenAI) — совместимый клиент.")
+@@
+-    def chat(self, prompt, system_msg="Ты — Aideon, самообучающийся AI."):
+-        """
+-        Свободный диалог с ChatGPT.
+-        """
+-        openai.api_key = self.api_key
+-        try:
+-            response = openai.ChatCompletion.create(
+-                model=self.openai_model,
+-                messages=[
+-                    {"role": "system", "content": system_msg},
+-                    {"role": "user", "content": prompt}
+-                ],
+-                temperature=self.temperature
+-            )
+-            return response["choices"][0]["message"]["content"]
+-        except Exception as e:
+-            return f"Ошибка при обращении к OpenAI: {e}"
++    def chat(self, prompt: str, system_msg: str = "Ты — Aideon, самообучающийся AI.") -> str:
++        """Свободный диалог с GPT с ретраями и совместимостью API."""
++        messages = [
++            {"role": "system", "content": system_msg},
++            {"role": "user", "content": prompt},
++        ]
++        last_err = None
++        for attempt in range(self.retry_attempts + 1):
++            try:
++                if _OPENAI_V1:
++                    # Сначала попробуем современный Responses API
++                    try:
++                        resp = self._client.responses.create(
++                            model=self.openai_model,
++                            input=prompt,
++                            temperature=self.temperature,
++                            timeout=self.request_timeout,
++                            system=system_msg,
++                        )
++                        # Унифицированный извлекатель текста
++                        return self._extract_text_v1(resp)
++                    except Exception:
++                        # Фолбэк на chat.completions (поддерживается в 1.x)
++                        resp = self._client.chat.completions.create(
++                            model=self.openai_model,
++                            messages=messages,
++                            temperature=self.temperature,
++                            timeout=self.request_timeout,
++                        )
++                        return resp.choices[0].message.content or ""
++                else:
++                    # Legacy 0.x
++                    response = openai.ChatCompletion.create(
++                        model=self.openai_model,
++                        messages=messages,
++                        temperature=self.temperature,
++                        request_timeout=self.request_timeout,
++                    )
++                    return response["choices"][0]["message"]["content"]
++            except Exception as e:
++                last_err = e
++                if attempt < self.retry_attempts:
++                    time.sleep(1.0 * (attempt + 1))
++                else:
++                    return f"Ошибка при обращении к OpenAI: {e}"
++
++    def _extract_text_v1(self, resp: Any) -> str:
++        """
++        Унифицированная распаковка текста для Responses API:
++        resp.output_text есть в новых версиях; иначе пробуем пройтись по output/choices.
++        """
++        # Новая удобная прослойка
++        if hasattr(resp, "output_text") and resp.output_text:
++            return resp.output_text
++        # Универсальный обход
++        try:
++            if getattr(resp, "output", None) and getattr(resp.output, "choices", None):
++                ch0 = resp.output.choices[0]
++                # message/content(0)/text
++                msg = getattr(ch0, "message", None)
++                if msg and getattr(msg, "content", None):
++                    parts = msg.content
++                    if isinstance(parts, list) and parts and getattr(parts[0], "text", None):
++                        return parts[0].text
++                    if isinstance(parts, str):
++                        return parts
++                if getattr(ch0, "content", None):
++                    return ch0.content
++            # try choices[0].message.content style
++            if getattr(resp, "choices", None):
++                ch0 = resp.choices[0]
++                msg = getattr(ch0, "message", None)
++                if msg and getattr(msg, "content", None):
++                    return msg.content
++        except Exception:
++            pass
++        return ""
+@@
+-        openai.api_key = self.api_key
+-        try:
+-            response = openai.ChatCompletion.create(
+-                model=self.openai_model,
+-                messages=[
+-                    {"role": "system", "content": context_prompt},
+-                    {"role": "user", "content": f"Анализируй код из файла {file_path}:\n{code_chunk}"}
+-                ],
+-                temperature=self.temperature
+-            )
+-            return response["choices"][0]["message"]["content"]
+-        except Exception as e:
+-            return f"Ошибка при обращении к OpenAI: {e}"
++        try:
++            if _OPENAI_V1:
++                # responses → фолбэк на chat
++                try:
++                    resp = self._client.responses.create(
++                        model=self.openai_model,
++                        input=f"{context_prompt}\n\nАнализируй код из файла {file_path}:\n{code_chunk}",
++                        temperature=self.temperature,
++                        timeout=self.request_timeout,
++                    )
++                    return self._extract_text_v1(resp)
++                except Exception:
++                    resp = self._client.chat.completions.create(
++                        model=self.openai_model,
++                        messages=[
++                            {"role": "system", "content": context_prompt},
++                            {"role": "user", "content": f"Анализируй код из файла {file_path}:\n{code_chunk}"},
++                        ],
++                        temperature=self.temperature,
++                        timeout=self.request_timeout,
++                    )
++                    return resp.choices[0].message.content or ""
++            else:
++                response = openai.ChatCompletion.create(
++                    model=self.openai_model,
++                    messages=[
++                        {"role": "system", "content": context_prompt},
++                        {"role": "user", "content": f"Анализируй код из файла {file_path}:\n{code_chunk}"},
++                    ],
++                    temperature=self.temperature,
++                    request_timeout=self.request_timeout,
++                )
++                return response["choices"][0]["message"]["content"]
++        except Exception as e:
++            return f"Ошибка при обращении к OpenAI: {e}"
```

</details>

<details><summary>patches/logger-fix.patch</summary>

```diff
diff --git a/patches/logger-fix.patch b/patches/logger-fix.patch
new file mode 100644
index 0000000..046f71b
--- /dev/null
+++ b/patches/logger-fix.patch
@@ -0,0 +1,9 @@
+*** a/app/logger.py
+--- b/app/logger.py
+@@
+ class ColorFormatter(logging.Formatter):
+@@
+-    def custom_format(self, record):
++    def format(self, record):
+         color = self.COLORS.get(record.levelno, "")
+         return f"{color}{super().format(record)}{self.RESET}"
```

</details>

<details><summary>patches/ui-analyzer-wire.patch</summary>

```diff
diff --git a/patches/ui-analyzer-wire.patch b/patches/ui-analyzer-wire.patch
new file mode 100644
index 0000000..61bcb19
--- /dev/null
+++ b/patches/ui-analyzer-wire.patch
@@ -0,0 +1,145 @@
+*** a/app/modules/ui_analyzer/analyzer.py
+--- b/app/modules/ui_analyzer/analyzer.py
+@@
+-from typing import List, Dict, Any
++from typing import List, Dict, Any, Optional
++from dataclasses import dataclass
++from datetime import datetime
++
++@dataclass
++class UIEvent:
++    ts: float
++    type: str
++    widget: str
++    detail: str = ""
+ 
+ class UIAnalyzer:
+-    def __init__(self):
+-        self.events: List[UIEvent] = []
++    def __init__(self):
++        self.events: List[UIEvent] = []
+ 
+-    def track(self, event: UIEvent) -> None:
+-        self.events.append(event)
++    def track(self, event: UIEvent) -> None:
++        self.events.append(event)
+ 
+     def snapshot(self) -> Dict[str, Any]:
+         return {
+             "events_count": len(self.events),
+             "widgets": sorted({e.widget for e in self.events})
+         }
+ 
+     def recommend(self) -> List[str]:
+-        # TODO: сюда позже добавим интеллект + запросы к GPT на базе метасаммери 
+-        return ["(scaffold) Недостаточно данных для рекомендаций"]
++        # TODO: сюда позже добавим интеллект + запросы к GPT на базе метасаммери
++        if len(self.events) < 5:
++            return ["(scaffold) Недостаточно данных для рекомендаций"]
++        hot = {}
++        for e in self.events:
++            hot[e.widget] = hot.get(e.widget, 0) + 1
++        top = sorted(hot.items(), key=lambda x: x[1], reverse=True)[:3]
++        tips = [f"Часто используется: {name} ({cnt}) — проверь доступность/хоткеи/подсказки." for name, cnt in top]
++        return tips
+*** a/app/ui/main_window.py
+--- b/app/ui/main_window.py
+@@
+-from .chat_panel import ChatPanel
++from .chat_panel import ChatPanel
+ from app.modules.self_improver import SelfImprover
+ from app.modules.improver.project_scanner import ProjectScanner
++from app.modules.ui_analyzer.analyzer import UIAnalyzer, UIEvent
++from PyQt6.QtCore import QObject, QEvent, QDateTime
++from PyQt6.QtWidgets import QApplication, QPushButton, QLineEdit, QComboBox, QCheckBox, QPlainTextEdit, QTextEdit, QTabWidget, QHBoxLayout, QVBoxLayout, QWidget
+@@
+ class SelfImproverPanel(QWidget):
+@@
+         layout.addLayout(btn_row)
+         self.setLayout(layout)
+ 
++class UIEventsFilter(QObject):
++    def __init__(self, ui_analyzer: UIAnalyzer):
++        super().__init__()
++        self.ui_analyzer = ui_analyzer
++
++    def eventFilter(self, obj, event):
++        et = event.type()
++        name = obj.objectName() or obj.__class__.__name__
++        if et in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick):
++            self.ui_analyzer.track(UIEvent(ts=QDateTime.currentDateTime().toSecsSinceEpoch(), type="click", widget=name))
++        elif et == QEvent.Type.KeyPress:
++            self.ui_analyzer.track(UIEvent(ts=QDateTime.currentDateTime().toSecsSinceEpoch(), type="key", widget=name))
++        elif et == QEvent.Type.FocusIn:
++            self.ui_analyzer.track(UIEvent(ts=QDateTime.currentDateTime().toSecsSinceEpoch(), type="focus", widget=name))
++        return super().eventFilter(obj, event)
++
+ class MainWindow(QMainWindow):
+@@
+-        splitter = QSplitter(Qt.Orientation.Horizontal)
++        splitter = QSplitter(Qt.Orientation.Horizontal)
+ 
+         self.chat_panel = ChatPanel(config=self.config, parent=self)
+         self.self_improver_panel = SelfImproverPanel(
+             config=self.config,
+             chat_panel=self.chat_panel,
+             parent=self
+         )
+ 
+-        splitter.addWidget(self.chat_panel)
+-        splitter.addWidget(self.self_improver_panel)
++        # UI Analyzer tab
++        self.ui_analyzer = UIAnalyzer()
++        self.ui_tab = QTextEdit()
++        self.ui_tab.setReadOnly(True)
++        self.ui_tab.setStyleSheet("background-color: #f0fff4; font-family: monospace;")
++        self.ui_tab.setText("UI Analyzer — собирать события и давать рекомендации.\n")
++
++        right_tabs = QTabWidget()
++        right_tabs.addTab(self.self_improver_panel, "Саморазвитие")
++        right_tabs.addTab(self.ui_tab, "UI-аналитика")
++
++        splitter.addWidget(self.chat_panel)
++        splitter.addWidget(right_tabs)
+@@
+         self.setCentralWidget(central_widget)
++        # Глобальный фильтр событий
++        app = QApplication.instance()
++        if app:
++            self._ui_filter = UIEventsFilter(self.ui_analyzer)
++            app.installEventFilter(self._ui_filter)
++        self._mount_ui_tab_toolbar(right_tabs)
++
++    def _mount_ui_tab_toolbar(self, parent_tabs: QTabWidget):
++        wrap = QWidget(parent_tabs)
++        layout = QVBoxLayout(wrap)
++        row = QHBoxLayout()
++        btn_snapshot = QPushButton("📸 Снимок")
++        btn_reco = QPushButton("🤖 Рекомендации")
++        btn_clear = QPushButton("🧹 Очистить")
++        row.addWidget(btn_snapshot)
++        row.addWidget(btn_reco)
++        row.addWidget(btn_clear)
++        row.addStretch(1)
++        layout.addLayout(row)
++        layout.addWidget(self.ui_tab)
++
++        idx = parent_tabs.indexOf(self.ui_tab)
++        parent_tabs.removeTab(idx)
++        parent_tabs.insertTab(idx, wrap, "UI-аналитика")
++
++        def on_snapshot():
++            snap = self.ui_analyzer.snapshot()
++            self.ui_tab.append(f"\n--- SNAPSHOT ---\n{snap}")
++        def on_reco():
++            tips = self.ui_analyzer.recommend()
++            self.ui_tab.append("\n--- РЕКОМЕНДАЦИИ ---")
++            for t in tips:
++                self.ui_tab.append(f"• {t}")
++        def on_clear():
++            self.ui_analyzer.events.clear()
++            self.ui_tab.append("\n(очищено)")
++
++        btn_snapshot.clicked.connect(on_snapshot)
++        btn_reco.clicked.connect(on_reco)
++        btn_clear.clicked.connect(on_clear)
```

</details>

<details><summary>scripts/diff_digest.py</summary>

```diff
diff --git a/scripts/diff_digest.py b/scripts/diff_digest.py
new file mode 100755
index 0000000..e3484c3
--- /dev/null
+++ b/scripts/diff_digest.py
@@ -0,0 +1,71 @@
+#!/usr/bin/env python3
+import os, subprocess, sys, pathlib, datetime
+
+ROOT = pathlib.Path(__file__).resolve().parents[1]
+REPORT = ROOT / "reports" / "last_changes.md"
+REPORT.parent.mkdir(parents=True, exist_ok=True)
+
+def sh(cmd, cwd=None):
+    return subprocess.check_output(cmd, cwd=cwd, text=True).strip()
+
+def main():
+    event = os.getenv("GITHUB_EVENT_NAME", "")
+    head  = os.getenv("GITHUB_SHA", "") or sh(["git","rev-parse","HEAD"])
+    base  = os.getenv("GITHUB_BASE_SHA", "")
+    pr_head = os.getenv("GITHUB_HEAD_SHA", "")
+
+    # Определяем диапазон сравнения
+    if event == "pull_request" and base and pr_head:
+        frm, to = base, pr_head
+        title = f"PR diff: {base[:7]}..{pr_head[:7]}"
+    else:
+        # push: сравниваем с предыдущим коммитом
+        frm = sh(["git","rev-parse","HEAD^"]) if sh(["git","rev-list","--count","HEAD"]) != "1" else head
+        to  = head
+        title = f"Push diff: {frm[:7]}..{to[:7]}"
+
+    changed = sh(["git","diff","--name-status", f"{frm}..{to}"])
+    files = [line.split("\t")[-1] for line in changed.splitlines()] if changed else []
+
+    # Сводка
+    lines = []
+    lines.append("# 📝 Last Changes Digest")
+    lines.append("")
+    lines.append(f"- Generated: {datetime.datetime.utcnow().isoformat()}Z")
+    lines.append(f"- Range: `{title}`")
+    lines.append(f"- Files changed: **{len(files)}**")
+    lines.append("")
+    if not files:
+        lines.append("_No changes detected._")
+    else:
+        lines.append("## Changed files")
+        lines.append("")
+        lines.append("```text")
+        lines.append(changed)
+        lines.append("```")
+        lines.append("")
+
+        # Короткие диффы по каждому файлу (без контекста, чтобы не раздувать отчёт)
+        lines.append("## Diffs (unified=0)")
+        for f in files:
+            lines.append(f"\n<details><summary>{f}</summary>\n")
+            try:
+                diff = sh(["git","diff","--unified=0", f"{frm}..{to}", "--", f])
+                if diff.strip():
+                    # Чуть урежем очень большие диффы
+                    parts = diff.splitlines()
+                    if len(parts) > 800:
+                        parts = parts[:800] + ["... (truncated)"]
+                    lines.append("```diff")
+                    lines.extend(parts)
+                    lines.append("```")
+                else:
+                    lines.append("_No textual diff (binary or rename)._")
+            except subprocess.CalledProcessError as e:
+                lines.append(f"_Error diffing {f}: {e}_")
+            lines.append("\n</details>")
+    REPORT.write_text("\n".join(lines), encoding="utf-8")
+    print(f"Wrote {REPORT}")
+
+if __name__ == "__main__":
+    main()
```

</details>
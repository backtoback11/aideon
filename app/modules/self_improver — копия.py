# app/modules/self_improver.py
from __future__ import annotations

import os
from typing import Generator, Optional

from app.core.file_manager import FileManager
from app.modules.improver.project_scanner import ProjectScanner
from app.modules.improver.file_summarizer import FileSummarizer
from app.modules.improver.improvement_planner import ImprovementPlanner
from app.modules.improver.patch_requester import PatchRequester
from app.modules.improver.patcher import CodePatcher
from app.modules.improver.error_debugger import ErrorDebugger
from app.modules.analyzer import CodeAnalyzer
from app.logger import log_info, log_warning, log_error

# AI-ассистент багфиксов
from app.modules.improver.ai_bug_fixer import AIBugFixer


class SelfImprover:
    """
    AI-модуль самоусовершенствования Aideon.
    Цикл:
      1) сканирует проект,
      2) строит метасаммери,
      3) (опц.) делает предварительный AI-багфикс,
      4) запрашивает план улучшений,
      5) запрашивает обновлённый код,
      6) применяет (или сохраняет diff) / чинит при ошибке.
    """

    def __init__(self, config, chat_panel=None, apply_patches_automatically: bool = False):
        self.config = config or {}
        # Новый FileManager поддерживает вызов без аргументов (repo_root как base_dir)
        self.file_manager = FileManager()
        self.chatgpt = CodeAnalyzer(config)

        self.backup_path = "app/backups"
        self.diff_path = "app/patches"
        os.makedirs(self.backup_path, exist_ok=True)
        os.makedirs(self.diff_path, exist_ok=True)

        self.summarizer = FileSummarizer()
        self.planner = ImprovementPlanner()
        self.requester = PatchRequester()
        # Патчер в прежнем режиме: бэкапы и диффы
        self.patcher = CodePatcher(backup_dir=self.backup_path, diff_dir=self.diff_path)
        self.debugger = ErrorDebugger(self.chatgpt)
        self.chat_panel = chat_panel  # может быть None

        # Управление процессом
        self.stop_requested = False
        self.apply_patches_automatically = bool(apply_patches_automatically)

        # Мягкие флаги (ядро не ломаем)
        self.auto_bugfix = bool(self.config.get("auto_bugfix", True))
        self.max_fix_cycles = int(self.config.get("max_fix_cycles", 2))
        # уважаем старый флаг, но позволяем переопределить через конфиг
        self.auto_apply_patches = bool(self.config.get("auto_apply_patches", self.apply_patches_automatically))

        # Багфиксер (инжектим анализатор)
        self.bugfixer = AIBugFixer(self.chatgpt, max_fix_cycles=self.max_fix_cycles)

    def run_self_improvement(self) -> Generator[str, None, None]:
        """
        Генератор шагов/логов процесса.
        """
        log_info("🧠 ▶️ Запущен процесс самоусовершенствования Aideon...")
        yield "🧠 ▶️ Запущен процесс самоусовершенствования Aideon..."
        log_info(
            "⚙️ Параметры: "
            f"auto_bugfix={self.auto_bugfix}, "
            f"max_fix_cycles={self.max_fix_cycles}, "
            f"auto_apply_patches={self.auto_apply_patches}, "
            f"backups={self.backup_path}, diffs={self.diff_path}"
        )

        scanner = ProjectScanner(root_path="app")
        log_info("🔍 Сканирую проект (ProjectScanner.scan)…")
        structure = scanner.scan()
        log_info(f"🗂️ Найдено папок: {len(structure)}")

        any_success = False

        for rel_dir, files in structure.items():
            log_info(f"📂 Папка: {rel_dir} — файлов: {len(files)}")
            if self.stop_requested:
                msg = "⏹️ Остановлено пользователем."
                log_warning(msg)
                yield msg
                break

            for file_entry in files:
                if self.stop_requested:
                    msg = "⏹️ Остановлено пользователем."
                    log_warning(msg)
                    yield msg
                    break

                fname = file_entry["name"]
                full_path = os.path.join("app", rel_dir, fname)
                abs_path = os.path.abspath(full_path)
                log_info(f"— ▶️ Работаю с файлом: {full_path}")

                # ✅ Новый FileManager API: read_text вместо read_file
                try:
                    old_code = self.file_manager.read_text(abs_path)
                except Exception as e:
                    old_code = None
                    log_warning(f"[SelfImprover] Не удалось прочитать файл {full_path}: {e}")

                if not old_code:
                    msg = f"⚠️ Пропущен файл (не читается): {full_path}"
                    log_warning(msg)
                    yield msg
                    continue
                log_info(f"📥 Прочитан файл ({len(old_code)} симв.)")

                # Шаг 1 — метасаммери
                log_info("🧾 Генерация метасаммери (FileSummarizer)…")
                summary = self.summarizer.summarize(full_path, old_code)
                msg = f"📄 Саммери: {full_path}\n{summary}"
                log_info(msg)
                yield msg

                # Шаг 1.5 — проактивный багфикс (до плана), diff-only или авто-применение
                if self.auto_bugfix:
                    log_info(f"🧪 Предварительный багфикс включен → пытаюсь для {full_path}")
                    yield f"🔍 Предварительный AI-багфикс для {full_path}..."

                    def _apply_attempt(new_code_text: str):
                        log_info(
                            "🧷 Применение bugfix-патча…"
                            + (" (auto-apply)" if self.auto_apply_patches else " (save diff only)")
                        )
                        if self.auto_apply_patches:
                            # интерактивное подтверждение (с бэкапом + diff)
                            self.patcher.confirm_and_apply_patch(
                                file_path=abs_path,
                                old_code=old_code,
                                new_code=new_code_text
                            )
                        else:
                            # Только сохранить DIFF, не перезаписывая файл
                            self.patcher._save_diff(abs_path, old_code, new_code_text)

                    def _on_error(err: Exception, attempt: int):
                        log_warning(f"⚠️ Ошибка при применении bugfix-патча (попытка {attempt}): {err}")

                    bugfixed = self.bugfixer.iterative_fix_cycle(
                        file_path=full_path,
                        summary=summary,
                        old_code=old_code,
                        apply_callback=_apply_attempt,
                        on_error_callback=_on_error
                    )
                    if bugfixed:
                        yield (
                            f"✅ Bugfix-патч подготовлен для {full_path} "
                            f"({ 'применён' if self.auto_apply_patches else 'diff сохранён' })"
                        )
                        log_info("🧪 Предварительный багфикс дал результат — продолжу улучшения поверх фикса.")
                        old_code = bugfixed  # делаем улучшения поверх фикса
                    else:
                        yield f"ℹ️ Не удалось выполнить предварительный багфикс для {full_path} — продолжаем."
                        log_info("ℹ️ Багфикс не дал результата, иду дальше к плану улучшений.")
                else:
                    log_info("🧪 Предварительный багфикс отключён настройками.")

                # Шаг 2 — план улучшения (строгий system + строковый промпт)
                log_info("📝 Формирую промпт плана (ImprovementPlanner)…")
                plan_prompt = self.planner.build_prompt(full_path, summary)
                if self.chat_panel:
                    self.chat_panel.add_gpt_request(plan_prompt)
                try:
                    log_info("🤖 Запрашиваю план у OpenAI…")
                    raw_plan = self.chatgpt.chat(plan_prompt, system_msg=self.planner.SYSTEM_MSG)
                    if self.chat_panel:
                        self.chat_panel.add_gpt_response(raw_plan)
                    log_info("📨 План получен.")
                except Exception as e:
                    msg = f"❌ Ошибка при запросе плана улучшения для {full_path}: {e}"
                    log_error(msg)
                    yield msg
                    continue

                log_info("🧩 Разбираю план (ImprovementPlanner.extract_plan)…")
                plan_data = self.planner.extract_plan(raw_plan)
                if not plan_data or not plan_data.get("plan"):
                    msg = f"❌ GPT не дал валидный план для: {full_path}"
                    log_error(msg)
                    yield msg
                    continue
                msg = f"💡 План улучшений для {full_path}:\n{plan_data['plan']}"
                log_info(msg)
                yield msg

                # Шаг 3 — патч (строгий system + извлечение «чистого» кода)
                log_info("🧵 Готовлю промпт для патча (PatchRequester)…")
                patch_prompt = self.requester.build_prompt(full_path, old_code, summary, plan_data)
                if self.chat_panel:
                    self.chat_panel.add_gpt_request(patch_prompt)
                try:
                    log_info("🤖 Запрашиваю новый код у OpenAI…")
                    raw_code = self.chatgpt.chat(patch_prompt, system_msg=self.requester.SYSTEM_MSG)
                    new_code = self.requester.extract_code(raw_code)
                    if self.chat_panel:
                        self.chat_panel.add_gpt_response(raw_code)
                    log_info(f"📨 Патч получен ({len(new_code) if new_code else 0} симв.).")
                except Exception as e:
                    msg = f"⚠️ Ошибка при получении патча: {full_path}: {e}"
                    log_warning(msg)
                    yield msg
                    continue

                if not new_code or "Ошибка" in new_code:
                    msg = f"⚠️ Патч не получен от GPT: {full_path}"
                    log_warning(msg)
                    yield msg
                    continue

                # Шаг 4 — применение или автоматическая отладка
                log_info("🧷 Применение патча…" + (" (auto-apply)" if self.auto_apply_patches else " (save diff only)"))
                try:
                    if self.auto_apply_patches:
                        self.patcher.confirm_and_apply_patch(
                            file_path=abs_path,
                            old_code=old_code,
                            new_code=new_code
                        )
                        msg = f"✅ Патч успешно применён: {full_path}"
                        log_info(msg)
                        yield msg
                        any_success = True
                    else:
                        # Только сохранить diff, не перезаписывая файл
                        self.patcher._save_diff(abs_path, old_code, new_code)
                        msg = f"📝 Diff сохранён (без применения): {full_path}"
                        log_info(msg)
                        yield msg
                        any_success = True

                except Exception as e:
                    log_error(f"💥 Ошибка при применении патча: {e}")
                    log_info("🧯 Запрашиваю автоматическое исправление через ErrorDebugger…")
                    fix_code: Optional[str] = self.debugger.request_fix(
                        file_path=full_path,
                        original_code=new_code,
                        error_message=str(e)
                    )

                    # Fallback: AI-багфиксер в несколько итераций
                    if not fix_code and self.auto_bugfix:
                        yield f"🧪 Пробую AI-Assisted Bug Fixer для {full_path} после ошибки применения…"
                        log_info("🧪 Запускаю AIBugFixer.iterative_fix_cycle (fallback)…")

                        def _apply_attempt2(nc: str):
                            log_info(
                                "🧷 Применение bugfix-патча (fallback)…"
                                + (" (auto-apply)" if self.auto_apply_patches else " (save diff only)")
                            )
                            if self.auto_apply_patches:
                                self.patcher.confirm_and_apply_patch(
                                    file_path=abs_path,
                                    old_code=old_code,
                                    new_code=nc
                                )
                            else:
                                self.patcher._save_diff(abs_path, old_code, nc)

                        def _on_error2(err: Exception, attempt: int):
                            log_warning(f"⚠️ Ошибка и при bugfix-попытке {attempt}: {err}")

                        got = self.bugfixer.iterative_fix_cycle(
                            file_path=full_path,
                            summary=summary,
                            old_code=old_code,
                            apply_callback=_apply_attempt2,
                            on_error_callback=_on_error2
                        )
                        fix_code = got

                    if fix_code:
                        msg = f"🛠️ Попытка автоматического исправления кода для: {full_path}"
                        log_info(msg)
                        yield msg
                        try:
                            if self.auto_apply_patches:
                                self.patcher.confirm_and_apply_patch(
                                    file_path=abs_path,
                                    old_code=old_code,
                                    new_code=fix_code
                                )
                                msg = f"✅ Исправление успешно применено: {full_path}"
                                log_info(msg)
                                yield msg
                                any_success = True
                            else:
                                self.patcher._save_diff(abs_path, old_code, fix_code)
                                msg = f"📝 Diff исправления сохранён (без применения): {full_path}"
                                log_info(msg)
                                yield msg
                                any_success = True
                        except Exception as e2:
                            msg = f"💥 Ошибка при втором применении патча: {e2}"
                            log_error(msg)
                            yield msg
                    else:
                        msg = f"💥 Не удалось автоматически исправить: {full_path}"
                        log_error(msg)
                        yield msg

        if not any_success:
            msg = "⚠️ Самоусовершенствование завершено, но ни один файл не был улучшён."
            log_warning(msg)
            yield msg
        else:
            msg = "🧠 ✅ Самоусовершенствование завершено успешно!"
            log_info(msg)
            yield msg
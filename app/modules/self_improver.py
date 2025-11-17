# app/modules/self_improver.py
from __future__ import annotations

import os
import ast
from typing import Generator, Optional, Dict, Any, Iterable, List, Tuple

from app.core.file_manager import FileManager
from app.modules.improver.project_scanner import ProjectScanner
from app.modules.improver.file_summarizer import FileSummarizer
from app.modules.improver.improvement_planner import ImprovementPlanner
from app.modules.improver.patch_requester import PatchRequester
from app.modules.improver.patcher import CodePatcher
from app.modules.improver.error_debugger import ErrorDebugger
from app.modules.analyzer import CodeAnalyzer
from app.logger import log_info, log_warning, log_error

from app.modules.improver.ai_bug_fixer import AIBugFixer


# ───────────────────────── настройки по умолчанию ─────────────────────────

DEFAULT_ROOT = "app"
DEFAULT_INCLUDE_EXTS: Tuple[str, ...] = (".py",)

DEFAULT_EXCLUDE_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode",
    "__pycache__", "venv", ".venv",
    "app/logs", "app/patches", "app/backups",
}

# «бережные» зоны (ядро), куда по умолчанию не пишем
DEFAULT_SENSITIVE_DIRS = {"app/agent", "app/core"}

HEARTBEAT_EVERY = 2  # как часто печатать прогресс


def _nice_rel(path: str, base: str) -> str:
    try:
        return os.path.relpath(path, base)
    except Exception:
        return path


def _to_abs(base_root: str, rel_or_name: str) -> str:
    """Конвертирует относительный путь в абсолютный, имена оставляет как есть."""
    if os.path.isabs(rel_or_name):
        return os.path.normpath(rel_or_name)
    # если это «короткое имя папки» (например, '__pycache__'), пусть остаётся именем
    if os.sep not in rel_or_name and "/" not in rel_or_name:
        return rel_or_name
    return os.path.normpath(os.path.join(base_root, rel_or_name))


class SelfImprover:
    """
    Глобальный AI-модуль самоусовершенствования Aideon.
    Цикл по проекту: скан → кандидаты → summary → (опц.) bugfix → план → патч → diff/apply.
    """

    def __init__(self, config: Dict[str, Any] | None, chat_panel=None, apply_patches_automatically: bool = False):
        self.config = dict(config or {})
        self.chat_panel = chat_panel

        # Менеджер файлов определяет базу репозитория
        self.file_manager = FileManager()
        fm_base = getattr(self.file_manager, "base_dir", None)

        # project_root: приоритет — явный конфиг → FileManager.base_dir → CWD
        self.project_root: str = os.path.abspath(
            self.config.get("project_root", fm_base if fm_base else os.getcwd())
        )

        self.chatgpt = CodeAnalyzer(self.config)

        # Пути бэкапов/диффов
        self.backup_path = self.config.get("backups_dir", "app/backups")
        self.diff_path = self.config.get("diffs_dir", "app/patches")
        os.makedirs(self.backup_path, exist_ok=True)
        os.makedirs(self.diff_path, exist_ok=True)

        # Модули пайплайна
        self.summarizer = FileSummarizer()
        self.planner = ImprovementPlanner()
        self.requester = PatchRequester()
        self.patcher = CodePatcher(backup_dir=self.backup_path, diff_dir=self.diff_path)
        self.debugger = ErrorDebugger(self.chatgpt)

        # Флаги/управление
        self.stop_requested = False
        self.auto_bugfix = bool(self.config.get("auto_bugfix", True))
        self.max_fix_cycles = int(self.config.get("max_fix_cycles", 2))
        self.auto_apply_patches = bool(self.config.get("auto_apply_patches", apply_patches_automatically))

        # Фильтры обхода
        self.include_exts: Tuple[str, ...] = tuple(self.config.get("include_exts", DEFAULT_INCLUDE_EXTS))

        # Нормализуем exclude/sensitive: храним как МИКС из «коротких имён» и «абсолютных префиксов»
        raw_exclude = set(DEFAULT_EXCLUDE_DIRS) | set(self.config.get("exclude_dirs", []))
        raw_sensitive = set(DEFAULT_SENSITIVE_DIRS) | set(self.config.get("sensitive_dirs", []))
        self.exclude_dirs: set[str] = {_to_abs(self.project_root, v) for v in raw_exclude}
        self.sensitive_dirs: set[str] = {_to_abs(self.project_root, v) for v in raw_sensitive}

        # Лимит обрабатываемых файлов (для отладки)
        self.limit_files: Optional[int] = self.config.get("limit_files")

        # Диагностика сканирования
        self.debug_scan: bool = bool(self.config.get("debug_scan", True))

        # Багфиксер
        self.bugfixer = AIBugFixer(self.chatgpt, max_fix_cycles=self.max_fix_cycles)

    # ───────────────────────── публичный API ─────────────────────────

    def run_self_improvement(self) -> Generator[str, None, None]:
        """Совместимость со старым интерфейсом."""
        yield from self.run_project_improvement()

    def run_project_improvement(
        self,
        root: str = DEFAULT_ROOT,
        *,
        auto_bugfix: Optional[bool] = None,
        max_fix_cycles: Optional[int] = None,
        auto_apply_patches: Optional[bool] = None,
        include_exts: Optional[Iterable[str]] = None,
        exclude_dirs: Optional[Iterable[str]] = None,
        sensitive_dirs: Optional[Iterable[str]] = None,
        limit_files: Optional[int] = None,
        debug_preview_count: int = 10,
    ) -> Generator[str, None, None]:

        auto_bugfix = self.auto_bugfix if auto_bugfix is None else bool(auto_bugfix)
        max_fix_cycles = self.max_fix_cycles if max_fix_cycles is None else int(max_fix_cycles)
        auto_apply_patches = self.auto_apply_patches if auto_apply_patches is None else bool(auto_apply_patches)
        include_exts = tuple(include_exts or self.include_exts)

        # если пользователь передал свои фильтры — тоже нормализуем
        exclude_dirs_set = self.exclude_dirs if exclude_dirs is None else {_to_abs(self.project_root, v) for v in exclude_dirs}
        sensitive_dirs_set = self.sensitive_dirs if sensitive_dirs is None else {_to_abs(self.project_root, v) for v in sensitive_dirs}
        limit_files = self.limit_files if (limit_files is None) else limit_files
        if isinstance(limit_files, bool):
            limit_files = None
        if isinstance(limit_files, int) and limit_files <= 0:
            limit_files = None

        # шапка
        header = (
            "🧠 ▶️ Запущен процесс самоусовершенствования Aideon...\n"
            f"⚙️ Параметры: auto_bugfix={auto_bugfix}, max_fix_cycles={max_fix_cycles}, "
            f"auto_apply_patches={auto_apply_patches}, backups={self.backup_path}, diffs={self.diff_path}\n"
            f"📁 project_root={self.project_root}\n"
            f"🎯 include_exts={list(include_exts)}\n"
            f"🚧 exclude_dirs(normalized)={sorted(exclude_dirs_set)}\n"
            f"🛡️ sensitive_dirs(normalized)={sorted(sensitive_dirs_set)}"
        )
        log_info(header.replace("\n", " | "))
        for line in header.split("\n"):
            if line:
                yield line

        # 1) Скан проекта (метаданные/кэш — для правой панели)
        scanner_root = os.path.abspath(os.path.join(self.project_root, root))
        yield f"🔎 scanner_root={scanner_root}"
        log_info(f"scanner_root={scanner_root}")

        yield "🔍 Сканирую проект (ProjectScanner.scan)…"
        try:
            _ = ProjectScanner(root_path=scanner_root).scan()
        except Exception as e:
            log_error(f"Скан провалился: {e}")
            yield f"💥 Ошибка сканера: {e}"
            return
        yield "✅ Сканирование завершено."

        # 2) Сбор кандидатов с диагностикой
        candidates, stats = self._collect_candidates_with_debug(
            root=root,
            include_exts=include_exts,
            exclude_abs=exclude_dirs_set,
            sensitive_abs=sensitive_dirs_set,
        )
        total_scanned = stats["scanned_files"]
        included = len(candidates)

        if limit_files:
            candidates = candidates[: int(limit_files)]
        chosen = len(candidates)

        diag = (
            f"🧮 Диагностика отбора: scanned={total_scanned}, "
            f"excluded_by_ext={stats['excluded_by_ext']}, "
            f"excluded_by_exclude={stats['excluded_by_exclude']}, "
            f"excluded_by_sensitive={stats['excluded_by_sensitive']}, "
            f"included={included}"
        )
        log_info(diag); yield diag
        if limit_files:
            lim_msg = f"🔢 Ограничение limit_files={limit_files} → к обработке: {chosen}"
            log_info(lim_msg); yield lim_msg

        # превью кандидатов
        if candidates:
            preview = [ _nice_rel(p, self.project_root) for p in candidates[:max(1, debug_preview_count)] ]
            msg = f"👀 Превью первых {min(debug_preview_count, len(candidates))} файлов: " + ", ".join(preview)
            log_info(msg); yield msg
        else:
            yield "ℹ️ Подходящих файлов не найдено. Ослабь фильтры (exclude/sensitive) или расширь include_exts."
            return

        any_success = False
        processed = 0

        # 3) Обработка каждого файла
        for abs_path in candidates:
            if self.stop_requested:
                msg = "⏹️ Остановлено пользователем."
                log_warning(msg)
                yield msg
                break

            rel_path = _nice_rel(abs_path, self.project_root)
            yield f"— ▶️ Работаю с файлом: {rel_path}"

            # чтение исходника
            try:
                old_code = self.file_manager.read_text(abs_path)
            except Exception as e:
                log_warning(f"[SelfImprover] Не удалось прочитать файл {rel_path}: {e}")
                yield f"⚠️ Пропущен файл (не читается): {rel_path}"
                continue

            yield f"📥 Прочитан файл ({len(old_code)} симв.)"

            # summary
            yield "🧾 Генерация метасаммери (FileSummarizer)…"
            try:
                summary = self.summarizer.summarize(rel_path, old_code)
            except Exception as e:
                log_warning(f"summary failed for {rel_path}: {e}")
                yield f"⚠️ Пропуск: не удалось сделать summary ({e})"
                continue
            yield f"📄 Саммери: {rel_path}\n{summary}"

            # предварительный багфикс
            if auto_bugfix:
                yield f"🧪 Предварительный багфикс включен → пытаюсь для {rel_path}"

                def _apply_attempt(new_text: str):
                    if auto_apply_patches:
                        self.patcher.confirm_and_apply_patch(abs_path, old_code, new_text)
                    else:
                        self.patcher._save_diff(abs_path, old_code, new_text)

                def _on_error(err: Exception, attempt: int):
                    log_warning(f"bugfix attempt {attempt} failed for {rel_path}: {err}")

                bugfixed = self.bugfixer.iterative_fix_cycle(
                    file_path=rel_path,
                    summary=summary,
                    old_code=old_code,
                    apply_callback=_apply_attempt,
                    on_error_callback=_on_error
                )
                if bugfixed and bugfixed != old_code:
                    yield "✅ Bugfix-патч подготовлен " + ("(applied)" if auto_apply_patches else "(diff сохранён)")
                    old_code = bugfixed
                else:
                    yield "ℹ️ Багфикс изменений не предложил."
            else:
                yield "🧪 Предварительный багфикс отключён настройками."

            # план
            yield "📝 Формирую промпт плана (ImprovementPlanner)…"
            plan_prompt = self.planner.build_prompt(rel_path, summary)
            if self.chat_panel:
                try:
                    self.chat_panel.add_gpt_request(plan_prompt)
                except Exception:
                    pass
            try:
                yield "🤖 Запрашиваю план у OpenAI…"
                raw_plan = self.chatgpt.chat(plan_prompt, system_msg=self.planner.SYSTEM_MSG)
                if self.chat_panel:
                    try:
                        self.chat_panel.add_gpt_response(raw_plan)
                    except Exception:
                        pass
            except Exception as e:
                yield f"❌ Ошибка при запросе плана: {e}"
                continue

            plan_data = self.planner.extract_plan(raw_plan)
            if not plan_data or not plan_data.get("plan"):
                yield f"❌ GPT не дал валидный план для: {rel_path}"
                continue

            if isinstance(plan_data["plan"], list):
                pretty_lines = []
                for it in plan_data["plan"]:
                    s = it.get("step")
                    a = it.get("action")
                    d = it.get("details")
                    if s is not None:
                        pretty_lines.append(f"{s}. {a or ''}{(' — ' + d) if d else ''}")
                    else:
                        pretty_lines.append(f"- {a or ''}{(' — ' + d) if d else ''}")
                plan_pretty = "\n".join(pretty_lines)
            else:
                plan_pretty = str(plan_data["plan"])
            yield f"💡 План улучшений для {rel_path}:\n{plan_pretty}"

            # запрос нового кода
            yield "🧵 Готовлю промпт для патча (PatchRequester)…"
            patch_prompt = self.requester.build_prompt(rel_path, old_code, summary, plan_data)
            if self.chat_panel:
                try:
                    self.chat_panel.add_gpt_request(patch_prompt)
                except Exception:
                    pass
            try:
                yield "🤖 Запрашиваю новый код у OpenAI…"
                raw_code = self.chatgpt.chat(patch_prompt, system_msg=self.requester.SYSTEM_MSG)
                new_code = self.requester.extract_code(raw_code)
                if self.chat_panel:
                    try:
                        self.chat_panel.add_gpt_response(raw_code)
                    except Exception:
                        pass
            except Exception as e:
                yield f"⚠️ Ошибка при получении патча: {e}"
                continue

            if not new_code or not isinstance(new_code, str):
                yield "⚠️ Пустой патч — пропускаю."
                continue

            yield f"📨 Патч получен ({len(new_code)} симв.)."

            # синтакс-проверка для .py
            syntax_ok = True
            if rel_path.endswith(".py"):
                try:
                    ast.parse(new_code)
                except SyntaxError as e:
                    syntax_ok = False
                    log_warning(f"syntax error in new code for {rel_path}: {e}")

            # применить / сохранить diff
            try:
                if auto_apply_patches and syntax_ok:
                    self.patcher.confirm_and_apply_patch(abs_path, old_code, new_code)
                    any_success = True
                    yield "🧷 Применение патча… (applied)"
                    yield f"✅ Патч успешно применён: {rel_path}"
                else:
                    self.patcher._save_diff(abs_path, old_code, new_code)
                    any_success = True
                    yield "🧷 Применение патча… (save diff only)"
                    yield f"📝 Diff сохранён (без применения): {rel_path}"
                    if auto_apply_patches and not syntax_ok:
                        yield "❌ Новый код не прошёл синтакс-проверку — авто-применение отменено."
            except Exception as e:
                log_error(f"Ошибка применения патча для {rel_path}: {e}")
                yield f"💥 Ошибка применения патча: {e}"
                # Fallback: пробуем исправить автоматически
                yield "🧯 Пытаюсь авто-исправить через ErrorDebugger/AIBugFixer…"
                fix_code: Optional[str] = None
                try:
                    fix_code = self.debugger.request_fix(rel_path, new_code, str(e))
                except Exception:
                    pass
                if not fix_code and auto_bugfix:
                    def _apply_attempt2(nc: str):
                        if auto_apply_patches:
                            self.patcher.confirm_and_apply_patch(abs_path, old_code, nc)
                        else:
                            self.patcher._save_diff(abs_path, old_code, nc)
                    def _on_error2(err: Exception, attempt: int):
                        log_warning(f"fallback bugfix attempt {attempt} failed for {rel_path}: {err}")
                    fix_code = self.bugfixer.iterative_fix_cycle(
                        file_path=rel_path,
                        summary=summary,
                        old_code=old_code,
                        apply_callback=_apply_attempt2,
                        on_error_callback=_on_error2
                    )
                if fix_code:
                    any_success = True
                    if auto_apply_patches:
                        yield f"✅ Исправление применено: {rel_path}"
                    else:
                        yield f"📝 Diff исправления сохранён (без применения): {rel_path}"
                else:
                    yield f"💥 Не удалось автоматически исправить: {rel_path}"

            processed += 1
            if processed % HEARTBEAT_EVERY == 0 or processed == chosen:
                yield f"⏳ Прогресс: {processed}/{chosen}"

        # 4) финальный статус
        if not any_success:
            msg = "⚠️ Самоусовершенствование завершено, но ни один файл не был улучшён."
            log_warning(msg)
            yield msg
        else:
            msg = "🧠 ✅ Самоусовершенствование завершено успешно!"
            log_info(msg)
            yield msg

    # ───────────────────────── утилиты ─────────────────────────

    def _collect_candidates_with_debug(
        self,
        *,
        root: str,
        include_exts: Iterable[str],
        exclude_abs: set[str],
        sensitive_abs: set[str],
    ) -> Tuple[List[str], Dict[str, int]]:
        """
        Возвращает (кандидаты, статистика отбора).
        Исключения проверяются как по абсолютному совпадению корня каталога, так и по префиксу поддерева.
        """
        base = os.path.abspath(os.path.join(self.project_root, root))
        result: List[str] = []
        stats = {
            "scanned_files": 0,
            "excluded_by_ext": 0,
            "excluded_by_exclude": 0,
            "excluded_by_sensitive": 0,
        }

        def _is_under(any_abs_dir: str, path_abs: str) -> bool:
            any_abs_dir = os.path.normpath(any_abs_dir)
            path_abs = os.path.normpath(path_abs)
            return path_abs == any_abs_dir or path_abs.startswith(any_abs_dir + os.sep)

        for dirpath, dirnames, filenames in os.walk(base):
            # режем обход сразу, чтобы не спускаться в отфильтрованные директории
            pruned: List[str] = []
            for d in list(dirnames):
                abs_dir = os.path.normpath(os.path.join(dirpath, d))
                if abs_dir in exclude_abs or any(_is_under(ex, abs_dir) for ex in exclude_abs):
                    pruned.append(d); continue
                if abs_dir in sensitive_abs or any(_is_under(sx, abs_dir) for sx in sensitive_abs):
                    pruned.append(d); continue
            for d in pruned:
                if d in dirnames:
                    dirnames.remove(d)

            # файлы
            for fn in filenames:
                abs_file = os.path.normpath(os.path.join(dirpath, fn))
                stats["scanned_files"] += 1

                if not fn.endswith(tuple(include_exts)):
                    stats["excluded_by_ext"] += 1
                    continue
                if any(_is_under(ex, abs_file) for ex in exclude_abs):
                    stats["excluded_by_exclude"] += 1
                    continue
                if any(_is_under(sx, abs_file) for sx in sensitive_abs):
                    stats["excluded_by_sensitive"] += 1
                    continue

                result.append(abs_file)

        # стабильно: ближе к корню раньше → удобнее читать диффы
        result.sort(key=lambda p: (_nice_rel(p, self.project_root).count(os.sep), p.lower()))
        return result, stats
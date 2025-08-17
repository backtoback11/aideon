import os
from datetime import datetime

from app.core.file_manager import FileManager
from app.modules.improver.project_scanner import ProjectScanner
from app.modules.improver.file_summarizer import FileSummarizer
from app.modules.improver.improvement_planner import ImprovementPlanner
from app.modules.improver.patch_requester import PatchRequester
from app.modules.improver.patcher import CodePatcher
from app.modules.improver.error_debugger import ErrorDebugger
from app.modules.analyzer import CodeAnalyzer
from app.logger import log_info, log_warning, log_error

class SelfImprover:
    """
    AI-модуль самоусовершенствования Aideon.
    Цикл:
    - сканирует проект с помощью ProjectScanner,
    - строит метасаммери каждого файла,
    - отправляет summary для генерации плана улучшений,
    - запрашивает обновлённый код,
    - сравнивает, применяет или отлаживает при ошибке.
    Может интегрироваться с ChatPanel для вывода GPT-запросов и ответов.
    """

    def __init__(self, config, chat_panel=None, apply_patches_automatically: bool = False):
        self.config = config
        self.file_manager = FileManager()
        self.chatgpt = CodeAnalyzer(config)
        self.backup_path = "app/backups"
        self.diff_path = "app/patches"
        os.makedirs(self.backup_path, exist_ok=True)
        os.makedirs(self.diff_path, exist_ok=True)
        self.summarizer = FileSummarizer()
        self.planner = ImprovementPlanner()
        self.requester = PatchRequester()
        self.patcher = CodePatcher(backup_dir=self.backup_path, diff_dir=self.diff_path)
        self.debugger = ErrorDebugger(self.chatgpt)
        self.chat_panel = chat_panel  # Для вывода GPT-запросов/ответов в интерфейс (может быть None)

        # Управление процессом
        self.stop_requested = False
        self.apply_patches_automatically = bool(apply_patches_automatically)

    def run_self_improvement(self):
        """
        Основной генератор логов/шагов самоусовершенствования.
        Выводит этапы в чат (если задан chat_panel).
        """
        log_info("🧠 ▶️ Запущен процесс самоусовершенствования Aideon...")
        yield "🧠 ▶️ Запущен процесс самоусовершенствования Aideon..."

        scanner = ProjectScanner(root_path="app")
        structure = scanner.scan()
        any_success = False

        for rel_dir, files in structure.items():
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

                old_code = self.file_manager.read_file(abs_path)
                if not old_code:
                    msg = f"⚠️ Пропущен файл (не читается): {full_path}"
                    log_warning(msg)
                    yield msg
                    continue

                # Шаг 1 — метасаммери
                summary = self.summarizer.summarize(full_path, old_code)
                msg = f"📄 Саммери: {full_path}\n{summary}"
                log_info(msg)
                yield msg

                # Шаг 2 — план улучшения (строим промт для GPT)
                prompt_plan = self.planner.build_prompt(full_path, summary)
                if self.chat_panel:
                    self.chat_panel.add_gpt_request(prompt_plan)
                try:
                    raw_response = self.chatgpt.chat(prompt_plan)
                    if self.chat_panel:
                        self.chat_panel.add_gpt_response(raw_response)
                except Exception as e:
                    msg = f"❌ Ошибка при запросе плана улучшения для {full_path}: {e}"
                    log_error(msg)
                    yield msg
                    continue

                plan_data = self.planner.extract_plan(raw_response)

                if not plan_data or not plan_data.get("plan"):
                    msg = f"❌ GPT не дал валидный план для: {full_path}"
                    log_error(msg)
                    yield msg
                    continue
                msg = f"💡 План улучшений для {full_path}:\n{plan_data['plan']}"
                log_info(msg)
                yield msg

                # Шаг 3 — патч (запрос нового кода)
                patch_prompt = self.requester.build_prompt(full_path, old_code, summary, plan_data)
                if self.chat_panel:
                    self.chat_panel.add_gpt_request(patch_prompt)
                try:
                    new_code = self.chatgpt.chat(patch_prompt)
                    if self.chat_panel:
                        self.chat_panel.add_gpt_response(new_code)
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
                try:
                    if self.apply_patches_automatically:
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
                        # Безопасный режим: только сохранить diff, не применяя
                        self.patcher._save_diff(abs_path, old_code, new_code)
                        msg = f"📝 Diff сохранён (без применения): {full_path}"
                        log_info(msg)
                        yield msg
                        any_success = True

                except Exception as e:
                    log_error(f"💥 Ошибка при применении патча: {e}")
                    fix_code = self.debugger.request_fix(
                        file_path=full_path,
                        original_code=new_code,
                        error_message=str(e)
                    )
                    if fix_code:
                        msg = f"🛠️ Попытка автоматического исправления кода для: {full_path}"
                        log_info(msg)
                        yield msg
                        try:
                            if self.apply_patches_automatically:
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

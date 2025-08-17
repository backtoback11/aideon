import json
import os
import time

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QFileDialog,
    QProgressBar, QCheckBox, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer

try:
    import psutil  # для мониторинга (если установлен psutil)
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from app.ui.analysis_thread import LoadAIThread  # Поток для фоновой загрузки
from app.modules.analyzer import CodeAnalyzer
from app.core.file_manager import FileManager


# Разрешённые расширения (код)
ALLOWED_EXTENSIONS = {".py", ".js", ".ts", ".java", ".cpp", ".cs", ".go", ".php"}
MAX_FILE_SIZE = 200 * 1024  # ~200 KB для примера


class ChatPanel(QWidget):
    """
    Панель «Чат» для:
      - ChatGPT (два варианта: «свободный чат» и «анализ кода»),
      - StarCoder (генерация кода).
      - + Оркестратор (демо-сценарий совместной работы GPT и StarCoder).
    """

    def __init__(
        self,
        config=None,
        panel_issues=None,
        panel_solutions=None,
        panel_process=None,
        panel_result=None,
        parent=None
    ):
        super().__init__(parent)

        self.config = config or {}
        self.analyzer = CodeAnalyzer(self.config)
        self.file_manager = FileManager()

        # Доп. панели
        self.panel_issues = panel_issues
        self.panel_solutions = panel_solutions
        self.panel_process = panel_process
        self.panel_result = panel_result

        # Оркестратор (пример полного сценария)
        self.orchestrator = Orchestrator(
            config=self.config,
            analyzer=self.analyzer,
            file_manager=self.file_manager
        )

        # Логика анализируемых файлов
        self.project_path = None
        self.project_files = []
        self.current_index = 0
        self.files_per_step = 3
        self.is_paused = False
        self.is_stopped = False

        # Мониторинг
        self.monitor_timer = None
        self.monitor_interval = 2000
        self.monitor_running = False

        # Поток фоновой загрузки (для лок. модели)
        self.load_ai_thread = None

        # Статистика
        self.total_tokens_processed = 0
        self.total_files_processed = 0

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # (1) Чат + лог
        layout.addWidget(QLabel("Чат для GPT / Анализа / StarCoder (генерация)"))
        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self.chat_log.setStyleSheet("background-color: #f4f4f4; padding: 5px;")
        layout.addWidget(self.chat_log)

        # Поле ввода + кнопки
        self.input_text = QTextEdit()
        self.input_text.setFixedHeight(50)

        self.send_chat_button = QPushButton("Отправить (ChatGPT - свободный)")
        self.send_chat_button.clicked.connect(self.handle_send_chat_gpt)

        self.send_analysis_button = QPushButton("Отправить (Анализ GPT)")
        self.send_analysis_button.clicked.connect(self.handle_send_analysis)

        self.generate_code_button = QPushButton("Сгенерировать (StarCoder)")
        self.generate_code_button.clicked.connect(self.handle_generate_code)

        row_top = QHBoxLayout()
        row_top.addWidget(self.input_text)
        row_top.addWidget(self.send_chat_button)
        row_top.addWidget(self.send_analysis_button)
        row_top.addWidget(self.generate_code_button)
        layout.addLayout(row_top)

        # (2) Управление AI (загрузить/выгрузить)
        ai_buttons_layout = QHBoxLayout()
        self.load_ai_button = QPushButton("Загрузить AI")
        self.load_ai_button.clicked.connect(self.handle_load_ai)

        self.unload_ai_button = QPushButton("Выгрузить AI")
        self.unload_ai_button.clicked.connect(self.handle_unload_ai)

        ai_buttons_layout.addWidget(self.load_ai_button)
        ai_buttons_layout.addWidget(self.unload_ai_button)
        layout.addLayout(ai_buttons_layout)

        self.model_load_progress = QProgressBar()
        self.model_load_progress.setRange(0, 100)
        self.model_load_progress.setValue(0)
        self.model_load_progress.setVisible(False)
        layout.addWidget(self.model_load_progress)

        # (3) Загрузка файлов/проекта + ручной анализ
        upload_file_button = QPushButton("Загрузить файл")
        upload_file_button.clicked.connect(self.handle_file_upload)

        upload_project_button = QPushButton("Загрузить проект")
        upload_project_button.clicked.connect(self.handle_project_upload)

        self.step_button = QPushButton("Анализ порции (вручную)")
        self.step_button.setEnabled(False)
        self.step_button.clicked.connect(lambda: self._analysis_loop(manual=True))

        row_files = QHBoxLayout()
        row_files.addWidget(upload_file_button)
        row_files.addWidget(upload_project_button)
        row_files.addWidget(self.step_button)
        layout.addLayout(row_files)

        # (4) Автоанализ
        self.start_button = QPushButton("Start Автоанализ")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_auto_analysis)

        self.pause_button = QPushButton("Пауза")
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.pause_analysis)

        self.resume_button = QPushButton("Продолжить")
        self.resume_button.setEnabled(False)
        self.resume_button.clicked.connect(self.resume_analysis)

        self.stop_button = QPushButton("Стоп")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_analysis)

        row_auto = QHBoxLayout()
        row_auto.addWidget(self.start_button)
        row_auto.addWidget(self.pause_button)
        row_auto.addWidget(self.resume_button)
        row_auto.addWidget(self.stop_button)
        layout.addLayout(row_auto)

        # (5) Переключение модели
        self.switch_ai_button = QPushButton(f"Текущая модель: {self.analyzer.model_mode}")
        self.switch_ai_button.clicked.connect(self.switch_ai_model)
        layout.addWidget(self.switch_ai_button)

        # (6) Оркестратор
        self.orchestrator_button = QPushButton("Запустить Оркестратор (Full Scenario)")
        self.orchestrator_button.clicked.connect(self.handle_orchestrator_scenario)
        layout.addWidget(self.orchestrator_button)

        # Прогресс-бар анализа
        self.analysis_progress_bar = QProgressBar()
        self.analysis_progress_bar.setRange(0, 100)
        self.analysis_progress_bar.setValue(0)
        layout.addWidget(self.analysis_progress_bar)

        self.analysis_stats_label = QLabel("Обработано файлов: 0, Токенов: 0")
        layout.addWidget(self.analysis_stats_label)

        # Мониторинг
        self.monitor_button = QPushButton("Включить мониторинг ресурсов")
        self.monitor_button.setCheckable(True)
        self.monitor_button.toggled.connect(self.toggle_monitor)
        layout.addWidget(self.monitor_button)

        self.resource_label = QLabel("Статистика: CPU: --%, RAM: -- MB")
        layout.addWidget(self.resource_label)

        self.limit_checkbox = QCheckBox("Разбивать крупные файлы (больше 1MB) на части")
        layout.addWidget(self.limit_checkbox)

        self.setLayout(layout)

    # ----------------------------------------------------------------
    # (Оркестратор) — запуск общего сценария
    # ----------------------------------------------------------------
    def handle_orchestrator_scenario(self):
        if not self.project_path:
            self._log_chat("<b>Сначала загрузите проект для оркестратора!</b>")
            return

        result_msg = self.orchestrator.run_big_scenario(self.project_path)
        self._log_chat(f"<b>Оркестратор завершил сценарий:</b>\n{result_msg}")

    # ----------------------------------------------------------------
    # (A) Свободный чат GPT
    # ----------------------------------------------------------------
    def handle_send_chat_gpt(self):
        import openai

        user_text = self.input_text.toPlainText().strip()
        if not user_text:
            return
        self.input_text.clear()

        self._log_chat(f"<b>Вы (GPT-свободный):</b> {user_text}")

        openai.api_key = self.analyzer.api_key
        try:
            resp = openai.ChatCompletion.create(
                model=self.analyzer.openai_model,
                messages=[
                    {"role": "system", "content": "Ты — Aideon, дружелюбный чат-ассистент."},
                    {"role": "user", "content": user_text}
                ],
                temperature=self.analyzer.temperature
            )
            gpt_answer = resp["choices"][0]["message"]["content"]
            self._log_chat(f"<b>GPT (свободный) ответ:</b> {gpt_answer}")

            # Проверяем, не предлагает ли GPT «Отправить задачу в StarCoder?»
            self._check_if_gpt_requests_starcoder(gpt_answer)

        except Exception as e:
            self._log_chat(f"<b>Ошибка свободного GPT-чата:</b> {e}")

    def _check_if_gpt_requests_starcoder(self, gpt_answer: str):
        if "Отправить задачу в StarCoder?" in gpt_answer:
            ret = QMessageBox.question(
                self,
                "Подтвердите StarCoder",
                "GPT предлагает сгенерировать код? Выполнить?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if ret == QMessageBox.StandardButton.Yes:
                self._log_chat("<i>Ок, генерируем код StarCoder.</i>")
                # Пример prompt — вы бы взяли из gpt_answer или спросили у юзера
                prompt_for_starcoder = "def hello_world():\n    print('Hello!')"
                code = self.analyzer.generate_code_star_coder(prompt_for_starcoder)
                self._log_chat("<b>StarCoder (результат):</b>")
                self._log_chat(f"<pre><code>{code}</code></pre>")
            else:
                self._log_chat("<i>Пользователь отказался от StarCoder.</i>")

    # ----------------------------------------------------------------
    # (B) Анализ кода (GPT / StarCoder, JSON)
    # ----------------------------------------------------------------
    def handle_send_analysis(self):
        user_text = self.input_text.toPlainText().strip()
        if not user_text:
            return
        self.input_text.clear()

        self._log_chat(f"<b>Вы (анализ GPT):</b> {user_text}")

        response_text = self.analyzer.analyze_code(user_text, file_path=None)
        approx_tokens = len(user_text.split())
        self.total_tokens_processed += approx_tokens
        self.update_analysis_stats()

        self.process_ai_response(response_text)

    # ----------------------------------------------------------------
    # (C) Генерация кода StarCoder
    # ----------------------------------------------------------------
    def handle_generate_code(self):
        prompt_text = self.input_text.toPlainText().strip()
        if not prompt_text:
            self._log_chat("<b>Нет инструкции для StarCoder</b>")
            return
        self.input_text.clear()

        self._log_chat(f"<b>Запрос для StarCoder:</b>\n{prompt_text}")
        code_result = self.analyzer.generate_code_star_coder(prompt_text)
        self._log_chat("<b>Результат StarCoder:</b>")
        self._log_chat(f"<pre><code>{code_result}</code></pre>")

    # ----------------------------------------------------------------
    # Загрузка / выгрузка AI
    # ----------------------------------------------------------------
    def handle_load_ai(self):
        self._log_chat("<b>Начинаем фоновую загрузку AI...</b>")
        self._log_process("Фоновая загрузка модели...")

        self.model_load_progress.setValue(0)
        self.model_load_progress.setVisible(True)
        self.load_ai_button.setEnabled(False)
        self.unload_ai_button.setEnabled(False)

        mode = self.analyzer.model_mode
        self.load_ai_thread = LoadAIThread(self.analyzer, mode, parent=self)
        self.load_ai_thread.loading_progress.connect(self.on_model_loading_progress)
        self.load_ai_thread.loading_finished.connect(self.on_model_loading_finished)
        self.load_ai_thread.loading_error.connect(self.on_model_loading_error)
        self.load_ai_thread.start()

    def on_model_loading_progress(self, pct: int):
        self._log_process(f"Прогресс загрузки: {pct}%")
        self.model_load_progress.setValue(pct)

    def on_model_loading_finished(self, success: bool):
        if success:
            self._log_chat("<b>AI модель успешно загружена!</b>")
            self._log_process("Фоновая загрузка: успех.")
            hist_entry = {
                "action": "model_loaded",
                "mode": self.analyzer.model_mode,
                "time": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            self._save_to_history(hist_entry)
        else:
            self._log_chat("<b>Не удалось загрузить AI модель!</b>")
            self._log_process("Фоновая загрузка: ошибка.")

        self.model_load_progress.setVisible(False)
        self.model_load_progress.setValue(0)
        self.load_ai_button.setEnabled(True)
        self.unload_ai_button.setEnabled(True)

    def on_model_loading_error(self, error_text: str):
        self._log_chat(f"<b>Ошибка загрузки модели:</b> {error_text}")
        self._log_process(f"Ошибка загрузки: {error_text}")

    def handle_unload_ai(self):
        self._log_chat("<b>Выгружаем AI модель...</b>")
        self._log_process("Выгрузка локальной модели...")
        try:
            self.analyzer.unload_local_model()
            self._log_chat("<b>Модель выгружена!</b>")
            self._log_process("Локальная модель выгружена.")
            hist_entry = {
                "action": "model_unloaded",
                "mode": self.analyzer.model_mode,
                "time": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            self._save_to_history(hist_entry)
        except Exception as e:
            self._log_chat(f"<b>Ошибка выгрузки модели:</b> {e}")
            self._log_process(f"Ошибка при выгрузке: {e}")

    # ----------------------------------------------------------------
    # Переключение модели (ChatGPT / StarCoder)
    # ----------------------------------------------------------------
    def switch_ai_model(self):
        self.stop_analysis()
        self.handle_unload_ai()

        modes = ["ChatGPT", "StarCoder"]
        current_mode = self.analyzer.model_mode
        if current_mode not in modes:
            current_mode = "ChatGPT"

        idx = modes.index(current_mode)
        next_idx = (idx + 1) % len(modes)
        new_mode = modes[next_idx]

        try:
            self.analyzer.switch_model(new_mode)
            self.switch_ai_button.setText(f"Текущая модель: {self.analyzer.model_mode}")
            self._log_chat(f"<b>Переключено на {new_mode} (AI ещё не загружен)</b>")
            self._log_process(f"Режим модели переключён: {new_mode}")
        except ValueError as e:
            self._log_chat(f"<b>Ошибка переключения модели:</b> {e}")
            self._log_process(f"Ошибка переключения модели: {e}")

    # ----------------------------------------------------------------
    # Загрузка файлов/проекта (БЕЗ автозапуска анализа)
    # ----------------------------------------------------------------
    def handle_file_upload(self):
        """
        Загружаем файл(ы) в песочницу, 
        НО не анализируем автоматически.
        """
        from_path_list = self.file_manager.open_file_dialog(multiple=True)
        if not from_path_list:
            return

        for from_path in from_path_list:
            saved_file = self.file_manager.save_file(from_path)
            if not saved_file:
                self._log_process(f"Не удалось сохранить файл: {from_path}")
                continue

            splitted_paths = self._split_file_if_needed(saved_file)
            for sp in splitted_paths:
                self._log_chat(f"<b>Файл загружен (без анализа):</b> {sp}")
                # Не вызываем analyze_code()

    def handle_project_upload(self):
        """
        Загружаем проект, собираем список code_files,
        НЕ анализируем автоматически — только готовим project_files.
        """
        project_path = self.file_manager.open_project_dialog()
        if not project_path:
            return

        self.project_path = project_path
        self._log_chat(f"<b>Проект загружен (без анализа):</b> {project_path}")

        tree_dict = self.file_manager.get_project_tree(project_path)
        raw_list = []
        for folder, files_in in tree_dict.items():
            for fn in files_in:
                full_path = os.path.join(folder, fn) if folder != "." else fn
                raw_list.append(full_path)

        code_files = []
        for rel_path in raw_list:
            abs_path = os.path.join(project_path, rel_path)
            splitted_paths = self._split_file_if_needed(abs_path)
            for sp in splitted_paths:
                if os.path.exists(sp) and self._is_code_file(sp):
                    code_files.append(os.path.relpath(sp, project_path))
                else:
                    self._log_process(f"Пропущен файл {sp}")

        self.project_files = code_files
        self.current_index = 0
        if code_files:
            self.step_button.setEnabled(True)
            self.start_button.setEnabled(True)

        hist_entry = {
            "action": "project_loaded",
            "project_path": project_path,
            "project_tree": tree_dict
        }
        self._save_to_history(hist_entry)

        self._log_chat(f"Проект загружен с {len(code_files)} кодовыми файлами (без анализа).")

    def _split_file_if_needed(self, path: str) -> list[str]:
        if not self.limit_checkbox.isChecked():
            return [path]

        one_mb = 1024 * 1024
        if os.path.getsize(path) <= one_mb:
            return [path]

        parts = []
        base = path + ".part"
        idx = 0
        with open(path, "rb") as f:
            while True:
                chunk = f.read(one_mb)
                if not chunk:
                    break
                part_name = f"{base}{idx}"
                with open(part_name, "wb") as pf:
                    pf.write(chunk)
                parts.append(part_name)
                idx += 1
        return parts

    def _is_code_file(self, path: str) -> bool:
        ext = os.path.splitext(path)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False
        if os.path.getsize(path) > MAX_FILE_SIZE:
            return False
        return True

    # ----------------------------------------------------------------
    # Ручной / Автоанализ (по кнопкам)
    # ----------------------------------------------------------------
    def start_auto_analysis(self):
        if not self.project_files:
            self._log_chat("<b>Нет файлов для анализа!</b>")
            return

        self._log_chat("<b>Автоанализ начат</b>")
        self._log_process("Автоанализ проекта.")
        self.is_paused = False
        self.is_stopped = False

        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.resume_button.setEnabled(False)
        self.start_button.setEnabled(False)

        self._analysis_loop(manual=False)

    def pause_analysis(self):
        self.is_paused = True
        self._log_chat("<b>Анализ приостановлен</b>")
        self._log_process("Пауза анализа.")
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(True)

    def resume_analysis(self):
        self.is_paused = False
        self._log_chat("<b>Возобновляем автоанализ...</b>")
        self._log_process("Продолжаем анализ.")
        self.pause_button.setEnabled(True)
        self.resume_button.setEnabled(False)
        self._analysis_loop(manual=False)

    def stop_analysis(self):
        self.is_stopped = True
        self._log_chat("<b>Анализ остановлен</b>")
        self._log_process("Анализ остановлен.")
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.start_button.setEnabled(True)

    def _analysis_loop(self, manual=False):
        total_files = len(self.project_files)
        while True:
            if self.is_stopped:
                self._log_process("Прерываем цикл анализа (Stop).")
                break
            if self.is_paused:
                self._log_process("Анализ на паузе, ждём Resume...")
                break
            if self.current_index >= total_files:
                self._log_chat("<b>Анализ проекта завершён!</b>")
                self._log_process("Все файлы обработаны.")
                self.pause_button.setEnabled(False)
                self.resume_button.setEnabled(False)
                self.stop_button.setEnabled(False)
                self.start_button.setEnabled(True)
                self.analysis_progress_bar.setValue(100)
                break

            start_idx = self.current_index
            end_idx = min(start_idx + self.files_per_step, total_files)
            batch = self.project_files[start_idx:end_idx]
            self.current_index = end_idx

            if manual:
                self._log_chat(f"<b>(Ручной) Файлы {start_idx+1}–{end_idx}/{total_files}</b>")
                self._log_process(f"Ручной анализ: {start_idx+1}–{end_idx}")
            else:
                self._log_chat(f"<b>(Авто) Файлы {start_idx+1}–{end_idx}/{total_files}</b>")
                self._log_process(f"Автоанализ: {start_idx+1}–{end_idx}")

            # Прогресс
            percent = int((end_idx / total_files) * 100)
            self.analysis_progress_bar.setValue(percent)

            for rel_path in batch:
                abs_path = os.path.join(self.project_path, rel_path)
                content = self.file_manager.read_file(abs_path)
                if not content:
                    self._log_process(f"Пустой/нечитаемый: {rel_path}")
                    continue

                self._log_process(f"Анализ: {rel_path}")
                response_text = self.analyzer.analyze_code(content, file_path=abs_path)

                # Подсчёт токенов
                approx_tokens = len(content.split())
                self.total_tokens_processed += approx_tokens
                self.total_files_processed += 1
                self.update_analysis_stats()

                self.process_ai_response(response_text)

            hist_entry = {
                "action": "analyze_chunk",
                "files": batch,
                "start_index": start_idx,
                "end_index": end_idx,
                "time": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            self._save_to_history(hist_entry)

            if manual:
                break

    def update_analysis_stats(self):
        txt = f"Обработано файлов: {self.total_files_processed}, Токенов: {self.total_tokens_processed}"
        self.analysis_stats_label.setText(txt)

    # ----------------------------------------------------------------
    # Вывод результата (JSON → панели)
    # ----------------------------------------------------------------
    def process_ai_response(self, ai_msg: str):
        try:
            data = json.loads(ai_msg)
            if "chat" in data:
                self._log_chat(f"<b>Aideon:</b> {data['chat']}")

            if self.panel_issues and "problems" in data:
                self.panel_issues.setText(data["problems"])
            if self.panel_solutions and "plan" in data:
                self.panel_solutions.setText(data["plan"])
            if self.panel_process and "process" in data:
                self.panel_process.setText(data["process"])
            if self.panel_result and "result" in data:
                self.panel_result.setText(data["result"])

            if "code" in data and data["code"]:
                self._log_chat("<b>AI сгенерировал код (анализ):</b>\n")
                self._log_chat(f"<pre><code>{data['code']}</code></pre>")

            if "errors" in data:
                self._log_chat(f"<b>Ошибки:</b> {data['errors']}")
            if "warnings" in data:
                self._log_chat(f"<b>Предупреждения:</b> {data['warnings']}")
        except json.JSONDecodeError:
            self._log_chat(f"<b>Ошибка JSON:</b> {ai_msg}")
            self._log_process("Возможно plain-текст или результат чанков.")

    # ----------------------------------------------------------------
    # Мониторинг ресурсов
    # ----------------------------------------------------------------
    def toggle_monitor(self, checked: bool):
        if checked:
            self.monitor_button.setText("Выключить мониторинг ресурсов")
            self._start_resource_monitor()
        else:
            self.monitor_button.setText("Включить мониторинг ресурсов")
            self._stop_resource_monitor()

    def _start_resource_monitor(self):
        if self.monitor_running:
            return
        self.monitor_running = True
        self.monitor_timer = QTimer(self)
        self.monitor_timer.setInterval(self.monitor_interval)
        self.monitor_timer.timeout.connect(self._update_resource_stats)
        self.monitor_timer.start()
        self._log_process("Мониторинг: включён.")

    def _stop_resource_monitor(self):
        self.monitor_running = False
        if self.monitor_timer:
            self.monitor_timer.stop()
            self.monitor_timer = None
        self.resource_label.setText("Статистика: CPU: --%, RAM: -- MB")
        self._log_process("Мониторинг: выключен.")

    def _update_resource_stats(self):
        if not PSUTIL_AVAILABLE:
            self.resource_label.setText("psutil не установлен.")
            return
        cpu_percent = psutil.cpu_percent(interval=None)
        mem_info = psutil.virtual_memory()
        ram_mb = int(mem_info.used / (1024 * 1024))
        self.resource_label.setText(f"CPU: {cpu_percent:.1f}%, RAM: {ram_mb} MB")

    # ----------------------------------------------------------------
    # Лог / История
    # ----------------------------------------------------------------
    def _log_chat(self, msg: str):
        self.chat_log.append(msg)
        self.chat_log.verticalScrollBar().setValue(
            self.chat_log.verticalScrollBar().maximum()
        )

    def _log_process(self, msg: str):
        if self.panel_process and hasattr(self.panel_process, "log_output"):
            self.panel_process.log_output.append(msg)
        else:
            self._log_chat(f"<i>{msg}</i>")

    def _save_to_history(self, entry: dict):
        history_path = "app/logs/history.json"
        if not os.path.exists(history_path):
            hist = []
        else:
            with open(history_path, "r", encoding="utf-8") as f:
                hist = json.load(f)

        hist.append(entry)
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(hist, f, indent=4, ensure_ascii=False)


# =============================================================================
# Пример класса Orchestrator
# =============================================================================

class Orchestrator:
    """
    Пример «оркестратора»:
    - Делает сводку (summaries) через GPT
    - Запрашивает GPT план
    - При необходимости генерирует код StarCoder
    - Сохраняет всё в orch_data.json
    """

    def __init__(self, config, analyzer, file_manager):
        self.config = config
        self.analyzer = analyzer
        self.file_manager = file_manager
        self.orch_data_path = "app/logs/orch_data.json"

    def run_big_scenario(self, project_path):
        """
        1) Создать сводку проекта
        2) Спросить GPT, что доработать?
        3) Если GPT говорит 'generate code', дернуть StarCoder
        4) Сохранить
        """
        tree_dict = self.file_manager.get_project_tree(project_path)
        summary_text = self._create_project_summary(tree_dict)

        gpt_plan = self._ask_gpt_for_plan(summary_text)

        code_result = ""
        if "generate code" in gpt_plan.lower():
            prompt = "def auto_generated():\n    print('Generated by StarCoder')"
            code_result = self.analyzer.generate_code_star_coder(prompt)

        scenario_result = {
            "project_path": project_path,
            "summary_text": summary_text,
            "gpt_plan": gpt_plan,
            "starcoder_result": code_result
        }
        self._save_orch_data(scenario_result)

        return (
            f"Проект: {project_path}\n\n"
            f"Summaries:\n{summary_text}\n\n"
            f"GPT plan:\n{gpt_plan}\n\n"
            f"StarCoder:\n{code_result}"
        )

    def _create_project_summary(self, tree_dict):
        lines = []
        for folder, files_in in tree_dict.items():
            for fn in files_in:
                lines.append(f"{folder}/{fn}")
        summary_str = "\n".join(lines)
        return "Список файлов:\n" + summary_str

    def _ask_gpt_for_plan(self, summary_text):
        import openai
        if self.analyzer.api_key is None:
            return "Нет openai_api_key, GPT не доступен"
        openai.api_key = self.analyzer.api_key

        prompt = (
            f"Имеется проект со структурой:\n{summary_text}\n\n"
            "Подскажи, что можно улучшить? Если нужно — напиши 'generate code'."
        )
        try:
            resp = openai.ChatCompletion.create(
                model=self.analyzer.openai_model,
                messages=[
                    {"role": "system", "content": "Ты — Aideon Orchestrator"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            return resp["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Ошибка GPT: {e}"

    def _save_orch_data(self, scenario_result):
        if not os.path.exists(self.orch_data_path):
            data = []
        else:
            with open(self.orch_data_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except:
                    data = []

        data.append(scenario_result)
        with open(self.orch_data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
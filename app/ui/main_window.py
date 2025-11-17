from __future__ import annotations

import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QMenuBar,
    QPushButton, QTextEdit, QHBoxLayout, QLabel, QSplitter, QTabWidget,
    QInputDialog, QMessageBox, QToolBar
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QSettings, Qt

from .chat_panel import ChatPanel
from app.modules.self_improver import SelfImprover
from app.modules.improver.project_scanner import ProjectScanner
from app.modules.analyzer import CodeAnalyzer

# безопасные геттеры параметров
from app.modules.utils import load_api_key, load_model_name, load_temperature

# ----- Агент и его совместимые зависимости (мягкие импорты) -----
try:
    from app.agent.agent import AideonAgent  # type: ignore
except Exception:
    AideonAgent = None  # type: ignore

try:
    from app.agent.bridge_self_improver import SelfImproverBridge  # type: ignore
except Exception:
    SelfImproverBridge = None  # type: ignore

try:
    from app.core.file_manager import FileManager, FileManagerConfig  # type: ignore
except Exception:
    FileManager = None  # type: ignore
    FileManagerConfig = None  # type: ignore

try:
    from app.modules.improver.patcher import CodePatcher  # type: ignore
except Exception:
    CodePatcher = None  # type: ignore


class SelfImproverPanel(QWidget):
    """
    Правая панель: модуль саморазвития (SelfImprover).
    Вкладки: процесс, метасаммери, AI-идеи, история, задачи.
    """
    def __init__(self, config: Dict[str, Any], chat_panel: Optional[ChatPanel] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.config = dict(config or {})
        self.chat_panel = chat_panel
        self.improver = SelfImprover(self.config, chat_panel=chat_panel)

        self.generator = None
        self.stopped = False

        # Инструменты
        self.code_analyzer = CodeAnalyzer(self.config)
        self.project_scanner = ProjectScanner(root_path="app")
        self.meta_summary_cache: Optional[Dict[str, Any]] = None

        # Данные для вкладок
        self.ai_ideas: List[str] = []
        self.history: List[str] = []
        self.tasks: List[str] = []

        self._init_ui()

    # ---------- UI ----------

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget(self)

        # Логи/вкладки
        self.log_output = self._make_tab("Процесс улучшения", "#f9f9f9")
        self.meta_output = self._make_tab("📊 Метасаммери проекта", "#eef5fa")
        self.ai_ideas_output = self._make_tab("💡 AI-идеи/Экспансия", "#e8faef")
        self.history_output = self._make_tab("🕓 История изменений", "#f5f0e6")
        self.tasks_output = self._make_tab("📝 Запросы/Задачи", "#f4eaff")

        header = QLabel("🤖 Саморазвитие Aideon")
        header.setStyleSheet("font-weight: 600;")
        layout.addWidget(header)
        layout.addWidget(self.tabs)

        # Кнопки
        btn_row = QHBoxLayout()
        self.run_btn = QPushButton("🔧 Запустить самоулучшение")
        self.run_btn.clicked.connect(self.start_manual_improvement)
        btn_row.addWidget(self.run_btn)

        self.next_btn = QPushButton("➡️ Далее")
        self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(self.do_next_step)
        btn_row.addWidget(self.next_btn)

        self.stop_btn = QPushButton("🛑 Стоп")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_process)
        btn_row.addWidget(self.stop_btn)

        self.meta_btn = QPushButton("📊 Метасаммери проекта")
        self.meta_btn.clicked.connect(self.show_meta_summary)
        btn_row.addWidget(self.meta_btn)

        self.add_idea_btn = QPushButton("💡+ AI-идея (вручную)")
        self.add_idea_btn.clicked.connect(self.add_ai_idea)
        btn_row.addWidget(self.add_idea_btn)

        self.auto_idea_btn = QPushButton("🤖 AI-сгенерировать идею")
        self.auto_idea_btn.clicked.connect(self.generate_ai_idea)
        btn_row.addWidget(self.auto_idea_btn)

        self.add_task_btn = QPushButton("📝+ Задача")
        self.add_task_btn.clicked.connect(self.add_task)
        btn_row.addWidget(self.add_task_btn)

        self.auto_task_btn = QPushButton("🤖 AI-задача по саммери")
        self.auto_task_btn.clicked.connect(self.generate_ai_task)
        btn_row.addWidget(self.auto_task_btn)

        layout.addLayout(btn_row)
        self.setLayout(layout)

    def _make_tab(self, title: str, bg: str) -> QTextEdit:
        widget = QTextEdit()
        widget.setReadOnly(True)
        widget.setStyleSheet(f"background-color: {bg}; font-family: monospace;")
        self.tabs.addTab(widget, title)
        return widget

    # ---------- Логика ----------

    def start_manual_improvement(self):
        self.tabs.setCurrentWidget(self.log_output)
        self.log_output.append("▶️ Запуск процесса самоулучшения...\n")
        try:
            self.generator = self.improver.run_self_improvement()
        except Exception as e:
            self.log_output.append(f"❌ Не удалось запустить процесс: {e}\n")
            self.reset_buttons()
            return
        self.stopped = False
        self.run_btn.setEnabled(False)
        self.next_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.do_next_step()

    def do_next_step(self):
        if self.stopped or not self.generator:
            self.log_output.append("🛑 Процесс был остановлен пользователем.\n")
            self.reset_buttons()
            return
        try:
            step = next(self.generator)
            if step:
                if not step.endswith("\n"):
                    step += "\n"
                self.log_output.append(step)
                self.history.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {step.strip()}")
                self.update_history_tab()
            if step and ("завершено" in step.lower()):
                self.reset_buttons()
        except StopIteration:
            self.log_output.append("🟢 Самоулучшение завершено.\n")
            self.reset_buttons()
        except ValueError:
            self.log_output.append("⚠️ Ошибка: повторный шаг до завершения предыдущего.\n")
            self.reset_buttons()
        except Exception as e:
            self.log_output.append(f"💥 Исключение в шаге: {e}\n")
            self.reset_buttons()

    def stop_process(self):
        self.stopped = True
        self.next_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.run_btn.setEnabled(True)
        try:
            self.improver.stop_requested = True
        except Exception:
            pass
        self.log_output.append("🛑 Самоулучшение остановлено.\n")

    def reset_buttons(self):
        self.next_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.run_btn.setEnabled(True)
        self.generator = None
        self.stopped = False

    # ---------- Метасаммери ----------

    def show_meta_summary(self):
        self.tabs.setCurrentWidget(self.meta_output)
        self.meta_output.clear()
        self.meta_output.append("📊 <b>Метасаммери по всем файлам:</b>\n")
        try:
            tree = self.project_scanner.scan()
        except Exception as e:
            self.meta_output.append(f"❌ Ошибка сканера проекта: {e}\n")
            return
        self.meta_summary_cache = tree
        import pprint
        for rel_dir, files in tree.items():
            self.meta_output.append(f"\n=== 📂 <b>{rel_dir}</b> ===")
            for f in files:
                summary = f.get("summary")
                summary_str = (
                    pprint.pformat(summary, compact=True, width=100)
                    if isinstance(summary, dict) else str(summary)
                )
                name = f.get("name", "unknown")
                self.meta_output.append(f"\n<b>{name}</b>:\n{summary_str}\n{'-'*50}")

    # ---------- Идеи ----------

    def add_ai_idea(self):
        idea, ok = QInputDialog.getText(self, "Добавить AI-идею", "Опишите идею:")
        if ok and idea.strip():
            entry = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {idea.strip()}"
            self.ai_ideas.append(entry)
            self.update_ai_ideas_tab()

    def generate_ai_idea(self):
        if not self.meta_summary_cache:
            self.show_meta_summary()
        text_summary = "\n".join(
            f"{f.get('name','?')}: {f.get('summary')}" for _, files in (self.meta_summary_cache or {}).items() for f in files
        )
        prompt = (
            "Проанализируй summary файлов проекта и предложи одну идею/модуль "
            "для усиления или расширения системы:\n\n"
            f"{text_summary}\n\nОтветь кратко:"
        )
        try:
            idea = self.code_analyzer.chat(prompt, system_msg="Ты — архитектор AI-модулей.")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка AI", f"Не удалось сгенерировать идею: {e}")
            return
        if idea:
            entry = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {idea.strip()}"
            self.ai_ideas.append(entry)
            self.update_ai_ideas_tab()
            QMessageBox.information(self, "AI-идея", f"AI-идея:\n{idea.strip()}")

    def update_ai_ideas_tab(self):
        self.ai_ideas_output.clear()
        self.ai_ideas_output.append("💡 <b>AI-идеи:</b>\n")
        for idea in self.ai_ideas:
            self.ai_ideas_output.append(f"{idea}\n{'-'*30}")

    # ---------- Задачи ----------

    def add_task(self):
        task, ok = QInputDialog.getText(self, "Добавить задачу", "Опишите задачу:")
        if ok and task.strip():
            entry = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {task.strip()}"
            self.tasks.append(entry)
            self.update_tasks_tab()

    def generate_ai_task(self):
        if not self.meta_summary_cache:
            self.show_meta_summary()
        text_summary = "\n".join(
            f"{f.get('name','?')}: {f.get('summary')}" for _, files in (self.meta_summary_cache or {}).items() for f in files
        )
        prompt = (
            "Посмотри на summary файлов и предложи одну актуальную задачу "
            "для развития проекта:\n\n"
            f"{text_summary}\n\nОтветь кратко:"
        )
        try:
            task = self.code_analyzer.chat(prompt, system_msg="Ты — AI-продукт менеджер.")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка AI", f"Не удалось сгенерировать задачу: {e}")
            return
        if task:
            entry = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {task.strip()}"
            self.tasks.append(entry)
            self.update_tasks_tab()
            QMessageBox.information(self, "AI-задача", f"AI-задача:\n{task.strip()}")

    def update_tasks_tab(self):
        self.tasks_output.clear()
        self.tasks_output.append("📝 <b>Задачи:</b>\n")
        for task in self.tasks:
            self.tasks_output.append(f"{task}\n{'-'*30}")

    # ---------- История ----------

    def update_history_tab(self):
        self.history_output.clear()
        self.history_output.append("🕓 <b>История изменений:</b>\n")
        for entry in self.history[-100:]:
            self.history_output.append(f"{entry}\n{'-'*30}")


class MainWindow(QMainWindow):
    """Главное окно Aideon 5.0"""
    def __init__(self, config: Optional[Dict[str, Any]] = None, agent: Optional["AideonAgent"] = None):
        super().__init__()
        self.config = self._load_config(config)

        self.setGeometry(100, 100, 1400, 850)
        self.setMinimumSize(1100, 650)
        self.setWindowTitle("Aideon 5.0")

        # 🔧 Агент
        self.agent: Optional["AideonAgent"] = agent
        self.agent_state: Optional[Dict[str, Any]] = None

        self._create_menu_bar()
        self._init_ui()
        self.ensure_agent_menu()
        self._create_agent_toolbar()
        self.load_settings()
        self._update_agent_badge()

    # --- публичный setter, если агент создаётся в main.py ---
    def set_agent(self, agent: Optional["AideonAgent"]) -> None:
        self.agent = agent
        self._update_agent_badge()

    # --- меню ---
    def _create_menu_bar(self):
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)

        # Файл
        file_menu = menubar.addMenu("Файл")
        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Контейнер «Агент»
        self._agent_menu_ref: Optional[Any] = menubar.addMenu("Агент")

    def ensure_agent_menu(self):
        """Создаёт/обновляет меню 'Агент'."""
        if not hasattr(self, "_agent_menu_ref") or self._agent_menu_ref is None:
            self._agent_menu_ref = self.menuBar().addMenu("Агент")
        agent_menu = self._agent_menu_ref
        agent_menu.clear()

        boot_action = QAction("🔎 Инициализировать (capabilities + skills)", self)
        boot_action.triggered.connect(self._agent_boot)
        agent_menu.addAction(boot_action)

        plan_action = QAction("📝 Построить план…", self)
        plan_action.triggered.connect(self._agent_plan_dialog)
        agent_menu.addAction(plan_action)

        run_action = QAction("▶️ Выполнить цель…", self)
        run_action.triggered.connect(self._agent_run_dialog)
        agent_menu.addAction(run_action)

    def _create_agent_toolbar(self):
        """Тулбар с действиями агента (виден всегда)."""
        tb = QToolBar("Агент", self)
        tb.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, tb)

        act_boot = QAction("Агент: Инициализировать", self)
        act_boot.triggered.connect(self._agent_boot)
        tb.addAction(act_boot)

        act_plan = QAction("Агент: План…", self)
        act_plan.triggered.connect(self._agent_plan_dialog)
        tb.addAction(act_plan)

        act_run = QAction("Агент: Выполнить…", self)
        act_run.triggered.connect(self._agent_run_dialog)
        tb.addAction(act_run)

    # --- основная раскладка ---
    def _init_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.chat_panel = ChatPanel(config=self.config, parent=self)
        self.self_improver_panel = SelfImproverPanel(config=self.config, chat_panel=self.chat_panel, parent=self)
        splitter.addWidget(self.chat_panel)
        splitter.addWidget(self.self_improver_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(splitter)
        self.setCentralWidget(central_widget)

    # --- settings ---
    def load_settings(self):
        settings = QSettings("Aideon", "Aideon5.0")
        if (geometry := settings.value("geometry")):
            self.restoreGeometry(geometry)
        if (window_state := settings.value("windowState")):
            self.restoreState(window_state)

    def save_settings(self):
        settings = QSettings("Aideon", "Aideon5.0")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)

    # ---------- Агент: helpers ----------

    def _ensure_agent(self):
        """Создаёт агента с максимальной совместимостью конструкторов."""
        if self.agent is not None:
            return

        if AideonAgent is None:
            raise RuntimeError("Модуль агента недоступен (AideonAgent not found).")

        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        policy_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agent", "policy_default.json"))

        fm = None
        bridge = None
        patcher = None

        try:
            if FileManager and FileManagerConfig:
                fm_cfg = FileManagerConfig(
                    base_dir=repo_root,
                    allowed_roots=[repo_root],
                    read_only_paths=[os.path.join(repo_root, ".git")],
                    backups_dirname=".aideon_backups",
                    create_missing_dirs=True,
                    atomic_write=True,
                )
                fm = FileManager(fm_cfg)
            if CodePatcher:
                try:
                    patcher = CodePatcher(file_manager=fm)  # type: ignore
                except TypeError:
                    patcher = CodePatcher()  # type: ignore
            if SelfImproverBridge:
                try:
                    bridge = SelfImproverBridge(file_manager=fm, patcher=patcher)  # type: ignore
                except TypeError:
                    try:
                        bridge = SelfImproverBridge(patcher=patcher)  # type: ignore
                    except Exception:
                        bridge = None
        except Exception:
            fm = None
            bridge = None
            patcher = None

        last_err: Optional[Exception] = None
        for kwargs in (
            dict(file_manager=fm, improver_bridge=bridge, policy_path=policy_path, config=self.config),
            dict(improver_bridge=bridge, policy_path=policy_path, config=self.config),
            dict(policy_path=policy_path, config=self.config),
            dict(policy_path=policy_path),
        ):
            try:
                self.agent = AideonAgent(**kwargs)  # type: ignore
                break
            except Exception as e:
                last_err = e
                self.agent = None

        if self.agent is None and last_err:
            raise last_err

    def _ensure_agent_boot(self):
        self._ensure_agent()
        if not self.agent:
            return
        if self.agent_state is None:
            try:
                if hasattr(self.agent, "boot"):
                    self.agent_state = self.agent.boot()  # type: ignore
                elif hasattr(self.agent, "initialize"):
                    self.agent_state = self.agent.initialize()  # type: ignore
                else:
                    self.agent_state = {}
            finally:
                self._update_agent_badge()

    def _append_to_chat(self, text: str):
        if hasattr(self.chat_panel, "append_assistant"):
            try:
                self.chat_panel.append_assistant(text)  # type: ignore
                return
            except Exception:
                pass
        try:
            QMessageBox.information(self, "Агент", text)
        except Exception:
            pass

    def _update_agent_badge(self):
        badge = "🧩 Агент: off"
        if self.agent_state is not None:
            badge = "🧩 Агент: ready"
        self.setWindowTitle(f"Aideon 5.0 — {badge}")

    # ---------- Агент: actions ----------

    def _agent_boot(self):
        try:
            self._ensure_agent_boot()
            if self.agent_state is not None:
                QMessageBox.information(self, "Агент", "Агент инициализирован (capabilities + skills).")
        except Exception as e:
            QMessageBox.critical(self, "Агент", f"Ошибка инициализации: {e}")

    def _agent_plan_dialog(self):
        try:
            self._ensure_agent_boot()
            if not self.agent:
                return
            goal, ok = QInputDialog.getText(self, "План агента", "Цель (goal):")
            if not ok or not goal.strip():
                return

            plan = None
            err: Optional[Exception] = None

            # 1) Новые API
            try:
                if hasattr(self.agent, "plan"):
                    plan = self.agent.plan(goal)  # type: ignore
            except Exception as e:
                err = e
                plan = None

            # 2) Современный планировщик
            if plan is None:
                try:
                    if hasattr(self.agent, "planner") and hasattr(self.agent.planner, "build_high_level_plan"):
                        plan = self.agent.planner.build_high_level_plan(goal=goal)  # type: ignore
                except Exception as e:
                    err = e
                    plan = None

            # 3) Совместимость со старым make_plan
            if plan is None:
                try:
                    if hasattr(self.agent, "planner") and hasattr(self.agent.planner, "make_plan"):
                        state = self.agent_state or {}
                        plan = self.agent.planner.make_plan([goal], state)  # type: ignore
                except Exception as e:
                    err = e
                    plan = None

            if not plan:
                msg = "План пуст.\nПроверь policy_default.json или задай более конкретную цель."
                if err:
                    msg += f"\nПоследняя ошибка: {err}"
                QMessageBox.warning(self, "Агент", msg)
                return

            pretty = json.dumps(plan, ensure_ascii=False, indent=2)
            self._append_to_chat(f"📝 План для цели:\n{pretty}")
        except Exception as e:
            QMessageBox.critical(self, "Агент", f"Ошибка построения плана: {e}")

    def _agent_run_dialog(self):
        try:
            self._ensure_agent_boot()
            if not self.agent:
                return
            goal, ok = QInputDialog.getText(self, "Выполнить цель", "Цель (goal):")
            if not ok or not goal.strip():
                return

            result = None
            err: Optional[Exception] = None

            # 1) Современный автономный ран
            try:
                if hasattr(self.agent, "run_autonomous"):
                    result = self.agent.run_autonomous(goal=goal, max_steps=8)  # type: ignore
            except Exception as e:
                err = e
                result = None

            # 2) Старый run_goals
            if result is None:
                try:
                    if hasattr(self.agent, "run_goals"):
                        result = self.agent.run_goals([goal])  # type: ignore
                except Exception as e:
                    err = e
                    result = None

            # 3) Очень старый execute
            if result is None:
                try:
                    if hasattr(self.agent, "execute"):
                        result = self.agent.execute(goal)  # type: ignore
                except Exception as e:
                    err = e
                    result = None

            if result is None:
                msg = "Агент не смог выполнить цель. Смотри app/logs/agent.jsonl и aideon.log."
                if err:
                    msg += f"\nПоследняя ошибка: {err}"
                QMessageBox.critical(self, "Агент", msg)
                return

            pretty = json.dumps(result, ensure_ascii=False, indent=2)
            self._append_to_chat(f"▶️ Результат выполнения:\n{pretty}")
            QMessageBox.information(self, "Агент", "Выполнение завершено. Результат выведен в чат.")
        except Exception as e:
            QMessageBox.critical(self, "Агент", f"Ошибка выполнения: {e}")

    # ---------- безопасная загрузка конфига ----------

    def _load_config(self, passed: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        cfg: Dict[str, Any] = {}
        if isinstance(passed, dict):
            cfg.update(passed)

        cfg_path_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config.json"))
        cfg = self._merge_json_safely(cfg, cfg_path_root)

        cfg_path_app = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "configs", "settings.json"))
        cfg = self._merge_json_safely(cfg, cfg_path_app)

        cfg["openai_api_key"] = load_api_key(cfg)
        cfg["model_name"] = load_model_name(cfg)
        cfg["temperature"] = load_temperature(cfg)

        return cfg

    def _merge_json_safely(self, base: Dict[str, Any], path: str) -> Dict[str, Any]:
        try:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    merged = dict(base)
                    merged.update(data)
                    return merged
        except Exception:
            pass
        return base
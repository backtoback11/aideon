import json
import time
import os
import openai

from app.modules.analyzer import CodeAnalyzer
from app.core.file_manager import FileManager


class Orchestrator:
    """
    Оркестратор проекта Aideon.
    Управляет вызовами к ChatGPT, анализом кода, формированием сценариев.
    """

    def __init__(self, config, analyzer=None, file_manager=None):
        self.config = config or {}

        # ChatGPT-анализатор
        self.chatgpt_analyzer = analyzer or CodeAnalyzer({**self.config, "model_mode": "ChatGPT"})

        # Менеджер файлов
        self.file_manager = file_manager or FileManager()

        # Путь к базам и журналам
        self.project_db = {}
        self.db_path = "app/logs/project_db.json"
        self.orch_data_path = "app/logs/orch_data.json"
        self._load_db()

    # ----------------------------------------------------------------
    # Работа с базой проектов
    # ----------------------------------------------------------------
    def _load_db(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    self.project_db = json.load(f)
            except json.JSONDecodeError:
                self.project_db = {}
        else:
            self.project_db = {}

    def _save_db(self):
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(self.project_db, f, indent=4, ensure_ascii=False)

    def add_project(self, project_name, sandbox_path):
        if project_name not in self.project_db:
            self.project_db[project_name] = {
                "sandbox_path": sandbox_path,
                "files": {},
                "history": []
            }
        self._save_db()

    def set_file_summary(self, project_name, file_path, summary_text):
        if project_name in self.project_db:
            self.project_db[project_name].setdefault("files", {})
            self.project_db[project_name]["files"][file_path] = {
                "summary": summary_text
            }
            self._save_db()

    def get_file_summary(self, project_name, file_path):
        return (
            self.project_db.get(project_name, {})
            .get("files", {})
            .get(file_path, {})
            .get("summary")
        )

    # ----------------------------------------------------------------
    # Работа с GPT
    # ----------------------------------------------------------------
    def ask_chatgpt(self, question):
        return self.chatgpt_analyzer.analyze_code(question)

    def create_file_summary(self, project_name, file_path):
        content = self.file_manager.read_file(file_path)
        if not content:
            return "Файл пуст или не читается"
        prompt = f"Прочти этот код и дай краткое summary:\n{content}"
        summary = self.ask_chatgpt(prompt)
        self.set_file_summary(project_name, file_path, summary)
        return summary

    # ----------------------------------------------------------------
    # Анализ проекта по чанкам
    # ----------------------------------------------------------------
    def analyze_project_chunks(self, project_path, max_tokens=25000, delay=60):
        tree_dict = self.file_manager.get_project_tree(project_path)
        overall_analysis = {}

        for folder, files in tree_dict.items():
            for f in files:
                file_path = os.path.join(project_path, folder, f) if folder != "." else os.path.join(project_path, f)
                content = self.file_manager.read_file(file_path)
                if not content:
                    continue

                chunks = self.chatgpt_analyzer._split_into_chunks(content, max_tokens)
                file_analysis = []

                for idx, chunk_text in enumerate(chunks, start=1):
                    prompt = (
                        f"Проанализируй следующий код из файла {file_path} "
                        f"(Чанк {idx}/{len(chunks)}):\n{chunk_text}"
                    )
                    try:
                        openai.api_key = self.chatgpt_analyzer.api_key
                        response = openai.ChatCompletion.create(
                            model=self.chatgpt_analyzer.openai_model,
                            messages=[
                                {"role": "system", "content": "Ты — AI-ассистент по анализу кода."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=self.chatgpt_analyzer.temperature
                        )
                        analysis_text = response["choices"][0]["message"]["content"]
                    except Exception as e:
                        analysis_text = f"Ошибка анализа: {e}"

                    file_analysis.append(f"[Чанк {idx}]\n{analysis_text}")
                    if idx < len(chunks):
                        time.sleep(delay)

                overall_analysis[file_path] = "\n\n".join(file_analysis)

        lines = ["Итоговый анализ проекта:\n"]
        for fp, analysis_str in overall_analysis.items():
            lines.append(f"\nФайл: {fp}\n{'-'*40}\n{analysis_str}\n{'-'*40}\n")
        return "".join(lines)

    # ----------------------------------------------------------------
    # Сценарий: обзор проекта, план, анализ, сохранение
    # ----------------------------------------------------------------
    def run_big_scenario(self, project_path):
        tree_dict = self.file_manager.get_project_tree(project_path)
        summary_text = self._create_project_summary(tree_dict)
        gpt_plan = self._ask_gpt_for_plan(summary_text)

        project_analysis = self.analyze_project_chunks(
            project_path=project_path,
            max_tokens=25000,
            delay=60
        )

        scenario_result = {
            "project_path": project_path,
            "summary_text": summary_text,
            "gpt_plan": gpt_plan,
            "project_analysis": project_analysis,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self._save_orch_data(scenario_result)

        return (
            f"Проект: {project_path}\n\n"
            f"Сводка:\n{summary_text}\n\n"
            f"GPT план:\n{gpt_plan}\n\n"
            f"Полный анализ проекта:\n{project_analysis}"
        )

    def _create_project_summary(self, tree_dict):
        lines = [f"{folder}/{fn}" for folder, files in tree_dict.items() for fn in files]
        return "Список файлов проекта:\n" + "\n".join(lines)

    def _ask_gpt_for_plan(self, summary_text):
        if not self.chatgpt_analyzer.api_key:
            return "Нет openai_api_key, GPT недоступен"

        openai.api_key = self.chatgpt_analyzer.api_key
        prompt = (
            "Ты — Aideon Orchestrator.\n"
            "У меня есть проект со структурой:\n"
            f"{summary_text}\n\n"
            "Подскажи, что можно улучшить или сгенерировать?\n"
            "Если нужно, напиши 'generate code'."
        )
        try:
            resp = openai.ChatCompletion.create(
                model=self.chatgpt_analyzer.openai_model,
                messages=[
                    {"role": "system", "content": "Ты — Aideon, помощник по анализу проектов."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.chatgpt_analyzer.temperature
            )
            return resp["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Ошибка GPT: {e}"

    def _save_orch_data(self, scenario_result):
        if not os.path.exists(self.orch_data_path):
            data = []
        else:
            try:
                with open(self.orch_data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                data = []

        data.append(scenario_result)
        with open(self.orch_data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
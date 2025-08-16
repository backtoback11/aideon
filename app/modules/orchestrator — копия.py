# app/modules/orchestrator.py

import json
import time
import os
import openai
from app.modules.analyzer import CodeAnalyzer
from app.core.file_manager import FileManager

class Orchestrator:
    """
    Оркестратор для управления проектами:
      - Формирование сводки проекта (summary) через ChatGPT
      - Запрос плана у ChatGPT
      - Анализ файлов проекта с разбивкой (чанкинг) и задержкой между запросами
      - При необходимости вызов генерации кода StarCoder
      - Сохранение всех результатов в orch_data.json (база проектов)
    """

    def __init__(self, config):
        self.config = config
        self.file_manager = FileManager()

        # Создаём два экземпляра анализатора для двух задач:
        # 1) chatgpt_analyzer – для аналитики (ChatGPT)
        # 2) starcoder_analyzer – для генерации кода (StarCoder)
        self.chatgpt_analyzer = CodeAnalyzer({**config, "model_mode": "ChatGPT"})
        self.starcoder_analyzer = CodeAnalyzer({**config, "model_mode": "StarCoder"})

        # Внутренняя база проектов (загружается из файла project_db.json)
        self.project_db = {}
        self.db_path = "app/logs/project_db.json"
        self._load_db()

        # Путь для сохранения данных оркестратора (сценариев)
        self.orch_data_path = "app/logs/orch_data.json"

    def _load_db(self):
        if os.path.exists(self.db_path):
            with open(self.db_path, "r", encoding="utf-8") as f:
                self.project_db = json.load(f)
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
            if file_path not in self.project_db[project_name]["files"]:
                self.project_db[project_name]["files"][file_path] = {}
            self.project_db[project_name]["files"][file_path]["summary"] = summary_text
            self._save_db()

    def get_file_summary(self, project_name, file_path):
        return self.project_db.get(project_name, {}).get("files", {}).get(file_path, {}).get("summary", None)

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

    def generate_code_starcoder(self, prompt_text):
        return self.starcoder_analyzer.generate_code_star_coder(prompt_text)

    def chatgpt_to_starcoder_flow(self, user_instructions):
        gpt_answer = self.ask_chatgpt(user_instructions)
        code_snippet = self._extract_code_from_json(gpt_answer)
        if not code_snippet:
            code_snippet = "print('Нет кода от GPT')"
        starcoder_code = self.generate_code_starcoder(code_snippet)
        return (gpt_answer, starcoder_code)

    def _extract_code_from_json(self, gpt_answer_str):
        try:
            data = json.loads(gpt_answer_str)
            return data.get("code", None)
        except:
            return None

    def analyze_project_chunks(self, project_path, max_tokens=25000, delay=60):
        """
        Анализирует проект, разбивая содержимое каждого файла на чанки (до max_tokens).
        Для каждого чанка:
          - Формируется промпт для анализа с указанием имени файла и номера чанка.
          - Отправляется запрос в ChatGPT через chatgpt_analyzer.
          - Ждёт delay секунд перед отправкой следующего чанка.
        Возвращает общий отчет по проекту.
        """
        tree_dict = self.file_manager.get_project_tree(project_path)
        overall_analysis = {}
        for folder, files in tree_dict.items():
            for f in files:
                # Формируем абсолютный путь к файлу
                file_path = os.path.join(project_path, folder, f) if folder != "." else os.path.join(project_path, f)
                content = self.file_manager.read_file(file_path)
                if not content:
                    continue
                # Разбиваем содержимое файла на чанки
                chunks = self.chatgpt_analyzer._split_into_chunks(content, max_tokens)
                file_analysis = []
                for idx, chunk in enumerate(chunks, start=1):
                    prompt = (
                        f"Проанализируй следующий код из файла {file_path} (Чанк {idx}/{len(chunks)}):\n{chunk}"
                    )
                    try:
                        response = openai.ChatCompletion.create(
                            model=self.chatgpt_analyzer.openai_model,
                            messages=[
                                {"role": "system", "content": "Ты — AI-ассистент по анализу кода."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=self.chatgpt_analyzer.temperature
                        )
                        analysis = response["choices"][0]["message"]["content"]
                    except Exception as e:
                        analysis = f"Ошибка анализа: {e}"
                    file_analysis.append(analysis)
                    # Задержка между запросами
                    time.sleep(delay)
                overall_analysis[file_path] = "\n\n".join(file_analysis)
        # Формируем итоговый отчет
        report = "Итоговый анализ проекта:\n"
        for fp, analysis in overall_analysis.items():
            report += f"\n\nФайл: {fp}\n{'-'*40}\n{analysis}\n{'-'*40}\n"
        return report

    def run_big_scenario(self, project_path):
        """
        Полный сценарий анализа проекта:
          1) Формирование сводки проекта (список файлов).
          2) Запрос у ChatGPT рекомендаций по доработке.
          3) Анализ проекта с использованием чанкинга (анализ каждого файла).
          4) Сохранение результатов в базу оркестратора.
          5) Возврат итогового отчёта.
        """
        tree_dict = self.file_manager.get_project_tree(project_path)
        summary_text = self._create_project_summary(tree_dict)
        gpt_plan = self._ask_gpt_for_plan(summary_text)
        project_analysis = self.analyze_project_chunks(project_path)
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
        lines = []
        for folder, files in tree_dict.items():
            for fn in files:
                lines.append(f"{folder}/{fn}")
        summary_str = "\n".join(lines)
        return "Список файлов проекта:\n" + summary_str

    def _ask_gpt_for_plan(self, summary_text):
        if self.chatgpt_analyzer.api_key is None:
            return "Нет openai_api_key, GPT не доступен"
        openai.api_key = self.chatgpt_analyzer.api_key
        prompt = (
            f"Ты — Aideon Orchestrator.\n"
            "У меня есть проект со следующей структурой:\n"
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
            with open(self.orch_data_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except:
                    data = []
        data.append(scenario_result)
        with open(self.orch_data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
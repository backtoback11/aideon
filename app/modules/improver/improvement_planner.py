# app/modules/improver/improvement_planner.py
from __future__ import annotations

import json
import re
from typing import Optional, Dict, Any, List, Union


class ImprovementPlanner:
    """
    Строит промпт для GPT, чтобы получить план улучшений по саммери кода.
    Возвращает строковый промпт (совместимо с CodeAnalyzer.chat).
    Умеет надёжно извлекать {"plan","comment"} из «болтливых» ответов.
    Поддерживает оба формата плана: строка или список шагов.
    """

    SYSTEM_MSG = (
        "Ты — эксперт по улучшению Python-кода. "
        "Тебе дают краткое описание файла проекта. "
        "Нужно предложить улучшения логики, устойчивости, читаемости и архитектуры. "
        "Отвечай строго JSON без пояснений вне JSON. "
        "Допустимые форматы:\n"
        "1) {\"plan\": \"многострочный текст\", \"comment\": \"краткая суть\"}\n"
        "2) {\"plan\": [{\"step\": 1, \"action\": \"...\", \"details\": \"...\"}, ...], \"comment\": \"...\"}\n"
        "Ключи обязательны: plan, comment."
    )

    def build_prompt(self, file_path: str, summary: str) -> str:
        """
        Возвращает ЕДИНУЮ строку-подсказку для CodeAnalyzer.chat(prompt, system_msg=...).
        Не используем списки сообщений — это устраняет ошибки новых SDK.
        """
        return (
            f"Путь к файлу: {file_path}\n\n"
            f"Описание файла:\n{summary}\n\n"
            "Сформулируй предложения по улучшению. "
            "Ответ строго в формате JSON (без кода и Markdown-разметки, без пояснений вне JSON). "
            "Разрешены два варианта:\n"
            "{\n"
            '  "plan": "пошаговый план улучшений (многострочный текст)",\n'
            '  "comment": "краткая суть предлагаемых изменений"\n'
            "}\n"
            "ИЛИ\n"
            "{\n"
            '  "plan": [\n'
            '    {"step": 1, "action": "что сделать", "details": "зачем/как"},\n'
            '    {"step": 2, "action": "...", "details": "..."}\n'
            "  ],\n"
            '  "comment": "краткая суть предлагаемых изменений"\n'
            "}\n"
        )

    # ── Дополнительно: если где-то в проекте хочется именно messages (например, для логов/панели) ──
    def build_messages(self, file_path: str, summary: str) -> list[dict]:
        """
        Опционально собирает messages (для отображения в UI). Для реального вызова модели
        используйте build_prompt + CodeAnalyzer.chat(prompt, system_msg=SYSTEM_MSG).
        """
        return [
            {"role": "system", "content": self.SYSTEM_MSG},
            {"role": "user", "content": self.build_prompt(file_path, summary)},
        ]

    def extract_plan(self, gpt_response: str) -> Optional[Dict[str, Any]]:
        """
        Пытается распарсить JSON-ответ и извлечь поля "plan" и "comment".
        Очень терпеливая обработка: срезает кодовые блоки, ищет подстроку {…}, чинит одинарные кавычки.
        Возвращает словарь {"plan": <str>, "comment": <str>} или None при ошибке.
        """
        if not gpt_response:
            return None

        text = gpt_response.strip()

        # 1) убрать возможные ```json ... ``` обёртки
        fence = re.compile(r"^```(?:json)?\s*([\s\S]*?)\s*```$", re.IGNORECASE)
        m = fence.match(text)
        if m:
            text = m.group(1).strip()

        # 2) если это уже валидный JSON
        data = self._try_json(text)
        data = self._massage_keys(data)  # подхват нестандартных ключей
        if self._valid_plan(data):
            return self._normalize_plan(data)

        # 3) попробовать вытащить самую большую { … } подстроку
        brace_extract = self._extract_braced_json(text)
        data = self._try_json(brace_extract)
        data = self._massage_keys(data)
        if self._valid_plan(data):
            return self._normalize_plan(data)

        # 4) грубая замена одинарных кавычек → двойные (внутри извлечённого блока)
        if brace_extract:
            fixed = self._single_to_double_quotes(brace_extract)
            data = self._try_json(fixed)
            data = self._massage_keys(data)
            if self._valid_plan(data):
                return self._normalize_plan(data)

        # 5) как крайняя мера — попытка вытащить план по ключевым словам
        heuristic = self._heuristic_extract(text)
        if heuristic:
            return heuristic

        return None

    # ── helpers ─────────────────────────────────────────────────────────────────

    def _try_json(self, s: Optional[str]) -> Optional[Dict[str, Any]]:
        if not s:
            return None
        try:
            obj = json.loads(s)
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None

    def _valid_plan(self, data: Optional[Dict[str, Any]]) -> bool:
        """
        Валиден, если есть ключи plan и comment.
        plan может быть строкой ИЛИ непустым списком.
        """
        if not isinstance(data, dict):
            return False
        keys = {k.lower(): k for k in data.keys()}
        if "plan" not in keys or "comment" not in keys:
            return False
        plan_val = data[keys["plan"]]
        if isinstance(plan_val, str):
            return plan_val.strip() != ""
        if isinstance(plan_val, list):
            return len(plan_val) > 0
        return False

    def _massage_keys(self, data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Мягкая адаптация: если модель прислала, например, "steps" без "plan", переложим в "plan".
        """
        if not isinstance(data, dict):
            return data
        if "plan" not in data and "steps" in data:
            data = dict(data)
            data["plan"] = data.pop("steps")
        return data

    def _normalize_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Нормализуем ключи к "plan" и "comment" и приводим plan к строке.
        Поддерживает:
          - plan: "текст плана"
          - plan: [{step, action, details}, ...] | ["шаг 1", "..."]
        """
        # 1) нормализуем ключи
        key_map = {}
        for k in data.keys():
            lk = k.lower().strip()
            if lk in ("plan", "план", "steps"):
                key_map["plan"] = k
            elif lk in ("comment", "комментарий", "summary", "resume", "суть"):
                key_map["comment"] = k

        plan_raw: Union[str, List[Any], None] = data.get(key_map.get("plan", ""), "")
        comment_raw: Any = data.get(key_map.get("comment", ""), "")

        # 2) приводим plan к строке
        plan_text: str = ""
        if isinstance(plan_raw, str):
            plan_text = plan_raw.strip()
        elif isinstance(plan_raw, list):
            lines: List[str] = []
            for i, item in enumerate(plan_raw, start=1):
                if isinstance(item, dict):
                    step_num = item.get("step", i)
                    action = str(item.get("action", "")).strip()
                    details = str(item.get("details", "")).strip()
                    if action and details:
                        lines.append(f"{step_num}. {action} — {details}")
                    elif action:
                        lines.append(f"{step_num}. {action}")
                    elif details:
                        lines.append(f"{step_num}. {details}")
                    else:
                        lines.append(f"{step_num}. (empty step)")
                else:
                    lines.append(f"{i}. {str(item).strip()}")
            plan_text = "\n".join(lines).strip()
        else:
            plan_text = ""

        return {
            "plan": plan_text,
            "comment": str(comment_raw).strip() if comment_raw is not None else "",
        }

    def _extract_braced_json(self, s: str) -> Optional[str]:
        """
        Возвращает наибольший фрагмент, ограниченный фигурными скобками { … }.
        """
        start = s.find("{")
        last = s.rfind("}")
        if start == -1 or last == -1 or last <= start:
            return None
        return s[start:last + 1]

    def _single_to_double_quotes(self, s: str) -> str:
        """
        Грубая, но иногда практичная замена одинарных кавычек на двойные в JSON-фрагменте.
        """
        return re.sub(r"(?<!\\)'", '"', s)

    def _heuristic_extract(self, s: str) -> Optional[Dict[str, str]]:
        """
        Последняя попытка: вытащить ключевые поля из обычного текста.
        """
        plan = ""
        comment = ""
        plan_match = re.search(r"(?:^|\n)\s*(?:plan|план)\s*:\s*(.+?)(?:\n\S|$)", s, re.IGNORECASE | re.DOTALL)
        if plan_match:
            plan = plan_match.group(1).strip()
        comment_match = re.search(r"(?:^|\n)\s*(?:comment|комментарий|суть)\s*:\s*(.+?)(?:\n\S|$)", s, re.IGNORECASE | re.DOTALL)
        if comment_match:
            comment = comment_match.group(1).strip()
        if plan or comment:
            return {"plan": plan, "comment": comment}
        return None


# 👇 Обёртка-функция для использования с SelfImprover (если где-то используется напрямую)
def get_improvement_plan(chatgpt, file_path: str, summary: str) -> Optional[dict]:
    """
    Унифицированный вызов: строим строковый промпт и обращаемся к CodeAnalyzer.chat
    с системным сообщением от планировщика.
    """
    planner = ImprovementPlanner()
    prompt = planner.build_prompt(file_path, summary)
    response = chatgpt.chat(prompt, system_msg=planner.SYSTEM_MSG)
    return planner.extract_plan(response)
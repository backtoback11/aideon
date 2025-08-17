"""
UI Analyzer (scaffold)

Задача: анализ UI-слоёв (Qt-панели), сбор метрик взаимодействия и рекомендации.
Пока только каркас: интерфейс + заглушки.
"""
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class UIEvent:
    when: float
    widget: str
    action: str
    meta: Dict[str, Any]

class UIAnalyzer:
    def __init__(self):
        self.events: List[UIEvent] = []

    def track(self, event: UIEvent) -> None:
        self.events.append(event)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "events_count": len(self.events),
            "widgets": sorted({e.widget for e in self.events})
        }

    def recommend(self) -> List[str]:
        # TODO: сюда позже добавим интеллект + запросы к GPT на базе метасаммери
        return ["(scaffold) Недостаточно данных для рекомендаций"]

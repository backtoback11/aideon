#!/usr/bin/env python3
# main.py

import sys
import json
import os
from PyQt6.QtWidgets import QApplication
from app.ui.main_window import MainWindow

def main():
    # Путь к файлу настроек (settings.json), где храним model_mode, model_name, local_paths и т.д.
    config_path = os.path.join("app", "configs", "settings.json")
    
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        config = {}
        print(f"⚠️ Не найден {config_path}, используем пустой config.")

    app = QApplication(sys.argv)

    # Создаём главное окно, передавая config
    window = MainWindow(config=config)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
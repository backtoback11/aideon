# app/ui/analysis_thread.py

import traceback
from PyQt6.QtCore import QThread, pyqtSignal

class LoadAIThread(QThread):
    """
    Фоновый поток для загрузки локальной AI-модели.
    Вызывает метод analyzer.load_model_in_background(mode, on_progress)
    и передаёт сигналы о ходе загрузки и её результате:
    
    - loading_progress(int): сигнал прогресса (0..100)
    - loading_finished(bool): сигнал завершения (True=успех, False=ошибка)
    - loading_error(str): сигнал ошибки (текст)

    В текущей конфигурации поддерживаются только два режима:
      1) "ChatGPT" (загрузка не требуется, т.к. это OpenAI),
      2) "StarCoder" (локальная модель).

    Если метод load_model_in_background вернёт успех (success=True),
    отправляем loading_finished(True). Иначе отправляем loading_error(...) + loading_finished(False).
    """
    loading_progress = pyqtSignal(int)
    loading_finished = pyqtSignal(bool)
    loading_error = pyqtSignal(str)

    def __init__(self, analyzer, mode, parent=None):
        super().__init__(parent)
        self.analyzer = analyzer   # Экземпляр CodeAnalyzer
        self.mode = mode           # Название модели ("StarCoder" или "ChatGPT")
        self._stop_flag = False    # Если захотим прерывать загрузку извне

    def run(self):
        """
        Запускается при start().
        Вызывает analyzer.load_model_in_background(mode, on_progress).

        Если всё ок, генерируем loading_finished(True).
        Если произошла ошибка → loading_error(...) + loading_finished(False).
        """
        try:
            def on_progress(pct: int):
                # Проверяем, не попросили ли остановить
                if self._stop_flag:
                    raise RuntimeError("Loading canceled by user")
                # Отправляем прогресс (0..100) в основной поток (GUI)
                self.loading_progress.emit(pct)

            # Пытаемся загрузить локальную модель (StarCoder),
            # либо ничего не делать для ChatGPT (в зависимости от реализации).
            success, error_msg = self.analyzer.load_model_in_background(self.mode, on_progress)
            if not success:
                # Ошибка или отмена
                self.loading_error.emit(error_msg or "Неизвестная ошибка загрузки модели")
                self.loading_finished.emit(False)
                return

            # Успешная загрузка
            self.loading_finished.emit(True)

        except Exception as e:
            # В случае непредвиденной ошибки
            err_text = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            self.loading_error.emit(err_text)
            self.loading_finished.emit(False)

    def stop(self):
        """
        Если нужно снаружи отменять загрузку, выставляем флаг
        и/или дергаем analyzer.cancel_loading().
        """
        self._stop_flag = True
        # Например, если в analyzer есть метод cancel_loading():
        # self.analyzer.cancel_loading()
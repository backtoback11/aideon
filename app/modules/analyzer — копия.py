import json
import openai
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from app.utils import load_api_key
from app.core.file_manager import FileManager


class CodeAnalyzer:
    """
    Модуль для анализа кода и (при необходимости) генерации кода.
    Поддерживает два режима:
      1) ChatGPT (GPT-4-turbo) через OpenAI — «менеджер/аналитик».
      2) StarCoder (локальная модель) — «исполнитель кода».

    Основные методы:
      - analyze_code(...) — анализ кода / текстовых фрагментов (с чанкованием).
      - generate_code_star_coder(...) — отдельный метод для генерации кода StarCoder’ом.
    """

    def __init__(self, config=None):
        """
        config — словарь с настройками. Пример структуры:
        {
          "model_mode": "ChatGPT" | "StarCoder",  # какой режим по умолчанию
          "model_name": "gpt-4-turbo",           # для ChatGPT
          "openai_api_key": "...",
          "local_paths": {
              "StarCoder": "/Users/xxx/models/starcoder/starcoder-7B"
          },
          "use_mps": true,            # Пытаться ли загрузить модель на MPS (Mac)
          "temperature": 0.7,
          "max_new_tokens": 512,      # Макс. кол-во генерируемых токенов (локальная модель)
          "max_context_tokens": 8192  # Примерный лимит для одного чанка
        }
        """
        self.config = config or {}
        self.file_manager = FileManager()

        # --- основные настройки ---
        self.model_mode = self.config.get("model_mode", "ChatGPT")   # "ChatGPT" или "StarCoder"
        self.api_key = load_api_key(self.config)                     # ключ OpenAI (может быть None)
        self.openai_model = self.config.get("model_name", "gpt-4-turbo")

        self.local_paths = self.config.get("local_paths", {})
        self.use_mps = self.config.get("use_mps", True)
        self.temperature = self.config.get("temperature", 0.7)
        self.max_new_tokens = self.config.get("max_new_tokens", 512)
        self.max_context_tokens = self.config.get("max_context_tokens", 8192)

        # --- ссылки на локальную модель (если StarCoder) ---
        self.local_tokenizer = None
        self.local_model = None
        self.current_device = "cpu"

        # Флаг для отмены фоновой загрузки (необязателен, если не нужен)
        self.loading_cancelled = False

        # Если по умолчанию выбрана StarCoder — подгружаем сразу
        if self.model_mode == "StarCoder":
            self._load_local_model("StarCoder")
        else:
            print("Используем ChatGPT (OpenAI).")

    # ----------------------------------------------------------------
    # Переключение между ChatGPT / StarCoder
    # ----------------------------------------------------------------
    def switch_model(self, mode):
        """
        Меняем режим: "ChatGPT" или "StarCoder".
        Если ChatGPT — выгружаем локальную модель (если была).
        Если StarCoder — загружаем локальную модель синхронно (или фоном).
        """
        if mode not in ["ChatGPT", "StarCoder"]:
            print(f"❌ Некорректный режим: {mode}")
            return

        self.model_mode = mode
        print(f"🔁 Переключено на режим: {mode}")

        if mode == "ChatGPT":
            print("Используем ChatGPT (OpenAI).")
            self.unload_local_model()
        else:
            self._load_local_model("StarCoder")

    def _load_local_model(self, mode):
        """
        Синхронная загрузка локальной модели (StarCoder).
        Если нужен прогресс — см. load_model_in_background.
        """
        self.unload_local_model()  # на всякий случай

        local_path = self.local_paths.get(mode)
        if not local_path:
            raise ValueError(f"Не указан путь к локальной модели '{mode}' в config['local_paths'].")

        print(f"🔽 Загрузка локальной модели: {mode} из {local_path}...")
        device_map = "mps" if self.use_mps else "cpu"

        try:
            self.local_tokenizer = AutoTokenizer.from_pretrained(
                local_path,
                local_files_only=True,
                trust_remote_code=True
            )
            self.local_model = AutoModelForCausalLM.from_pretrained(
                local_path,
                local_files_only=True,
                trust_remote_code=True,
                torch_dtype=torch.float32,
                device_map=device_map
            )
            self.current_device = device_map
            print(f"✅ Модель {mode} загружена на {device_map}!")

        except RuntimeError as e:
            err_str = str(e).lower()
            if "out of memory" in err_str and device_map == "mps":
                print("⚠️ MPS OOM. Пытаемся fallback на CPU...")
                try:
                    self.local_model = AutoModelForCausalLM.from_pretrained(
                        local_path,
                        local_files_only=True,
                        trust_remote_code=True,
                        torch_dtype=torch.float32,
                        device_map="cpu"
                    )
                    self.current_device = "cpu"
                    print(f"✅ Модель {mode} успешно загружена на CPU (fallback)!")
                except Exception as e2:
                    print(f"❌ Ошибка при загрузке (CPU fallback): {e2}")
                    self.local_tokenizer = None
                    self.local_model = None
                    self.current_device = "none"
            else:
                print(f"❌ Ошибка при загрузке локальной модели {mode}: {e}")
                self.local_tokenizer = None
                self.local_model = None
                self.current_device = "none"
        except Exception as e:
            print(f"❌ Ошибка при загрузке локальной модели {mode}: {e}")
            self.local_tokenizer = None
            self.local_model = None
            self.current_device = "none"

    def unload_local_model(self):
        """Освобождаем память — удаляем ссылки на модель/токенизатор."""
        if self.local_model is not None:
            print("🗑 Выгружаем локальную модель из памяти...")
            self.local_model = None
            self.local_tokenizer = None
            self.current_device = "none"
            print("✅ Локальная модель выгружена.")

    # ----------------------------------------------------------------
    # Фоновая загрузка (если нужно)
    # ----------------------------------------------------------------
    def load_model_in_background(self, mode, on_progress=None):
        """
        Вызывается из LoadAIThread.
        Возвращает (success: bool, error_msg: str).
        """
        try:
            self.loading_cancelled = False

            def progress(pct):
                if self.loading_cancelled:
                    raise RuntimeError("Loading canceled by user.")
                if on_progress:
                    on_progress(pct)

            progress(10)
            self.unload_local_model()

            local_path = self.local_paths.get(mode)
            if not local_path:
                return (False, f"Не указан путь к локальной модели {mode}")

            progress(20)
            device_map = "mps" if self.use_mps else "cpu"

            # Токенизатор
            self.local_tokenizer = AutoTokenizer.from_pretrained(
                local_path,
                local_files_only=True,
                trust_remote_code=True
            )
            progress(50)

            # Модель
            self.local_model = AutoModelForCausalLM.from_pretrained(
                local_path,
                local_files_only=True,
                trust_remote_code=True,
                torch_dtype=torch.float32,
                device_map=device_map
            )
            self.current_device = device_map
            progress(100)

            return (True, None)

        except RuntimeError as e:
            err_str = str(e).lower()
            if "canceled by user" in err_str:
                return (False, "Загрузка отменена пользователем")
            if "out of memory" in err_str and device_map == "mps":
                # fallback CPU
                try:
                    progress(90)
                    self.local_model = AutoModelForCausalLM.from_pretrained(
                        local_path,
                        local_files_only=True,
                        trust_remote_code=True,
                        torch_dtype=torch.float32,
                        device_map="cpu"
                    )
                    self.current_device = "cpu"
                    if on_progress:
                        on_progress(100)
                    return (True, None)
                except Exception as e2:
                    return (False, f"OOM при fallback на CPU: {e2}")
            else:
                return (False, f"Runtime ошибка: {e}")

        except Exception as e:
            return (False, f"Ошибка при загрузке модели {mode}: {e}")

    def cancel_loading(self):
        """Если нужно отменить фоновую загрузку модели."""
        self.loading_cancelled = True

    # ----------------------------------------------------------------
    # Метод для анализа кода (ChatGPT / StarCoder) — ЧАНКОВАНИЕ
    # ----------------------------------------------------------------
    def analyze_code(self, code_text, file_path=None):
        """
        Если «текст кода» очень большой → разбиваем на чанки,
        каждый чанк анализируем (примерно) и собираем общий JSON-ответ.
        
        Применимо как для ChatGPT, так и для StarCoder, но
        обычно ChatGPT «выдаёт» анализ, а StarCoder «исполнитель».
        """
        chunks = self._split_into_chunks(code_text, self.max_context_tokens)
        if len(chunks) <= 1:
            return self._analyze_single_chunk(chunks[0], file_path)

        # Собираем итоговый JSON, склеивая ответы от каждого чанка
        combined = {
            "chat": "",
            "problems": "",
            "plan": "",
            "process": "",
            "result": "",
            "code": ""
        }
        for i, chunk_text in enumerate(chunks, start=1):
            result_str = self._analyze_single_chunk(
                chunk_text,
                f"{file_path or 'без имени'} [chunk {i}/{len(chunks)}]"
            )
            try:
                parsed_json = json.loads(result_str)
                for key in combined.keys():
                    if key in parsed_json and parsed_json[key]:
                        combined[key] += f"\n\n[CHUNK {i}] {parsed_json[key]}"
            except json.JSONDecodeError:
                # если не JSON — пишем ошибку в 'chat'
                combined["chat"] += f"\n\n[CHUNK {i} ERROR]\n{result_str}"

        return json.dumps(combined, ensure_ascii=False, indent=2)

    def _analyze_single_chunk(self, code_chunk, file_path=None):
        """
        Сюда приходит 1 чанк кода. Либо ChatGPT, либо StarCoder.
        Возвращаем JSON (string).
        """
        project_tree = self.file_manager.get_project_tree("app")

        context_prompt = (
            "Ты — Aideon, AI-ассистент по анализу кода.\n"
            f"Тебе дана структура проекта:\n{project_tree}\n\n"
            "Теперь проанализируй следующий код:\n"
            f"{code_chunk}\n\n"
            "Ответ должен быть в JSON формате с ключами:\n"
            "{\n"
            "  \"chat\": \"...\",\n"
            "  \"problems\": \"...\",\n"
            "  \"plan\": \"...\",\n"
            "  \"process\": \"...\",\n"
            "  \"result\": \"...\",\n"
            "  \"code\": \"...\"\n"
            "}\n"
            "Не добавляй ничего, кроме JSON."
        )

        if self.model_mode == "ChatGPT":
            # Обращаемся к OpenAI
            openai.api_key = self.api_key
            try:
                resp = openai.ChatCompletion.create(
                    model=self.openai_model,
                    messages=[
                        {
                            "role": "system",
                            "content": context_prompt
                        },
                        {
                            "role": "user",
                            "content": (
                                f"Проанализируй код из файла {file_path or 'без имени'}:\n{code_chunk}"
                            )
                        }
                    ],
                    temperature=self.temperature
                )
                return resp["choices"][0]["message"]["content"]
            except Exception as e:
                return f"Ошибка при обращении к OpenAI: {e}"

        else:
            # StarCoder (локальная)
            if not self.local_model or not self.local_tokenizer:
                return "Ошибка: Локальная модель не загружена/инициализирована."

            full_prompt = (
                f"{context_prompt}\n\n"
                f"Проанализируй код из файла {file_path or 'без имени'}:\n{code_chunk}"
            )
            try:
                inputs = self.local_tokenizer(full_prompt, return_tensors="pt")
                device = next(self.local_model.parameters()).device
                inputs = inputs.to(device)

                out_tokens = self.local_model.generate(
                    **inputs,
                    max_new_tokens=self.max_new_tokens
                )
                return self.local_tokenizer.decode(
                    out_tokens[0],
                    skip_special_tokens=True
                )
            except Exception as e:
                return f"Ошибка при генерации локальной модели: {e}"

    # ----------------------------------------------------------------
    # Отдельный метод для генерации кода в StarCoder
    # ----------------------------------------------------------------
    def generate_code_star_coder(self, prompt_text):
        """
        Если хотим использовать StarCoder именно как «исполнителя кода»:
        - Подаём инструкцию/заголовок, 
        - Получаем сгенерированный результат (строку).
        
        Этот метод вы можете вызывать, когда ChatGPT 
        «дал задание» сгенерировать кусок кода (или пользователь нажал «Генерировать»).
        """
        if self.model_mode != "StarCoder":
            return "Ошибка: Режим StarCoder не активен. Переключитесь на StarCoder."
        if not self.local_model or not self.local_tokenizer:
            return "Ошибка: Локальная модель StarCoder не загружена."

        # Формируем промпт (минимальный, без «JSON only»)
        try:
            inputs = self.local_tokenizer(prompt_text, return_tensors="pt")
            device = next(self.local_model.parameters()).device
            inputs = inputs.to(device)

            gen_tokens = self.local_model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                temperature=self.temperature,
                do_sample=True   # например, разрешаем сэмплинг
            )
            return self.local_tokenizer.decode(
                gen_tokens[0],
                skip_special_tokens=True
            )
        except Exception as e:
            return f"Ошибка при генерации кода (StarCoder): {e}"

    # ----------------------------------------------------------------
    # Метод _split_into_chunks: общий для ChatGPT / StarCoder
    # ----------------------------------------------------------------
    def _split_into_chunks(self, text, max_ctx: int):
        """
        Дробим текст на чанки по max_ctx «токенов».
        Для ChatGPT берём кол-во слов как приближённое кол-во токенов.
        Для StarCoder — реальный tokenizer.encode().
        """
        text = text.strip()
        if not text:
            return [""]

        if self.model_mode == "ChatGPT":
            # Примерно считаем: 1 слово ~ 1 токен
            words = text.split()
            if len(words) <= max_ctx:
                return [text]
            chunks = []
            for i in range(0, len(words), max_ctx):
                chunk_slice = words[i:i + max_ctx]
                chunk_text = " ".join(chunk_slice)
                chunks.append(chunk_text)
            return chunks
        else:
            # StarCoder
            if not self.local_tokenizer:
                return [text]
            tokens = self.local_tokenizer.encode(text)
            if len(tokens) <= max_ctx:
                return [text]
            chunks = []
            start_i = 0
            while start_i < len(tokens):
                end_i = start_i + max_ctx
                sub_tokens = tokens[start_i:end_i]
                sub_text = self.local_tokenizer.decode(sub_tokens, skip_special_tokens=True)
                chunks.append(sub_text)
                start_i = end_i
            return chunks

    # ----------------------------------------------------------------
    # Мониторинг ресурсов (CPU/RAM)
    # ----------------------------------------------------------------
    def get_resource_stats(self):
        """
        Возвращает словарь вида:
        {
            "device": "cpu" | "mps" | "none",
            "cpu_percent": float или None,
            "ram_used_mb": int или None
        }
        """
        stats = {
            "device": self.current_device,
            "cpu_percent": None,
            "ram_used_mb": None
        }
        if PSUTIL_AVAILABLE:
            cpu_perc = psutil.cpu_percent(interval=None)
            mem_info = psutil.virtual_memory()
            ram_mb = int(mem_info.used / (1024 * 1024))
            stats["cpu_percent"] = cpu_perc
            stats["ram_used_mb"] = ram_mb
        return stats
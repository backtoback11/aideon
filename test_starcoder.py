import sys
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

def test_starcoder_local(local_path, device_map="mps"):
    print(f"Проверяем модель StarCoder из: {local_path}")
    model = None
    tokenizer = None
    try:
        # 1) Загружаем токенизатор
        tokenizer = AutoTokenizer.from_pretrained(
            local_path,
            local_files_only=True,
            trust_remote_code=True
        )

        # 2) Загружаем модель
        model = AutoModelForCausalLM.from_pretrained(
            local_path,
            local_files_only=True,
            trust_remote_code=True,
            torch_dtype=torch.float32,  # Если хотите float16, замените на torch.float16
            device_map=device_map       # "mps" или "cpu"
        )
        print("✅ Модель успешно загружена!")

        # 3) Мини-тест на генерацию
        prompt = "def greet(name):\n    return f'Hello, {name}'"
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        print("Выполняем generate()...")

        # Минимальный пример для быстрой генерации
        out_tokens = model.generate(
            **inputs,
            max_new_tokens=8,
            do_sample=True,   # отключаем сэмплинг, чтобы быстрее завершилось
            temperature=0.1
        )

        result = tokenizer.decode(out_tokens[0], skip_special_tokens=True)
        print("\n===== Результат генерации =====\n")
        print(result)
        print("\n===== Успех! =====")

    except Exception as e:
        print(f"❌ Ошибка при работе со StarCoder: {e}")

    finally:
        # Попытка освободить память и завершить процесс
        if model is not None:
            print("🗑 Завершаем работу: переносим модель на CPU и освобождаем ссылки.")
            try:
                model.to("cpu")
            except:
                pass
        del model
        del tokenizer

        # Для CUDA можно добавить:
        # torch.cuda.empty_cache()

        # Принудительное завершение процесса
        sys.exit(0)

if __name__ == "__main__":
    # Укажите путь к папке с моделью StarCoder
    local_path = "/Users/backtoback/models/starcoder/starcoder-7B"

    # Можно поставить device_map="cpu", если MPS вызывает OOM
    test_starcoder_local(local_path, device_map="mps")
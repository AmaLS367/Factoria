from playwright.sync_api import sync_playwright, TimeoutError
import time
import os
from config import USER_DATA_DIR

# Путь к постоянному профилю
# USER_DATA_DIR = os.path.abspath("user-data")

def get_answer_from_gemini(prompt: str, headless=True, slow_mo=50):
    with sync_playwright() as p:
        # Открываем persistent браузер с сохранением профиля
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=headless,
            slow_mo=slow_mo,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled"
            ],
            viewport=None  # Используем размер окна по умолчанию
        )

        page = context.new_page()

        try:
            print("[INFO] Открываю Gemini...")
            page.goto("https://gemini.google.com/app")
            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)

            input_selector = 'div.ql-editor[contenteditable="true"]'
            page.wait_for_selector(input_selector, timeout=15000)
            input_elem = page.query_selector(input_selector)

            if not input_elem:
                raise Exception("Элемент ввода не найден")

            input_elem.fill(prompt)
            page.keyboard.press("Enter")

            # Дать время Gemini обработать запрос
            time.sleep(8)  # ← можно увеличить при необходимости

            response_selector = 'div.markdown-main-panel'
            page.wait_for_selector(response_selector, timeout=30000)

            # Дожидаемся пока ответ действительно появится внутри
            for _ in range(30):  # пробуем 30 раз (до 30 сек)
                content = page.query_selector(response_selector)
                if content:
                    answer = content.inner_text()
                    if answer.strip():  # если что-то появилось
                        print("[INFO] Ответ получен")
                        return answer
                time.sleep(1)

            raise Exception("Ответ не был получен за отведённое время")

        except TimeoutError as e:
            print("[ERROR] Timeout: ", str(e))
            page.screenshot(path="error_timeout.png")
            return "Ошибка: ответ не получен (timeout)"

        except Exception as e:
            print("[ERROR] Произошла ошибка: ", str(e))
            page.screenshot(path="error_generic.png")
            return f"Ошибка: {str(e)}"

        finally:
            context.close()

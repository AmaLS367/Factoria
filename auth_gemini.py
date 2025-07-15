from playwright.sync_api import sync_playwright
import os
import time

USER_DATA_DIR = os.path.abspath("user-data/user-data-3")  # Папка с браузерным профилем

def launch_gemini_browser():
    with sync_playwright() as p:
        print("[INFO] Запускаю 'человеческий' браузер для авторизации в Gemini...")
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled"
            ],
            viewport=None  # Отключаем фиксацию размера — берётся системное окно
        )

        page = context.new_page()
        page.goto("https://gemini.google.com/app")
        print("[INFO] Войдите вручную в аккаунт (если нужно) и отправьте любой тестовый промт")
        print("[INFO] После этого просто закройте окно — сессия сохранится")

        # Ждём пока пользователь сам закроет окно
        while True:
            if not context.pages:
                break
            time.sleep(1)

        context.close()
        print("[DONE] Сессия сохранена в user-data/")

if __name__ == "__main__":
    launch_gemini_browser()

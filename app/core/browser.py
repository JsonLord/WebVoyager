import os
import platform
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

class BrowserService:
    def __init__(self, download_dir="downloads", headless=True, window_width=1024, window_height=768):
        self.download_dir = download_dir
        self.headless = headless
        self.window_width = window_width
        self.window_height = window_height

    def get_options(self, user_data_dir=None):
        options = webdriver.ChromeOptions()

        if self.headless:
            options.add_argument("--headless")
            options.add_argument(
                "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )

        # Security and performance options for containerized environments
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--force-device-scale-factor=1")

        if user_data_dir:
            options.add_argument(f"--user-data-dir={user_data_dir}")

        options.add_experimental_option(
            "prefs", {
                "download.default_directory": os.path.abspath(self.download_dir),
                "plugins.always_open_pdf_externally": True
            }
        )
        return options

    def create_driver(self, user_data_dir=None):
        options = self.get_options(user_data_dir)
        driver = webdriver.Chrome(options=options)
        driver.set_window_size(self.window_width, self.window_height)

        # Prevent space key from scrolling the page
        driver.execute_script("""
            window.onkeydown = function(e) {
                if(e.keyCode == 32 && e.target.type != 'text' && e.target.type != 'textarea') {
                    e.preventDefault();
                }
            };
        """)
        return driver

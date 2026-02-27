import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from app.core.config import settings
from PIL import Image, ImageDraw

class BrowserService:
    def __init__(self):
        self.drivers = {}

    def get_driver(self, session_id: str):
        if session_id in self.drivers:
            try:
                # Check if driver is still responsive
                _ = self.drivers[session_id].current_url
                return self.drivers[session_id]
            except Exception:
                logging.warning(f"Driver for session {session_id} is unresponsive. Re-initializing.")
                self.close_session(session_id)

        # Initialize new driver for session
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")

        # Session persistence
        session_dir = os.path.abspath(os.path.join(settings.SESSIONS_DIR, session_id))
        os.makedirs(session_dir, exist_ok=True)
        options.add_argument(f"--user-data-dir={session_dir}")

        driver = webdriver.Chrome(options=options)
        driver.set_window_size(1024, 768)
        self.drivers[session_id] = driver
        return driver

    def close_session(self, session_id: str):
        if session_id in self.drivers:
            try:
                self.drivers[session_id].quit()
            except:
                pass
            del self.drivers[session_id]

    def navigate(self, session_id: str, url: str):
        driver = self.get_driver(session_id)
        driver.get(url)
        time.sleep(5)

    def click(self, session_id: str, element_id: int, web_eles: list):
        driver = self.get_driver(session_id)
        web_ele = web_eles[element_id]

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", web_ele)
        time.sleep(1)

        driver.execute_script("arguments[0].setAttribute('target', '_self')", web_ele)
        web_ele.click()
        time.sleep(3)

    def type_text(self, session_id: str, element_id: int, text: str, web_eles: list):
        driver = self.get_driver(session_id)
        web_ele = web_eles[element_id]

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", web_ele)
        time.sleep(1)

        actions = ActionChains(driver)
        actions.click(web_ele).perform()
        actions.pause(1)

        try:
            web_ele.clear()
            web_ele.send_keys(Keys.CONTROL + "a")
            web_ele.send_keys(Keys.BACKSPACE)
        except:
            pass

        actions.send_keys(text)
        actions.pause(1)
        actions.send_keys(Keys.ENTER)
        actions.perform()
        time.sleep(5)

    def scroll(self, session_id: str, direction: str):
        driver = self.get_driver(session_id)
        if direction == "down":
            driver.execute_script("window.scrollBy(0, 500);")
        else:
            driver.execute_script("window.scrollBy(0, -500);")
        time.sleep(2)

    def capture_screenshot(self, session_id: str, path: str):
        driver = self.get_driver(session_id)
        driver.save_screenshot(path)
        return path

    def get_web_elements(self, session_id: str):
        driver = self.get_driver(session_id)
        js_script = """
        let labels = [];
        function markPage() {
            var bodyRect = document.body.getBoundingClientRect();
            var items = Array.prototype.slice.call(
                document.querySelectorAll('*')
            ).map(function(element) {
                var vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
                var vh = Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0);
                var rects = [...element.getClientRects()].filter(bb => {
                    var center_x = bb.left + bb.width / 2;
                    var center_y = bb.top + bb.height / 2;
                    var elAtCenter = document.elementFromPoint(center_x, center_y);
                    return elAtCenter === element || element.contains(elAtCenter)
                }).map(bb => {
                    const rect = {
                        left: Math.max(0, bb.left),
                        top: Math.max(0, bb.top),
                        right: Math.min(vw, bb.right),
                        bottom: Math.min(vh, bb.bottom)
                    };
                    return { ...rect, width: rect.right - rect.left, height: rect.bottom - rect.top }
                });
                var area = rects.reduce((acc, rect) => acc + rect.width * rect.height, 0);
                return {
                    element: element,
                    include: (element.tagName === "INPUT" || element.tagName === "TEXTAREA" || element.tagName === "SELECT") ||
                             (element.tagName === "BUTTON" || element.tagName === "A" || (element.onclick != null) || window.getComputedStyle(element).cursor == "pointer") ||
                             (element.tagName === "IFRAME" || element.tagName === "VIDEO" || element.tagName === "LI" || element.tagName === "TD" || element.tagName === "OPTION"),
                    area, rects, text: element.textContent.trim().replace(/\s{2,}/g, ' ')
                };
            }).filter(item => item.include && (item.area >= 20));
            const buttons = Array.from(document.querySelectorAll('button, a, input[type="button"], div[role="button"]'));
            items = items.filter(x => !buttons.some(y => items.some(z => z.element === y) && y.contains(x.element) && !(x.element === y) ));
            items = items.filter(x => !items.some(y => x.element.contains(y.element) && !(x == y)));
            items.forEach(function(item, index) {
                item.rects.forEach((bbox) => {
                    let newElement = document.createElement("div");
                    newElement.style.outline = "2px dashed #000000";
                    newElement.style.position = "fixed";
                    newElement.style.left = bbox.left + "px";
                    newElement.style.top = bbox.top + "px";
                    newElement.style.width = bbox.width + "px";
                    newElement.style.height = bbox.height + "px";
                    newElement.style.pointerEvents = "none";
                    newElement.style.boxSizing = "border-box";
                    newElement.style.zIndex = 2147483647;
                    let label = document.createElement("span");
                    label.textContent = index;
                    label.style.position = "absolute";
                    label.style.top = Math.max(-19, -bbox.top) + "px";
                    label.style.left = Math.min(Math.floor(bbox.width / 5), 2) + "px";
                    label.style.background = "#000000";
                    label.style.color = "white";
                    label.style.padding = "2px 4px";
                    label.style.fontSize = "12px";
                    label.style.borderRadius = "2px";
                    newElement.appendChild(label);
                    document.body.appendChild(newElement);
                    labels.push(newElement);
                });
            });
            return [labels, items];
        }
        return markPage();
        """
        rects, items_raw = driver.execute_script(js_script)

        format_ele_text = []
        for web_ele_id in range(len(items_raw)):
            label_text = items_raw[web_ele_id]['text']
            ele = items_raw[web_ele_id]['element']
            ele_tag_name = ele.tag_name.lower()
            ele_type = ele.get_attribute("type")
            ele_aria_label = ele.get_attribute("aria-label")

            if not label_text:
                if (ele_tag_name == 'input') or ele_tag_name == 'textarea' or ele_tag_name == 'button':
                    label = ele_aria_label if ele_aria_label else ""
                    format_ele_text.append(f"[{web_ele_id}]: <{ele_tag_name}> \"{label}\";")
            elif label_text and len(label_text) < 200:
                label = f"\"{label_text}\""
                if ele_aria_label and ele_aria_label != label_text:
                    label += f", \"{ele_aria_label}\""
                format_ele_text.append(f"[{web_ele_id}]: <{ele_tag_name}> {label};")

        return rects, [item['element'] for item in items_raw], "\t".join(format_ele_text)

    def remove_rects(self, session_id: str, rects: list):
        driver = self.get_driver(session_id)
        for rect in rects:
            try:
                driver.execute_script("arguments[0].remove()", rect)
            except:
                pass

browser_service = BrowserService()

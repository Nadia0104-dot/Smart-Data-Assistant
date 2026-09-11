from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

import time, random, logging, re

logger = logging.getLogger(__name__)



class WorkableScraper:

    BASE_URL = "https://jobs.workable.com/"

    def __init__(self, headless=False):

        opt = webdriver.ChromeOptions()

        if headless:
            opt.add_argument("--headless=new")

        opt.add_argument("--disable-gpu")
        opt.add_argument("--no-sandbox")
        opt.add_argument("--disable-dev-shm-usage")
        opt.add_argument("--start-maximized")
        opt.add_argument("--disable-blink-features=AutomationControlled")

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=opt
        )

        self.wait = WebDriverWait(self.driver, 25)

    # ================= UTIL =================
    def sleep(self, a=0.6, b=1.5):
        time.sleep(random.uniform(a, b))

    def close(self):
        try:
            self.driver.quit()
        except:
            pass

    # ================= COOKIE HANDLER (FIXED) =================
    def handle_cookies(self):

        try:
            self.sleep(2, 3)

            buttons = self.driver.find_elements(
                By.XPATH,
                "//button[contains(., 'Accept') or contains(., 'I agree') or contains(., 'Accept all')]"
            )

            for btn in buttons:
                try:
                    self.driver.execute_script("arguments[0].click();", btn)
                    self.sleep(2, 3)
                    logger.info("Cookies accepted")
                    return
                except:
                    pass

        except:
            pass

    # ================= OPEN =================
    def open(self):

        self.driver.get(self.BASE_URL)

        self.wait.until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        self.handle_cookies()

    # ================= SEARCH =================

    def search(self, job, location=None):

        try:
            self.sleep(2, 3)

            # ================= JOB INPUT =================
            job_input = None

            selectors = [
                (By.CSS_SELECTOR, "input[type='search']"),
                (By.CSS_SELECTOR, "input[placeholder*='Job']"),
                (By.TAG_NAME, "input")
            ]

            for by, sel in selectors:
                try:
                    els = self.driver.find_elements(by, sel)
                    if els:
                        job_input = els[0]
                        break
                except:
                    pass

            if not job_input:
                raise Exception("Job input not found on Workable")

            job_input.click()
            self.sleep(0.3, 0.6)

            job_input.send_keys(Keys.CONTROL, "a")
            job_input.send_keys(Keys.DELETE)

            for ch in job:
                job_input.send_keys(ch)
                time.sleep(random.uniform(0.02, 0.05))

            self.sleep(0.5, 1)
            job_input.send_keys(Keys.ENTER)

            self.sleep(2, 3)

            # ================= LOCATION (FIXED AUTOSUGGEST) =================
            if location:

                try:
                    location_input = self.wait.until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "input[placeholder*='City']")
                        )
                    )

                    location_input.click()
                    self.sleep(0.3, 0.6)

                    # clear existing value
                    location_input.send_keys(Keys.CONTROL, "a")
                    location_input.send_keys(Keys.DELETE)

                    self.sleep(0.3, 0.5)

                    # type slowly (IMPORTANT for React autosuggest)
                    for ch in location:
                        location_input.send_keys(ch)
                        time.sleep(random.uniform(0.05, 0.09))

                    # wait suggestions to load
                    self.sleep(2.5, 3.5)

                    # ================= BEST RELIABLE SELECTION =================
                    try:
                        # try keyboard selection first (MOST STABLE)
                        location_input.send_keys(Keys.ARROW_DOWN)
                        self.sleep(0.3, 0.5)
                        location_input.send_keys(Keys.ENTER)

                    except:
                        # fallback: force enter
                        location_input.send_keys(Keys.ENTER)

                    self.sleep(1.5, 2)

                except Exception as e:
                    logger.warning(f"Location selection failed: {e}")

            # ================= FINAL STABILIZATION =================
            self.wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            self.sleep(2, 3)

        except Exception as e:
            raise Exception(f"Workable search failed: {str(e)}")
    # ================= PARSE JOB =================
    def parse_job(self, card):

        data = {
            "title": None,
            "company": None,
            "location": None,
            "url": None,
            "description": None,
            "skills": []
        }

        try:
            a = card.find_element(By.TAG_NAME, "a")
            data["url"] = a.get_attribute("href")
            data["title"] = a.text.strip()
        except:
            pass

        try:
            text = card.text.split("\n")

            if len(text) > 1:
                data["company"] = text[1]

            if len(text) > 2:
                data["location"] = text[2]

        except:
            pass

        return data



    # ================= SLOW HUMAN SCROLL (🔥 FIX) =================
    def slow_scroll(self, steps=12):

        for i in range(steps):

            self.driver.execute_script(
                "window.scrollBy(0, window.innerHeight * 0.8);"
            )

            self.sleep(1.5, 2.5)  # IMPORTANT DELAY
    # ================= JOB DETAIL =================
    def job_detail(self, url):

        try:
            main = self.driver.current_window_handle

            self.driver.execute_script("window.open(arguments[0]);", url)

            self.sleep(2, 3)

            new_tab = [
                t for t in self.driver.window_handles
                if t != main
            ][-1]

            self.driver.switch_to.window(new_tab)

            self.wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            text = self.driver.find_element(By.TAG_NAME, "body").text

            self.driver.close()
            self.driver.switch_to.window(main)

            return text[:7000]

        except:
            try:
                self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return None


    # ================= STREAM =================
    def scrape_stream(self, job, location=None, full_job=False, max_pages=1):

        results = []
        seen = set()

        try:
            yield {"log": "🚀 Starting Workable scraper..."}

            self.open()
            self.search(job, location)

            for page in range(max_pages):

                yield {"log": f"📄 Page {page+1}"}

                self.sleep(3, 4)

                cards = self.driver.find_elements(By.TAG_NAME, "article")

                if not cards:
                    cards = self.driver.find_elements(By.CSS_SELECTOR, "div")

                yield {"log": f"Found {len(cards)} possible job blocks"}

                for card in cards:

                    try:
                        data = self.parse_job(card)

                        if not data["title"]:
                            continue

                        key = (data["title"], data["company"])

                        if key in seen:
                            continue

                        seen.add(key)

                        if full_job and data["url"]:
                            jd = self.job_detail(data["url"])
                            data["description"] = jd

                        results.append(data)

                        yield {"job": data}

                        self.sleep(0.2, 0.6)

                    except Exception as e:
                        yield {"log": f"Card error: {str(e)}"}

            yield {"done": True, "results": results}

        except Exception as e:
            yield {"log": f"FATAL: {str(e)}", "done": True, "results": results}

        finally:
            self.close()

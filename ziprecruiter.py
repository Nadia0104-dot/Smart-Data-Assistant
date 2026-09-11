from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

import time
import random
import logging
import re

logger = logging.getLogger(__name__)


class ZipRecruiterScraper:

    BASE_URL = "https://www.ziprecruiter.com/Search-Jobs-Near-Me"

    def __init__(self, headless=False, proxy=None):

        opt = webdriver.ChromeOptions()

        if headless:
            opt.add_argument("--headless=new")

        opt.add_argument("--disable-gpu")
        opt.add_argument("--no-sandbox")
        opt.add_argument("--disable-dev-shm-usage")
        opt.add_argument("--disable-blink-features=AutomationControlled")
        opt.add_argument("--start-maximized")

        if proxy:
            opt.add_argument(f"--proxy-server={proxy}")

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=opt
        )

        self.wait = WebDriverWait(self.driver, 25)

    # ================= UTIL =================
    def sleep(self, a=0.3, b=1.0):
        time.sleep(random.uniform(a, b))

    def safe_find(self, by, selector):
        try:
            return self.driver.find_element(by, selector)
        except:
            return None

    def close(self):
        try:
            self.driver.quit()
        except:
            pass

    # ================= OPEN =================
    def open(self):
        self.driver.get(self.BASE_URL)

        self.wait.until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

    # ================= SEARCH =================
    def search(self, job, location):

        try:
            keyword_input = self.wait.until(
                EC.presence_of_element_located((By.ID, "search1"))
            )

            location_input = self.wait.until(
                EC.presence_of_element_located((By.ID, "location1"))
            )

        except Exception:
            raise Exception("Search inputs not found on ZipRecruiter page")

        # clear fields
        self.driver.execute_script("arguments[0].value='';", keyword_input)
        self.driver.execute_script("arguments[0].value='';", location_input)

        self.sleep()

        keyword_input.send_keys(job)
        location_input.send_keys(location)

        self.sleep(0.5, 1.0)

        # submit search
        try:
            self.driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
        except:
            location_input.send_keys(Keys.ENTER)

        # wait for results
        self.wait.until(
            EC.presence_of_element_located((By.TAG_NAME, "article"))
        )

    # ================= SKILLS =================
    def extract_skills(self, text):

        if not text:
            return []

        text = text.lower()

        skills = [
            "python","sql","aws","react","node","docker","kubernetes",
            "java","javascript","typescript","mongodb","firebase",
            "django","flask","fastapi","mysql","postgresql",
            "azure","gcp","tensorflow","pytorch","c#","c++"
        ]

        return list({s for s in skills if s in text})

    # ================= SALARY =================
    def extract_salary(self, text):

        if not text:
            return None

        match = re.findall(
            r"\$[\d,]+(?:\s*-\s*\$[\d,]+)?",
            text
        )

        return match[0] if match else None

    # ================= JOB DETAIL =================
    
    # ================= JOB DETAIL =================
    def scrape_job_detail(self, url):

        try:
            main = self.driver.current_window_handle

            # open new tab
            self.driver.execute_script(
                "window.open(arguments[0]);",
                url
            )

            # wait until tab appears
            self.wait.until(
                lambda d: len(d.window_handles) > 1
            )

            new_tab = [
                t for t in self.driver.window_handles
                if t != main
            ][-1]

            self.driver.switch_to.window(new_tab)

            # wait body
            self.wait.until(
                EC.presence_of_element_located(
                    (By.TAG_NAME, "body")
                )
            )

            # 🔥 IMPORTANT FIX
            # wait for full page load / anti-bot / lazy content
            logger.info("Waiting 10 seconds before scraping job detail...")

            time.sleep(15)

            # optional scroll
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )

            self.sleep(1, 2)

            # scrape text
            text = self.driver.find_element(
                By.TAG_NAME,
                "body"
            ).text

            self.driver.close()

            self.driver.switch_to.window(main)

            return text[:7000]

        except Exception as e:

            logger.warning(f"Job detail scrape failed: {e}")

            try:
                self.driver.switch_to.window(
                    self.driver.window_handles[0]
                )
            except:
                pass

            return None

    # ================= PARSE CARD =================
    def parse_card(self, card):

        job = {
            "title": None,
            "company": None,
            "location": None,
            "salary": None,
            "url": None,
            "description": None,
            "skills": []
        }

        try:
            a = card.find_element(By.CSS_SELECTOR, "a")
            job["title"] = a.text.strip()
            job["url"] = a.get_attribute("href")
        except:
            pass

        try:
            job["company"] = card.text.split("\n")[1]
        except:
            pass

        try:
            job["location"] = card.text.split("\n")[2]
        except:
            pass

        job["salary"] = self.extract_salary(card.text)
        job["skills"] = self.extract_skills(card.text)

        return job

    # ================= STREAM =================
    def scrape_stream(self, job, location, full_job=False, max_pages=1):

        results = []
        seen = set()

        try:
            yield {"log": "🚀 Starting ZipRecruiter scraper..."}

            self.open()
            self.search(job, location)

            # 🔥 IMPORTANT STABILITY FIX
            yield {"log": "⏳ Waiting 10 seconds for page stabilization..."}
            self.sleep(10, 10)

            for page in range(max_pages):

                yield {"log": f"📄 Page {page+1}"}

                cards = self.driver.find_elements(By.TAG_NAME, "article")

                yield {"log": f"Found {len(cards)} jobs"}

                for card in cards:

                    data = self.parse_card(card)

                    key = (data["title"], data["company"])
                    if key in seen:
                        continue

                    seen.add(key)

                    if full_job and data["url"]:
                        jd = self.scrape_job_detail(data["url"])
                        data["description"] = jd
                        data["skills"] += self.extract_skills(jd or "")

                    results.append(data)

                    yield {"job": data}

                    self.sleep(0.2, 0.6)

                # ================= NEXT PAGE =================
                try:
                    next_btn = self.safe_find(By.LINK_TEXT, "Next")

                    if not next_btn:
                        break

                    self.driver.execute_script("arguments[0].click();", next_btn)
                    self.sleep(2, 3)

                except:
                    break

            yield {"done": True, "results": results}

        except Exception as e:
            yield {
                "log": f"FATAL: {str(e)}",
                "done": True,
                "results": results
            }

        finally:
            self.close()
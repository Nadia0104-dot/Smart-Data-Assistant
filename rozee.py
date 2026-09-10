# backend/rozee.py

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


class RozeeScraper:

    BASE_URL = "https://www.rozee.pk"

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
    def sleep(self, a=0.5, b=1.2):
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

    # ================= INPUT =================
    def clear_and_type(self, el, text):
        try:
            el.click()
            self.sleep(0.2, 0.4)

            el.send_keys(Keys.CONTROL, "a")
            el.send_keys(Keys.DELETE)

            for ch in text:
                el.send_keys(ch)
                time.sleep(random.uniform(0.01, 0.04))

        except Exception as e:
            logger.warning(f"Typing failed: {e}")

    # ================= OPEN =================
    def open(self):
        self.driver.get(self.BASE_URL)

        self.wait.until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

    # ================= SEARCH (FIXED + STABLE) =================

    def search(self, job, location):

        try:
            # ================= JOB INPUT =================
            keyword_input = self.wait.until(
                EC.presence_of_element_located((By.ID, "search"))
            )

            self.driver.execute_script("arguments[0].value='';", keyword_input)
            self.clear_and_type(keyword_input, job)

            self.sleep(0.5, 1)

            # ================= CITY DROPDOWN OPEN =================
 

            dropdown_btn = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, ".jobCity .dropdown-toggle")
                )
            )

            self.driver.execute_script("arguments[0].click();", dropdown_btn)

            self.sleep(1.5, 2.5)

            # WAIT FOR LIST FULLY OPEN
            self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".jobCity .dropdown-menu.inner li")
                )
            )

            target = location.strip().lower()

            options = self.driver.find_elements(
                By.CSS_SELECTOR,
                ".jobCity .dropdown-menu.inner li"
            )

            clicked = False

            for option in options:
                try:
                    text_el = option.find_element(By.CSS_SELECTOR, "span.text")
                    text = text_el.text.strip().lower()

                    if not text or text == "city":
                        continue

                    if target in text:

                        # 🔥 IMPORTANT FIX: click INNER <a> not <li>
                        a_tag = option.find_element(By.TAG_NAME, "a")

                        self.driver.execute_script(
                            "arguments[0].scrollIntoView(true);",
                            a_tag
                        )

                        self.sleep(0.2, 0.5)

                        self.driver.execute_script(
                            "arguments[0].click();",
                            a_tag
                        )

                        clicked = True
                        break

                except Exception as e:
                    logger.warning(f"Option error: {e}")

            if not clicked:
                raise Exception(f"City not selectable: {location}")

            self.sleep(1, 2)

            # ================= SEARCH BUTTON =================
            search_btn = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, ".jobBtn button[type='submit']")
                )
            )

            self.driver.execute_script("arguments[0].click();", search_btn)

            # ================= STABILIZATION =================
            self.wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            time.sleep(5)

        except Exception as e:
            raise Exception(f"Rozee search failed: {str(e)}")
    # ================= SKILLS =================
    def extract_skills(self, text):

        if not text:
            return []

        text = text.lower()

        skills = [
            "python", "sql", "aws", "react", "node",
            "docker", "kubernetes", "java",
            "javascript", "typescript",
            "mongodb", "firebase",
            "django", "flask", "fastapi",
            "mysql", "postgresql",
            "azure", "gcp",
            "tensorflow", "pytorch",
            "c#", "c++", "php",
            "laravel", "wordpress"
        ]

        return list({s for s in skills if s in text})

    # ================= SALARY =================
    def extract_salary(self, text):

        if not text:
            return None

        matches = re.findall(
            r"(Rs\.?\s?[\d,]+(?:\s?-\s?Rs\.?\s?[\d,]+)?)",
            text,
            re.IGNORECASE
        )

        return matches[0] if matches else None

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

            href = a.get_attribute("href")
            if href and href.startswith("/"):
                href = self.BASE_URL + href

            job["url"] = href

        except:
            pass

        try:
            lines = card.text.split("\n")
            if len(lines) > 1:
                job["company"] = lines[1]
            if len(lines) > 2:
                job["location"] = lines[2]
        except:
            pass

        text = card.text
        job["salary"] = self.extract_salary(text)
        job["skills"] = self.extract_skills(text)

        return job

    # ================= JOB DETAIL =================
    def scrape_job_detail(self, url):

        try:
            main = self.driver.current_window_handle

            self.driver.execute_script("window.open(arguments[0]);", url)

            self.wait.until(lambda d: len(d.window_handles) > 1)

            new_tab = [t for t in self.driver.window_handles if t != main][-1]

            self.driver.switch_to.window(new_tab)

            self.wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            self.sleep(1, 1.5)

            text = self.driver.find_element(By.TAG_NAME, "body").text

            self.driver.close()
            self.driver.switch_to.window(main)

            return text[:7000]

        except Exception as e:
            logger.warning(f"JD failed: {e}")
            return None

    # ================= STREAM =================
    def scrape_stream(self, job, location, full_job=False, max_pages=1):

        results = []
        seen = set()

        try:
            yield {"log": "🚀 Starting Rozee scraper..."}

            self.open()
            self.search(job, location)

            for page in range(max_pages):

                yield {"log": f"📄 Page {page+1}"}

                self.sleep(2, 3)

                # stronger selectors
                cards = self.driver.find_elements(By.CSS_SELECTOR, ".jobListing, .job, article")

                yield {"log": f"Found {len(cards)} jobs"}

                for card in cards:

                    try:
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

                    except Exception as e:
                        yield {"log": f"Card error: {str(e)}"}

                # next page
                try:
                    next_btn = self.safe_find(By.LINK_TEXT, "Next")
                    if not next_btn:
                        break

                    self.driver.execute_script("arguments[0].click();", next_btn)
                    self.sleep(3, 4)

                except:
                    break

            yield {"done": True, "results": results}

        except Exception as e:
            yield {"log": f"FATAL: {str(e)}", "done": True, "results": results}

        finally:
            self.close()
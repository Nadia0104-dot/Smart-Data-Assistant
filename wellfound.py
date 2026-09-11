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
import traceback
import re


logger = logging.getLogger(__name__)


class WellfoundScraper:

    BASE_URL = "https://wellfound.com/jobs"

    def __init__(self, headless=False, proxy=None):

        options = webdriver.ChromeOptions()

        if headless:
            options.add_argument("--headless=new")

        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--start-maximized")

        # anti detection
        options.add_experimental_option(
            "excludeSwitches",
            ["enable-automation"]
        )

        options.add_experimental_option(
            'useAutomationExtension',
            False
        )

        if proxy:
            options.add_argument(f"--proxy-server={proxy}")

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

        self.wait = WebDriverWait(self.driver, 20)

    # =============================
    # UTIL
    # =============================
    def sleep(self, a=0.5, b=1.2):
        time.sleep(random.uniform(a, b))

    def safe_find(self, by, selector, parent=None):

        try:
            root = parent if parent else self.driver
            return root.find_element(by, selector)
        except:
            return None

    def safe_text(self, el):

        try:
            return el.text.strip()
        except:
            return None

    def close(self):

        try:
            self.driver.quit()
        except:
            pass

    # =============================
    # SKILLS
    # =============================
    def extract_skills(self, text):

        if not text:
            return []

        text = text.lower()

        skills = [
            "python","sql","aws","react","node","docker",
            "kubernetes","java","javascript","typescript",
            "mongodb","firebase","django","flask","fastapi",
            "spring","mysql","postgresql","azure","gcp",
            "tensorflow","pytorch","c#","c++","html","css",
            "nextjs","vue","express","redis","graphql"
        ]

        return list({s for s in skills if s in text})

    # =============================
    # OPEN
    # =============================
    def open(self):

        self.driver.get(self.BASE_URL)

        self.wait.until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        self.sleep()

    # =============================
    # SEARCH
    # =============================
    def search(self, job, location):

        query = f"{job} {location}"

        self.driver.get(
            f"https://wellfound.com/jobs?"
            f"query={query.replace(' ', '%20')}"
        )

        self.wait.until(
            EC.presence_of_element_located(
                (By.TAG_NAME, "body")
            )
        )

        self.sleep(2, 3)

    # =============================
    # PARSE CARD
    # =============================
    def parse_card(self, card):

        data = {
            "title": None,
            "company": None,
            "location": None,
            "salary": None,
            "url": None,
            "snippet": None,
            "description": None,
            "skills": []
        }

        try:

            links = card.find_elements(By.TAG_NAME, "a")

            for a in links:

                href = a.get_attribute("href")

                if href and "/jobs/" in href:

                    data["url"] = href

                    txt = a.text.strip()

                    if txt and len(txt) > 2:
                        data["title"] = txt

                    break

        except:
            pass

        # company
        try:

            company_selectors = [
                "[data-test='StartupName']",
                ".company-name",
                ".styles_startupName__",
                "h2"
            ]

            for sel in company_selectors:

                el = self.safe_find(By.CSS_SELECTOR, sel, card)

                if el:
                    data["company"] = self.safe_text(el)
                    break

        except:
            pass

        # location
        try:

            text = card.text

            lines = text.split("\n")

            for line in lines:

                if any(k in line.lower() for k in [
                    "remote",
                    "new york",
                    "san francisco",
                    "usa",
                    "uk",
                    "canada"
                ]):

                    data["location"] = line.strip()
                    break

        except:
            pass

        # snippet
        try:
            data["snippet"] = card.text[:1000]
        except:
            pass

        # salary
        try:

            txt = card.text

            salary_match = re.findall(
                r"\$[\d,]+(?:\s*-\s*\$[\d,]+)?",
                txt
            )

            if salary_match:
                data["salary"] = salary_match[0]

        except:
            pass

        data["skills"] = self.extract_skills(
            data["snippet"] or ""
        )

        return data

    # =============================
    # JOB DETAIL
    # =============================
    def scrape_job_detail(self, url):

        try:

            main_window = self.driver.current_window_handle

            before_tabs = len(self.driver.window_handles)

            self.driver.execute_script(
                "window.open(arguments[0]);",
                url
            )

            self.wait.until(
                lambda d: len(d.window_handles) > before_tabs
            )

            new_tab = [
                t for t in self.driver.window_handles
                if t != main_window
            ][-1]

            self.driver.switch_to.window(new_tab)

            self.wait.until(
                EC.presence_of_element_located(
                    (By.TAG_NAME, "body")
                )
            )

            self.sleep(1, 2)

            self.driver.execute_script("""
                window.scrollTo(
                    0,
                    document.body.scrollHeight
                );
            """)

            self.sleep(1, 2)

            body = self.driver.find_element(
                By.TAG_NAME,
                "body"
            ).text

            self.driver.close()

            self.driver.switch_to.window(main_window)

            return body[:7000]

        except Exception as e:

            logger.warning(f"JD failed: {e}")

            try:
                self.driver.switch_to.window(
                    self.driver.window_handles[0]
                )
            except:
                pass

            return None

    # =============================
    # STREAM
    # =============================
    def scrape_stream(
        self,
        job,
        location,
        full_job=False,
        max_pages=1
    ):

        results = []
        seen = set()

        try:

            yield {
                "log": "🚀 Starting Wellfound scraper..."
            }

            self.open()

            self.search(job, location)

            for page in range(max_pages):

                yield {
                    "log": f"📄 Page {page+1}"
                }

                self.sleep(2, 3)

                cards = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "div"
                )

                valid_cards = []

                for c in cards:

                    try:

                        txt = c.text.strip()

                        if (
                            len(txt) > 40 and
                            ("Apply" in txt or "Remote" in txt)
                        ):

                            links = c.find_elements(By.TAG_NAME, "a")

                            if any(
                                "/jobs/" in (
                                    a.get_attribute("href") or ""
                                )
                                for a in links
                            ):
                                valid_cards.append(c)

                    except:
                        pass

                yield {
                    "log": f"Found {len(valid_cards)} jobs"
                }

                for card in valid_cards:

                    try:

                        data = self.parse_card(card)

                        if not data["title"]:
                            continue

                        key = (
                            data["title"],
                            data["company"]
                        )

                        if key in seen:
                            continue

                        seen.add(key)

                        # full description
                        if full_job and data["url"]:

                            jd = self.scrape_job_detail(
                                data["url"]
                            )

                            data["description"] = jd

                            data["skills"] = list(set(
                                data["skills"] +
                                self.extract_skills(jd or "")
                            ))

                        results.append(data)

                        yield {
                            "job": data
                        }

                        self.sleep(0.5, 1)

                    except Exception as e:

                        yield {
                            "log": f"Card parse failed: {str(e)}"
                        }

                # pagination
                try:

                    next_btn = self.safe_find(
                        By.XPATH,
                        "//a[contains(., 'Next')]"
                    )

                    if not next_btn:
                        break

                    self.driver.execute_script(
                        "arguments[0].click();",
                        next_btn
                    )

                    self.sleep(3, 4)

                except:
                    break

            yield {
                "done": True,
                "results": results
            }

        except Exception as e:

            yield {
                "log": f"FATAL: {str(e)}",
                "trace": traceback.format_exc(),
                "done": True,
                "results": results
            }

        finally:
            self.close()
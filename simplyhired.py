# # backend/simplyhired.py

# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.common.keys import Keys
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from webdriver_manager.chrome import ChromeDriverManager

# import time, random, json, logging, re, traceback

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)


# class SimplyHiredScraper:

#     BASE_URL = "https://www.simplyhired.com"

#     def __init__(self, headless=False, proxy=None):
#         options = webdriver.ChromeOptions()

#         if headless:
#             options.add_argument("--headless=new")

#         # 🔥 Anti-detection + stability
#         options.add_argument("--disable-blink-features=AutomationControlled")
#         options.add_argument("--disable-gpu")
#         options.add_argument("--no-sandbox")
#         options.add_argument("--disable-dev-shm-usage")
#         options.add_argument("--disable-extensions")
#         options.add_argument("--start-maximized")

#         if proxy:
#             options.add_argument(f"--proxy-server={proxy}")

#         self.driver = webdriver.Chrome(
#             service=Service(ChromeDriverManager().install()),
#             options=options
#         )

#         self.wait = WebDriverWait(self.driver, 15)

#     # ================= UTIL =================
#     def human_delay(self, a=0.4, b=1.2):
#         time.sleep(random.uniform(a, b))

#     def safe_find(self, by, selector):
#         try:
#             return self.driver.find_element(by, selector)
#         except:
#             return None

#     def safe_text(self, element):
#         try:
#             return element.text.strip()
#         except:
#             return None

#     # 🔥 Improved salary extraction
#     def extract_salary(self, text):
#         if not text:
#             return None
#         match = re.findall(
#             r"\$?\d{1,3}(?:,\d{3})?(?:[kK])?(?:\s*-\s*\$?\d{1,3}(?:,\d{3})?(?:[kK])?)?",
#             text
#         )
#         return match if match else None

#     # 🔥 Stronger skill extraction
#     def extract_skills(self, text):
#         if not text:
#             return []

#         text = text.lower()

#         SKILL_KEYWORDS = [
#             "python","sql","aws","react","node","docker","kubernetes",
#             "java","c++","javascript","typescript","mongodb","firebase",
#             "unity","c#","ai","ml","django","flask","fastapi","spring",
#             "mysql","postgresql","gcp","azure","tensorflow","pytorch",
#             "html","css","nextjs","vue","express","redis"
#         ]

#         return list(set([k for k in SKILL_KEYWORDS if k in text]))

#     def close(self):
#         try:
#             self.driver.quit()
#         except:
#             pass

#     # ================= INPUT =================
#     def clear_and_type(self, element, text):
#         try:
#             element.click()
#             self.human_delay(0.2, 0.5)

#             element.send_keys(Keys.CONTROL, "a")
#             element.send_keys(Keys.DELETE)

#             self.human_delay(0.2, 0.4)

#             try:
#                 element.clear()
#             except:
#                 pass

#             for ch in text:
#                 element.send_keys(ch)
#                 time.sleep(random.uniform(0.02, 0.06))

#             element.send_keys(Keys.TAB)

#         except Exception as e:
#             logger.warning(f"Typing failed: {e}")

#     # ================= CORE =================
#     def _open_home(self):
#         self.driver.get(self.BASE_URL)

#         self.wait.until(EC.presence_of_element_located(
#             (By.CSS_SELECTOR, "input[data-testid='findJobsKeywordInput']")
#         ))

#     def _search(self, job, location):

#         job_input = self.safe_find(By.CSS_SELECTOR, "input[data-testid='findJobsKeywordInput']")
#         loc_input = self.safe_find(By.CSS_SELECTOR, "input[data-testid='findJobsLocationInput']")

#         if not job_input or not loc_input:
#             raise Exception("Search inputs not found")

#         # Force clear
#         self.driver.execute_script("""
#             document.querySelector("input[data-testid='findJobsKeywordInput']").value = '';
#             document.querySelector("input[data-testid='findJobsLocationInput']").value = '';
#         """)

#         self.human_delay(0.3, 0.6)

#         self.clear_and_type(job_input, job)
#         self.clear_and_type(loc_input, location)

#         btn = self.wait.until(EC.element_to_be_clickable(
#             (By.CSS_SELECTOR, "button[data-testid='findJobsSearchSubmit']")
#         ))

#         self.human_delay(0.3, 0.7)
#         btn.click()

#         self.wait.until(EC.presence_of_element_located(
#             (By.CSS_SELECTOR, "div[data-testid='searchSerpJob']")
#         ))

#     # ================= PARSER =================
#     def _parse_job(self, card, full_job=False):
#         job = {
#             "title": None,
#             "company": None,
#             "location": None,
#             "snippet": None,
#             "salary": None,
#             "skills": [],
#             "description": None,
#             "url": None
#         }

#         try:
#             title_el = card.find_element(By.CSS_SELECTOR, "h2 a")
#             job["title"] = self.safe_text(title_el)
#             job["url"] = title_el.get_attribute("href")
#         except:
#             pass

#         try:
#             job["company"] = self.safe_text(
#                 card.find_element(By.CSS_SELECTOR, "[data-testid='companyName']")
#             )
#         except:
#             pass

#         try:
#             job["location"] = self.safe_text(
#                 card.find_element(By.CSS_SELECTOR, "[data-testid='searchSerpJobLocation']")
#             )
#         except:
#             pass

#         try:
#             snippet = self.safe_text(card.find_element(By.CSS_SELECTOR, "p"))
#             job["snippet"] = snippet
#             job["salary"] = self.extract_salary(snippet)
#             job["skills"] = self.extract_skills(snippet)
#         except:
#             pass

#         # FULL DESCRIPTION
#         if full_job and job["url"]:
#             try:
#                 self.driver.execute_script("window.open(arguments[0]);", job["url"])
#                 self.driver.switch_to.window(self.driver.window_handles[-1])

#                 self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
#                 self.human_delay()

#                 text = self.driver.find_element(By.TAG_NAME, "body").text

#                 job["description"] = text[:5000]  # 🔥 extended

#                 job["skills"] = list(set(job["skills"] + self.extract_skills(text)))
#                 job["salary"] = job["salary"] or self.extract_salary(text)

#             except Exception as e:
#                 logger.warning(f"Full job parse failed: {e}")

#             finally:
#                 self.driver.close()
#                 self.driver.switch_to.window(self.driver.window_handles[0])

#         return job

#     # ================= STREAM =================
#     def scrape_stream(self, job, location, full_job=False, max_pages=1):

#         results = []
#         seen = set()

#         try:
#             yield f"STEP::Start scraping: {job} in {location}"

#             self._open_home()
#             self._search(job, location)

#             for page in range(1, max_pages + 1):
#                 yield f"STEP::Page {page}"

#                 cards = self.driver.find_elements(
#                     By.CSS_SELECTOR, "div[data-testid='searchSerpJob']")
                
#                 yield f"STEP::Found {len(cards)} jobs"

#                 for card in cards:
#                     try:
#                         data = self._parse_job(card, full_job)

#                         key = (data["title"], data["company"])
#                         if key in seen:
#                             continue

#                         seen.add(key)
#                         results.append(data)

#                         yield f"STEP::Job {len(results)}: {data['title']}"

#                         self.human_delay(0.3, 0.8)

#                     except Exception as e:
#                         yield f"STEP::ERROR::{str(e)}\n{traceback.format_exc()}"

#                 # PAGINATION FIX
#                 try:
#                     if page >= max_pages:
#                         break

#                     next_btn = self.safe_find(By.CSS_SELECTOR, "a[aria-label='Next']")

#                     if not next_btn or next_btn.get_attribute("aria-disabled") == "true":
#                         break

#                     self.driver.execute_script("arguments[0].scrollIntoView();", next_btn)
#                     self.human_delay()
#                     next_btn.click()

#                     self.wait.until(EC.presence_of_element_located(
#                         (By.CSS_SELECTOR, "div[data-testid='searchSerpJob']")
#                     ))

#                 except:
#                     break

#             yield f"DONE::{json.dumps(results, ensure_ascii=False)}"

#         except Exception as e:
#             yield f"STEP::FATAL::{str(e)}"
#             yield f"DONE::{json.dumps(results, ensure_ascii=False)}"

#         finally:
#             self.close()

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

import time, random, json, logging, re, traceback

logger = logging.getLogger(__name__)


class SimplyHiredScraper:

    BASE_URL = "https://www.simplyhired.com"

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

        self.wait = WebDriverWait(self.driver, 20)

    # ================= UTIL =================
    def sleep(self, a=0.3, b=0.9):
        time.sleep(random.uniform(a, b))

    def safe_find(self, by, sel):
        try:
            return self.driver.find_element(by, sel)
        except:
            return None

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
            logger.warning(f"Typing error: {e}")

    # ================= OPEN =================
    def open(self):
        self.driver.get(self.BASE_URL)

        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='findJobsKeywordInput']"))
        )

    # ================= SEARCH =================
    def search(self, job, location):

        job_in = self.safe_find(By.CSS_SELECTOR, "input[data-testid='findJobsKeywordInput']")
        loc_in = self.safe_find(By.CSS_SELECTOR, "input[data-testid='findJobsLocationInput']")

        if not job_in or not loc_in:
            raise Exception("Search inputs missing")

        self.driver.execute_script("""
            arguments[0].value='';
            arguments[1].value='';
        """, job_in, loc_in)

        self.sleep()

        self.clear_and_type(job_in, job)
        self.clear_and_type(loc_in, location)

        btn = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='findJobsSearchSubmit']"))
        )

        btn.click()

        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='searchSerpJob']"))
        )

    # ================= PARSE LIST CARD =================
    def parse_card(self, card):

        job = {
            "title": None,
            "company": None,
            "location": None,
            "url": None,
            "description": None,
            "skills": []
        }

        try:
            a = card.find_element(By.CSS_SELECTOR, "h2 a")
            job["title"] = a.text.strip()
            job["url"] = a.get_attribute("href")
        except:
            pass

        try:
            job["company"] = card.find_element(By.CSS_SELECTOR, "[data-testid='companyName']").text.strip()
        except:
            pass

        try:
            job["location"] = card.find_element(By.CSS_SELECTOR, "[data-testid='searchSerpJobLocation']").text.strip()
        except:
            pass

        return job

    # ================= SAFE JD SCRAPER (FIXED CORE) =================
    def scrape_job_detail(self, url):

        try:
            main_window = self.driver.current_window_handle
            before_tabs = len(self.driver.window_handles)

            self.driver.execute_script("window.open(arguments[0]);", url)

            # wait new tab
            self.wait.until(lambda d: len(d.window_handles) > before_tabs)

            new_tab = [t for t in self.driver.window_handles if t != main_window][-1]

            self.driver.switch_to.window(new_tab)

            # wait page load
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            self.sleep(1, 1.5)

            # scroll for lazy content
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            self.sleep(0.8, 1.2)

            body = self.driver.find_element(By.TAG_NAME, "body").text

            # fallback retry if empty JD
            if not body or len(body) < 200:
                self.sleep(1)
                body = self.driver.find_element(By.TAG_NAME, "body").text

            self.driver.close()
            self.driver.switch_to.window(main_window)

            return body[:6000]

        except Exception as e:
            logger.warning(f"JD failed: {e}")

            try:
                self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass

            return None

    # ================= SKILLS =================
    def extract_skills(self, text):
        if not text:
            return []

        text = text.lower()

        skills = [
            "python","sql","aws","react","node","docker","kubernetes",
            "java","javascript","typescript","mongodb","firebase",
            "django","flask","fastapi","spring","mysql","postgresql",
            "azure","gcp","tensorflow","pytorch","c#","c++"
        ]

        return list({s for s in skills if s in text})

    # ================= STREAM =================
    def scrape_stream(self, job, location, full_job=False, max_pages=1):

        results = []
        seen = set()

        try:
            yield {"log": "🚀 Starting scraper..."}

            self.open()
            self.search(job, location)

            for p in range(max_pages):

                yield {"log": f"📄 Page {p+1}"}

                cards = self.driver.find_elements(By.CSS_SELECTOR, "div[data-testid='searchSerpJob']")

                yield {"log": f"Found {len(cards)} jobs"}

                for c in cards:

                    data = self.parse_card(c)

                    key = (data["title"], data["company"])
                    if key in seen:
                        continue

                    seen.add(key)

                    # ================= FULL JD =================
                    if full_job and data["url"]:
                        jd = self.scrape_job_detail(data["url"])
                        data["description"] = jd
                        data["skills"] = self.extract_skills(jd)

                    results.append(data)

                    yield {"job": data}

                    self.sleep(0.2, 0.5)

                # pagination
                try:
                    next_btn = self.safe_find(By.CSS_SELECTOR, "a[aria-label='Next']")
                    if not next_btn:
                        break

                    self.driver.execute_script("arguments[0].click();", next_btn)

                    self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='searchSerpJob']"))
                    )

                except:
                    break

            yield {"done": True, "results": results}

        except Exception as e:
            yield {"log": f"FATAL: {str(e)}", "done": True, "results": results}

        finally:
            try:
                self.driver.quit()
            except:
                pass
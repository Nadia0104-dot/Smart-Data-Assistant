from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, as_completed
import time, random, re


# =========================
# DRIVER
# =========================
def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


# =========================
# HELPERS
# =========================
def parse_rating(text):
    if not text:
        return None, None

    rating = re.search(r'([\d.]+)', text)
    reviews = re.search(r'\((.*?)\)', text)

    return (
        rating.group(1) if rating else None,
        reviews.group(1) if reviews else None
    )


def extract_coordinates(url):
    match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', url)
    return (match.group(1), match.group(2)) if match else (None, None)


# =========================
# PHONE
# =========================
def extract_phone(driver, wait):
    try:
        el = wait.until(EC.presence_of_element_located(
            (By.XPATH, '//button[contains(@data-item-id,"phone")]')
        ))
        if el.text:
            return el.text
    except:
        pass

    try:
        for b in driver.find_elements(By.XPATH, '//button'):
            aria = b.get_attribute("aria-label") or ""
            if "Phone" in aria:
                return aria.split(":")[-1].strip()
    except:
        pass

    try:
        body = driver.find_element(By.TAG_NAME, "body").text
        match = re.search(r'(\+?\d[\d\-\(\) ]{7,})', body)
        if match:
            return match.group(1)
    except:
        pass

    return None


# =========================
# INFO
# =========================
def extract_info(driver, wait):
    data = {"address": None, "phone": None, "website": None}

    try:
        el = wait.until(EC.presence_of_element_located(
            (By.XPATH, '//button[contains(@data-item-id,"address")]')
        ))
        data["address"] = el.text
    except:
        pass

    data["phone"] = extract_phone(driver, wait)

    try:
        el = driver.find_element(By.XPATH, '//a[contains(@data-item-id,"authority")]')
        data["website"] = el.get_attribute("href")
    except:
        pass

    return data


# =========================
# SINGLE SCRAPE
# =========================
def scrape_single(url):
    driver = create_driver()
    wait = WebDriverWait(driver, 15)

    try:
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))

        # scroll
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(2, 3))

        name = driver.find_element(By.TAG_NAME, "h1").text

        rating_raw = None
        try:
            rating_raw = driver.find_element(By.XPATH, '//div[@role="img"]').get_attribute("aria-label")
        except:
            pass

        rating, reviews = parse_rating(rating_raw)

        info = extract_info(driver, wait)

        current_url = driver.current_url
        lat, lng = extract_coordinates(current_url)

        return {
            "name": name,
            "rating": rating,
            "reviews": reviews,
            "address": info["address"],
            "phone": info["phone"],
            "website": info["website"],
            "maps_url": current_url,
            "latitude": lat,
            "longitude": lng,
            "status": "success"
        }

    except Exception as e:
        return {"url": url, "status": "failed", "error": str(e)}

    finally:
        driver.quit()


# =========================
# PARALLEL SCRAPER
# =========================
def scrape_google_maps_stream(urls, max_workers=5):
    from concurrent.futures import ThreadPoolExecutor

    results = [None] * len(urls)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:

        future_map = {
            executor.submit(scrape_single, url): idx
            for idx, url in enumerate(urls)
        }

        for future in future_map:
            idx = future_map[future]

            try:
                results[idx] = future.result()
            except Exception as e:
                results[idx] = {
                    "maps_url": urls[idx],
                    "status": "failed",
                    "error": str(e)
                }

        # RETURN RESULTS IN ORIGINAL ORDER
        for result in results:
            yield result

def clean_text(text):
    if not text:
        return None

    # remove weird unicode symbols (Google icons)
    text = text.encode("ascii", "ignore").decode()

    # remove extra spaces/newlines
    text = text.replace("\n", " ").strip()

    return text

def scrape_google_maps_stream(urls, max_workers=5):
    from concurrent.futures import ThreadPoolExecutor, as_completed

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(scrape_single, url) for url in urls]

        for future in as_completed(futures):
            try:
                yield future.result()
            except:
                yield {"status": "failed"}
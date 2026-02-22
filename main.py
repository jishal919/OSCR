import socket
import pandas as pd
import re
import os
import time
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright

INPUT_FILE = "TrusteeConnect Data.csv"
OUTPUT_FILE = "charity_results.csv"

MAIN_URL = "https://www.oscr.org.uk/search/register-search?Keyword="

EMAIL_REGEX = r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"

GENERIC_PREFIXES = [
    "info@", "contact@", "enquiries@", "admin@",
    "hello@", "office@", "support@", "team@"
]

# --------------------------------------------------
# CSV INPUT
# --------------------------------------------------
def extract_charity_names(file_path, column_name="Charity Name"):
    df = pd.read_csv(
        file_path,
        usecols=[column_name],
        dtype=str,
        encoding="cp1252",
        engine="c"
    )
    return df[column_name].dropna().str.strip().tolist()

# --------------------------------------------------
# INTERNET CHECK
# --------------------------------------------------
def internet_available():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except:
        return False

# --------------------------------------------------
# SAFE NAVIGATION (UPDATED LOGIC)
# --------------------------------------------------
def safe_goto(page, url, retry_delay=5):
    while True:
        try:
            response = page.goto(
                url,
                timeout=15000,
                wait_until="domcontentloaded"
            )

            if response:
                status = response.status
                if status >= 400:
                    print(f"⚠ Skipping {url} (HTTP {status})")
                    return False

            return True

        except Exception as e:
            error_message = str(e).lower()

            # ONLY retry if whole internet is disconnected
            if "net::err_internet_disconnected" in error_message:
                print("\n⚠ Internet disconnected.")
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue

            # DNS errors (NXDOMAIN), timeouts, refused connections etc.
            print(f"⏭ Skipping {url} ({error_message.splitlines()[0]})")
            return False
# --------------------------------------------------
# COOKIE HANDLER
# --------------------------------------------------
def handle_cookie_once(page):
    try:
        page.wait_for_timeout(2000)
        button = page.query_selector("#ccc-reject-settings")
        if button and button.is_visible():
            button.click()
    except:
        pass

# --------------------------------------------------
# EMAIL CLEANING
# --------------------------------------------------
VALID_TLD_MIN_LENGTH = 2
MAX_LOCAL_LENGTH = 64
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg", "css", "js", "ico", "pdf"}

def clean_email(email):
    email = email.strip().lower()

    match = re.search(EMAIL_REGEX, email)
    if not match:
        return None

    email = match.group(0)

    try:
        local, domain = email.split("@", 1)
    except:
        return None

    if len(local) > MAX_LOCAL_LENGTH:
        return None

    if "." not in domain:
        return None

    parts = domain.split(".")
    tld = parts[-1]

    if tld in IMAGE_EXTENSIONS:
        return None

    if not re.fullmatch(r"[a-z]{%d,}" % VALID_TLD_MIN_LENGTH, tld):
        return None

    if not re.search(r"[a-z]", domain):
        return None

    if re.search(r"\d+x\d+", domain):
        return None

    return email

def choose_best_email(emails):
    for prefix in GENERIC_PREFIXES:
        for email in emails:
            if email.startswith(prefix):
                return email
    return next(iter(emails)) if emails else None

# --------------------------------------------------
# EXTRACT EMAILS
# --------------------------------------------------
def extract_emails_from_page(page):
    emails = set()
    try:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1200)

        html = page.content()
        matches = re.findall(EMAIL_REGEX, html)

        for match in matches:
            valid = clean_email(match)
            if valid:
                emails.add(valid)

    except:
        pass

    return emails

# --------------------------------------------------
# CONTROLLED DOMAIN CRAWLER
# --------------------------------------------------
def crawl_for_email(page, start_url, max_pages=10):
    parsed = urlparse(start_url)
    domain = parsed.netloc
    root_url = f"{parsed.scheme}://{parsed.netloc}"

    visited = set()
    queue = [start_url]

    if start_url != root_url:
        queue.append(root_url)

    common_paths = [
        "/contact",
        "/contact.php",
        "/contact-us",
        "/contact-us.php",
        "/user_contact.php",
        "/about",
        "/about.php",
        "/team"
    ]

    for path in common_paths:
        queue.append(root_url + path)

    while queue and len(visited) < max_pages:
        url = queue.pop(0)

        if url in visited:
            continue

        visited.add(url)
        print(f"Scanning: {url}")

        if not safe_goto(page, url):
            continue

        emails = extract_emails_from_page(page)
        if emails:
            return choose_best_email(emails)

        try:
            links = page.query_selector_all("a[href]")
            for link in links:
                href = link.get_attribute("href")
                if not href:
                    continue

                full_url = urljoin(url, href)

                if domain in full_url and full_url not in visited:
                    queue.append(full_url)
        except:
            continue

    return None

# --------------------------------------------------
# RESUME + DUPLICATE PROTECTION
# --------------------------------------------------
def load_existing_results():
    if not os.path.exists(OUTPUT_FILE):
        return pd.DataFrame()
    try:
        return pd.read_csv(OUTPUT_FILE)
    except:
        return pd.DataFrame()

def append_result(row):
    existing_df = load_existing_results()

    if not existing_df.empty:
        if row["Charity Name"] in existing_df["Charity Name"].values:
            print("Duplicate charity detected. Skipping write.")
            return

    df = pd.DataFrame([row])

    if existing_df.empty:
        df.to_csv(OUTPUT_FILE, index=False)
    else:
        df.to_csv(OUTPUT_FILE, mode="a", header=False, index=False)

def get_resume_index():
    if not os.path.exists(OUTPUT_FILE):
        return 0

    try:
        df = pd.read_csv(OUTPUT_FILE)

        if df.empty:
            return 0

        if "Index" not in df.columns:
            return 0

        df = df.dropna(subset=["Index"])
        last_index = df["Index"].astype(int).max()

        return last_index + 1

    except:
        return 0

# --------------------------------------------------
# WAIT FOR WEBSITE COLUMN
# --------------------------------------------------
def wait_for_website_column(page, max_attempts=15):
    for _ in range(max_attempts):
        try:
            page.wait_for_load_state("domcontentloaded")

            website_element = page.query_selector(
                "span.col-7.col-lg-9.text a[target='_blank']"
            )

            if website_element:
                return website_element.get_attribute("href")

            result_row = page.query_selector("div.charitydetailrow")
            if result_row:
                break

            page.wait_for_timeout(1000)

        except:
            page.wait_for_timeout(1000)
            continue

    return ""

# --------------------------------------------------
# MAIN PROCESSOR (UPDATED)
# --------------------------------------------------
def process_all_charities():
    charities = extract_charity_names(INPUT_FILE)
    start_index = get_resume_index()

    print(f"Resuming from index: {start_index}")

    total_time = 0
    execution_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--start-maximized"])
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        if not safe_goto(page, MAIN_URL):
            print("Failed to open OSCR.")
            return

        handle_cookie_once(page)

        for idx in range(start_index, len(charities)):
            start_time = time.time()

            charity = charities[idx]
            print(f"\nProcessing [{idx}] {charity}")

            website_status = "Not Found"
            website_url = ""
            email_status = "Not Found"
            contact_email = ""

            try:
                if not safe_goto(page, MAIN_URL):
                    continue

                page.wait_for_selector("#CharityName", timeout=15000)

                page.fill("#CharityName", "")
                page.fill("#CharityName", charity)
                page.click("#search-submit")
                page.wait_for_load_state("networkidle")

                website_url = wait_for_website_column(page)

                if website_url:
                    website_status = "Found"
                    print(f"Website Found: {website_url}")

                    best_email = crawl_for_email(page, website_url)

                    if best_email:
                        email_status = "Found"
                        contact_email = best_email
                        print(f"✅ Email Found: {contact_email}")
                else:
                    print("Website not found.")

            except Exception as e:
                print(f"Error processing {charity}: {e}")

            append_result({
                "Index": idx,
                "Charity Name": charity,
                "Website Status": website_status,
                "Website URL": website_url,
                "Contact Email Status": email_status,
                "Contact Email": contact_email
            })

            end_time = time.time()
            execution_time = end_time - start_time

            total_time += execution_time
            execution_count += 1
            avg_time = total_time / execution_count

            print(f"Execution Time: {execution_time:.2f} sec")
            print(f"Average Time: {avg_time:.2f} sec")
            print("Saved progress.")

        browser.close()

if __name__ == "__main__":
    process_all_charities()
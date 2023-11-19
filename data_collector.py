import modal
from email import encoders
import requests
from subprocess import getoutput
from time import sleep

import logging
import smtplib
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


CIRA_URL = "https://www.cira.ca/en/ca-domains/tbr/"
SEO_RANK_BASE_URL = "https://seo-rank.my-addr.com"
SEO_RANK_API_KEY = ""

EMAIL_RECEPIENTS = []
EMAIL_SUBJECT = "Scraping Data"
EMAIL_SENDER = "noreply@urls-scraper.com"
EMAIL_LOGIN = "" 
EMAIL_PASSWORD = ""


chrome_image = modal.Image.debian_slim(python_version="3.10").run_commands(
    "apt-get update",
    "apt-get install -y curl",
    "curl -LO https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb",
    "apt install -y ./google-chrome-stable_current_amd64.deb",
    "pip3 install selenium webdriver-manager requests"
)
stub = modal.Stub(name="link-scraper")


@stub.function(image=chrome_image)
def scrape_urls():
    logging.info("Started scrape_urls function")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--verbose')
    chrome_options.add_experimental_option("prefs", {
            "download.default_directory": "./downloads/",
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing_for_trusted_sources_enabled": False,
            "safebrowsing.enabled": False
    })
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-software-rasterizer')

    browser = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
    logging.info("Launched the Chrome")
    browser.get(CIRA_URL)
    logging.info("Retrieved CIRA website")
    try:
        WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div/div[2]/div/div[1]/div/div[1]/div/div/button"))).click()
        WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div/div[2]/div/div[1]/div/div[2]/div[2]/div/div/div[2]/ul/li[1]/button"))).click()
    except:
        raise Exception("Failed to scrape list of URLs from CIRA")
    finally:
        logging.info("Downloaded URLs list")
    browser.close()
    downloaded_file = getoutput('ls downloads').split('\n')[-1]
    return open(f"downloads/{downloaded_file}").readlines()

@stub.function(image=chrome_image, timeout=3600)
def process_urls(links_csv):
    logging.info("Started process_urls function")
    links_output = ""
    for row in links_csv[1:]:
        links_output += f"{row.split(',')[0]}\n"
    try:
        response = requests.post(f"{SEO_RANK_BASE_URL}/upload_file.php?secret={SEO_RANK_API_KEY}&moz=0&sr=1&fb=0", files={'file': ('links.txt', links_output)})
        file_id = response.json()
        logging.info(f"Submitted URLs to Seo Rank: fileId {file_id}")
    except:
        raise Exception("Failed to POST links to Seo Rank for batch processing")
    for _ in range(60):
        sleep(60)
        response = requests.get(f'{SEO_RANK_BASE_URL}/file_info.php?secret={SEO_RANK_API_KEY}&id={file_id}')
        result = response.content.decode()
        status = result.split('|')[3]
        if status == 'finished':
            logging.info("Seo Rank processing URLs finished")
            break
        else:
            logging.info(f"Seo Rank processing URLs with status: {status}")
    try:
        response = requests.get(result.split('|')[-1])
        if not response.status_code == 200:
            raise Exception("Failed to retrieve Seo Rank results")
        logging.info("Downloaded Seo Rank results")
        result = response.content.decode().replace('"', "").split('\n')
    except:
        raise Exception("Failed to retrieve Seo Rank results")
    SORT_COLUMN = 2
    data, result = [result[0]], sorted(result[1:-1], key=lambda x: int(x.split(',')[SORT_COLUMN]), reverse=True)
    data.extend(result)
    return '\n'.join(data)

@stub.function(image=chrome_image)
def send_email(links_data, success=True, message=""):
    msg = MIMEMultipart()
    msg['Subject'] = EMAIL_SUBJECT
    msg['From'] = EMAIL_SENDER
    msg['To'] = ', '.join(EMAIL_RECEPIENTS)
    if success:
        logging.info("Notifying begin on Success")
        # Add the attachment to the message
        attachment = MIMEBase("application", "octet-stream")
        attachment.set_payload(links_data)
        encoders.encode_base64(attachment)
        attachment.add_header(
            "Content-Disposition",
            f"attachment; filename=links.csv",
        )
        msg.attach(attachment)
    else:
        logging.info("Notifying begin on Failure")
    html_part = MIMEText(message)
    msg.attach(html_part)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_LOGIN, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEPIENTS, msg.as_string())
    
@stub.local_entrypoint()
def main():
    try:
        scrapped_links_data = scrape_urls.remote()
        links_data = process_urls.remote(scrapped_links_data)
        send_email.remote(links_data, True, message="Successfuly collected URLs information")
    except Exception as e:
        send_email.remote(None, False, message=str(e))

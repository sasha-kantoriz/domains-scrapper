import csv
from subprocess import getoutput
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def gather():
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
    chrome_options.add_argument('--disable-software-rasterizer')

    browser = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
    browser.get("https://www.cira.ca/en/ca-domains/tbr/")
    try:
        WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div/div[2]/div/div[1]/div/div[1]/div/div/button"))).click()
        WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div/div[2]/div/div[1]/div/div[2]/div[2]/div/div/div[2]/ul/li[1]/button"))).click()
    except:
        pass
    browser.close()

def process():
    links_csv = getoutput('ls downloads').split("\n")[-1]
    with open(f"downloads/{links_csv}") as csvfile:
        linksreader = csv.reader(csvfile)
        for row in linksreader:
            print(row[0])

if __name__ == '__main__':
    gather()
    process()

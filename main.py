from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.edge.options import Options
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import pandas as pd
import time
import re
import logging
import os

def get_lat_long_from_google_maps(driver, address):
    """Fetch latitude and longitude for a given address using Google Maps."""
    search_url = f"https://www.google.com/maps/search/{address.replace(' ', '+')}"
    driver.get(search_url)
    time.sleep(5)  # Allow time for Google Maps to load
    
    # Extract the current URL after page load
    current_url = driver.current_url
    match = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", current_url)
    if match:
        return float(match.group(1)), float(match.group(2))
    else:
        logging.warning(f"Could not find coordinates for address: {address}")
        return None, None

# Initialize the Edge WebDriver
def init_driver():
    options = Options()
    options.use_chromium = True  # Use Chromium-based Edge
    options.add_argument("--start-maximized")  # Start browser maximized
    driver = webdriver.Edge(
        service=EdgeService(EdgeChromiumDriverManager().install()),
        options=options
    )
    return driver

# Extract property URLs from a single page
def extract_property_urls(driver):
    property_urls = []
    try:
        property_elements = driver.find_elements(By.CSS_SELECTOR, ".property-box a.property-img")
        for elem in property_elements:
            url = elem.get_attribute("href")
            property_urls.append(url)
    except Exception as e:
        print(f"Error extracting property URLs: {e}")
    return property_urls

# Scrape property details from an individual property page
def scrape_property_details(driver, url):
    data = {"URL": url}
    try:
        driver.get(url)
        time.sleep(3)  # Wait for the page to load

        # Extract Name
        name_element = driver.find_element(By.CSS_SELECTOR, ".heading-properties-3 h1")
        data["Name"] = name_element.text

        # Extract Price, Address, Transaction
        details_element = driver.find_element(By.CSS_SELECTOR, ".heading-properties-3 .mb-30")
        price = details_element.find_element(By.CSS_SELECTOR, ".property-price").text
        transaction = details_element.find_element(By.CSS_SELECTOR, ".rent").text
        address = details_element.find_element(By.CSS_SELECTOR, ".location").text

        data["Price"] = price
        data["Transaction"] = transaction
        data["Address"] = address

        # Extract Description
        description_element = driver.find_element(By.CSS_SELECTOR, ".properties-description.mb-40 p")
        data["Description"] = description_element.text

        # Extract Characteristics
        characteristics = {}
        features = {}
        table_elements = driver.find_elements(By.CSS_SELECTOR, ".floor-plans.mb-50 table")
        if len(table_elements) >= 1:
            char_rows = table_elements[0].find_elements(By.TAG_NAME, "tr")
            for row in char_rows[1:]:
                cols = row.find_elements(By.TAG_NAME, "td")
                for i in range(len(cols)):
                    characteristics[char_rows[0].find_elements(By.TAG_NAME, "td")[i].text.strip()] = cols[i].text.strip()

        layout = {}
        if len(table_elements) >= 2:
            rows = table_elements[1].find_elements(By.TAG_NAME, "tr")
            headers = [th.text.strip() for th in rows[0].find_elements(By.TAG_NAME, "td")]
            values = [td.text.strip() for td in rows[1].find_elements(By.TAG_NAME, "td")]
            layout = dict(zip(headers, values))

        data["Layout"] = layout

        # Extract Features
        if len(table_elements) >= 2:
            feature_rows = table_elements[1].find_elements(By.TAG_NAME, "tr")
            for row in feature_rows[1:]:
                cols = row.find_elements(By.TAG_NAME, "td")
                for i in range(len(cols)):
                    features[feature_rows[0].find_elements(By.TAG_NAME, "td")[i].text.strip()] = cols[i].text.strip()

        data["Characteristics"] = characteristics
        data["Features"] = features

        data['Property Type'] = characteristics.get("Lloj", "-")
        data['Area'] = features.get("Siperfaqe Bruto", "-")

        # Extract latitude and longitude
        data["Latitude"], data["Longitude"] = get_lat_long_from_google_maps(driver, address)

    except Exception as e:
        print(f"Error scraping details from {url}: {e}")
    return data

# Scrape properties from all pages
def scrape_all_pages(start_page, end_page):
    driver = init_driver()
    base_url = "https://anem-ks.com/properties?business_type=sale"
    all_properties = []
    scraped_urls = set()

    try:
        for page_number in range(start_page, end_page + 1):
            pagination_url = f"{base_url}&page={page_number}"
            print(f"Scraping page {page_number}... : {pagination_url}")
            driver.get(pagination_url)
            time.sleep(3)  # Wait for the page to load

            # Extract property URLs
            property_urls = extract_property_urls(driver)
            if not property_urls:
                print("No more properties found. Exiting...")
                break

            # Scrape each property
            for url in property_urls:
                if url not in scraped_urls:
                    scraped_urls.add(url)
                    property_data = scrape_property_details(driver, url)
                    all_properties.append(property_data)

    except Exception as e:
        print(f"Error occurred during scraping: {e}")

    finally:
        driver.quit()

    return all_properties

# Save data to Excel in the 'output' folder
def save_to_excel(data, filename="output/51_55.xlsx"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)
    print(f"Data saved to {filename}")

# Run the scraper
if __name__ == "__main__":
    start_page = 51
    end_page = 55
    data = scrape_all_pages(start_page, end_page)
    save_to_excel(data)

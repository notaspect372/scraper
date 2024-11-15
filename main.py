import os
import re
import math
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable
from urllib.parse import urljoin

# Ensure the artifacts folder exists
os.makedirs("artifacts", exist_ok=True)

def delay(seconds):
    time.sleep(seconds)

headers = {
    "Beacon-Device-ID": "4fac34ee-d40e-46ee-a867-bb0163593e1c",
    "correlationId": "ba3af455-e0ce-473b-b3e8-5564286d3bc4",
    "sec-ch-ua-platform": "\"Windows\"",
    "Referer": "https://ghanapropertycentre.com/",
    "Beacon-Device-Instance-ID": "e58c545c-5ef8-446b-860a-77920b2fe91c",
    "sec-ch-ua": "\"Chromium\";v=\"130\", \"Microsoft Edge\";v=\"130\", \"Not?A_Brand\";v=\"99\"",
    "Helpscout-Origin": "Beacon-Embed",
    "sec-ch-ua-mobile": "?0",
    "Helpscout-Release": "2.2.223",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
    "Accept": "application/json, text/plain, */*"
}

cookies = {
    "cf_clearance": "Oh0902T.bmkktoMePJQGxwBOQTw6WaTKswHWRhAI3Mc-1731413990-1.2.1.1-zfqEraO0fmo38RvMHS7SIsLP61cbsw_1pjbH1Wv_1I8wXsHsgTn5unckGtCiogvCLlr_2Xermloqd0Qj3BafMT54QRyyETM4qeVXtDkjmqfTx0hLy9r219sHX5aL6rZ6aPxE0Ax1FKT8r59rViK848ZdFhCMCT5icwSGnP90roy88kceJaZnGBGw2pCUGNnO02lLx62_mQK.V29tRwAcj6JHMGM2yadYVhTg20ifjNYsrPsrDLFQIuIjls8G7Hvj.mntyxCAbC5dRbv2SKMFpseHby_TK4Mjd2PxpiR93PMPXFpRV_IIn3LQIJ1wkEVLJP7gOZPAXieHap3lkKcx6otzaKoqSXOeUxDGZHzDCd0P1_x__oMakMV6YgiX8cF3vyW3yuCYuIIT4xC8r6M29PMkv.1NNnXE45MBJIuN1RpNPU9hiCWZAnCwz9m.LHEh",
    "XSRF-TOKEN": "eyJpdiI6IkVrUGZTM1BRU0dyRDdjNXkyNjVLVlE9PSIsInZhbHVlIjoiQm5kRG81N0UzUktpREQySDEzRGNGWHI1UnlwUXdGOTZyOGo4WC9iMXJialhWTnpHYjZHZzFhQnp2U2o1enhpaEVNcWM2NkxCY2lkcUJvL2ZJcHc1MW1XOTFwNzFsd1NrbEdOQTdiREtRUnMwL3E3RjE2MGdvTzJFYzlwSCtuWDAiLCJtYWMiOiJlZTdiNTZhNzA5NmQ0ZGRhNTNkYTA0NmJjNWYyMTJlZDljMWUxNDZmOGFiNWQzNzJmOWJmZWEyMTQ0MDljMWFmIiwidGFnIjoiIn0%3D"
}
def get_lat_lon(address, retries=3, delay_between_retries=2):
    geolocator = Nominatim(user_agent="property_scraper", timeout=10)
    for attempt in range(retries):
        try:
            location = geolocator.geocode(address)
            if location:
                return location.latitude, location.longitude
            else:
                return None, None
        except GeocoderUnavailable:
            print(f"Geocoder service unavailable for address '{address}', retrying ({attempt + 1}/{retries})...")
            time.sleep(delay_between_retries)
        except Exception as e:
            print(f"An error occurred while geocoding '{address}': {e}")
            return None, None
    print(f"Failed to retrieve coordinates for '{address}' after {retries} attempts.")
    return None, None

def scrape_property_details(property_url):
    response = requests.get(property_url, headers=headers, cookies=cookies)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    transaction_type = "sale" if "sale" in property_url.lower() else "rent"
    
    # Check if the title element exists
    name_element = soup.find('h4', class_='content-title')
    name = name_element.text.strip() if name_element else "N/A"  # Use "N/A" if not found
    
    # Check if the description element exists
    description_element = soup.find('p', itemprop='description')
    description = description_element.text.strip() if description_element else "N/A"
    
    # Check if the address element exists
    address_element = soup.find('address')
    address = address_element.text.strip() if address_element else "N/A"
    
    price_span = soup.find('span', class_='pull-right property-details-price')
    if price_span:
        price_amount = "".join([elem.text for elem in price_span.find_all('span', class_='price')]).strip()
        price_period = price_span.find('span', class_='period').text.strip() if price_span.find('span', class_='period') else ""
        price_approx = price_span.find('span', class_='naira-equiv').text.strip() if price_span.find('span', class_='naira-equiv') else ""
        price = f"{price_amount} {price_period} ({price_approx})" if price_approx else f"{price_amount} {price_period}"
    else:
        price = None

    characteristics_table = soup.find('table', class_='table table-bordered table-striped')
    characteristics = {}
    area = None
    property_type = None
    if characteristics_table:
        for row in characteristics_table.find_all('tr'):
            for cell in row.find_all('td'):
                strong = cell.find('strong')
                if strong:
                    key = strong.text.strip().replace(':', '')
                    value = cell.text.replace(strong.text, '').strip()
                    characteristics[key] = value
                    if key == "Total Area":
                        area = value
                    if key == "Type":
                        property_type = value

    covered_area = characteristics.get("Covered Area", "")

    latitude, longitude = get_lat_lon(address)
    
    property_data = {
        'URL': property_url,
        'Name': name,
        'Description': description,
        'Address': address,
        'Price': price,
        'Area': area,
        'Covered Area': covered_area,
        'Characteristics': characteristics,
        'Property Type': property_type,
        'Transaction Type': transaction_type,
        'Latitude': latitude,
        'Longitude': longitude
    }
    
    return property_data

def scrape_properties_from_urls(base_urls):
    for base_url in base_urls:
        property_urls = set()
        response = requests.get(f"{base_url}", headers=headers, cookies=cookies)
        soup = BeautifulSoup(response.content, 'html.parser')

        pagination_results = soup.find('span', class_='pagination-results')
        total_pages = 1

        if pagination_results:
            total_listings_text = pagination_results.text.strip()
            total_listings = int(total_listings_text.split("of")[1].replace(",", "").strip())
            listings_per_page = 20
            total_pages = math.ceil(total_listings / listings_per_page)

        for page in range(1, total_pages + 1):
            url = f"{base_url}?page={page}"
            print(f"Scraping page: {url}")
            response = requests.get(url, headers=headers, cookies=cookies)
            if response.status_code != 200:
                print(f"Skipping page {page} due to non-200 status code.")
                continue

            soup = BeautifulSoup(response.content, 'html.parser')
            property_divs = soup.find_all('div', class_='wp-block-content')
            for div in property_divs:
                links = div.find_all('a', href=True)
                for link in links:
                    full_url = urljoin(base_url, link['href'])
                    property_urls.add(full_url)
            delay(2)

        print(f"Total unique property URLs scraped from {base_url}: {len(property_urls)}")

        all_properties_data = []
        for property_url in property_urls:
            property_data = scrape_property_details(property_url)
            print(property_data)
            all_properties_data.append(property_data)

        filename = re.sub(r'[\\/*?:"<>|]', "", base_url.split('?')[0].replace('/', '_')) + ".xlsx"
        file_path = os.path.join("artifacts", filename)  # Save within artifacts folder
        df = pd.DataFrame(all_properties_data)
        df.to_excel(file_path, index=False)
        print(f"Data saved to {file_path}")

# Example usage
base_urls = [
    "https://ghanapropertycentre.com/for-rent",
    # Add more URLs if needed
]

scrape_properties_from_urls(base_urls)

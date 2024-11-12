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
    "cf_clearance": "C_Tv3WxD_NhG19KuONuB6zJ.gdTZqXxnraMqFusA6ks-1731414234-1.2.1.1-woHk5zuGNHFtp2hyhuPxGW6aj3iPgaefu5qwSGbZHt07XBSQTRmBVWBpRNZBQbK6msFb03ye0IdDRINtHM8uDUdFi5T_VmdK3zQjHx4vQohZ2fS7mm0HiRlVX567ESKhFJa26EfpIbkeSHfJ1akt2bb7dbLw4g8dWGe8SDM6qIRNLJMt6ECFbF9YhNB64A6.H94zuafPqOM1kEbyCrKgQhJW4RZ8uB75r9PLfFBwo6fNaSPya30K9jszeORuKo00JmNFjdMjOa3J_lreVrgJfKmCJoqY4Eau5v0MTMD2vaqbA8QZtHs1eFoY5GDrRqZWFPb6Lfy8EGikB5Uj2OwmOJ1GkmJ1HC02tfeR0sua7px8lMJnoFOwSs9LSjwehzrASDOQViTNYHjaqYSXoy3tR_SyozrLTuWKEKM0rJKJkGcWubVdE4WmAAl8ZFPzA.4s",
    "XSRF-TOKEN": "eyJpdiI6Im9rejhlY2pVWlNCZU1rdEZaU0FRWlE9PSIsInZhbHVlIjoiSGNoSFNaQmdxcVBielViR0k4MHVDMGx3TFQrcFhVTHNrTDR4cmo5eWpkOGhNempWR3g4QlFJL2ttNHlVWU1YeTh4ay82NTJEb01MY0ovVXJHQ3NwMnFNNURnQ2JtdGhEZzlaTkhtVVBidkhkVVo1d04xNXYzTkc4dEJwZUJrQW0iLCJtYWMiOiIxMTZlOWI3OGQ2ZTY0ZTY1NGQwZTdjYWI2MjZiOTNjNGI2OWFhYzIyY2VkNDQ2YmE4MTU4M2E3MWE5ZmU3ODg3IiwidGFnIjoiIn0%3D"
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
    name = soup.find('h4', class_='content-title').text.strip()
    description = soup.find('p', itemprop='description').text.strip()
    address = soup.find('address').text.strip()
    
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
    "https://ghanapropertycentre.com/for-sale",
    # Add more URLs if needed
]

scrape_properties_from_urls(base_urls)

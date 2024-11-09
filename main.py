import requests
from bs4 import BeautifulSoup
import json
import math
import re
import pandas as pd
from urllib.parse import urlparse
import os

# Function to scrape data from a single URL
def scrape_data(base_url):
    response = requests.get(base_url)
    soup = BeautifulSoup(response.content, "html.parser")

    # Find the specific div with the class "a-search-subtitle search-results-nb"
    search_subtitle_div = soup.find("div", class_="a-search-subtitle search-results-nb")

    # Extract the number of listings from the span tag within this div
    if search_subtitle_div:
        number_of_listings = search_subtitle_div.find("span").text.strip()
        number_of_listings = int(number_of_listings.replace(" ", ""))  # Remove any spaces and convert to integer
    else:
        print("Could not find the number of listings.")
        number_of_listings = 1

    # Calculate the total number of pages (assuming 20 listings per page)
    listings_per_page = 20
    total_pages = math.ceil(number_of_listings / listings_per_page)

    # Initialize a list to store all property URLs
    all_property_urls = []

    # Iterate through each page and scrape property URLs
    for page in range(1, total_pages + 1):
        # Construct the URL for the current page
        page_url = f"{base_url}&page={page}"
        
        # Send a GET request to the current page
        page_response = requests.get(page_url)
        page_soup = BeautifulSoup(page_response.content, "html.parser")
        
        # Find all anchor tags with the specific class
        anchor_tags = page_soup.find_all("a", class_="a-card__image")
        
        # Extract the href attributes (the property URLs)
        property_urls = ["https://krisha.kz" + tag['href'] for tag in anchor_tags if 'href' in tag.attrs]
        
        # Add the property URLs to the list
        all_property_urls.extend(property_urls)
        
        print(f"Scraped {len(property_urls)} property URLs from page {page}")

    # Initialize a list to store the scraped data
    property_data = []

    # Iterate over each property URL to scrape detailed data
    for property_url in all_property_urls:
        property_response = requests.get(property_url)
        property_soup = BeautifulSoup(property_response.content, "html.parser")
        
        # Extract data from the <script> tag containing JSON data
        script_tag = property_soup.find("script", id="jsdata")
        if script_tag:
            script_text = script_tag.string.strip()
            
            # Remove the `window.data = ` part and extract the JSON object
            json_str = re.search(r"window\.data\s*=\s*({.*});", script_text)
            if json_str:
                json_data = json.loads(json_str.group(1))  # Extracted JSON data
                
                # Extract required details
                advert = json_data.get("advert", {})
                map_data = advert.get("map", {})
                address_data = advert.get("address", {})
                
                name = advert.get("title")
                address = f"{address_data.get('city')}, {address_data.get('street')} {address_data.get('house_num')}"
                price = advert.get("price")
                latitude = map_data.get("lat")
                longitude = map_data.get("lon")
                property_type = advert.get("categoryAlias")
                transaction_type = advert.get("sectionAlias")
                area = advert.get("square")
                characteristics = f"Rooms: {advert.get('rooms')}"
                
                # Scrape description from <meta name="description">
                meta_description_tag = property_soup.find("meta", attrs={"name": "description"})
                description = meta_description_tag["content"] if meta_description_tag else "No description available"

                details_div = property_soup.find("div", class_="offer__short-description")
                if details_div:
                    property_details = {}
            
                # Extract individual data points and store them as key-value pairs
                    for item in details_div.find_all("div", class_="offer__info-item"):
                        title = item.find("div", class_="offer__info-title").text.strip()
                        value = item.find("div", class_="offer__advert-short-info").text.strip()
                        property_details[title] = value
                
                    property_data.append({
                        "URL": property_url,
                        "Name": name,
                        "Address": address,
                        "Price": price,
                        "Description": description,
                        "Latitude": latitude,
                        "Longitude": longitude,
                        "Property Type": property_type,
                        "Transaction Type": transaction_type,
                        "Area": area,
                        "Characteristics": characteristics,
                        "Properties": property_details
                    })

                    print(f"Data extracted from {property_url}")
                
            else:
                print(f"Failed to extract JSON from script content on {property_url}")
        
        else:
            print(f"No 'jsdata' script tag found on {property_url}")

    # Convert the data into a DataFrame
    df = pd.DataFrame(property_data)
    
    # Ensure the artifacts directory exists
    os.makedirs("artifacts", exist_ok=True)
    
    # Save the DataFrame to an Excel file in the artifacts directory, named after the base URL
    parsed_url = urlparse(base_url)
    safe_url_name = parsed_url.netloc.replace(".", "_") + parsed_url.path.replace("/", "_")
    excel_filename = f"artifacts/{safe_url_name}.xlsx"
    df.to_excel(excel_filename, index=False)
    print(f"Data saved to {excel_filename}")

# List of base URLs to scrape
urls = [
    "https://krisha.kz/arenda/garazhi/",
    # Add more URLs here
]

# Scrape data for each URL in the list
for url in urls:
    scrape_data(url)

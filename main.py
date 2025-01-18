import requests
from bs4 import BeautifulSoup
import pandas as pd
import math
import os

# Input and output file paths
input_file = "brands_links.csv"
output_file = "artifacts/scraped_data.xlsx"

# Ensure the artifacts directory exists
os.makedirs(os.path.dirname(output_file), exist_ok=True)

# Read product links from the input CSV file
all_products_df = pd.read_csv(input_file)
product_urls = all_products_df["Brand Link"].tolist()

# Define headers for the requests
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Initialize the final data storage
all_data = []

for url in product_urls:
    print(f"Processing URL: {url}")
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        # Scrape total products and calculate total pages
        total_products_text = soup.select_one(".collection__products-count-total")
        if total_products_text:
            total_products = int(total_products_text.get_text(strip=True).split()[0])
            total_pages = math.ceil(total_products / 24)
            print(f"Total products: {total_products}, Total pages: {total_pages}")
        else:
            print("Could not find total products. Skipping this URL.")
            continue

        # Scrape product URLs from all pages
        product_links = []
        for page in range(1, total_pages + 1):
            page_url = f"{url}?page={page}"
            print(f"Scraping page: {page_url}")
            page_response = requests.get(page_url, headers=headers)
            if page_response.status_code == 200:
                page_soup = BeautifulSoup(page_response.text, "html.parser")
                product_anchors = page_soup.select("a.product-item__image-wrapper")
                for anchor in product_anchors:
                    product_link = anchor.get("href")
                    if product_link:
                        product_links.append(f"https://floorscenter.com{product_link}")
            else:
                print(f"Failed to retrieve page {page}. Status code: {page_response.status_code}")

        print(f"Found {len(product_links)} product links.")

        # Visit each product URL and extract details
        for product_link in product_links:
            print(f"Scraping product URL: {product_link}")
            product_response = requests.get(product_link, headers=headers)
            if product_response.status_code == 200:
                product_soup = BeautifulSoup(product_response.text, "html.parser")

                # Extract product description
                description_blocks = product_soup.find_all("div", class_="product-block-list__item--description")
                product_description = " ".join(
                    block.get_text(strip=True) for block in description_blocks if block.get_text(strip=True)
                )

                # Extract product specifications
                product_specs = {}
                spec_table = product_soup.find("div", class_="product-block-list__item--description")
                if spec_table:
                    rows = spec_table.find_all("tr")
                    for row in rows:
                        th = row.find("th")
                        td = row.find("td")
                        if th and td:
                            product_specs[th.get_text(strip=True)] = td.get_text(strip=True)

                # Extract product images
                image_urls = []
                img_tags = product_soup.select(".product-gallery__carousel-wrapper img")
                for img in img_tags:
                    src = img.get("src")
                    if src:
                        image_urls.append("https:" + src if src.startswith("//") else src)

                # Combine all scraped data
                product_data = {
                    "Product URL": product_link,
                    "Description": product_description,
                }
                product_data.update(product_specs)
                for i, img_url in enumerate(image_urls):
                    product_data[f"Image {i + 1}"] = img_url

                # Append data to the list
                all_data.append(product_data)
            else:
                print(f"Failed to retrieve product page {product_link}. Status code: {product_response.status_code}")

    else:
        print(f"Failed to retrieve collection page {url}. Status code: {response.status_code}")

# Save all data to an Excel file
if all_data:
    print(f"Saving data to {output_file}")
    df = pd.DataFrame(all_data)
    df.to_excel(output_file, index=False)
    print(f"Data saved successfully.")
else:
    print("No data to save.")

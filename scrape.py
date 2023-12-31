import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import requests
import pandas as pd
from urllib.parse import urlparse

async def fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

def get_page_urls(url):
    try:
        response = requests.get(url)
    except:
        exit()

    soup = BeautifulSoup(response.text, 'html.parser')

    sections = {
        "Israel-Gaza war":"",
        "War in Ukraine":"",
        "Tech":"",
        "Entertainment & Arts":"",
        "Health":""
    }

    page_links = soup.find_all('a', class_='nw-o-link')

    for page in page_links:
        heading = page.find('span')
        if heading:
            heading = heading.text.strip()
            if heading in sections:
                sections[heading] = url[:-5] + page['href']
            
    return sections

async def get_article_urls(main_url):
    try:
        async with aiohttp.ClientSession() as session:
            response = await session.get(main_url)
            html = await response.text()
    except:
        return []

    soup = BeautifulSoup(html, 'html.parser')

    article_links = soup.find_all('a', {'class': 'ssrcss-9haqql-LinkPostLink ej9ium92'})

    return [f"https://www.bbc.com{link['href']}" for link in article_links]

async def scrape_article(main_url):
    try:
        async with aiohttp.ClientSession() as session:
            response = await session.get(main_url)
            html = await response.text()
    except:
        return None

    soup = BeautifulSoup(html, 'html.parser')

    paragraphs = soup.find_all('p', class_='ssrcss-1q0x1qg-Paragraph e1jhz7w10')
    
    article_text = ' '.join(paragraph.text for paragraph in paragraphs)

    return article_text

def save_data(data, file_path):
    if len(data):
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(data)

async def scrape_and_save_article(url, output_folder):
    article_text = await scrape_article(url)
    if article_text is not None:
        save_data(article_text, os.path.join(output_folder, generate_filename(url)))

async def main():
    main_url = 'https://www.bbc.com/news'
    output_folder = 'scraped_data'
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    page_urls = get_page_urls(main_url)
    
    article_urls = dict(set())
    all_article_urls = set()

    tasks = []

    for topic, url in page_urls.items():
        topic_urls = set(await get_article_urls(url))
        unique_topic_urls = set()

        for current_url in topic_urls:
            if current_url not in all_article_urls:
                unique_topic_urls.add(current_url)
                all_article_urls.add(current_url)

        article_urls[topic] = unique_topic_urls

        tasks.extend([scrape_and_save_article(url, output_folder) for url in unique_topic_urls])

    await asyncio.gather(*tasks)

    csv_file = os.path.join(output_folder, 'article_data.csv')
    save_data_to_csv_pandas(article_urls, csv_file)

def generate_filename(url):
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.split('/')
    filename = path_parts[-1] if path_parts[-1] else "index"
    return f"{filename}.txt"

def save_data_to_csv_pandas(data, csv_file):
    data_flat = [(url, section, generate_filename(url)) for section, urls in data.items() for url in urls]
    df = pd.DataFrame(data_flat, columns=['URL', 'Section', 'File_Name'])
    df.to_csv(csv_file, index=False)

if __name__ == '__main__':
    asyncio.run(main())
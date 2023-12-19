import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import requests
import pandas as pd
from urllib.parse import urlparse
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, classification_report
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

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

def generate_filename(url):
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.split('/')
    filename = path_parts[-1] if path_parts[-1] else "index"
    return f"{filename}.txt"

def save_data_to_csv_pandas(data, csv_file):
    data_flat = [(url, section, generate_filename(url)) for section, urls in data.items() for url in urls]
    df = pd.DataFrame(data_flat, columns=['URL', 'Section', 'File_Name'])
    df.to_csv(csv_file, index=False)

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
    
    base_folder = "./scraped_data"

    df = pd.read_csv(csv_file)

    file_names = df['File_Name'].tolist()
    labels = df['Section'].tolist()

    data = []
    filtered_labels = []
    filtered_filenames = []

    for file_name, label in zip(file_names, labels):
        file_path = os.path.join(base_folder, file_name)

        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                text_content = file.read()
                data.append(text_content)
                filtered_labels.append(label)
                filtered_filenames.append(file_name)

    class_counts = pd.Series(filtered_labels).value_counts().to_dict()

    labels = filtered_labels

    file_data_df = pd.DataFrame({'File_Name': filtered_filenames, 'Text': data})

    df_train, df_test, y_train, y_test = train_test_split(file_data_df, labels, test_size=0.2, random_state=42)

    X_train = df_train.drop('File_Name', axis=1)['Text']
    X_test = df_test.drop('File_Name', axis=1)['Text']

    vectorizer = CountVectorizer(stop_words=list(ENGLISH_STOP_WORDS))
    X_train_vectorized = vectorizer.fit_transform(X_train)
    X_test_vectorized = vectorizer.transform(X_test)

    classifier = MultinomialNB()
    classifier.fit(X_train_vectorized, y_train)

    predictions = classifier.predict(X_test_vectorized)

    results_df = pd.DataFrame({
        'File_Name': df_test['File_Name'],
        'Actual_Label': y_test,
        'Predicted_Label': predictions
    })

    if not os.path.exists('results/'):
        os.mkdir('results')

    results_csv = 'results/classification_results.csv'
    results_df.to_csv(results_csv, index=False)

    accuracy = accuracy_score(y_test, predictions)
    print(f"\nAccuracy: {accuracy:.2f}")

    print("\nClassification Report:")
    print(classification_report(y_test, predictions))

if __name__ == '__main__':
    asyncio.run(main())

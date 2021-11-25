import json
import logging
import os
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.exceptions import ConnectionError, HTTPError, InvalidURL


BOOK_NUMBER = 1
BOOK_DESCRIPTIONS = []


def get_books_from_page(page: str):
    global BOOK_NUMBER
    global BOOK_DESCRIPTIONS
    url = urljoin('https://tululu.org/l55/', page)
    response = requests.get(url)
    response.raise_for_status()

    book_cards = get_book_cards(response.text)
    for book_card in book_cards:
        book_id = book_card.find('a')['href']
        book_url = urljoin('https://tululu.org/', book_id)

        book_id = book_id.replace('/', '').replace('b', '')
        try:
            book_description = get_book(book_url, book_id)
        except (ConnectionError, InvalidURL, HTTPError):
            logging.info(f'Book with id = {book_id} not found.\n')
            continue
        BOOK_DESCRIPTIONS.append(book_description)
        BOOK_NUMBER += 1


def get_book_cards(text):
    soup = BeautifulSoup(text, 'lxml')
    book_cards = soup.find_all('table', class_='d_book')
    return book_cards


def get_book(book_url, book_id):
    book_description = parse_book_page(book_url)
    book_path = save_book_text(book_id, book_description['title'])
    book_description.update({'book_path': book_path})

    img_src = save_book_cover(book_description['img_src'])
    book_description.update({'img_src': img_src})

    return book_description


def parse_book_page(book_url):
    response = requests.get(book_url)
    response.raise_for_status()
    check_for_redirect(response)

    soup = BeautifulSoup(response.text, 'lxml')

    title_author = soup.find(class_='ow_px_td').find('h1').text
    title, author = title_author.split('::')

    img_relative_address = soup.find(class_='bookimage').find('img')['src']
    img_url = urljoin(book_url, img_relative_address).strip()

    comment_tags = soup.find_all(class_='texts')
    comment_texts = [
        comment_tag.find(class_='black').text for comment_tag in comment_tags
    ]

    genres_tag = soup.find('span', class_='d_book').find_all('a')
    genres = [genre_tag.text for genre_tag in genres_tag]

    book_description = {
        'title': title.strip(),
        'author': author.strip(),
        'img_src': img_url,
        'book_path': '',
        'comments': comment_texts,
        'genres': genres,
    }

    return book_description


def save_book_description(description):
    with open('book_descriptions.json', 'w') as json_file:
        json.dump(description, json_file, ensure_ascii=False, indent=4)


def get_image_name(url):
    filepath = urlparse(unquote(url)).path
    _, filename = os.path.split(filepath)
    return filename


def download_image(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.content


def save_book_cover(url, folder='images'):
    os.makedirs(folder, exist_ok=True)

    filename = get_image_name(url)
    filepath = os.path.join(folder, filename)
    img = download_image(url)

    with open(filepath, 'wb') as file:
        file.write(img)
    return filepath


def download_txt(book_id):
    params = {
        'id': book_id,
    }
    url = 'https://tululu.org/txt.php'
    response = requests.get(url, params=params)
    response.raise_for_status()
    check_for_redirect(response)
    return response.text


def save_book_text(book_id, filename, folder='books'):
    os.makedirs(folder, exist_ok=True)
    book_text = download_txt(book_id)
    book_name = filename.replace(r'\\', '').replace('/', '')
    filename = f'{BOOK_NUMBER}.{book_name}.txt'
    filepath = os.path.join(folder, filename)
    with open(filepath, 'w') as file:
        file.write(book_text)
    return filepath


def check_for_redirect(response):
    if response.history:
        raise HTTPError


def main():
    logging.basicConfig(level=logging.INFO)
    for page in range(1, 5):
        get_books_from_page(str(page))
    save_book_description(BOOK_DESCRIPTIONS)


if __name__ == '__main__':
    main()

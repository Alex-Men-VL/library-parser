import logging
import os

import requests
from bs4 import BeautifulSoup


def check_for_redirect(response):
    if response.history:
        raise requests.exceptions.HTTPError


def get_book_title_and_author(book_id):
    url = f'https://tululu.org/b{book_id}'
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'lxml')

    title_with_author = soup.find(class_='ow_px_td').find('h1').text
    title, author = map(lambda x: x.strip(), title_with_author.split('::'))
    return title, author


def download_txt(text, book_id, filename, folder='books'):
    filename = filename.replace(r'\\', '').replace('/', '')
    name, extension = os.path.splitext(filename)
    if extension != '.txt':
        filename = f'{book_id}. {filename}.txt'
    filepath = os.path.join(folder, filename)
    with open(filepath, 'w') as file:
        file.write(text)
    return filepath


def get_books(books_amount=10):
    for book_id in range(1, books_amount + 1):
        params = {
            'id': book_id,
        }
        url = 'https://tululu.org/txt.php'
        response = requests.get(url, params=params)
        response.raise_for_status()
        try:
            check_for_redirect(response)
        except requests.exceptions.HTTPError:
            logging.info(f'Книга с id = {book_id} не найдена.')
            continue

        title, author = get_book_title_and_author(book_id)
        download_txt(response.text, book_id, title)


def main():
    os.makedirs('books', exist_ok=True)
    get_books()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()

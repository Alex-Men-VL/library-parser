import argparse
import logging
import os
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.exceptions import ConnectionError, HTTPError, InvalidURL


def parse_arguments():
    parser = argparse.ArgumentParser(description='Downloading books from the '
                                                 'website tululu.org')
    parser.add_argument('start_id', nargs='?',
                        help='Enter the number of the first page',
                        default=1,
                        type=int)
    parser.add_argument('end_id', nargs='?',
                        help='Enter the number of the last page',
                        default=10,
                        type=int)
    return parser.parse_args()


def parse_book_page(book_id):
    url = f'https://tululu.org/b{book_id}/'
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'lxml')

    title_author = soup.find(class_='ow_px_td').find('h1').text
    title, author = title_author.split('::')

    img_relative_address = soup.find(class_='bookimage').find('img')['src']
    img_url = urljoin(url, img_relative_address).strip()

    comment_tags = soup.find_all(class_='texts')
    comment_texts = [
        comment_tag.find(class_='black').text for comment_tag in comment_tags
    ]

    genres_tag = soup.find('span', class_='d_book').find_all('a')
    genres = [genre_tag.text for genre_tag in genres_tag]

    book_description = {
        'title': title.strip(),
        'author': author.strip(),
        'img_url': img_url,
        'comments': comment_texts,
        'genres': genres,
    }

    return book_description


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


def save_book_text(text, book_id, filename, folder='books'):
    os.makedirs(folder, exist_ok=True)
    book_name = filename.replace(r'\\', '').replace('/', '')
    filename = f'{book_id}. {book_name}.txt'
    filepath = os.path.join(folder, filename)
    with open(filepath, 'w') as file:
        file.write(text)
    return filepath


def check_for_redirect(response):
    if response.history:
        raise HTTPError


def get_books(start_id, end_id):
    for book_id in range(start_id, end_id + 1):
        params = {
            'id': book_id,
        }
        url = 'https://tululu.org/txt.php'
        response = requests.get(url, params=params)
        try:
            response.raise_for_status()
            check_for_redirect(response)
        except (ConnectionError, InvalidURL, HTTPError):
            logging.info(f'Book with id = {book_id} not found.\n')
            continue

        book_description = parse_book_page(book_id)

        print('Title:', book_description['title'])
        print('Author:', book_description['author'])
        print()

        save_book_text(response.text, book_id, book_description['title'])
        save_book_cover(book_description['img_url'])


def main():
    logging.basicConfig(level=logging.INFO)

    args = parse_arguments()
    start_id = args.start_id
    end_id = args.end_id
    if start_id > end_id:
        logging.error(
            'The number of start page cannot be greater than the last one.'
        )
        return
    get_books(start_id, end_id)


if __name__ == '__main__':
    main()

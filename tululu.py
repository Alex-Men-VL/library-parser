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
    comment_texts = []
    for comment_tag in comment_tags:
        comment_text_tag = comment_tag.find(class_='black')
        comment_text = comment_text_tag.text
        comment_texts.append(comment_text)

    genres_tag = soup.find('span', class_='d_book').find_all('a')
    genres = []
    for genre_tag in genres_tag:
        genre = genre_tag.text
        genres.append(genre)

    return title.strip(), author.strip(), img_url, comment_texts, genres


def download_txt(text, book_id, filename, folder='books'):
    os.makedirs(folder, exist_ok=True)
    filename = filename.replace(r'\\', '').replace('/', '')
    name, extension = os.path.splitext(filename)
    if not extension:
        filename = f'{book_id}. {filename}.txt'
    else:
        filename = f'{book_id}. {filename}'
    filepath = os.path.join(folder, filename)
    with open(filepath, 'w') as file:
        file.write(text)
    return filepath


def find_filename_in_url(url):
    filepath = urlparse(unquote(url)).path
    _, filename = os.path.split(filepath)
    return filename


def get_img_from_url(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.content


def download_image(url, folder='images'):
    os.makedirs(folder, exist_ok=True)

    filename = find_filename_in_url(url)
    filepath = os.path.join(folder, filename)
    img = get_img_from_url(url)

    with open(filepath, 'wb') as file:
        file.write(img)


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

        title, author, img_url, comments, genres = parse_book_page(book_id)

        print('Title:', title)
        print('Author:', author)
        print()

        download_txt(response.text, book_id, title)
        download_image(img_url)


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

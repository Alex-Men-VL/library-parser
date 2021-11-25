import argparse
import json
import logging
import os
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.exceptions import ConnectionError, HTTPError, InvalidURL


BOOK_NUMBER = 1
BOOK_DESCRIPTIONS = []


def parse_arguments():
    parser = argparse.ArgumentParser(description='Downloading books from the '
                                                 'website tululu.org')
    parser.add_argument('--start_page',
                        help='Enter the number of the first page',
                        default=1,
                        type=int)
    parser.add_argument('--end_page',
                        help='Enter the number of the last page',
                        default=702,
                        type=int)
    parser.add_argument('--dest_folder',
                        help='Enter the path to the directory with the parsing '
                             'results: pictures, books, JSON',
                        default='',
                        type=str)
    parser.add_argument('--skip_imgs',
                        help='Do not download images',
                        default=False,
                        type=bool)
    parser.add_argument('--skip_txt',
                        help='Do not download books',
                        default=False,
                        type=bool)
    parser.add_argument('--json_path',
                        help='Specify your path to *.json file with results',
                        default='book_descriptions.json',
                        type=str)
    return parser.parse_args()


def get_books_from_page(page, dest_folder, skip_imgs, skip_txt):
    global BOOK_NUMBER
    global BOOK_DESCRIPTIONS
    url = urljoin('https://tululu.org/l55/', page)
    response = requests.get(url)
    response.raise_for_status()

    book_cards = get_book_cards(response.text)
    for book_card in book_cards:
        book_id = book_card['href']
        book_url = urljoin('https://tululu.org/', book_id)

        book_id = book_id.replace('/', '').replace('b', '')
        try:
            book_description = get_book(book_url,
                                        book_id,
                                        dest_folder,
                                        skip_imgs,
                                        skip_txt)
        except (ConnectionError, InvalidURL, HTTPError):
            logging.info(f'Book with id = {book_id} not found.\n')
            continue
        BOOK_DESCRIPTIONS.append(book_description)
        BOOK_NUMBER += 1


def get_book_cards(text):
    soup = BeautifulSoup(text, 'lxml')
    selector = '.ow_px_td .d_book .bookimage a'
    book_cards = soup.select(selector)
    return book_cards


def get_book(book_url, book_id, dest_folder, skip_imgs, skip_txt):
    book_description = parse_book_page(book_url)
    if skip_txt:
        book_description.update({'book_path': 'Not downloaded'})
    else:
        book_path = save_book_text(book_id,
                                   book_description['title'],
                                   dest_folder)
        book_description.update({'book_path': book_path})

    if skip_imgs:
        book_description.update({'img_src': 'Not downloaded'})
    else:
        img_src = save_book_cover(book_description['img_src'], dest_folder)
        book_description.update({'img_src': img_src})

    return book_description


def parse_book_page(book_url):
    response = requests.get(book_url)
    response.raise_for_status()
    check_for_redirect(response)

    soup = BeautifulSoup(response.text, 'lxml')
    selectors = {
        'title': 'tr .ow_px_td h1',
        'img': 'tr .ow_px_td .d_book .bookimage img',
        'comments': 'tr .ow_px_td .texts .black',
        'genres': 'tr .ow_px_td span.d_book a'
    }
    title_author = soup.select_one(selectors['title']).text
    title, author = title_author.split('::')

    img_relative_address = soup.select_one(selectors['img'])['src']
    img_url = urljoin(book_url, img_relative_address).strip()

    comment_tags = soup.select(selectors['comments'])
    comment_texts = [comment_tag.text for comment_tag in comment_tags]

    genres_tag = soup.select(selectors['genres'])
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


def save_book_description(description, dest_folder, json_path):
    os.makedirs(dest_folder, exist_ok=True)
    folder = os.path.join(dest_folder, json_path)
    with open(folder, 'w') as json_file:
        json.dump(description, json_file, ensure_ascii=False, indent=4)


def get_image_name(url):
    filepath = urlparse(unquote(url)).path
    _, filename = os.path.split(filepath)
    return filename


def download_image(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.content


def save_book_cover(url, dest_folder, folder_name='images'):
    folder = os.path.join(dest_folder, folder_name)
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


def save_book_text(book_id, filename, dest_folder, folder_name='books'):
    folder = os.path.join(dest_folder, folder_name)
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

    args = parse_arguments()
    start_page = args.start_page
    end_page = args.end_page
    dest_folder = args.dest_folder
    skip_imgs = args.skip_imgs
    skip_txt = args.skip_txt
    json_path = args.json_path

    if start_page >= end_page:
        logging.error(
            'The number of start page cannot be greater than the last one.'
        )
        return

    if os.path.splitext(json_path)[-1] != '.json':
        logging.error(
            'Enter the correct name of the JSON file.'
        )
        return

    for page in range(start_page, end_page):
        get_books_from_page(str(page), dest_folder, skip_imgs, skip_txt)
    save_book_description(BOOK_DESCRIPTIONS, dest_folder, json_path)


if __name__ == '__main__':
    main()
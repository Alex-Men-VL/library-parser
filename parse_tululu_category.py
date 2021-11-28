import argparse
import json
import logging
import os
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.exceptions import HTTPError, RequestException


def parse_arguments():
    parser = argparse.ArgumentParser(description='Downloading books from the '
                                                 'website tululu.org')
    parser.add_argument('--start_page',
                        help='Enter the number of the first page',
                        default=1,
                        type=int)
    parser.add_argument('--end_page',
                        help='Enter the number of the last page',
                        type=int)
    parser.add_argument('--dest_folder',
                        help='Enter the path to the directory with the '
                             'parsing results: pictures, books, JSON',
                        default='',
                        type=str)
    parser.add_argument('--skip_imgs',
                        help='Do not download images',
                        action='store_true')
    parser.add_argument('--skip_txt',
                        help='Do not download books',
                        action='store_true')
    parser.add_argument('--json_path',
                        help='Specify your path to *.json file with results',
                        default='book_descriptions.json',
                        type=str)
    return parser.parse_args()


def get_books(start_page, end_page, skip_txt,
              skip_imgs, dest_folder, json_path):
    book_descriptions = []
    for page in range(start_page, end_page + 1):
        try:
            book_descriptions_per_page = get_books_from_page(
                str(page), skip_txt,
                skip_imgs, dest_folder
            )
        except RequestException:
            logging.info(f'Books from page {page} have not been downloaded')
        book_descriptions += book_descriptions_per_page

    save_book_description(book_descriptions, dest_folder, json_path)


def get_last_page_number():
    url = 'https://tululu.org/l55/'
    response = requests.get(url)
    response.raise_for_status()
    check_for_redirect(response)

    soup = BeautifulSoup(response.text, 'lxml')
    selector = 'tr .ow_px_td .center a:last-child'
    last_page_number = soup.select(selector)[0].text
    return int(last_page_number)


def get_books_from_page(page, skip_txt, skip_imgs, dest_folder):
    url = urljoin('https://tululu.org/l55/', page)
    response = requests.get(url)
    response.raise_for_status()
    check_for_redirect(response)

    book_cards = get_book_cards(response.text)
    book_descriptions = []
    for book_card in book_cards:
        book_id = book_card['href']
        book_url = urljoin('https://tululu.org/', book_id)

        book_id = book_id.replace('/', '').replace('b', '')
        try:
            book_description = get_book(book_url, book_id, skip_txt,
                                        skip_imgs, dest_folder)
        except RequestException:
            logging.info(f'Book with id = {book_id} not downloaded.\n')
            continue
        book_descriptions.append(book_description)
    return book_descriptions


def get_book_cards(text):
    soup = BeautifulSoup(text, 'lxml')
    selector = '.ow_px_td .d_book .bookimage a'
    book_cards = soup.select(selector)
    return book_cards


def get_book(book_url, book_id, skip_txt, skip_imgs, dest_folder):
    book_description, img_url = parse_book_page(book_url)
    if not skip_txt:
        book_path = save_book_text(book_id, book_description['title'],
                                   dest_folder)
        book_description.update({'book_path': book_path})

    if not skip_imgs:
        img_src = save_book_cover(img_url, dest_folder)
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
        'comments': comment_texts,
        'genres': genres,
    }

    return book_description, img_url


def save_book_description(description, dest_folder, json_path):
    try:
        os.makedirs(dest_folder, exist_ok=True)
    except FileNotFoundError:
        pass
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
    filename = f'{book_id}.{book_name}.txt'
    filepath = os.path.join(folder, filename)

    with open(filepath, 'w') as file:
        file.write(book_text)
    return filepath


def check_for_redirect(response):
    if response.history:
        raise HTTPError


def main():
    logging.basicConfig(level=logging.INFO)
    try:
        last_page_number = get_last_page_number()
    except RequestException:
        logging.info("Couldn't access the site")
        return

    args = parse_arguments()
    if not args.end_page:
        args.end_page = last_page_number
    elif args.end_page > last_page_number:
        logging.error(
            f'The maximum possible number of the last page: {last_page_number}'
        )
        return
    elif args.end_page < args.start_page:
        logging.error(
            'The number of start page cannot be greater than the last one.'
        )
        return

    if os.path.splitext(args.json_path)[-1] != '.json':
        logging.error(
            'Enter the correct name of the JSON file.'
        )
        return

    get_books(args.start_page, args.end_page, args.skip_txt,
              args.skip_imgs, args.dest_folder, args.json_path)


if __name__ == '__main__':
    main()

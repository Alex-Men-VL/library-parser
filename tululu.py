import logging
import os
from urllib.parse import urljoin, urlparse, unquote

import requests
from bs4 import BeautifulSoup


def check_for_redirect(response):
    if response.history:
        raise requests.exceptions.HTTPError


def get_book_features(book_id):
    url = f'https://tululu.org/b{book_id}'
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'lxml')

    title_with_author = soup.find(class_='ow_px_td').find('h1').text
    title, author = map(lambda x: x.strip(), title_with_author.split('::'))

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

    return title, author, img_url, comment_texts, genres


def download_txt(text, book_id, filename, folder='books'):
    os.makedirs(folder, exist_ok=True)
    filename = filename.replace(r'\\', '').replace('/', '')
    name, extension = os.path.splitext(filename)
    if extension != '.txt':
        filename = f'{book_id}. {filename}.txt'
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

        title, author, img_url, comments, genres = get_book_features(book_id)
        print('Заголовок:', title)
        # for comment in comments:
        #     print(comment)
        print(genres)
        print()

        download_txt(response.text, book_id, title)
        download_image(img_url)


def main():
    get_books()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()

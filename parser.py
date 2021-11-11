import os

import requests


def download_books(books_amount=10):
    for book_id in range(1, books_amount + 1):
        params = {
            'id': book_id,
        }
        url = 'https://tululu.org/txt.php'
        response = requests.get(url, params=params)
        response.raise_for_status()

        filename = f'id{book_id}.txt'
        with open(os.path.join('books', filename), 'w') as file:
            file.write(response.text)


def main():
    os.makedirs('books', exist_ok=True)
    download_books()


if __name__ == '__main__':
    main()

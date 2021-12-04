import json
import os

from more_itertools import chunked

from jinja2 import Environment, FileSystemLoader, select_autoescape
from livereload import Server


def on_reload():
    env = Environment(
        loader=FileSystemLoader('.'),
        autoescape=select_autoescape(['html', 'xml'])
    )

    template = env.get_template('template.html')

    with open('book_descriptions.json', 'r') as json_file:
        books_json = json_file.read()

    books_count_per_line = 2
    books = chunked(json.loads(books_json), books_count_per_line)

    book_column_count = 10
    books_per_pages = list(chunked(books, book_column_count))

    os.makedirs('pages', exist_ok=True)
    for page_number, books_per_page in enumerate(books_per_pages, start=1):
        rendered_page = template.render(books=books_per_page,
                                        current_page_number=page_number,
                                        pages_number=books_per_pages.__len__())

        html_file_name = f'index{page_number}.html'
        html_path = os.path.join('pages', html_file_name)
        with open(html_path, 'w', encoding="utf8") as file:
            file.write(rendered_page)


def main():
    on_reload()
    server = Server()
    server.watch('template.html', on_reload)

    server.serve(default_filename='pages/index1.html', root='.')


if __name__ == '__main__':
    main()

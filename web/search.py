from wsgiref.simple_server import make_server
import common
import database
from urllib.parse import parse_qs
import json

KEYS = ('aids', 'title', 'opts')


def app(environ, start_response):
    url = environ['PATH_INFO']
    if url == '/':
        start_response('200 OK', [('Content-Type', 'text/html')])
        htm = common.read_all('index.html')
        return [htm.encode()]
    elif url == '/search' and environ['REQUEST_METHOD'] == 'POST':
        start_response('200 OK', [('Content-Type', 'application/json')])
        size = int(environ.get('CONTENT_LENGTH', 0))
        body: bytes = environ['wsgi.input'].read(size)
        data = parse_qs(body.decode())
        del body
        key = data['key']
        if key:
            key = key[0]
            if key:
                db = database.SQLite(db_path)
                data = db.search(key)
                for i in range(len(data)):
                    data[i] = dict(zip(KEYS, data[i]))
                data = json.dumps(data)
                return [data.encode()]
        return [b'{}']
    start_response('404 Not Found', [])
    return [b'']


db_path = common.get_path('database.db')

if __name__ == '__main__':
    with make_server('0.0.0.0', 8080, app) as httpd:
        print("Serving HTTP on port 8000...")
        httpd.serve_forever()

import os
import re
import json
import base64
import logging
import requests
import time
import random
import database
import common
import threading
from pyquery import PyQuery
from typing import Union

mode_list = [
    {
        'id': '5f71e934bcdbf3a8c3ba51d5',
        'name': '英雄篇',
        'mode': 1,
        'time': 600
    },
    {
        'id': '5f71e934bcdbf3a8c3ba51d6',
        'name': '复兴篇',
        'mode': 1,
        'time': 600
    },
    {
        'id': '5f71e934bcdbf3a8c3ba51d7',
        'name': '创新篇',
        'mode': 1,
        'time': 600
    },
    {
        'id': '5f71e934bcdbf3a8c3ba51d8',
        'name': '信念篇',
        'mode': 1,
        'time': 180
    },
    {
        'id': '5f71e934bcdbf3a8c3ba51d9',
        'name': '限时赛',
        'mode': 2,
        'time': 600
    },
    {
        'id': '5f71e934bcdbf3a8c3ba51da',
        'name': '抢十赛',
        'mode': 3,
        'time': 600
    }
]
pattern_id = re.compile(r'^[\da-z]{24}$')
pattern_no_display = re.compile(r'(?:^|[\t ]*)display:\s*none(?:;|[\t ]*|$)')
pattern_title = re.compile(r'\s+')
logger = logging.getLogger(__name__)
activity_id = '5f71e934bcdbf3a8c3ba5061'


def get_uid(token: str) -> [str, None]:
    if token:
        arr = token.split('.')
        if len(arr) == 3:
            data = arr[1]
            length = len(data)
            n = 4 - length % 4
            if n:
                data += '=' * n
            data = base64.b64decode(data).decode()
            try:
                data = json.loads(data)
                return data['uid']
            except json.decoder.JSONDecodeError:
                logger.error('json parse error')
                raise
            except KeyError:
                logger.error(data)
                logger.error('not found `uid`')
                raise


def remove_no_display(pq: PyQuery):
    style = pq.attr('style')
    if style and pattern_no_display.search(style):
        pq.remove()
        return
    children = pq.children()
    for child in children:
        remove_no_display(PyQuery(child))


def get_text_from_html(html: str) -> str:
    pq = PyQuery(html)
    remove_no_display(pq)
    return pq.text(block_symbol='').strip()


class User:

    def set_uid(self, uid: str):
        self.uid = uid
        self.token_file = os.path.join(self.token_dir, uid + '.txt')

    def set_token(self, token: str, save: bool = False):
        self.token = token
        self.session.headers.update({
            'Authorization': 'Bearer %s' % token
        })
        if save:
            with open(self.token_file, 'w') as fp:
                fp.write(token)

    def get_local_token(self) -> [str, None]:
        logger.debug(self.token_file)
        if os.path.exists(self.token_dir):
            file = self.token_file
            if os.path.isfile(file):
                return common.read_all(file)
        else:
            os.makedirs(self.token_dir)

    def get_remote_token(self) -> str:
        logger.debug('uid %s', self.uid)
        data = self.session.request('GET', 'https://ssxx.univs.cn/cgi-bin/authorize/token/', {
            'uid': self.uid
        }).json()
        token = data['token']
        self.token_expired = False
        return token

    def on_request_error(self, code: int, *args):
        if code == 1002:
            logger.debug('token has expired, getting new remote token')
            if self.token_expired:
                raise Exception('got token has expired')
            self.token_expired = True
            self.set_token(self.get_remote_token(), True)
            return self.request(*args)
        return False

    def request(self, method, url, params=None, data=None) -> dict:
        data: dict = self.session.request(method, url, params, json=data).json()
        code = data['code']
        if data['status_code'] != 200 or code != 0:
            if 'message' in data:
                logger.warning('Message: %s', data['message'])
            result = self.on_request_error(code, method, url, params, data)
            if isinstance(result, dict):
                return result
            if not result:
                logger.error(json.dumps(data))
                raise Exception('data error')
        return data

    def request_data(self, *args) -> dict:
        data = self.request(*args)
        return data['data']

    def parse_mixed(self, mixed: str, remote: bool = False, maybe_file: bool = True):
        if pattern_id.fullmatch(mixed):
            self.set_uid(mixed)
            token = None
            save = False
            if not remote:
                token = self.get_local_token()
            if not token:
                save = True
                token = self.get_remote_token()
            self.set_token(token, save)
        elif maybe_file and os.path.isfile(mixed):
            self.parse_mixed(common.read_all(mixed), remote, False)
        else:
            self.set_uid(get_uid(mixed))
            self.set_token(self.get_remote_token() if remote else mixed, True)

    def api_info(self):
        data = self.request_data('GET', 'https://ssxx.univs.cn/cgi-bin/race/grade/', {
            'activity_id': activity_id
        })
        return data

    def info(self):
        data = self.api_info()
        print('Hi, %s' % data['name'])
        print('Your score: %d' % data['integral'])

    def mode(self, mid: Union[str, int] = 0, sleep: float = 0.5):
        return Mode(self, mid, sleep)

    def modes(self, mixed: list[Union[str, int]], count: int = 1000, sleep: float = 0.5):
        threads = []
        for m in mixed:
            mode = self.mode(m, sleep)
            t = threading.Thread(target=mode.starts, args=(count, threads), daemon=True)
            threads.append(t)
            t.start()
        try:
            while True:
                time.sleep(0.05)
                if len(threads) == 0:
                    break
        except KeyboardInterrupt:
            pass

    def __init__(self, mixed: str = common.get_path('token.txt'), db: Union[database.DB, None] = None,
                 token_dir: str = common.get_path('tokens'), remote: bool = False):
        """
        :param mixed: uid, file or file path
        """
        self.db = db
        self.uid: str = ''
        self.token: str = ''
        self.token_dir: str = token_dir
        self.token_file: str = ''
        self.token_expired = False
        self.session = requests.session()
        self.parse_mixed(mixed, remote)


class Mode:

    def params(self, params: Union[dict, None] = None) -> dict:
        default = {
            'activity_id': activity_id,
            'mode_id': self.mid,
            'way': 1,
            't': int(time.time())
        }
        if params:
            default.update(params)
        return default

    def api_begin(self):
        return self.user.request(
            'GET',
            'https://ssxx.univs.cn/cgi-bin/race/beginning/',
            self.params()
        )

    def api_question(self, qid):
        return self.user.request_data(
            'GET',
            'https://ssxx.univs.cn/cgi-bin/race/question/',
            self.params({
                'question_id': qid
            })
        )

    def api_answer(self, qid, aids):
        return self.user.request_data(
            'POST',
            'https://ssxx.univs.cn/cgi-bin/race/answer/',
            None,
            self.params({
                'question_id': qid,
                'answer': aids
            })
        )

    def api_finish(self, race_code):
        return self.user.request_data(
            'POST',
            'https://ssxx.univs.cn/cgi-bin/race/finish/',
            None,
            self.params({
                'race_code': race_code
            })
        )

    def api_save_code(self):
        return self.user.request(
            'POST',
            'https://ssxx.univs.cn/cgi-bin/save/verification/code/',
            None,
            self.params({
                'code': 'HD1bhUGI4d/FhRfIX4m972tZ0g3jRHIwH23ajyre9m1Jxyw4CQ1bMKeIG5T/voFOsKLmnazWkPe6yBbr'
                        '+juVcMkPwqyafu4JCDePPsVEbVSjLt8OsiMgjloG1fPKANShQCHAX6BwpK33pEe8jSx55l3Ruz/HfcSjDLEHCATdKs4='
            })
        )

    def api_check_code(self):
        return self.user.request(
            'POST',
            'https://ssxx.univs.cn/cgi-bin/check/verification/code/',
            None,
            self.params({
                'code': 'E5ZKeoD8xezW4TVEn20JVHPFVJkBIfPg+zvMGW+kx1s29cUNFfNka1'
                        '+1Fr7lUWsyUQhjiZXHDcUhbOYJLK4rS5MflFUvwSwd1B+1kul06t1z9x0mfxQZYggbnrJe3PKEk4etwG/rm3s3FFJd'
                        '/EbFSdanfslt41aULzJzSIJ/HWI='
            })
        )

    def start(self) -> int:
        data = self.api_begin()
        if not ('race_code' in data):
            logger.warning(data)
            raise Exception('not found `race_code`')
        race_code = data['race_code']
        questions = data['question_ids']

        for i in range(len(questions)):
            qid = questions[i]
            question = self.api_question(qid)
            _title = question['title'] = pattern_title.sub('', get_text_from_html(question['title']))
            options: list[dict] = question['options']
            _options = []
            for option in options:
                title = get_text_from_html(option['title'])
                _options.append(title)
                option['title'] = title
            _options.sort()
            aids = []
            _aids = None
            has_db = self.user.db is not None
            if has_db:
                _aids = self.user.db.get(_title, _options)
            new = _aids is None
            if new:
                if question['category'] != 2:
                    option = options[random.randint(0, len(options) - 1)]
                    aids.append(option['id'])
                else:
                    for option in options:
                        aids.append(option['id'])
            else:
                for j in range(len(_aids)):
                    _aids[j] = _options[_aids[j]]
                for option in options:
                    if option['title'] in _aids:
                        aids.append(option['id'])
            time.sleep(self.sleep)
            data = self.api_answer(qid, aids)
            if new and has_db:
                aids = data['correct_ids']
                _aids = []
                for option in options:
                    if option['id'] in aids:
                        _aids.append(_options.index(option['title']))
                self.user.db.insert(_aids, _title, _options)
            if data['finished']:
                break

        self.api_save_code()
        data = self.api_check_code()
        if not data['status']:
            logger.error('api-data: %s', data)
            raise Exception('check code error')
        data = self.api_finish(race_code)
        return data['integral']

    def starts(self, count: int, threads: list):
        try:
            a = 0
            for i in range(count):
                score = self.start()
                a += score
                print('mid: %s, count: %d, score: %d, all: %d' % (self.mid, i, score, a))
        finally:
            threads.remove(threading.current_thread())

    def __init__(self, user: User, mixed: Union[str, int] = 0, sleep: float = 0.5):
        """
        :param mixed: mode_id or mode_list index
        """
        self.user = user
        self.sleep = sleep
        self.mid = mixed if isinstance(mixed, str) and pattern_id.fullmatch(mixed) else mode_list[int(mixed)]['id']

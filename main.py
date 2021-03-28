#!/usr/bin/env python3

import os
import common
import core
import logging
import database
import json
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--user',
                        help='uid, token or file path. default read token.txt')
    parser.add_argument('-m', '--mode',
                        help='mode, default 0')
    parser.add_argument('-s', '--sleep',
                        help='delay ms, default 500, e.g. 500 500~1000')
    parser.add_argument('-n', '--count', type=int,
                        help='count, default 1')
    parser.add_argument('--db', help='database file path, default database.db')
    parser.add_argument('--debug', action=argparse.BooleanOptionalAction,
                        help='debug')

    file = common.get_path('config.json')
    config = {
        'db': common.get_path('database.db'),
        'debug': False,
        'sleep': 500,
        'count': 1,
        'mode': 0
    }
    if os.path.isfile(file):
        config.update(json.loads(common.read_all(file)))
    config = parser.parse_args(namespace=argparse.Namespace(**config))
    logging.basicConfig(
        level=logging.DEBUG if config.debug else logging.WARNING,
        format='%(filename)s:%(lineno)d:%(funcName)s:%(levelname)s: %(message)s'
    )

    if not config.user:
        file = common.get_path('token.txt')
        if os.path.isfile(file):
            print('no user')
            exit(1)
    db = database.SQLite(config.db)
    user = core.User(config.user, db)
    user.info()

    modes = config.mode
    if not isinstance(modes, list):
        if isinstance(modes, int):
            modes = [modes]
        else:
            modes = modes.split(',')
    user.modes(modes, config.count, config.sleep)

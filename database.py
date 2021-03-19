import sqlite3

import json
import common


def json_dump(obj: any):
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))


class DB:
    def inserts(self, aids: str, title: str, options: str): ...

    def gets(self, title: str, options: str) -> [list, None]: ...

    def insert(self, aids: list, title: str, options: list):
        aids = json_dump(aids)
        options = json_dump(options)
        self.inserts(aids, title, options)

    def get(self, title: str, options: list) -> [list, None]:
        options = json_dump(options)
        return self.gets(title, options)


class SQLite(DB):

    def inserts(self, aids: str, title: str, options: str):
        cursor = self.con.cursor()
        cursor.execute(
            'INSERT INTO `question` (`aids`, `title`, `opts`) VALUES (?, ?, ?)',
            (
                aids,
                title,
                options
            )
        )
        cursor.close()
        self.con.commit()

    def gets(self, title: str, options: str) -> [list, None]:
        cursor = self.con.cursor()
        cursor.execute(
            'SELECT `aids` FROM `question` WHERE `title` = ? AND `opts` = ?',
            (
                title,
                options
            )
        )
        data = cursor.fetchone()
        cursor.close()
        if data is None:
            return None
        aids, = data
        return json.loads(aids)

    def __init__(self, file: str = common.get_path('database.db')):
        self.con = sqlite3.connect(file, check_same_thread=False)
        cursor = self.con.cursor()
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name = 'question'")
        count, = cursor.fetchone()
        if count == 0:
            cursor.execute("""
CREATE TABLE `question`
(
    `aids`  TEXT NOT NULL,
    `title` TEXT NOT NULL,
    `opts`  TEXT NOT NULL,
    PRIMARY KEY (title, opts)
);
""")
            self.con.commit()
        cursor.close()

    def __del__(self):
        self.con.close()

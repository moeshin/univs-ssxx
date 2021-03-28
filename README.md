且用且珍惜，别去冲榜

[Get UID](https://api.moeshin.com/univs_ssxx_uid/)

### Database

Download [database.db](https://github.com/moeshin/univs-ssxx/releases/download/database/database.db)

### Requirements

```shell
pip3 -r requirements.txt
```

### Usage

```text
python3 main.py [options]

options:
-u, --user              uid, token or file path.
                        default read token.txt
-s, --sleep             delay ms, default 500, e.g.
                        500
                        500-1000
-m, --mode              mode, default 0
-n, --count             count, default 1
--db                    database file path, default database.db
--debug, --no-debug     debug
```

### Question Bank

```shell
python3 search.py
```

Then open http://127.0.0.1:8080/

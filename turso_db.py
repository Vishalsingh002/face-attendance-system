import json
import logging
import requests
from config import Config

logger = logging.getLogger(__name__)

class TursoRow(dict):
    """
    Emulates sqlite3.Row allowing both column name access (row['name'])
    and zero-based integer index access (row[0]).
    """
    def __init__(self, cols, values):
        super().__init__(zip(cols, values))
        self._values = list(values)
        self._cols = list(cols)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)

    def keys(self):
        return self._cols

class TursoCursor:
    def __init__(self, connection):
        self.connection = connection
        self.description = None
        self._rows = []
        self._row_index = 0
        self.lastrowid = None
        self.rowcount = 0

    def execute(self, sql, params=()):
        # Normalize sql - remove trailing semicolons for consistency
        clean_sql = sql.strip()
        
        # Build statement for Turso Pipeline API
        stmt_args = []
        for p in params:
            if p is None:
                stmt_args.append({"type": "null"})
            elif isinstance(p, int):
                stmt_args.append({"type": "integer", "value": str(p)})
            elif isinstance(p, float):
                stmt_args.append({"type": "float", "value": p})
            elif isinstance(p, bytes):
                import base64
                stmt_args.append({"type": "blob", "base64": base64.b64encode(p).decode('ascii')})
            else:
                stmt_args.append({"type": "text", "value": str(p)})

        payload = {
            "requests": [
                {
                    "type": "execute",
                    "stmt": {
                        "sql": clean_sql,
                        "args": stmt_args
                    }
                },
                {"type": "close"}
            ]
        }

        resp = requests.post(
            f"{self.connection.http_url}/v2/pipeline",
            headers={
                "Authorization": f"Bearer {self.connection.auth_token}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=10
        )

        if not resp.ok:
            raise RuntimeError(f"Turso API Error ({resp.status_code}): {resp.text}")

        data = resp.json()
        results = data.get("results", [])
        if not results:
            self._rows = []
            return self

        first = results[0]
        if first.get("type") == "error":
            err_msg = first.get("error", {}).get("message", "Unknown Turso Error")
            raise RuntimeError(f"Turso SQL Error: {err_msg}")

        res = first.get("response", {}).get("result", {})
        cols = [c.get("name") for c in res.get("cols", [])]
        self.description = [(c, None, None, None, None, None, None) for c in cols]
        
        # Parse rows
        parsed_rows = []
        for r in res.get("rows", []):
            vals = []
            for cell in r:
                t = cell.get("type")
                if t == "null":
                    vals.append(None)
                elif t == "integer":
                    vals.append(int(cell.get("value", 0)))
                elif t == "float":
                    vals.append(float(cell.get("value", 0.0)))
                else:
                    vals.append(cell.get("value", ""))
            parsed_rows.append(TursoRow(cols, vals))

        self._rows = parsed_rows
        self._row_index = 0
        self.rowcount = res.get("affected_row_count", len(parsed_rows))
        self.lastrowid = res.get("last_insert_rowid")
        return self

    def fetchone(self):
        if self._row_index < len(self._rows):
            r = self._rows[self._row_index]
            self._row_index += 1
            return r
        return None

    def fetchall(self):
        remaining = self._rows[self._row_index:]
        self._row_index = len(self._rows)
        return remaining

    def close(self):
        pass

class TursoConnection:
    def __init__(self, db_url, auth_token):
        # Convert libsql:// to https://
        clean_url = db_url.strip().replace("libsql://", "https://").rstrip("/")
        if not clean_url.startswith("http"):
            clean_url = f"https://{clean_url}"
        self.http_url = clean_url
        self.auth_token = auth_token.strip()
        self.row_factory = None

    def cursor(self):
        return TursoCursor(self)

    def execute(self, sql, params=()):
        c = self.cursor()
        return c.execute(sql, params)

    def commit(self):
        # In HTTP pipeline, executions commit atomically
        pass

    def rollback(self):
        pass

    def close(self):
        pass

def get_turso_connection():
    """
    Returns TursoConnection if configured in Config, else returns None.
    """
    url = getattr(Config, "TURSO_DATABASE_URL", "").strip()
    token = getattr(Config, "TURSO_AUTH_TOKEN", "").strip()
    if url and token:
        try:
            conn = TursoConnection(url, token)
            return conn
        except Exception as e:
            logger.warning(f"[TURSO] Could not establish connection: {e}")
    return None

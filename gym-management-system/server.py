import json, sqlite3, os, uuid
from datetime import date, datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

DB = os.path.join(os.path.dirname(__file__), "gym.db")
FRONTEND = os.path.join(os.path.dirname(__file__), "frontend")

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS members(
            id TEXT PRIMARY KEY, name TEXT NOT NULL, phone TEXT, email TEXT,
            plan TEXT, join_date TEXT, fee_status TEXT DEFAULT 'Pending'
        );
        CREATE TABLE IF NOT EXISTS attendance(
            id TEXT PRIMARY KEY, member_id TEXT, checkin_date TEXT, checkin_time TEXT
        );
        CREATE TABLE IF NOT EXISTS payments(
            id TEXT PRIMARY KEY, member_id TEXT, amount REAL, pay_date TEXT, method TEXT
        );
        """)

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=FRONTEND, **kw)

    def log_message(self, *a): pass

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/members":
            with db() as con:
                rows = con.execute("SELECT * FROM members ORDER BY name").fetchall()
            return self.send_json([dict(r) for r in rows])
        if path == "/api/attendance":
            with db() as con:
                rows = con.execute("""SELECT a.*, m.name FROM attendance a
                    JOIN members m ON m.id=a.member_id
                    ORDER BY a.checkin_date DESC, a.checkin_time DESC LIMIT 100""").fetchall()
            return self.send_json([dict(r) for r in rows])
        if path == "/api/payments":
            with db() as con:
                rows = con.execute("""SELECT p.*, m.name FROM payments p
                    JOIN members m ON m.id=p.member_id
                    ORDER BY p.pay_date DESC LIMIT 100""").fetchall()
            return self.send_json([dict(r) for r in rows])
        if path == "/api/stats":
            with db() as con:
                members = con.execute("SELECT COUNT(*) c FROM members").fetchone()["c"]
                today = date.today().isoformat()
                present = con.execute("SELECT COUNT(DISTINCT member_id) c FROM attendance WHERE checkin_date=?", (today,)).fetchone()["c"]
                paid = con.execute("SELECT COUNT(*) c FROM members WHERE fee_status='Paid'").fetchone()["c"]
                revenue = con.execute("SELECT COALESCE(SUM(amount),0) s FROM payments").fetchone()["s"]
            return self.send_json({"members": members, "present_today": present, "paid": paid, "revenue": revenue})
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        data = self.read_json()
        if path == "/api/members":
            if not data.get("name"):
                return self.send_json({"error": "Name is required"}, 400)
            member = {"id": str(uuid.uuid4())[:8], "name": data["name"], "phone": data.get("phone",""),
                      "email": data.get("email",""), "plan": data.get("plan","Monthly"),
                      "join_date": data.get("join_date") or date.today().isoformat(),
                      "fee_status": data.get("fee_status","Pending")}
            with db() as con:
                con.execute("INSERT INTO members VALUES (?,?,?,?,?,?,?)", tuple(member.values()))
            return self.send_json(member, 201)
        if path == "/api/attendance":
            member_id = data.get("member_id")
            with db() as con:
                member = con.execute("SELECT id FROM members WHERE id=?", (member_id,)).fetchone()
                if not member:
                    return self.send_json({"error": "Member not found"}, 404)
                rec = {"id": str(uuid.uuid4())[:8], "member_id": member_id,
                       "checkin_date": date.today().isoformat(), "checkin_time": datetime.now().strftime("%H:%M:%S")}
                con.execute("INSERT INTO attendance VALUES (?,?,?,?)", tuple(rec.values()))
            return self.send_json(rec, 201)
        if path == "/api/payments":
            member_id, amount = data.get("member_id"), data.get("amount")
            if not member_id or not amount:
                return self.send_json({"error": "member_id and amount are required"}, 400)
            with db() as con:
                if not con.execute("SELECT id FROM members WHERE id=?", (member_id,)).fetchone():
                    return self.send_json({"error": "Member not found"}, 404)
                rec = {"id": str(uuid.uuid4())[:8], "member_id": member_id, "amount": float(amount),
                       "pay_date": date.today().isoformat(), "method": data.get("method","Cash")}
                con.execute("INSERT INTO payments VALUES (?,?,?,?,?)", tuple(rec.values()))
                con.execute("UPDATE members SET fee_status='Paid' WHERE id=?", (member_id,))
            return self.send_json(rec, 201)
        return self.send_json({"error": "Not found"}, 404)

    def do_PUT(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/members/"):
            return self.send_json({"error": "Not found"}, 404)
        member_id = path.split("/")[-1]
        data = self.read_json()
        with db() as con:
            row = con.execute("SELECT * FROM members WHERE id=?", (member_id,)).fetchone()
            if not row:
                return self.send_json({"error": "Member not found"}, 404)
            updated = {**dict(row), **{k: data[k] for k in ("name","phone","email","plan","fee_status") if k in data}}
            con.execute("""UPDATE members SET name=?,phone=?,email=?,plan=?,fee_status=? WHERE id=?""",
                        (updated["name"],updated["phone"],updated["email"],updated["plan"],updated["fee_status"],member_id))
        return self.send_json(updated)

    def do_DELETE(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/members/"):
            return self.send_json({"error": "Not found"}, 404)
        member_id = path.split("/")[-1]
        with db() as con:
            con.execute("DELETE FROM members WHERE id=?", (member_id,))
            con.execute("DELETE FROM attendance WHERE member_id=?", (member_id,))
            con.execute("DELETE FROM payments WHERE member_id=?", (member_id,))
        return self.send_json({"ok": True})

if __name__ == "__main__":
    init_db()
    print("Gym Management System running at http://localhost:8000")
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
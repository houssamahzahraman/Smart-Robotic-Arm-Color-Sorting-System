from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import requests
import mysql.connector
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret123'
socketio = SocketIO(app, cors_allowed_origins="*")

ESP_IP = "http://192.168.0.7"

data = {
    "red":       0,
    "blue":      0,
    "green":     0,
    "total":     0,
    "armStatus": "IDLE",
    "lastColor": "",
    "logs":      [],
    "servos":    [370, 360, 200, 320, 200, 320]
}

# ════════════════════════════════
# DATABASE — MySQL / XAMPP
# ════════════════════════════════

DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "",           # XAMPP default is empty
    "database": "sorting_db"
}

def get_conn():
    return mysql.connector.connect(**DB_CONFIG)

def init_db():
    conn = mysql.connector.connect(
        host=DB_CONFIG["host"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"]
    )
    c = conn.cursor()
    c.execute("CREATE DATABASE IF NOT EXISTS sorting_db")
    c.execute("USE sorting_db")
    c.execute("""
        CREATE TABLE IF NOT EXISTS sorting_events (
            id        INT AUTO_INCREMENT PRIMARY KEY,
            color     VARCHAR(10) NOT NULL,
            x         FLOAT,
            y         FLOAT,
            timestamp DATETIME NOT NULL,
            success   TINYINT DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()
    print("Database ready!")

def save_event(color, x, y, success=1):
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute(
            "INSERT INTO sorting_events (color, x, y, timestamp, success) VALUES (%s, %s, %s, %s, %s)",
            (color, x, y, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), success)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

def query_db(sql, args=()):
    try:
        conn = get_conn()
        c = conn.cursor(dictionary=True)
        c.execute(sql, args)
        rows = c.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"DB Query Error: {e}")
        return []

def add_log(msg):
    data["logs"].insert(0, msg)
    if len(data["logs"]) > 20:
        data["logs"].pop()

# ════════════════════════════════
# MAIN ROUTES
# ════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/data")
def get_data():
    return jsonify(data)

@app.route("/detect", methods=["POST"])
def detect():

    color   = request.json.get("color", "").upper()
    x       = request.json.get("x", 0)
    y       = request.json.get("y", 0)
    success = request.json.get("success", 1)
    if color in ["RED", "BLUE", "GREEN"]:
        data[color.lower()] += 1
        data["total"]        += 1
        data["lastColor"]     = color
        data["armStatus"]     = "SORTING"
        add_log(f"{color} at ({x},{y}) → sorting")
        save_event(color, x, y, success)
        socketio.emit("update", data)
    return jsonify({"status": "ok"})

@app.route("/done", methods=["POST"])
def done():
    data["armStatus"] = "IDLE"
    add_log("Done ✓ — ready")
    socketio.emit("update", data)
    return jsonify({"status": "ok"})

@app.route("/send", methods=["POST"])
def send_cmd():
    cmd = request.json.get("cmd")
    try:
        requests.post(f"{ESP_IP}/control", json={"cmd": cmd}, timeout=2)
        add_log(f"Manual: {cmd}")
    except Exception as e:
        add_log(f"ESP Error: {str(e)}")
    socketio.emit("update", data)
    return jsonify({"status": "ok"})

@app.route("/reset", methods=["POST"])
def reset():
    data["red"] = data["blue"] = data["green"] = data["total"] = 0
    data["logs"] = []
    data["armStatus"] = "IDLE"
    socketio.emit("update", data)
    return jsonify({"status": "ok"})

@app.route("/servo", methods=["POST"])
def servo_control():
    servo_id  = request.json.get("id")
    pwm_value = request.json.get("value")
    try:
        requests.post(f"{ESP_IP}/servo", json={"id": servo_id, "value": pwm_value}, timeout=2)
        data["servos"][servo_id] = pwm_value
        add_log(f"Servo {servo_id} → {pwm_value}")
    except Exception as e:
        add_log(f"ESP Error: {str(e)}")
    socketio.emit("update", data)
    return jsonify({"status": "ok"})

# ════════════════════════════════
# ADMIN API
# ════════════════════════════════

@app.route("/api/stats/today")
def stats_today():
    today = datetime.now().strftime("%Y-%m-%d")
    rows = query_db("SELECT color, COUNT(*) as count FROM sorting_events WHERE DATE(timestamp) = %s GROUP BY color", (today,))
    result = {"RED": 0, "BLUE": 0, "GREEN": 0, "total": 0}
    for r in rows:
        result[r["color"]] = r["count"]
        result["total"] += r["count"]
    return jsonify(result)

@app.route("/api/stats/last30days")
def stats_last30():
    since = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    rows = query_db("""
        SELECT DATE(timestamp) as day, color, COUNT(*) as count
        FROM sorting_events WHERE DATE(timestamp) >= %s
        GROUP BY day, color ORDER BY day
    """, (since,))
    return jsonify([{**r, "day": str(r["day"])} for r in rows])

@app.route("/api/stats/weekly")
def stats_weekly():
    since = (datetime.now() - timedelta(weeks=8)).strftime("%Y-%m-%d")
    rows = query_db("""
        SELECT DATE_FORMAT(timestamp, '%%Y-W%%u') as week, color, COUNT(*) as count
        FROM sorting_events WHERE DATE(timestamp) >= %s
        GROUP BY week, color ORDER BY week
    """, (since,))
    return jsonify(rows)

@app.route("/api/stats/colors")
def stats_colors():
    return jsonify(query_db("SELECT color, COUNT(*) as count FROM sorting_events GROUP BY color"))

@app.route("/api/stats/accuracy")
def stats_accuracy():
    overall  = query_db("SELECT COUNT(*) as total, SUM(success) as successful, ROUND(SUM(success)*100.0/COUNT(*),1) as accuracy FROM sorting_events")
    by_color = query_db("SELECT color, COUNT(*) as total, SUM(success) as successful, ROUND(SUM(success)*100.0/COUNT(*),1) as accuracy FROM sorting_events GROUP BY color")
    return jsonify({
        "overall":  overall[0] if overall else {"total": 0, "successful": 0, "accuracy": 0},
        "by_color": by_color
    })

@app.route("/api/stats/hourly")
def stats_hourly():
    today = datetime.now().strftime("%Y-%m-%d")
    return jsonify(query_db("SELECT HOUR(timestamp) as hour, COUNT(*) as count FROM sorting_events WHERE DATE(timestamp) = %s GROUP BY hour ORDER BY hour", (today,)))

@app.route("/api/stats/recent")
def stats_recent():
    rows = query_db("SELECT color, x, y, timestamp, success FROM sorting_events ORDER BY id DESC LIMIT 50")
    return jsonify([{**r, "timestamp": str(r["timestamp"])} for r in rows])

if __name__ == "__main__":
    init_db()
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)

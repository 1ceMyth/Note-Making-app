from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Initialize the database with migration check for 'timestamp' column
def init_db():
    with sqlite3.connect("notes.db") as conn:
        cur = conn.cursor()

        # Create users table if not exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT
            )
        """)

        # Check if 'notes' table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notes'")
        table_exists = cur.fetchone()

        if table_exists:
            # Check if 'timestamp' column exists
            cur.execute("PRAGMA table_info(notes)")
            columns = [col[1] for col in cur.fetchall()]
            if 'timestamp' not in columns:
                print("[Migration] Rebuilding 'notes' table to include 'timestamp'")
                cur.execute("DROP TABLE notes")

        # Create notes table with timestamp
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        conn.commit()

init_db()

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        with sqlite3.connect("notes.db") as conn:
            try:
                conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                conn.commit()
                return redirect('/login')
            except sqlite3.IntegrityError:
                return "Username already exists!"
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    next_page = request.args.get('next', '/notes')

    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        with sqlite3.connect("notes.db") as conn:
            cur = conn.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password))
            user = cur.fetchone()
            if user:
                session['user_id'] = user[0]
                return redirect(next_page)
            else:
                return "Invalid credentials"
    return render_template('login.html')

@app.route('/notes', methods=['GET', 'POST'])
def notes():
    if 'user_id' not in session:
        return redirect('/login?next=/notes')

    user_id = session['user_id']

    with sqlite3.connect("notes.db") as conn:
        cur = conn.cursor()

        if request.method == 'POST':
            content = request.form.get('note', '').strip()
            if content:
                try:
                    conn.execute("INSERT INTO notes (user_id, content) VALUES (?, ?)", (user_id, content))
                    conn.commit()
                except Exception as e:
                    print("Note insert error:", e)

        cur.execute("SELECT id, content, timestamp FROM notes WHERE user_id=? ORDER BY timestamp DESC", (user_id,))
        user_notes = cur.fetchall()

    return render_template("notes.html", notes=user_notes)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'user_id' not in session:
        return redirect('/login?next=/chat')

    response = ""
    user_message = ""

    try:
        with sqlite3.connect("notes.db") as conn:
            cur = conn.cursor()
            cur.execute("SELECT content, timestamp FROM notes WHERE user_id=?", (session['user_id'],))
            user_notes = cur.fetchall()
    except Exception as e:
        return f"Error loading chat data: {e}"

    if request.method == 'POST':
        user_message = request.form.get('message', '').lower()

        # Smart reply logic
        if "when" in user_message and "note" in user_message:
            response = "Here are your notes with timestamps:\n\n"
            for note, ts in user_notes:
                response += f"- {note.strip()} (Saved on {ts})\n"
        else:
            matched = [note for note, _ in user_notes if user_message in note.lower()]
            if matched:
                response = "Based on your notes, I found:\n" + "\n".join(f"- {m}" for m in matched)
            else:
                response = "Sorry, I couldn't find anything related in your notes."

    return render_template("chat.html", response=response, message=user_message)

if __name__ == '__main__':
    app.run(debug=True)

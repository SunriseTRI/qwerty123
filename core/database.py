import sqlite3
import os
import logging
import pandas as pd
import hashlib

logger = logging.getLogger(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'bot_data.db')




def generate_question_hash(question: str) -> str:
    return hashlib.sha256(question.encode()).hexdigest()[:16]


def get_question_by_hash(question_hash: str) -> str:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT question FROM faq WHERE question_hash = ?", (question_hash,))
        row = cur.fetchone()
        return row[0] if row else None


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        phone TEXT,
                        full_name TEXT
                    )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS faq (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        question TEXT UNIQUE,
                        answer TEXT,
                        question_hash TEXT UNIQUE
                    )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS unanswered_questions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        question TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )''')
        conn.commit()
        logger.info("База данных инициализирована")


def merge_faq_from_excel(file_path: str) -> tuple[int, int]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Excel-файл {file_path} не найден")

    try:
        df = pd.read_excel(file_path)
        if 'question' not in df.columns or 'answer' not in df.columns:
            raise ValueError("Excel должен содержать колонки 'question' и 'answer'")

        new_entries = 0
        updated_entries = 0

        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute('''CREATE TABLE IF NOT EXISTS faq (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            question TEXT UNIQUE,
                            answer TEXT,
                            question_hash TEXT UNIQUE
                        )''')

            for _, row in df.iterrows():
                question = str(row['question']).strip().replace('#', '')
                answer = str(row['answer']).strip().replace('#', '')

                if not question:
                    continue

                question_hash = generate_question_hash(question)

                cur.execute("SELECT id FROM faq WHERE question = ?", (question,))
                if cur.fetchone():
                    cur.execute('''UPDATE faq SET 
                                answer = ?, 
                                question_hash = ?
                                WHERE question = ?''',
                                (answer, question_hash, question))
                    updated_entries += 1
                else:
                    cur.execute('''INSERT INTO faq 
                                  (question, answer, question_hash) 
                                  VALUES (?, ?, ?)''',
                                (question, answer, question_hash))
                    new_entries += 1
            conn.commit()
        return new_entries, updated_entries

    except Exception as e:
        logger.error(f"Ошибка при синхронизации FAQ: {e}")
        return 0, 0


def get_all_faq_questions():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT question FROM faq WHERE answer IS NOT NULL")
        return [row[0] for row in cur.fetchall()]


def log_unanswered_question(question: str):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO unanswered_questions (question) VALUES (?)",
            (question,)
        )
        conn.commit()


def get_faq_answer(question: str) -> str | None:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT answer FROM faq WHERE question = ?", (question,))
            row = cur.fetchone()
            return row[0] if row else None
    except sqlite3.Error as e:
        logging.error(f"Database error in get_faq_answer: {e}")
        return None

def insert_faq_question(question: str):
    question_hash = generate_question_hash(question)
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute('''INSERT OR IGNORE INTO faq 
                     (question, answer, question_hash) 
                     VALUES (?, NULL, ?)''',
                    (question, question_hash))
        conn.commit()


def is_user_registered(user_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        return cur.fetchone() is not None


def insert_user(user_id: int, username: str, phone: str, full_name: str):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO users (user_id, username, phone, full_name) VALUES (?, ?, ?, ?)",
            (user_id, username, phone, full_name)
        )
        conn.commit()


# novoe
def insert_user(user_id: int, username: str, phone: str, full_name: str):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO users (user_id, username, phone, full_name) VALUES (?, ?, ?, ?)",
            (user_id, username, phone, full_name)
        )
        conn.commit()

def is_user_registered(user_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        return cur.fetchone() is not None

def insert_faq_question(question: str):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO unanswered_questions (question) VALUES (?)", (question,))
        conn.commit()

def get_faq_answer(question: str) -> str:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT answer FROM faq WHERE question = ?", (question,))
        row = cur.fetchone()
        return row[0] if row else "Ответ пока не найден"

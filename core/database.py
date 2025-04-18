import sqlite3
import os
import logging
import pandas as pd  # убедись, что в requirements.txt есть pandas

logger = logging.getLogger(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'bot_data.db')


def merge_faq_from_excel(file_path: str) -> tuple[int, int]:
    try:
        df = pd.read_excel(file_path)
        new_entries = 0
        updated_entries = 0
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            for _, row in df.iterrows():
                question = row['question']
                answer = row['answer']
                cur.execute("SELECT id FROM faq WHERE question = ?", (question,))
                result = cur.fetchone()
                if result:
                    cur.execute("UPDATE faq SET answer = ? WHERE question = ?", (answer, question))
                    updated_entries += 1
                else:
                    cur.execute("INSERT INTO faq (question, answer) VALUES (?, ?)", (question, answer))
                    new_entries += 1
            conn.commit()
        return new_entries, updated_entries
    except Exception as e:
        print(f\"Ошибка при обновлении FAQ: {e}\")
        return 0, 0

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                phone TEXT,
                full_name TEXT
            )'''
        )
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS faq (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT UNIQUE,
                answer TEXT
            )'''
        )
        conn.commit()
        logger.info("База данных инициализирована")

# Получить ответ из FAQ
def get_faq_answer(question: str):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT answer FROM faq WHERE question = ?", (question,))
        row = cur.fetchone()
        return row[0] if row else None

# Сохранить новый вопрос-заглушку
def insert_faq_question(question: str):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO faq (question, answer) VALUES (?, NULL)",
            (question,)
        )
        conn.commit()

# Проверка регистрации
def is_user_registered(user_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM users WHERE user_id = ?", (user_id,)
        )
        return cur.fetchone() is not None

# Добавить пользователя
def insert_user(user_id: int, username: str, phone: str, full_name: str):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO users (user_id, username, phone, full_name) VALUES (?, ?, ?, ?)",
            (user_id, username, phone, full_name)
        )
        conn.commit()
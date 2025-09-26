

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer
import re
from difflib import SequenceMatcher
from fuzzywuzzy import fuzz

# =========================
# Настройки поиска (можно редактировать)
# =========================

# Порог схожести для TF-IDF (0.0–1.0)
TFIDF_THRESHOLD = 0.3  # если хотите более "мягкий" поиск, уменьшите до 0.3

# Порог схожести для fuzzy (0–100)
FUZZY_THRESHOLD = 50  # 100 — строгое совпадение, 50 — допускает опечатки

# Порог схожести по символам/частям слов (0.0–1.0)
CHAR_THRESHOLD = 0.55  # чем ниже — тем больше шансов найти кривой ввод

# Максимальное число результатов
TOP_N_RESULTS = 5


# =========================
# NLP подготовка
# =========================

nltk.download('stopwords', quiet=True)
stemmer = SnowballStemmer("russian")
stop_words = set(stopwords.words("russian"))

def preprocess_text(text: str) -> str:
    """
    Преобразует текст: приведение к нижнему регистру,
    удаление пунктуации, стемминг и удаление стоп-слов.
    """
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    words = text.split()
    words = [stemmer.stem(word) for word in words if word not in stop_words]
    return ' '.join(words)

# =========================
# Класс FAQEngine
# =========================

class FAQEngine:
    def __init__(self):
        self.vectorizer = None
        self.faq_vectors = None
        self.faq_questions = []

    def fit(self, questions: list[str]):
        self.faq_questions = questions
        if questions:
            processed_questions = [preprocess_text(q) for q in questions]
            self.vectorizer = TfidfVectorizer()
            self.faq_vectors = self.vectorizer.fit_transform(processed_questions)

faq_engine = FAQEngine()

# =========================
# Основная функция поиска
# =========================

def find_similar_questions(user_question: str, faq_questions: list[str],
                           threshold: float = None,  # для совместимости со старым кодом
                           tfidf_threshold: float = None,
                           fuzzy_threshold: int = None,
                           char_threshold: float = None,
                           top_n: int = None):
    """
    Ищет похожие вопросы в базе FAQ.
    Использует комбинированный подход:
    1) TF-IDF косинусная схожесть
    2) fuzzy string matching
    3) совпадение символов / частей слов (SequenceMatcher)
    """
    # =========================
    # Подготовка порогов и top_n
    # =========================
    tfidf_threshold = tfidf_threshold if tfidf_threshold is not None else (threshold if threshold is not None else TFIDF_THRESHOLD)
    fuzzy_threshold = fuzzy_threshold if fuzzy_threshold is not None else FUZZY_THRESHOLD
    char_threshold = char_threshold if char_threshold is not None else CHAR_THRESHOLD
    top_n = top_n if top_n is not None else TOP_N_RESULTS

    if not faq_questions:
        return []

    # =========================
    # Подготовка векторов TF-IDF
    # =========================
    faq_engine.fit(faq_questions)
    processed_user = preprocess_text(user_question)
    user_vector = faq_engine.vectorizer.transform([processed_user])
    similarities = cosine_similarity(user_vector, faq_engine.faq_vectors)[0]

    # =========================
    # Первый уровень: TF-IDF
    # =========================
    tfidf_results = []
    for idx, score in enumerate(similarities):
        if score >= tfidf_threshold:
            tfidf_results.append((faq_questions[idx], score))

    if tfidf_results:
        tfidf_results.sort(key=lambda x: x[1], reverse=True)
        return tfidf_results[:top_n]

    # =========================
    # Второй уровень: fuzzy
    # =========================
    fuzzy_results = []
    for q in faq_questions:
        score = fuzz.token_set_ratio(user_question.lower(), q.lower())
        if score >= fuzzy_threshold:
            fuzzy_results.append((q, score / 100.0))
    if fuzzy_results:
        fuzzy_results.sort(key=lambda x: x[1], reverse=True)
        return fuzzy_results[:top_n]

    # =========================
    # Третий уровень: совпадение символов / частей слов
    # =========================
    char_results = []
    for q in faq_questions:
        score = SequenceMatcher(None, user_question.lower(), q.lower()).ratio()
        if score >= char_threshold:
            char_results.append((q, score))
    if char_results:
        char_results.sort(key=lambda x: x[1], reverse=True)
        return char_results[:top_n]

    # =========================
    # Если ничего не найдено
    # =========================
    return []

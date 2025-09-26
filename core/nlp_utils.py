import re
import logging
import numpy as np
from difflib import SequenceMatcher
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from fuzzywuzzy import fuzz
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer
import nltk

# ==========================
# NLP Настройки и инициализация
# ==========================
nltk.download('stopwords')
STEMMER = SnowballStemmer("russian")
STOPWORDS = set(stopwords.words("russian"))

# ==========================
# Настройки поиска
# ==========================
# Каждый порог можно менять для настройки чувствительности
TFIDF_THRESHOLD = 0.5      # Косинусная схожесть TF-IDF, 0.0-1.0 (чем выше, тем строже)
FUZZY_THRESHOLD = 70        # Fuzzy matching, 0-100 (чем выше, тем строже)
SEQUENCE_THRESHOLD = 0.3    # SequenceMatcher, 0.0-1.0
SUBWORD_THRESHOLD = 0.3     # Частичная подсловная схожесть
LEVENSHTEIN_THRESHOLD = 2   # Максимальное расстояние редактирования
JACCARD_THRESHOLD = 0.3     # Jaccard similarity, 0.0-1.0
# EMBBEDDING_THRESHOLD = 0.5 # (если будем добавлять семантический поиск)
# PHONETIC_THRESHOLD = 0.5   # (если будем добавлять фонетику)

TOP_N_RESULTS = 5           # Количество результатов для отображения пользователю

# ==========================
# Препроцессинг
# ==========================
def preprocess_text(text: str) -> str:
    """Приводит текст к нижнему регистру, убирает пунктуацию, стоп-слова и стеммит слова"""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    words = text.split()
    words = [STEMMER.stem(word) for word in words if word not in STOPWORDS]
    return ' '.join(words)

# ==========================
# Методы поиска
# ==========================
def tfidf_search(user_question: str, faq_questions: list[str]):
    """Поиск с помощью TF-IDF + косинусная схожесть"""
    if not faq_questions:
        return []
    processed_questions = [preprocess_text(q) for q in faq_questions]
    vectorizer = TfidfVectorizer()
    faq_vectors = vectorizer.fit_transform(processed_questions)
    user_vector = vectorizer.transform([preprocess_text(user_question)])
    similarities = cosine_similarity(user_vector, faq_vectors)[0]
    results = [(faq_questions[i], sim) for i, sim in enumerate(similarities) if sim >= TFIDF_THRESHOLD]
    logging.info(f"[TF-IDF] Найдено {len(results)} совпадений")
    return results

def fuzzy_search(user_question: str, faq_questions: list[str]):
    """Поиск по Fuzzy string matching"""
    results = []
    for q in faq_questions:
        score = fuzz.token_set_ratio(user_question, q)
        if score >= FUZZY_THRESHOLD:
            results.append((q, score / 100))
    logging.info(f"[Fuzzy] Найдено {len(results)} совпадений")
    return results

def sequence_search(user_question: str, faq_questions: list[str]):
    """Поиск по SequenceMatcher (частичная схожесть символов)"""
    results = []
    for q in faq_questions:
        score = SequenceMatcher(None, user_question, q).ratio()
        if score >= SEQUENCE_THRESHOLD:
            results.append((q, score))
    logging.info(f"[SequenceMatcher] Найдено {len(results)} совпадений")
    return results

def subword_search(user_question: str, faq_questions: list[str]):
    """Подсловный поиск: проверка совпадений подстрок"""
    results = []
    uq = preprocess_text(user_question)
    for q in faq_questions:
        pq = preprocess_text(q)
        words_u = set(uq.split())
        words_q = set(pq.split())
        if not words_u:
            continue
        overlap = len(words_u & words_q) / len(words_u)
        if overlap >= SUBWORD_THRESHOLD:
            results.append((q, overlap))
    logging.info(f"[Subword] Найдено {len(results)} совпадений")
    return results

def levenshtein_search(user_question: str, faq_questions: list[str]):
    """Поиск по расстоянию Левенштейна"""
    def levenshtein_distance(s1, s2):
        if s1 == s2:
            return 0
        if len(s1) == 0:
            return len(s2)
        if len(s2) == 0:
            return len(s1)
        prev_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            curr_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = prev_row[j + 1] + 1
                deletions = curr_row[j] + 1
                substitutions = prev_row[j] + (c1 != c2)
                curr_row.append(min(insertions, deletions, substitutions))
            prev_row = curr_row
        return prev_row[-1]

    results = []
    for q in faq_questions:
        dist = levenshtein_distance(user_question.lower(), q.lower())
        if dist <= LEVENSHTEIN_THRESHOLD:
            results.append((q, 1 - dist / max(len(user_question), len(q))))
    logging.info(f"[Levenshtein] Найдено {len(results)} совпадений")
    return results

def jaccard_search(user_question: str, faq_questions: list[str]):
    """Поиск по Jaccard similarity (overlap слов)"""
    uq_set = set(preprocess_text(user_question).split())
    results = []
    for q in faq_questions:
        fq_set = set(preprocess_text(q).split())
        if not uq_set:
            continue
        overlap = len(uq_set & fq_set) / len(uq_set)
        if overlap >= JACCARD_THRESHOLD:
            results.append((q, overlap))
    logging.info(f"[Jaccard] Найдено {len(results)} совпадений")
    return results

# ==========================
# Основная функция поиска
# ==========================
def find_similar_questions(user_question: str, faq_questions: list[str]):
    """
    Главная функция поиска. Использует все методы по очереди.
    Возвращает список: [(вопрос, средняя_оценка), ...] отсортированный по релевантности.
    """
    all_results = []

    # 1. TF-IDF
    all_results.extend(tfidf_search(user_question, faq_questions))

    # 2. Fuzzy
    all_results.extend(fuzzy_search(user_question, faq_questions))

    # 3. SequenceMatcher
    all_results.extend(sequence_search(user_question, faq_questions))

    # 4. Subword
    all_results.extend(subword_search(user_question, faq_questions))

    # 5. Levenshtein
    all_results.extend(levenshtein_search(user_question, faq_questions))

    # 6. Jaccard
    all_results.extend(jaccard_search(user_question, faq_questions))

    # ==========================
    # Комбинируем результаты
    # ==========================
    # Считаем среднюю оценку для каждого вопроса, встречающегося в разных методах
    counter = {}
    scores = {}
    for q, score in all_results:
        if q not in counter:
            counter[q] = 0
            scores[q] = []
        counter[q] += 1
        scores[q].append(score)

    # Средняя оценка
    combined_results = [(q, sum(scores[q]) / len(scores[q]), counter[q]) for q in counter]

    # Сортировка: сначала по количеству совпадений (чем чаще встречался), потом по средней оценке
    combined_results.sort(key=lambda x: (x[2], x[1]), reverse=True)

    # Логирование
    logging.info(f"[Combined] Всего кандидатов: {len(combined_results)}")
    for q, avg, count in combined_results[:TOP_N_RESULTS]:
        logging.info(f"Вопрос: {q}, Средняя оценка: {avg:.2f}, Методов: {count}")

    return combined_results[:TOP_N_RESULTS]

# ==========================
# Функция для ручного добавления вопросов в unanswered
# ==========================
unanswered_questions = []

def add_unanswered_question(user_question: str):
    unanswered_questions.append(user_question)
    logging.info(f"[Unanswered] Добавлен вопрос: {user_question}")

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer
import re

nltk.download('stopwords')
stemmer = SnowballStemmer("russian")
stop_words = set(stopwords.words("russian"))


def preprocess_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    words = text.split()
    words = [stemmer.stem(word) for word in words if word not in stop_words]
    return ' '.join(words)


# def find_similar_questions(user_question: str, faq_questions: list, threshold=0.5, top_n=3):
#     if not faq_questions:
#         return []
#
#     processed_user = preprocess_text(user_question)
#     processed_faq = [preprocess_text(q) for q in faq_questions]
#
#     vectorizer = TfidfVectorizer()
#     vectors = vectorizer.fit_transform([processed_user] + processed_faq)
#
#     cosine_matrix = cosine_similarity(vectors[0:1], vectors[1:])
#     similarities = cosine_matrix[0]

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

def find_similar_questions(user_question: str, threshold=0.5, top_n=3):
    if not faq_engine.faq_questions:
        return []
    processed_user = preprocess_text(user_question)
    user_vector = faq_engine.vectorizer.transform([processed_user])
    similarities = cosine_similarity(user_vector, faq_engine.faq_vectors)[0]
    sorted_indices = np.argsort(similarities)[::-1]
    results = []
    for idx in sorted_indices:
        if similarities[idx] >= threshold:
            results.append((faq_questions[idx], similarities[idx]))

    return results[:top_n]

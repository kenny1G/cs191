import os
import sys
import sqlite3

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from collections import Counter
import streamlit as st
import streamlit.components.v1 as components
import pinecone
from sentence_transformers import SentenceTransformer
import numpy as np
from dotenv import load_dotenv
from sql_queries.queries import GET_PHOTO_BY_DATE

ROOT_DIRECTORY = os.path.dirname(os.path.abspath(os.curdir))
FLASK_PATH = "http://127.0.0.1:5000/static/"
INSTANCE_DIR = os.path.join(ROOT_DIRECTORY, "instance")
DB_PATH = os.path.join(INSTANCE_DIR, "photos.db")

class ImageSearchApp:
    def __init__(self):
        self.load_env_vars()
        self.init_pinecone()
        self.model = SentenceTransformer("clip-ViT-B-32")
        self.conn = sqlite3.connect(DB_PATH)
        self.selection = None

    def load_env_vars(self):
        load_dotenv()
        self.api_key = os.getenv("PINECONE_API_KEY")
        if not self.api_key:
            print("Warning: No Pinecone API key found.")

    def init_pinecone(self):
        pinecone.init(api_key=self.api_key, environment="us-west1-gcp-free")
        self.index = pinecone.Index("cs191")

    def get_query_vector(self, text):
        query_emb = self.model.encode([text], show_progress_bar=False)
        return np.ndarray.tolist(query_emb)

    def search_images(self, query_vector, top_k=10):
        query_response = self.index.query(
            namespace="image_embeddings",
            vector=query_vector,
            top_k=top_k,
            include_values=False,
            include_metadata=True,
        )
        return query_response.get("matches", [])

    def aggregate_results(self, matches):
        date_scores = {}
        for match in matches:
            date = match.metadata["date"]
            score = match.score
            date_scores[date] = date_scores.get(date, 0) + score
        date_counts = sorted(date_scores.items(), key=lambda x: x[1], reverse=True)
        return date_counts

    def display_results(self, date_counts):
        cursor = self.conn.cursor()
        st.write("Dates with the highest scores:")
        for date, score in date_counts:
            cursor.execute(f"{GET_PHOTO_BY_DATE}", (date,))
            photos = cursor.fetchall()
            img_string = ""
            for photo in photos:
                photo_path = os.path.join(FLASK_PATH, "converted_photos", photo[0])
                img_string += f"""
                <img src="{photo_path}"
                    style="margin: 5px; height: 300px; object-fit: contain"
                    alt="Photo taken on {date}" >
                """
            html_string = f"""
            <main >
            <div style='display: flex; justify-content: center; overflow-x: auto;'>
            {img_string}
            </div>
            </main>
            """
            if st.button(date):
                print(self.selection)
                self.selection = date
                return date
            components.html(html_string, height=400)

    def search_and_display(self, query):
        query_vector = self.get_query_vector(query)
        matches = self.search_images(query_vector)
        date_counts = self.aggregate_results(matches)
        selection = self.display_results(date_counts)
        return selection

if 'app' not in st.session_state:
    st.session_state.app = ImageSearchApp()
app = st.session_state.app
st.title("Image Search")
query = st.text_input("What Event Do You seek?")
if st.button("Search"):
    try:
        app.search_and_display(query)
    except Exception as e:
        st.write("An error occurred during the search.")
        st.write(str(e))
elif app.selection:
    st.write(f"You selected {app.selection}")
    st.write("Now you can label the photos from this event.")
    st.write("TODO: Add a form to label the photos.")
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
print("ROOT_DIRECTORY:", ROOT_DIRECTORY)
print("INSTANCE_DIR:", INSTANCE_DIR)
print("DB_PATH:", DB_PATH)

load_dotenv()
api_key = os.getenv("PINECONE_API_KEY")
if not api_key:
    print("Warning: No Pinecone API key found.")

pinecone.init(api_key=os.getenv(api_key), environment="us-west1-gcp-free")
# Initialize Pinecone
INDEX_NAME = "cs191"
NAMESPACE = "image_embeddings"
index = pinecone.Index(INDEX_NAME)


def get_query_vector(text):
    model = SentenceTransformer("clip-ViT-B-32")
    query_emb = model.encode([text], show_progress_bar=False)
    return np.ndarray.tolist(query_emb)


def search_images(query_vector, top_k=10):
    query_response = index.query(
        namespace=NAMESPACE,
        vector=query_vector,
        top_k=top_k,
        include_values=False,
        include_metadata=True,
    )

    return query_response.get("matches", [])


def aggregate_results(matches):
    # Create a dictionary to store the dates and their corresponding scores
    date_scores = {}
    for match in matches:
        date = match.metadata["date"]
        score = match.score
        if date in date_scores:
            # If the date already exists in the dictionary, add the score to the existing score
            date_scores[date] += score
        else:
            # If the date does not exist in the dictionary, add it and initialize the score
            date_scores[date] = score
    # Sort the dictionary by score in descending order and convert it to a list of tuples
    date_counts = sorted(date_scores.items(), key=lambda x: x[1], reverse=True)
    return date_counts


def display_results(date_counts):
    # Connect to the database
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        st.write("Dates with the highest scores:")
        html_string = ""
        for date, score in date_counts:
            # Use the GET_PHOTO_BY_DATE query to get the photos associated with the date
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
            <h2 style='color: white;'>{date} with {score} score</h2>
            <div style='display: flex; justify-content: center; overflow-x: auto;'>
            {img_string}
            </div>
            </main>
            """
            components.html(html_string, height=400)
        # Display the photos in the html component
        # Close the database connection


def search_and_display(query):
    query_vector = get_query_vector(query)
    matches = search_images(query_vector)
    date_counts = aggregate_results(matches)
    display_results(date_counts)


st.title("Image Search")
query = st.text_input("What Event Do You seek?")
if st.button("Search"):
    try:
        search_and_display(query)
    except Exception as e:
        st.write("An error occurred during the search.")
        st.write(str(e))

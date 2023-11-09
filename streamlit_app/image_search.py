import streamlit as st
import pinecone
from collections import Counter
from sentence_transformers import SentenceTransformer
import numpy as np
import os
from dotenv import load_dotenv

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
    st.write("Dates with the highest scores:")
    for date, score in date_counts:
        st.write(f"{date}: {score} score")


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

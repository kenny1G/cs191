import streamlit as st

st.set_page_config(
    page_title="Storylines Image Search",
    page_icon="🔍",
    layout="wide"
)

st.write("# Welcome to Storylines Image Search! 🔍")

st.sidebar.success("Follow the steps on the right to use the app.")

st.markdown(
"""
Storylines Image Search is an application that allows you to search for images using natural language queries.
Here's how to use it:
1. **Setup Demo**: Enter a unique ID and authenticate with Google Photos API.
2. **Upsert Images**: Select a date range to fetch images from your Google Photos account. The images are then embedded and stored in a Pinecone vector index.
3. **Image Search**: Enter a natural language query to search for images. \
You can refine your search by adding more queries. Once you find your target image, click 'Accept' to train the system and improve future searches.
"""
)

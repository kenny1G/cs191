import streamlit as st

st.set_page_config(
    page_title="Storylines Image Search",
    page_icon="🔍",
    layout="wide"
)

st.write("# Welcome to Storylines Image Search! 🔍")

st.sidebar.success("Follow the steps on the right to use the app.")

st.subheader("💡 Abstract:")

st.markdown("""
We present Storylines, a prototype image information retrieval
system that leverages vector databases and the in-context learning capabilities
of large language models to  adapt to its users in real time. Storylines implements
existing techniques found in Image Information Retrieval research.
Furthermore, it augments these techniques, further reducing the semantic gap,
by applying additional labeling data inferred from the user's search journeys
while using the tool. We describe its implementation details and how we plan to
demonstrate its performance during the conference demo session.
""")

st.subheader("👨🏻‍💻 How to use the app:")
st.markdown(
"""
1. Go to **Setup Demo**: Enter a unique ID and authenticate with Google Photos API.
2. Go to **Upsert Images**: Select a date range to fetch images from your Google Photos account. The images are then embedded and stored in a Pinecone vector index.
3. Go to **Image Search**: Enter a natural language query to search for images. \
You can refine your search by adding more queries. Once you find your target image, click 'Accept' to train the system and improve future searches.
"""
)
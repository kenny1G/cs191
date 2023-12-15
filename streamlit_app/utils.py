import os
import pinecone
import streamlit as st
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from langchain.embeddings import HuggingFaceEmbeddings

im_index_name = "photo-captions"
@st.cache_resource
def load_model():
    return SentenceTransformer("clip-ViT-B-32")

@st.cache_resource
def load_embedder():
    return HuggingFaceEmbeddings(model_name="clip-Vit-B-32")

@st.cache_resource
def get_pinecone_image_index():
    load_dotenv()
    pinecone.init(
        api_key=os.getenv("PINECONE_API_KEY"),
        environment=os.getenv("PINECONE_ENVIRONMENT"),
    )
    if im_index_name not in pinecone.list_indexes():
        pinecone.create_index(name=im_index_name, dimension=512, metric="cosine")
    return pinecone.Index(im_index_name)

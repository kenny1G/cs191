import logging
from dotenv import load_dotenv
import os
import pinecone
from sentence_transformers import SentenceTransformer
import streamlit as st
from streamlit_image_select import image_select
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.llms import HuggingFaceHub
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.retrievers import RePhraseQueryRetriever
from langchain.vectorstores import Pinecone
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate


if "credentials" not in st.session_state or "uid" not in st.session_state:
    st.warning(
        "You are not authenticated yet. Please enter your unique ID in Setup Demo to Authenticate."
    )
    st.stop()

if "media_items_df" not in st.session_state:
    st.warning(
        "No media items in session, Please go to the Upsert Images page to upload images."
    )
    st.stop()

im_index_name = "photo-captions"

month_names = [
    "NOOP",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


@st.cache_resource
def init_langchain(uid, _pinecone_index):
    logging.basicConfig()
    logging.getLogger("langchain.retrievers.re_phraser").setLevel(logging.DEBUG)

    embed = HuggingFaceEmbeddings(model_name="clip-Vit-B-32")
    text_field = "captions"
    vectorstore = Pinecone(_pinecone_index, embed, text_field, namespace=uid)
    QUERY_PROMPT = PromptTemplate(
        input_variables=["queries"],
        template="""
        Prompt: You are an AI assistant tasked with processing a series of natural
        language image search queries from a user. Your job is to analyze these
        queries, identify the core visual elements they are seeking, and combine
        these elements into a single, coherent query. This synthesized query should
        be optimized for searching against a vectorstore with CLIP embeddings,
        which means it needs to be clear, focused, and stripped of any irrelevant details.

        Here are the user's queries: {queries}

        Your task is to synthesize these queries into one concise and effective
        query for a vectorstore. Remember to focus on visual elements and
        descriptors that are key for image retrieval.

        Synthesized Query:""",
    )
    llm = ChatOpenAI(temperature=0)
    llm_chain = LLMChain(llm=llm, prompt=QUERY_PROMPT)

    retriever_from_llm_chain = RePhraseQueryRetriever(
        retriever=vectorstore.as_retriever(), llm_chain=llm_chain
    )
    return retriever_from_llm_chain


@st.cache_resource
def load_model():
    return SentenceTransformer("clip-ViT-B-32")


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



if "showing_results" not in st.session_state:
    st.session_state["showing_results"] = False

if "search_journey" not in st.session_state:
    st.session_state["search_journey"] = []

if "image_results" not in st.session_state:
    st.session_state["image_results"] = []

st.set_page_config(layout="wide")
clip_model = load_model()
# images = st.session_state["images"]
uid = st.session_state["uid"]
pinecone_index = get_pinecone_image_index()
llm_agent = init_langchain(uid, pinecone_index)
id_to_image = st.session_state["image_dict"]
media_items_df = st.session_state["media_items_df"]
row_size = 5
top_k = 50


def click_search_button(query):
    st.session_state.search_journey.append(query)
    st.session_state.image_results = query_images(query)
    st.session_state.showing_results = True


def query_images(query):
    # create the query vector
    xq = clip_model.encode(query).tolist()

    # now query
    xc = pinecone_index.query(
        xq,
        namespace=uid,
        top_k=top_k,
        include_metadata=True,
    )

    docs = llm_agent.get_relevant_documents("\n\n".join(st.session_state.search_journey))
    print(docs)
    results = []
    # for doc in docs:
    #     results.append((doc["metadata"]["baseUrl"], doc["metadata"]["captions"]))

    # print(media_items_df.head())
    i = 0
    while i < top_k and i < len(xc["matches"]):
        img_id = xc["matches"][i]["id"]
        # print("got id", img_id)
        if img_id in media_items_df["id"].values:
            image_url = media_items_df.loc[
                media_items_df["id"] == img_id, "baseUrl"
            ].iloc[0]
            # print("got url", img_url)

            img_year = media_items_df.loc[
                media_items_df["id"] == img_id, "metadata"
            ].iloc[0]["year"]
            # print("got year", img_year)
            img_month = media_items_df.loc[
                media_items_df["id"] == img_id, "metadata"
            ].iloc[0]["month"]
            # print("got month", img_month)
            img_text = month_names[img_month] + " of " + str(img_year)

            results.append((image_url, img_text))
            i += 1
    # print (results)
    return results


col1, col2 = st.columns(2)
with col1:
    st.header("Search")
    query = st.text_input("Search till you find it!", key="text_input_query")
    st.button("Search", on_click=click_search_button, args=[query])
    if st.session_state.image_results != []:
        image_results = st.session_state.image_results
        cols = st.columns(len(image_results))
        images = [x[0] for x in image_results]
        img = image_select(
            label="Select the image", images=images, return_value="index"
        )
        # TODO: LEARN!
        if img != 0:
            print(img)
with col2:
    st.header("Gallery")
    grid = st.columns(row_size)
    col = 0
    for i, image in enumerate(media_items_df["baseUrl"].values):
        with grid[col]:
            st.image(image)
            st.write(media_items_df["captions"].iloc[i])
        col = (col + 1) % row_size


with st.sidebar:
    if st.session_state.search_journey != []:
        st.header("Search Journey So Far")
        for user_query in st.session_state.search_journey:
            st.write(user_query)
        if st.button("Clear Search Journey"):
            st.session_state.image_results = []
            st.session_state.search_journey = []
            st.session_state["showing_results"] = False
            st.rerun()

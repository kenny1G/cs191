import os
import sys
import sqlite3
import uuid
from math import ceil

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import streamlit as st
from streamlit_image_select import image_select
import streamlit.components.v1 as components
import pinecone
from sentence_transformers import SentenceTransformer
import numpy as np
from dotenv import load_dotenv
from sql_queries.queries import GET_PHOTO_BY_DATE
from google_photos import GooglePhotosApi
import ipyplot

ROOT_DIRECTORY = os.path.dirname(os.path.abspath(os.curdir))
FLASK_PATH = "http://127.0.0.1:5000/static/"
INSTANCE_DIR = os.path.join(ROOT_DIRECTORY, "instance")
DB_PATH = os.path.join(INSTANCE_DIR, "photos.db")
AUTH = 0
DATE_SELECTION = 1
LEARNINGS = 2
RESULTS = 3


def month_name(month):
    if month == 1:
        month_text = "January"
    if month == 2:
        month_text = "February"
    if month == 3:
        month_text = "March"
    if month == 4:
        month_text = "April"
    if month == 5:
        month_text = "May"
    if month == 6:
        month_text = "June"
    if month == 7:
        month_text = "July"
    if month == 8:
        month_text = "August"
    if month == 9:
        month_text = "September"
    if month == 10:
        month_text = "October"
    if month == 11:
        month_text = "November"
    if month == 12:
        month_text = "December"
    return month_text


def generate_gphotos_secret():
    credentials = {
        "installed": {
            "client_id": st.secrets["google_photos_credentials"]["client_id"],
            "project_id": st.secrets["google_photos_credentials"]["project_id"],
            "auth_uri": st.secrets["google_photos_credentials"]["auth_uri"],
            "token_uri": st.secrets["google_photos_credentials"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["google_photos_credentials"][
                "auth_provider_x509_cert_url"
            ],
            "client_secret": st.secrets["google_photos_credentials"]["client_secret"],
            "redirect_uris": st.secrets["google_photos_credentials"]["redirect_uris"],
        }
    }
    print(credentials)
    return credentials


class ImageSearchApp:
    def __init__(self):
        self.load_env_vars()
        self.init_pinecone()
        self.index_name = "photo-captions"
        self.new_index = pinecone.Index(self.index_name)
        # self.text_model = SentenceTransformer('clip-ViT-B-32')
        self.model = SentenceTransformer("clip-ViT-B-32")
        # self.google_photos_api = GooglePhotosApi()
        # self.google_photos_api.run_local_server()
        # self.google_photos_api.get_media_files(self.model)
        self.selection = None

    def load_env_vars(self):
        load_dotenv()
        self.api_key = os.getenv("PINECONE_API_KEY")
        if not self.api_key:
            print("Warning: No Pinecone API key found.")

    def init_pinecone(self):
        pinecone.init(api_key=self.api_key, environment="us-west1-gcp-free")
        self.index = pinecone.Index("cs191")

    def get_images(self):
        return self.google_photos_api.media_items_df["baseUrl"]

    def search_and_display(self, _query):
        years_filter = [2023]
        months_filter = [2]
        top_k = 30
        return self.query_images(_query, years_filter, months_filter, top_k)
        # first_pass = self.first_pass_search(query)
        # st.write(first_pass)
        # if not first_pass:
        #     query_vector = self.get_query_vector_clip(query)
        #     matches = self.search_images(query_vector)
        #     date_counts = self.aggregate_results(matches)
        #     return (self.generate_results(date_counts), query_vector)
        # else:
        #     date_counts = self.aggregate_results(first_pass)
        #     return (self.generate_results(date_counts), None)

    def query_images(self, query, years_filter, months_filter, top_k):
        # create the query vector
        xq = self.model.encode(query).tolist()

        # now query
        xc = self.new_index.query(
            xq,
            namespace=self.namespace,
            # filter={"year": {"$in": years_filter}, "month": {"$in": months_filter}},
            top_k=top_k,
            include_metadata=True,
        )

        img_urls = []
        meta_text = []

        media_items_df = self.google_photos_api.media_items_df
        print(xc)
        for i in range(0, top_k):
            img_id = xc["matches"][i]["id"]
            # print("got id", img_id)
            img_url = media_items_df.loc[
                media_items_df["id"] == img_id, "baseUrl"
            ].iloc[0]
            # print("got url", img_url)
            img_urls.append(img_url)
            img_year = media_items_df.loc[
                media_items_df["id"] == img_id, "metadata"
            ].iloc[0]["year"]
            # print("got year", img_year)
            img_month = media_items_df.loc[
                media_items_df["id"] == img_id, "metadata"
            ].iloc[0]["month"]
            # print("got month", img_month)
            img_text = month_name(img_month) + " of " + str(img_year)
            meta_text.append(img_text)

        # ipyplot.plot_images(img_urls, meta_text, img_width=250, show_url=False)
        return img_urls

    def first_pass_search(self, query):
        query_vector = self.get_query_vector_clip(query)
        query_matches = self.search_queries(query_vector)
        if not query_matches:
            return None
        # Filter matches with a score less than 0.9
        query_matches = [match for match in query_matches if match.score >= 0.9]
        return query_matches

    def get_query_vector_clip(self, text):
        query_emb = self.model.encode([text], show_progress_bar=False)
        return np.ndarray.tolist(query_emb)

    def search_queries(self, query_vector, top_k=10):
        query_response = self.index.query(
            namespace="query_embeddings",
            vector=query_vector,
            top_k=top_k,
            include_values=False,
            include_metadata=True,
        )
        return query_response.get("matches", [])

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

    def generate_results(self, date_counts):
        with sqlite3.connect(DB_PATH) as conn:
            results = []
            cursor = conn.cursor()
            for date, score in date_counts:
                image_paths = []
                cursor.execute(f"{GET_PHOTO_BY_DATE}", (date,))
                photos = cursor.fetchall()
                img_string = ""
                for photo in photos:
                    photo_path = os.path.join(FLASK_PATH, "converted_photos", photo[0])
                    image_paths.append(photo_path)
                    img_string += f"""
                    <img src="{photo_path}"
                        style="margin: 5px; height: 300px; object-fit: contain"
                        alt="Photo taken on {date}" >
                    """
                html_string = f"""
                <main style='width: 100%;'>
                    <div style='display: flex; justify-content: center; overflow-x: auto;'>
                        {img_string}
                    </div>
                </main>
                """
                results.append((date, html_string, image_paths))
            return results


st.set_page_config(layout="wide")
if "app" not in st.session_state:
    st.session_state.app = ImageSearchApp()

if "app_state" not in st.session_state:
    st.session_state["app_state"] = AUTH

if "search_journey" not in st.session_state:
    st.session_state["search_journey"] = []

app = st.session_state.app


def click_search_button(query):
    if st.session_state["app_state"] != AUTH:
        st.session_state["app_state"] = RESULTS
        st.session_state.search_journey.append(query)
    # Clear the text in the search bar
    # query = st.session_state["text_input_query"]
    # st.session_state["text_input_query"] = ""


# We update pinecone with queries that users have matched with an event
def click_date_button(date, query_vector, query):
    st.session_state["app_state"] = LEARNINGS
    query_id = uuid.uuid4()
    app.index.upsert(
        vectors=[
            {
                "id": str(query_id),
                "values": query_vector[0],
                "metadata": {"date": date, "query": query},
            }
        ],
        namespace="query_embeddings",
    )
    app.selection = date


def click_auth_button(email):
    app.google_photos_api = GooglePhotosApi(
        credentials=generate_gphotos_secret(), email=email
    )
    app.google_photos_api.run_local_server()
    app.namespace = email
    # app.google_photos_api.get_media_files(app.model)
    media_items_pickle_file = f"./data/media_items_{email}.pickle"
    if os.path.exists(media_items_pickle_file):
        app.google_photos_api.get_embed_and_upsert_photos(app.model, app.index_name)
        st.session_state["app_state"] = LEARNINGS
    else:
        st.session_state["app_state"] = DATE_SELECTION


def click_date_range_button(start_date, end_date):
    # Check if the date range is longer than 3 months
    if (end_date - start_date).days > 90:
        st.warning(
            "The date range is longer than 3 months. Please select a shorter range.",
            icon="⚠️",
        )
    else:
        if app.google_photos_api.get_embed_and_upsert_photos(
            app.model, app.index_name, start_date, end_date
        ):
            st.session_state["app_state"] = LEARNINGS
        else:
            st.warning("No images found for the specified date range.", icon="⚠️")


st.title("Storylines: Smart Image Search")
match st.session_state["app_state"]:
    case 0:
        st.header("Authentication")
        st.write(
            "Please Enter the email address associated with your Google Photos account"
        )
        email = st.text_input("Email")
        st.button("Authenticate", on_click=click_auth_button, args=[email])
    case 1:
        st.header("Date Selection")
        st.write("Please select a date range for your search")
        start_date = st.date_input("Start Date")
        end_date = st.date_input("End Date")
        st.button(
            "Confirm", on_click=click_date_range_button, args=[start_date, end_date]
        )
    case 2:
        query = st.text_input("Search till you find it!", key="text_input_query")
        st.button("Search", on_click=click_search_button, args=[query])
        # TODO: Cleaner gallery, organized by date
        st.header("Gallery")
        image_urls = app.get_images()
        controls = st.columns(3)
        with controls[0]:
            batch_size = st.select_slider("Batch size:", range(10, 110, 10))
        with controls[1]:
            row_size = st.select_slider("Row size:", range(1, 6), value=5)
        num_batches = ceil(len(image_urls) / batch_size)
        with controls[2]:
            page = st.selectbox("Page", range(1, num_batches + 1))

        batch = image_urls[(page - 1) * batch_size : page * batch_size]
        grid = st.columns(row_size)
        col = 0
        for image_url in batch:
            with grid[col]:
                st.image(image_url)
            col = (col + 1) % row_size
    case 3:
        st.header("Results")
        query = st.text_input("Search till you find it!", key="text_input_query")
        st.button("Search", on_click=click_search_button, args=[query])
        try:
            # results, query_vector = app.search_and_display(query)
            # for date, html_string, image_paths in results:
            #     if query_vector:
            #         st.button(
            #             date,
            #             on_click=click_date_button,
            #             args=[date, query_vector, query],
            #         )
            #     components.html(html_string, height=400)
            image_urls = app.search_and_display(query)
            cols = st.columns(len(image_urls))
            img = image_select(
                label="Select the image", images=image_urls, return_value="index"
            )
            # TODO: LEARN!
            print(img)
            # for col, image_path in zip(cols, image_urls):
            #     col.image(image_path, width=300)
            # for i, image_path in enumerate(image_paths):
            #     st.image(image_path, width=300)
            # st.image(image_paths[:10], width=100)

        except Exception as e:
            st.write("An error occurred during the search.")
            st.write(str(e))
    case _:
        st.write(st.session_state)

with st.sidebar:
    if st.session_state.search_journey != []:
        st.header("Search Journey So Far")
        for user_query in st.session_state.search_journey:
            st.write(user_query)
        if st.button("Clear Search Journey"):
            st.session_state.search_journey = []

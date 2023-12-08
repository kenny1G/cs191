import os
import pickle
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

LOGIN = 0
GOOGLE_AUTH = 1
DATE_SELECTION = 2
LEARNINGS = 3
RESULTS = 4


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
        "web": {
            "client_id": st.secrets["google_photos_credentials"]["client_id"],
            "project_id": st.secrets["google_photos_credentials"]["project_id"],
            "auth_uri": st.secrets["google_photos_credentials"]["auth_uri"],
            "token_uri": st.secrets["google_photos_credentials"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["google_photos_credentials"][
                "auth_provider_x509_cert_url"
            ],
            "client_secret": st.secrets["google_photos_credentials"]["client_secret"],
            "redirect_uris": st.secrets["google_photos_credentials"]["redirect_uris"],
            "javascript_origins": st.secrets["google_photos_credentials"][
                "javascript_origins"
            ],
        }
    }
    return credentials


class ImageSearchApp:
    def __init__(self):
        self.load_env_vars()
        self.init_pinecone()
        self.model = SentenceTransformer("clip-ViT-B-32")

    def load_env_vars(self):
        load_dotenv()
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.environment = os.getenv("PINECONE_ENVIRONMENT")
        print(self.environment)
        if not self.api_key:
            print("Warning: No Pinecone API key found.")

    def init_pinecone(self):
        pinecone.init(api_key=self.api_key, environment=self.environment)
        self.index_name = "photo-captions"
        self.index = pinecone.Index(self.index_name)

    def get_images(self):
        return self.google_photos_api.media_items_df["baseUrl"]

    def search_and_display(self, _query):
        years_filter = [2023]
        months_filter = [2]
        top_k = 30
        return self.query_images(_query, years_filter, months_filter, top_k)

    def query_images(self, query, years_filter, months_filter, top_k):
        # create the query vector
        xq = self.model.encode(query).tolist()

        # now query
        xc = self.index.query(
            xq,
            namespace=self.google_photos_api.uid,
            # filter={"year": {"$in": years_filter}, "month": {"$in": months_filter}},
            top_k=top_k,
            include_metadata=True,
        )

        img_urls = []
        meta_text = []

        media_items_df = self.google_photos_api.media_items_df
        print(media_items_df.head())
        # print(xc)
        for i in range(0, top_k):
            img_id = xc["matches"][i]["id"]
            print("got id", img_id)
            if img_id in media_items_df["id"].values:
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

if not os.path.exists('./credentials'):
    os.makedirs('./credentials')
if not os.path.exists('./data'):
    os.makedirs('./data')


state = None
uid = None
if "state" in st.experimental_get_query_params():
    state = st.experimental_get_query_params()["state"][0]
    uid_state_pickle_file = f"./credentials/uid_{state}.pickle"
    with open(uid_state_pickle_file, "rb") as uid_file:
        uid = pickle.load(uid_file)

st.set_page_config(layout="wide")
if "app" not in st.session_state:
    st.session_state.app = ImageSearchApp()
    # Case when google redirects back to the app
    if state is not None:
        st.session_state.app.uid = uid
        st.session_state.app.google_photos_api = GooglePhotosApi(
            credentials=generate_gphotos_secret(), _uid=uid
        )
        st.session_state.app.google_photos_api.init_auth()
        st.session_state.app.google_photos_api.get_embed_and_upsert_photos(
            st.session_state.app.model, st.session_state.app.index_name
        )
    print("NEW APP")

if "app_state" not in st.session_state:
    if state is not None:
        st.session_state["app_state"] = LEARNINGS
    else:
        st.session_state["app_state"] = LOGIN

if "search_journey" not in st.session_state:
    st.session_state["search_journey"] = []

app = st.session_state.app


def click_search_button(query):
    if st.session_state["app_state"] != GOOGLE_AUTH:
        st.session_state["app_state"] = RESULTS
        st.session_state.search_journey.append(query)
    # Clear the text in the search bar
    # query = st.session_state["text_input_query"]
    # st.session_state["text_input_query"] = ""


# Step 2: Embed and upsert photos
# We get here when user clicks the "Confirm" button on the date selection page
# We embed and upsert photos for the specified date range
def click_date_range_button(start_date, end_date, code=None):
    # Check if the date range is longer than 3 months
    if (end_date - start_date).days > 90:
        st.warning(
            "The date range is longer than 3 months. Please select a shorter range.",
            icon="⚠️",
        )
    else:
        if code is not None:
            app.google_photos_api.get_credentials(code)
        if app.google_photos_api.get_embed_and_upsert_photos(
            app.model, app.index_name, start_date, end_date
        ):
            st.session_state["app_state"] = LEARNINGS
        else:
            st.warning("No images found for the specified date range.", icon="⚠️")


# Step 1: Authenticate with Google Photos API
# We get here when user clicks the "LETS GO!" button which means
# this is their first time authenticating with the google photos API so we
# need to send them to date selection
# def click_auth_button(code):
#     app.google_photos_api.get_access_token(code)

#     media_items_pickle_file = f"./data/media_items_{app.uid}.pickle"
#     app.google_photos_api.get_embed_and_upsert_photos(app.model, app.index_name, st)
#     st.session_state["app_state"] = DATE_SELECTION


# Step 0: Login, if user has already authenticated before go to the LEARNINGS Step
# We always get here on app start
# If user has already authenticated before go to the LEARNINGS Step
# Otherwise take them through onboarding
# i.e google photos auth -> date selection -> pinecone embed and upsert
def click_login_button(uid):
    app.uid = uid
    app.google_photos_api = GooglePhotosApi(
        credentials=generate_gphotos_secret(), _uid=uid
    )
    app.google_photos_api.init_auth()
    state = app.google_photos_api.state
    with open(f"./credentials/uid_{state}.pickle", "wb") as uid_file:
        pickle.dump(uid, uid_file)

    if os.path.exists(f"./credentials/token_{uid}.pickle"):
        if os.path.exists(f"./data/media_items_{uid}.pickle"):
            app.google_photos_api.get_embed_and_upsert_photos(app.model, app.index_name)
            st.session_state["app_state"] = LEARNINGS
        else:
            st.session_state["app_state"] = DATE_SELECTION
    else:
        st.session_state["app_state"] = GOOGLE_AUTH


st.title("Storylines: Smart Image Search")
match st.session_state["app_state"]:
    case 0:
        if "state" in st.experimental_get_query_params():
            code = st.experimental_get_query_params()["code"][0]
            st.write("Google Photos API Authenticated!")
            st.header("Date Selection")
            st.write("Please select a date range for your search")
            start_date = st.date_input("Start Date")
            end_date = st.date_input("End Date")
            st.button(
                "Confirm",
                on_click=click_date_range_button,
                args=[start_date, end_date, code],
            )
        else:
            # User Onboarding
            # Link to login if we have no credentials
            st.write(
                "Please Enter a unique ID to login. This will be used to keep track of your session."
            )
            uid = st.text_input("UID")
            st.button("Login/SignUp", on_click=click_login_button, args=[uid])
    case 1:
        st.header("Authentication")
        st.write(
            f"""<h1>
            Please login using this <a target="_self"
            href="{app.google_photos_api.auth_url}">url</a></h1>""",
            unsafe_allow_html=True,
        )
    case 2:
        if "code" in st.experimental_get_query_params():
            code = st.experimental_get_query_params()["code"][0]
            app.google_photos_api.get_credentials(code)
        st.header("Date Selection")
        st.write("Please select a date range for your search")
        start_date = st.date_input("Start Date")
        end_date = st.date_input("End Date")
        st.button(
            "Confirm", on_click=click_date_range_button, args=[start_date, end_date]
        )
    case 3:
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
    case 4:
        st.header("Results")
        query = st.text_input("Search till you find it!", key="text_input_query")
        st.button("Search", on_click=click_search_button, args=[query])
        print(f"Searching for {query}")
        try:
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

import json
import requests
import pinecone
import itertools
import pandas as pd
from tqdm import tqdm
import streamlit as st
from datetime import timedelta
from google.auth.transport.requests import Request
import utils
from utils_modal import stub, ModalEmbedding

st.set_page_config(layout="wide")
if "credentials" not in st.session_state or "uid" not in st.session_state:
    st.warning(
        "You are not authenticated yet. Please enter your unique ID in Setup Demo to Authenticate."
    )
    st.stop()

credentials = st.session_state["credentials"]
uid = st.session_state["uid"]
# index name for image embeddings
im_index_name = "photo-captions"

if credentials.expired and credentials.refresh_token:
    credentials.refresh(Request())
    st.session_state["credentials"] = credentials
    st.info("Credentials refreshed")


pinecone_index = utils.get_pinecone_image_index()


def list_of_media_items(year, month, day, media_items_df):
    """
    Args:
        year, month, day: day for the filter of the API call
        self.media_items_df: existing data frame with all find media items so far
    Return:
        media_items_df: media items data frame extended by the articles found for the specified tag
        items_df: media items uploaded on specified date
    """

    items_list_df = pd.DataFrame()

    # create request for specified date
    response = get_response_from_medium_api(year, month, day)

    try:
        for item in response.json()["mediaItems"]:
            items_df = pd.DataFrame(item)
            items_df = items_df.rename(columns={"mediaMetadata": "creationTime"})
            items_df.set_index("creationTime")
            items_df = items_df[items_df.index == "creationTime"]

            # append the existing media_items data frame
            items_list_df = pd.concat([items_list_df, items_df])
            media_items_df = pd.concat([media_items_df, items_df])

    except:
        print(response.text)

    return (items_list_df, media_items_df)


def get_response_from_medium_api(year, month, day):
    url = "https://photoslibrary.googleapis.com/v1/mediaItems:search"
    payload = {
        "filters": {
            "dateFilter": {"dates": [{"day": day, "month": month, "year": year}]}
        }
    }
    headers = {
        "content-type": "application/json",
        "Authorization": "Bearer {}".format(credentials.token),
    }

    try:
        res = requests.request("POST", url, data=json.dumps(payload), headers=headers)
    except:
        print("URL: ", url)
        print("Payload: ", json.dumps(payload))
        print("Headers: ", headers)
        print("Request error")

    return res


@st.cache_data(ttl=3600)
def get_images_in_date_range(uid, sdate, edate):
    date_list = pd.date_range(sdate, edate - timedelta(days=1), freq="d")
    media_items_df = pd.DataFrame()
    for i, date in tqdm(enumerate(date_list), desc="Fetching Dates", total=len(date_list)):
        items_df, media_items_df = list_of_media_items(
            year=date.year,
            month=date.month,
            day=date.day,
            media_items_df=media_items_df,
        )
    if len(media_items_df) == 0:
        return None
    else:
        media_items_df.drop(
            ["productUrl", "mimeType", "filename"], axis=1, inplace=True
        )
        media_items_df["year"] = [
            int(x) for x in media_items_df["creationTime"].str[0:4].values
        ]
        media_items_df["month"] = [
            int(x) for x in media_items_df["creationTime"].str[5:7].values
        ]
        media_items_df["day"] = [
            int(x) for x in media_items_df["creationTime"].str[8:10].values
        ]
        media_items_df.reset_index(drop=True, inplace=True)
        return media_items_df


@st.cache_data
def embed_images_with_modal(media_items_df):
    with stub.run() as _:
        media_items_df = ModalEmbedding().generate.remote(media_items_df)
    return media_items_df


def chunks(iterable, batch_size=100):
    """A helper function to break an iterable into chunks of size batch_size."""
    it = iter(iterable)
    chunk = tuple(itertools.islice(it, batch_size))
    while chunk:
        yield chunk
        chunk = tuple(itertools.islice(it, batch_size))


def upsert_to_pinecone(namespace, media_items_df, is_caption=False):
    vector = media_items_df.caption_embeddings if is_caption else media_items_df.vector
    namespace = namespace + "_captions" if is_caption else namespace

    vectors = zip(
        media_items_df.id,
        vector,
        media_items_df.metadata,
    )

    pinecone_index.delete(delete_all=True, namespace=namespace)

    # Upsert data with 100 vectors per upsert request asynchronously
    # - Create pinecone.Index with pool_threads=30 (limits to 30 simultaneous requests)
    # - Pass async_req=True to index.upsert()
    with pinecone.Index(index_name=im_index_name, pool_threads=30) as index:
        # Send requests in parallel
        async_results = [
            index.upsert(vectors=ids_vectors_chunk, namespace=namespace, async_req=True)
            for ids_vectors_chunk in chunks(vectors, batch_size=100)
        ]
        # Wait for and retrieve responses (this raises in case of error)
        try:
            [async_result.get() for async_result in async_results]
        except Exception as e:
            print(f"Error upserting to Pinecone: {e}")
            st.warning("Error upserting to Pinecone Please try again.")
            st.stop()

    while pinecone_index.describe_index_stats()["total_vector_count"] == 0:
        print(index.describe_index_stats())


def click_date_range_button(start_date, end_date):
    # Check if the date range is longer than 3 months
    if (end_date - start_date).days > 93:
        st.warning(
            "The date range is longer than 3 months. Please select a shorter range.",
            icon="⚠️",
        )
        return

    media_items_df = None

    with st.spinner("Fetching Images"):
        media_items_df = get_images_in_date_range(uid, start_date, end_date)

    if media_items_df is None:
        st.warning("No images found in date range")
        return

    media_items_df["metadata"] = media_items_df.loc[
        :, ["id", "year", "month", "day"]
    ].to_dict("records")

    with st.spinner("Embedding Images"):
        media_items_df = embed_images_with_modal(media_items_df)

    with st.spinner("Upserting Images to Vector Store"):
        upsert_to_pinecone(uid, media_items_df)

    st.info(f"Indexed {len(media_items_df)} images from {start_date} to {end_date} ")

    st.session_state["media_items_df"] = media_items_df


def ui_date_form():
    st.write("Select a date range for the images to index for search")
    start_date = st.date_input("Start Date")
    end_date = st.date_input("End Date")
    st.button("Confirm", on_click=click_date_range_button, args=[start_date, end_date])

st.title("Date Selection")
col1, col2 = st.columns([2, 1])
if "media_items_df" in st.session_state:
    with col1:
        st.header("Indexed Images")
        st.caption(
            "To index from a different date range, please select a new date range below."
        )
        st.dataframe(st.session_state["media_items_df"])
    with col2:
        ui_date_form()
else:
    ui_date_form()
import os
import json
import requests
import pinecone
import itertools
import pandas as pd
from PIL import Image
import streamlit as st
from dotenv import load_dotenv
from datetime import date, timedelta, datetime
from google.auth.transport.requests import Request
from sentence_transformers import SentenceTransformer

if "credentials" not in st.session_state or "uid" not in st.session_state:
    st.warning(
        "You are not authenticated yet. Please go to Setup Demo to Authenticate."
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
    return pinecone.Index("im_index_name")


clip_model = load_model()
pinecone_index = get_pinecone_image_index()


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


@st.cache_data
def get_images_in_date_range(uid, sdate, edate):
    date_list = pd.date_range(sdate, edate - timedelta(days=1), freq="d")
    media_items_df = pd.DataFrame()
    print("get_image_in_date_range, listing media items")
    for date in date_list:
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
def get_image(url):
    try:
        return Image.open(requests.get(url, stream=True).raw)
    except Exception as e:
        print(f"Error opening image {url}, error: {e}")
        return None


# @st.cache_data
def load_images_into_memory(media_items_df):
    url_list = media_items_df["baseUrl"].values.tolist()
    images = []
    image_dict = {}
    i = 0
    for j, url in enumerate(url_list):
        image = get_image(url)
        # Hacky way to deal with images that error out
        while image is None:
            i += 1
            image = get_image(url_list[i])

        images.append(image)
        image_dict[media_items_df["id"].values[j]] = image
    return images, image_dict

@st.cache_data
def embed_images(_images, uid, sdate, edate):
    embeddings = clip_model.encode(_images)
    img_embeddings = []
    for embedding in embeddings:
        img_embeddings.append(embedding.tolist())
    return img_embeddings

def chunks(iterable, batch_size=100):
    """A helper function to break an iterable into chunks of size batch_size."""
    it = iter(iterable)
    chunk = tuple(itertools.islice(it, batch_size))
    while chunk:
        yield chunk
        chunk = tuple(itertools.islice(it, batch_size))

def upsert_to_pinecone(namespace, media_items_df):
    vectors = zip(
        media_items_df.id,
        media_items_df.vector,
        media_items_df.metadata,
    )

    # Upsert data with 100 vectors per upsert request asynchronously
    # - Create pinecone.Index with pool_threads=30 (limits to 30 simultaneous requests)
    # - Pass async_req=True to index.upsert()
    with pinecone.Index(index_name=im_index_name, pool_threads=30) as index:
        # Send requests in parallel
        async_results = [
            index.upsert(
                vectors=ids_vectors_chunk, namespace=namespace, async_req=True
            )
            for ids_vectors_chunk in chunks(vectors, batch_size=100)
        ]
        # Wait for and retrieve responses (this raises in case of error)
        try:
            [async_result.get() for async_result in async_results]
        except Exception as e:
            print(f"Error upserting to Pinecone: {e}")
            st.warning("Error upserting to Pinecone Please try again.")
            st.stop()

    while index.describe_index_stats()["total_vector_count"] == 0:
        print(index.describe_index_stats())

def click_date_range_button(start_date, end_date):
    print("Fetching Images")
    media_items_df = get_images_in_date_range(uid, start_date, end_date)
    if media_items_df is None:
        st.warning("No images found in date range")
        return

    print("Loading Images")
    images, image_dict = load_images_into_memory(media_items_df)

    print("Embedding Images")
    embeddings = embed_images(images, uid, start_date, end_date)
    media_items_df["vector"] = embeddings
    media_items_df["metadata"] = media_items_df.loc[
        :, ["year", "month", "day"]
    ].to_dict("records")
    print(image_dict)

    print("Upserting to Pinecone")
    upsert_to_pinecone(uid, media_items_df)
    st.info(f"Upserted {len(media_items_df)} images from {start_date} to {end_date} ")

    st.session_state["media_items_df"] = media_items_df
    st.session_state["image_dict"] = image_dict

st.header("Date Selection")
st.write("Please select a date range for the images to include in your search")
start_date = st.date_input("Start Date")
end_date = st.date_input("End Date")
st.button("Confirm", on_click=click_date_range_button, args=[start_date, end_date])

from dotenv import load_dotenv
import os
import pinecone
from sentence_transformers import SentenceTransformer
import streamlit as st
from streamlit_image_select import image_select

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


if "credentials" not in st.session_state or "uid" not in st.session_state:
    st.warning(
        "You are not authenticated yet. Please enter your unique ID in Setup Demo to Authenticate."
    )
    st.stop()

if "image_dict" not in st.session_state or "media_items_df" not in st.session_state:
    st.warning(
        "No media items in session, Please go to the Upsert Images page to upload images."
    )
    st.stop()

if "showing_results" not in st.session_state:
    st.session_state["showing_results"] = False

if "search_journey" not in st.session_state:
    st.session_state["search_journey"] = []

st.set_page_config(layout="wide")
clip_model = load_model()
# images = st.session_state["images"]
id_to_image = st.session_state["image_dict"]
media_items_df = st.session_state["media_items_df"]
uid = st.session_state["uid"]
row_size = 5
pinecone_index = get_pinecone_image_index()
top_k = 10



def click_search_button(query):
    if query == "":
        st.warning("Please enter a query")
        st.session_state.showing_results = False
        return
    st.session_state.search_journey.append(query)
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

    results = []

    print(media_items_df.head())
    # print(xc)
    i = 0
    while i < top_k:
        img_id = xc["matches"][i]["id"]
        # print("got id", img_id)
        if img_id in media_items_df["id"].values:
            image = id_to_image[img_id]
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

            results.append((image, img_text))
            i += 1
    # print (results)
    return results


st.header("Gallery")
query = st.text_input("Search till you find it!", key="text_input_query")
st.button("Search", on_click=click_search_button, args=[query])
grid = st.columns(row_size)
col = 0

if st.session_state.showing_results:
    image_results = query_images(query)
    print(f"Got {len(image_results)} results")
    cols = st.columns(len(image_results))
    images = [x[0] for x in image_results]
    # images.insert(0, 'dummy_image')  # Inserting dummy image at index 0
    img = image_select(
        label="Select the image", images=images, return_value="index"
    )
    # TODO: LEARN!
    if img != 0:
        print(img)
else:
    for image in id_to_image.values():
        with grid[col]:
            st.image(image)
        col = (col + 1) % row_size



with st.sidebar:
    if st.session_state.search_journey != []:
        st.header("Search Journey So Far")
        for user_query in st.session_state.search_journey:
            st.write(user_query)
        if st.button("Clear Search Journey"):
            st.session_state.search_journey = []
            st.session_state["showing_results"] = False
            st.rerun()

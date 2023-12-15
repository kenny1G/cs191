import os
from dotenv import load_dotenv
import streamlit as st

from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

PROD_AUTHORIZED_UIDS = ["kenny", "nicki", "jay"]
@st.cache_resource
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
# @st.cache_resource
def load_flow():
    flow = Flow.from_client_config(
        generate_gphotos_secret(), ["https://www.googleapis.com/auth/photoslibrary"]
    )
    return flow

flow = load_flow()
load_dotenv()
is_prod = os.getenv("IS_PROD", False)

@st.cache_data
def get_credentials(uid):
    print(f"Getting credentials for {uid}")
    code = st.experimental_get_query_params()["code"][0]
    redirect_uri = st.secrets["google_photos_credentials"]["redirect_uris"][0]
    redirect_uri += f"Setup_Demo?uid={uid}"
    flow.redirect_uri = redirect_uri
    flow.fetch_token(code=code)
    return flow.credentials

def click_login_button(uid):
    if is_prod and uid not in PROD_AUTHORIZED_UIDS:
        st.error("That UID is not authorized to use this demo, Please contact the developer to be added to the allow list.")
        return
    try:
        # Reached when user logs in and we already have a token so dont need
        # to go through google
        credentials = get_credentials(uid)
        st.session_state["credentials"] = credentials
        st.session_state["uid"] = uid
        st.header("You are successfully authenticated against the Google Photos API!")
        st.write("Go to other parts of the demo to search or upload images.")
        st.write("You can also reauth as a different user by entering a different UID.")
        # st.write(credentials)
    except KeyError:
        redirect_uri = st.secrets["google_photos_credentials"]["redirect_uris"][0]
        redirect_uri += f"Setup_Demo?uid={uid}"
        flow.redirect_uri = redirect_uri
        auth_url, state = flow.authorization_url()
        st.write(
            f"""<h1>
            Please login using this <a target="_blank"
            href="{auth_url}">url</a></h1>""",
            unsafe_allow_html=True,
        )
        st.session_state["authenticating"] = True


if "authenticating" not in st.session_state:
    st.session_state["authenticating"] = False

authenticating = st.session_state["authenticating"]
if not authenticating:
    if "code" not in st.experimental_get_query_params():
        if "uid" in st.session_state:
            # User is already logged in
            st.header("You are successfully authenticated against the Google Photos API!")
            st.write("Go to other parts of the demo to search or upload images.")
            st.write("You can also reauth as a different user by entering a different UID.")
            uid = st.text_input("UID")
            st.button("Login", on_click=click_login_button, args=[uid])
        else:
            # First entry, ask for user id
            uid = st.text_input("UID")
            st.button("Login", on_click=click_login_button, args=[uid])
    else:
        # Reached when we are redirected back from google
        code = st.experimental_get_query_params()["code"][0]
        uid = st.experimental_get_query_params()["uid"][0]
        credentials = get_credentials(uid)
        st.session_state["uid"] = uid
        st.session_state["credentials"] = credentials
        st.header("You are successfully authenticated against the Google Photos API!")
        st.write("Go to other parts of the demo to search or upload images.")
        st.write("You can also reauth as a different user by entering a different UID.")
        uid = st.text_input("UID")
        st.button("Login", on_click=click_login_button, args=[uid])

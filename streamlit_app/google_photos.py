import pickle
import os
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build

# from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
import json
import pandas as pd
from datetime import date, timedelta, datetime
import requests
from PIL import Image


class GooglePhotosApi:
    def __init__(
        self,
        api_name="photoslibrary",
        client_secret_file=r"./credentials/client_secret.json",
        api_version="v1",
        scopes=["https://www.googleapis.com/auth/photoslibrary"],
    ):
        """
        Args:
            client_secret_file: string, location where the requested credentials are saved
            api_version: string, the version of the service
            api_name: string, name of the api e.g."docs","photoslibrary",...
            api_version: version of the api

        Return:
            service:
        """

        self.api_name = api_name
        self.client_secret_file = client_secret_file
        self.api_version = api_version
        self.scopes = scopes
        self.cred_pickle_file = (
            f"./credentials/token_{self.api_name}_{self.api_version}.pickle"
        )

        self.cred = None

    def run_local_server(self):
        # is checking if there is already a pickle file with relevant credentials
        if os.path.exists(self.cred_pickle_file):
            with open(self.cred_pickle_file, "rb") as token:
                self.cred = pickle.load(token)

        # if there is no pickle file with stored credentials, create one using google_auth_oauthlib.flow
        if not self.cred or not self.cred.valid:
            if self.cred and self.cred.expired and self.cred.refresh_token:
                self.cred.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secret_file, self.scopes
                )
                self.cred = flow.run_local_server()

            with open(self.cred_pickle_file, "wb") as token:
                pickle.dump(self.cred, token)


    # Populate class' media_items_df with Photos in the date range specified
    #
    # Fields of note in the data frame:
    # **id** Immutable
    # **baseUrl** Base URLs within the Google Photos Library API allow
    #  you to access the bytes of the media items. They are valid for 60 minutes.
    # (https://developers.google.com/photos/library/guides/access-media-items)
    def get_media_files(self, img_model, sdate=date(2023, 2, 1), edate=date(2023, 4, 1)):
        # create a list with all dates between start date and end date
        # edate = date.today()
        date_list = pd.date_range(sdate, edate - timedelta(days=1), freq="d")

        self.media_items_df = pd.DataFrame()

        self.media_items_pickle_file = (
            f"./data/media_items_{sdate}_to_{edate}.pickle"
        )
        if os.path.exists(self.media_items_pickle_file):
            with open(self.media_items_pickle_file, "rb") as items_df:
                self.media_items_df = pickle.load(items_df)
            print(f"{len(self.media_items_df)} images sourced from pickle file")
        else:
            for date in date_list:
                # get a list with all media items for specified date (year, month, day)
                items_df, self.media_items_df = self.list_of_media_items(
                    year=date.year,
                    month=date.month,
                    day=date.day
                )

            self.media_items_df.drop(["productUrl", "mimeType", "filename"], axis=1, inplace=True)
            self.media_items_df["year"] = [
                int(x) for x in self.media_items_df["creationTime"].str[0:4].values
            ]
            self.media_items_df["month"] = [
                int(x) for x in self.media_items_df["creationTime"].str[5:7].values
            ]
            self.media_items_df["day"] = [
                int(x) for x in self.media_items_df["creationTime"].str[8:10].values
            ]
            self.media_items_df.reset_index(drop=True, inplace=True)

            url_list = self.media_items_df['baseUrl'].values.tolist()
            images = []
            errored = []
            images_pickle_file = f"./data/images_{sdate}_to_{edate}.pickle"
            if os.path.exists(images_pickle_file):
                with open(images_pickle_file, "rb") as images_file:
                    images = pickle.load(images_file)
                print(f"{len(images)} images sourced from pickle file")
            else:
                for i in url_list:
                    try:
                        images.append(Image.open(requests.get(i, stream=True).raw))
                    except:
                        images.append(Image.open(requests.get(url_list[0], stream=True).raw))
                        errored.append(i)
                        print('Image error')
                with open(images_pickle_file, "wb") as images_file:
                    pickle.dump(images, images_file)

            embeddings = img_model.encode(images)
            img_embeddings = []
            for i, embedding in enumerate(embeddings):
                img_embeddings.append(embedding.tolist())

            self.media_items_df['vector'] = img_embeddings
            self.media_items_df['metadata'] = self.media_items_df.loc[:,['year','month','day']].to_dict('records')
            self.media_items_df.head()

            with open(self.media_items_pickle_file, "wb") as items_df:
                pickle.dump(self.media_items_df, items_df)

            print(f"{len(self.media_items_df)} images fetched from Google Photos API")

    def list_of_media_items(self, year, month, day):
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
        response = self.get_response_from_medium_api(year, month, day)

        try:
            for item in response.json()["mediaItems"]:
                items_df = pd.DataFrame(item)
                items_df = items_df.rename(columns={"mediaMetadata": "creationTime"})
                items_df.set_index("creationTime")
                items_df = items_df[items_df.index == "creationTime"]

                # append the existing media_items data frame
                items_list_df = pd.concat([items_list_df, items_df])
                self.media_items_df = pd.concat([self.media_items_df, items_df])

        except:
            print(response.text)

        return (items_list_df, self.media_items_df)

    def get_response_from_medium_api(self, year, month, day):
        url = "https://photoslibrary.googleapis.com/v1/mediaItems:search"
        payload = {
            "filters": {
                "dateFilter": {"dates": [{"day": day, "month": month, "year": year}]}
            }
        }
        headers = {
            "content-type": "application/json",
            "Authorization": "Bearer {}".format(self.cred.token),
        }

        try:
            res = requests.request("POST", url, data=json.dumps(payload), headers=headers)
        except:
            print("Request error")

        return res





    # Load images into memory, returns list of images loaded
    def load_images_in_mem(self):

        url_list = self.media_items_df['baseUrl'].values.tolist()
        self.images = []
        errored = []
        for i in url_list:
            try:
                self.images.append(Image.open(requests.get(i, stream=True).raw))
            except:
                self.images.append(Image.open(requests.get(url_list[0], stream=True).raw))
                errored.append(i)
                print('Image error')
        # print(f"{len(images)} images loaded into memory")
        # print(f"{len(errored)} images failed to load")
        print(errored)


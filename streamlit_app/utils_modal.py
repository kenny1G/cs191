from modal import Stub, Image, method

stub = Stub()

def download_models():
    # Caches the model inside the Modal image, so subsequent cold starts are faster.
    from sentence_transformers import SentenceTransformer

    SentenceTransformer("sentence-transformers/clip-ViT-B-32")

container_image = (
    Image.debian_slim()
    .pip_install("sentence-transformers")
    .pip_install("pandas")
    .run_function(download_models)
)

@stub.cls(
    image=container_image,
)
class ModalEmbedding:
    def __enter__(self):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer("sentence-transformers/clip-ViT-B-32")

    @method()
    def generate(self, media_items_df):
        from tqdm import tqdm
        import pandas as pd

        # Generate embeddings for each image
        # with open(f'/root/instance/embeddings.json', 'r') as json_file:
        embeddings = []
        url_list = media_items_df["baseUrl"].values.tolist()
        for url in tqdm(url_list, desc="Generating embeddings"):
            from PIL import Image
            import requests

            try:
                image = Image.open(requests.get(url, stream=True).raw)
            except Exception as e:
                print(f"Error opening image {url}, error: {e}")
                image = None

            img_emb = self.model.encode(image).tolist()
            embeddings.append(img_emb)
        media_items_df["vector"] = embeddings

        return media_items_df

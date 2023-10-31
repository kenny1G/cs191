import os
from PIL import Image


def create_thumbnails(source_dir, target_dir, thumbnail_size=200):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    for root, dirs, files in os.walk(source_dir):
        for filename in files:
            if filename.endswith(".jpg") or filename.endswith(".png"):
                source_path = os.path.join(root, filename)
                target_path = os.path.join(
                    target_dir, os.path.relpath(source_path, source_dir)
                )

                # Skip files that already exist in the target directory
                if os.path.exists(target_path):
                    continue

                # Create directories in target path if they don't exist
                os.makedirs(os.path.dirname(target_path), exist_ok=True)

                try:
                    img = Image.open(source_path)
                    width, height = img.size
                    aspect_ratio = width / height
                    new_size = (thumbnail_size, int(thumbnail_size / aspect_ratio))

                    img.thumbnail(new_size)
                    img.save(target_path)
                except OSError:
                    print(f"Error: Broken data stream when reading image file {source_path}. Skipping this file.")


create_thumbnails("misc/users_1_40", "misc/users_1_40_thumbnails")

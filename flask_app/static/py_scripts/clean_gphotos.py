import os
import sys
from PIL import Image
from pillow_heif import register_heif_opener
import sqlite3
import uuid

from tqdm import tqdm


class DatabaseEntry:
    def __init__(
        self,
        primary_key,
        file_path,
        file,
        new_file_path,
        width,
        height,
    ):
        self.primary_key = primary_key
        self.file_path = file_path
        self.file = file
        self.new_file_path = new_file_path
        self.width = width
        self.height = height


def create_database():
    # Connect to or create a database file
    conn = sqlite3.connect("photos.db")

    # Create a cursor object to execute SQL commands
    c = conn.cursor()

    # SQL command to create a table with the specified schema, only if it doesn't already exist
    c.execute(
        """
              CREATE TABLE IF NOT EXISTS photos (
              PhotoID INTEGER PRIMARY KEY NOT NULL,
              FilePath TEXT NOT NULL,
              FileName TEXT NOT NULL,
              FileSize INTEGER NOT NULL,
              ThumbnailPath TEXT NOT NULL,
              DateTaken DATETIME,
              DateUploaded DATETIME DEFAULT CURRENT_TIMESTAMP,
              ExifData TEXT,
              PETACategory TEXT,
              UserTag TEXT,
              GeoData TEXT,
              ImageWidth INTEGER,
              ImageHeight INTEGER,
              ThumbnailWidth INTEGER,
              ThumbnailHeight INTEGER
              )
              """
    )
    # Commit the changes and close the connection
    conn.commit()
    conn.close()


def generate_database_entry(file_path, output_directory):
    register_heif_opener()

    # Only process image files
    if not (file_path.lower().endswith(".jpg") or file_path.lower().endswith(".heic")):
        return None

    # Construct new file path
    file_name = os.path.basename(file_path)

    try:
        with Image.open(file_path) as img:
            # Resize the image while maintaining the aspect ratio
            width, height = img.size
            # Generate a primary key
            primary_key = hash(file_path)

            return DatabaseEntry(
                primary_key,
                file_path,
                file_name,
                width,
                height,
            )

    except OSError:
        print(
            f"Error: OSError when reading image file {file_path}. Skipping this file."
        )
        return None


def process_image(file_path, output_directory):
    register_heif_opener()

    # Only process image files
    if not (file_path.lower().endswith(".jpg") or file_path.lower().endswith(".heic")):
        return None

    # Construct new file path
    new_file_name = os.path.splitext(os.path.basename(file_path))[0] + ".jpg"
    new_file_path = os.path.join(output_directory, new_file_name)

    # Check if the image already exists in the output directory
    if not os.path.exists(new_file_path):
        try:
            with Image.open(file_path) as img:
                # Resize the image while maintaining the aspect ratio
                width, height = img.size
                new_width = 300
                new_height = int((new_width / width) * height)
                img_resized = img.resize((new_width, new_height))

                # Save the processed image
                img_resized.save(new_file_path, "JPEG")
                # Generate a primary key
                primary_key = hash(new_file_path)

                return DatabaseEntry(
                    primary_key,
                    file_path,
                    new_file_name,
                    new_file_path,
                    new_width,
                    new_height,
                )

        except OSError:
            print(
                f"Error: OSError when reading image file {file_path}. Skipping this file."
            )
            return None


def update_database(entry):
    # Connect to the database
    with sqlite3.connect("photos.db") as conn:
        c = conn.cursor()
        # Upsert data into the database
        c.execute(
            """
                  INSERT INTO photos (PhotoID, FilePath, FileName, FileSize, ThumbnailPath, ImageWidth, ImageHeight, ThumbnailWidth, ThumbnailHeight)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                  ON CONFLICT(PhotoID) DO UPDATE SET
                  FilePath = excluded.FilePath,
                  FileName = excluded.FileName,
                  FileSize = excluded.FileSize,
                  ThumbnailPath = excluded.ThumbnailPath,
                  ImageWidth = excluded.ImageWidth,
                  ImageHeight = excluded.ImageHeight,
                  """,
            (
                entry.primary_key,
                entry.file_path,
                entry.file,
                os.path.getsize(entry.file_path),
                os.path.abspath(entry.new_file_path),
                entry.width,
                entry.height,
            ),
        )
        conn.commit()


def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <path_to_directory>")
        sys.exit(1)

    root_directory = sys.argv[1]

    if not os.path.isdir(root_directory):
        print(f"Error: The path {root_directory} does not exist or is not a directory")
        sys.exit(1)

    create_database()

    # ensure the output directory exists
    output_directory = "data_cleaned"
    os.makedirs(output_directory, exist_ok=True)

    # Get the total number of files for the progress bar
    total_files = sum([len(files) for r, d, files in os.walk(root_directory)])
    print(total_files)
    progress_bar = tqdm(total=total_files, desc="Processing images", unit="image")

    for subdir, _, files in os.walk(root_directory):
        for file in files:
            file_path = os.path.join(subdir, file)
            entry = process_image(file_path, output_directory)
            if entry is not None:
                update_database(entry)
            # Update the progress bar
            progress_bar.update()

    # Close the progress bar
    progress_bar.close()


if __name__ == "__main__":
    main()

import argparse
import os
from PIL import Image
import sqlite3
import sys

from tqdm import tqdm
DATE_TIME_EXIF_TAG = 0x9003
# ----------------------------------------------------------------------
# Parameters
parser = argparse.ArgumentParser(description="Storylines DB Populator")
parser.add_argument("--album_path", type=str)
parser.add_argument("--db_path", type=str, default="photos.db")


class DatabaseEntry:
    def __init__(self, file_path):
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                self.primary_key = hash(file_path)
                self.file_path = os.path.abspath(file_path)
                self.file_name = os.path.basename(file_path)
                self.file_size = os.path.getsize(file_path)
                self.width = width
                self.height = height
                self.taken_date = img._getexif().get(DATE_TIME_EXIF_TAG)
                # self.exif_data = str(img._getexif())  # Fetching the EXIF data
                self.peta_label = ""
                self.user_label = ""
        except AttributeError:
            raise ValueError(f"Image {file_path} does not have EXIF data")


def create_database(conn):
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
              ImageWidth INTEGER,
              ImageHeight INTEGER,
              DateTaken DATETIME,
              ExifData TEXT,
              PETALabel TEXT,
              UserLabel TEXT
              )
              """
    )
    # Commit the changes and close the connection
    conn.commit()


def update_database(conn, entry):
    c = conn.cursor()
    # Upsert data into the database
    c.execute(
        """
                INSERT OR REPLACE INTO photos (PhotoID, FilePath, FileName, FileSize, ImageWidth, ImageHeight, DateTaken, PETALabel, UserLabel)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
        (
            entry.primary_key,
            entry.file_path,
            entry.file_name,
            entry.file_size,
            entry.width,
            entry.height,
            entry.taken_date,
            # entry.exif_data,
            entry.peta_label,
            entry.user_label,
        ),
    )
    conn.commit()


def main():
    args = parser.parse_args()
    # Connect to or create a database file
    with sqlite3.connect(args.db_path) as conn:

        root_directory = args.album_path

        if not os.path.isdir(root_directory):
            print(f"Error: The path {root_directory} does not exist or is not a directory")
            sys.exit(1)

        create_database(conn)
        # Get the total number of files for the progress bar
        total_files = sum([len(files) for r, d, files in os.walk(root_directory)])
        progress_bar = tqdm(total=total_files, desc="Processing images", unit="image")

        failed_files = []
        for subdir, _, files in os.walk(root_directory):
            for file in files:
                file_path = os.path.join(subdir, file)
                # Only process image files
                sRet = file_path.lower()
                if sRet.endswith(".jpg") or sRet.endswith(".heic") or sRet.endswith(".png"):
                    db_entry = DatabaseEntry(file_path)
                    update_database(conn, db_entry)
                    # try:
                    # except ValueError as ve:
                    #     failed_files.append((file_path, str(ve)))
                    # except Exception as e:
                    #     print(e)
                    #     failed_files.append((file_path, str(e)))
                # Update the progress bar
                progress_bar.update()

        # Close the progress bar
        progress_bar.close()
        for file, error in failed_files:
            print(f"{file}: {error}")
        print(f"Failed to process {len(failed_files)} files:")


if __name__ == "__main__":
    main()

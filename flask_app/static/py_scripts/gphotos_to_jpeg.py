import argparse
import os
import sys
from PIL import Image
from pillow_heif import register_heif_opener

from tqdm import tqdm
# ----------------------------------------------------------------------
# Parameters
parser = argparse.ArgumentParser(description='Storylines Cleanser')
parser.add_argument('--album_path', type=str)

def process_image(file_path, output_directory, failed_files = []):

    # Construct new file path
    new_file_name = os.path.splitext(os.path.basename(file_path))[0] + ".jpg"
    new_file_path = os.path.join(output_directory, new_file_name)

    # Check if the image already exists in the output directory
    if not os.path.exists(new_file_path):
        try:
            with Image.open(file_path) as img:
                # Resize the image while maintaining the aspect ratio
                width, height = img.size
                new_width = 1080
                new_height = int((new_width / width) * height)
                img_resized = img.resize((new_width, new_height))

                # Save the processed image
                img_resized.save(new_file_path, "JPEG")
        except OSError:
            failed_files.append(file_path)
            return None


def main():
    args = parser.parse_args()

    root_directory = args.album_path

    if not os.path.isdir(root_directory):
        print(f"Error: The path {root_directory} does not exist or is not a directory")
        sys.exit(1)

    output_directory = "../converted_photos"
    os.makedirs(output_directory, exist_ok=True)

    # Get the total number of files for the progress bar
    total_files = sum([len(files) for r, d, files in os.walk(root_directory)])
    progress_bar = tqdm(total=total_files, desc="Processing images", unit="image")

    register_heif_opener()
    failed_files = []
    for subdir, _, files in os.walk(root_directory):
        for file in files:
            file_path = os.path.join(subdir, file)
            # Only process image files
            sRet = file_path.lower()
            if (sRet.endswith(".jpg") or sRet.endswith(".heic") or sRet.endswith(".png")):
                process_image(file_path, output_directory, failed_files)
            # Update the progress bar
            progress_bar.update()

    # Close the progress bar
    progress_bar.close()
    print("Failed to process the following files:")
    for file in failed_files:
        print(file)
if __name__ == "__main__":
    main()
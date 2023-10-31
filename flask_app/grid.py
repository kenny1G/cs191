import sys
import functools

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
    current_app
)

bp = Blueprint("grid", __name__)
database_path = current_app.config['DATABASE']
print(database_path)


@bp.route("/", methods=("GET", "POST"))
def index():
    return render_template("index.html")


import sqlite3


@bp.route("/images", methods=["GET"])
def images():
    # Connect to the database
    conn = sqlite3.connect(database_path)
    c = conn.cursor()

    # Execute the query to fetch all photos
    c.execute("SELECT * FROM photos")
    rows = c.fetchall()

    # Close the connection
    conn.close()

    # Prepare the images data according to the new database definition
    images = []
    for row in rows:
        file_name = row[2]
        image_width = row[5]
        image_height = row[6]
        # images.html expects (name, width, height)
        images.append((file_name, image_width, image_height))

    return render_template("images.html", images=images)

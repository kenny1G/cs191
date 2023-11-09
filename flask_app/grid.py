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

    # Execute the query to fetch all photos taken in 2023 where DateTaken is not null and order them by taken_date
    c.execute("SELECT * FROM copied WHERE DateTaken IS NOT NULL AND SUBSTR(DateTaken, 1, 4) = '2023' ORDER BY DateTaken")
    rows = c.fetchall()

    # Prepare the images data according to the new database definition
    images = []
    current_day = None
    for row in rows:
        file_name = row[2]
        image_width = row[4]
        image_height = row[5]
        taken_date = row[6]
        # Convert SQL date time to just date
        taken_date = taken_date.split(' ')[0]
        # images.html expects (day, [(file_name, width, height), ...])
        if current_day != taken_date:
            current_day = taken_date
            images.append((current_day, []))
        images[-1][1].append((file_name, image_width, image_height))

    # Fetch the tags associated with each day
    c.execute("SELECT dates_have_tags.date, PETA_tags.tag FROM dates_have_tags JOIN PETA_tags ON dates_have_tags.tag_id = PETA_tags.id ORDER BY dates_have_tags.date")
    tag_rows = c.fetchall()

    # Prepare the tags data
    tags = {}
    for row in tag_rows:
        date = row[0]
        tag = row[1]
        if date not in tags:
            tags[date] = []
        tags[date].append(tag)

    # Close the connection
    conn.close()

    return render_template("images.html", images=images, tags=tags)

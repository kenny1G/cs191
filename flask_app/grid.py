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

    # Execute the query to fetch all photos where DateTaken is not null and order them by taken_date
    c.execute("SELECT * FROM photos WHERE DateTaken IS NOT NULL ORDER BY DateTaken")
    rows = c.fetchall()

    # Close the connection
    conn.close()

    # Prepare the images data according to the new database definition
    print(rows[32])
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

    return render_template("images.html", images=images)

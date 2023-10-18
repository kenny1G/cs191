import sys
import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from . import todo as _todo

bp = Blueprint('grid', __name__)

@bp.route('/', methods=('GET', 'POST'))
def index():
    return render_template('index.html')

@bp.route("/images", methods=["GET"])
def images():
    images = []
    import os
    from PIL import Image
    print(os.getcwd(), file=sys.stderr)
    directory = 'flask_app/static/photos/users_1_40_thumbnails'
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith(".jpg") or filename.endswith(".png"):
                with Image.open(os.path.join(root, filename)) as img:
                    width, height = img.size
                    images.append((os.path.join(root, filename).replace(directory + '/', ''), width, height))
    print(images[0], len(images))
    return render_template("images.html", images = images)
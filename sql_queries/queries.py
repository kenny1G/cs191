# queries.py
GET_ALL_PHOTOS = "SELECT * FROM photos"

GET_2023_PHOTOS = """
SELECT DISTINCT FileName, ImageWidth, ImageHeight, DateTaken
FROM copied
WHERE DateTaken IS NOT NULL
AND SUBSTR(DateTaken, 1, 4) = '2023'
ORDER BY DateTaken
"""

GET_DATE_TAGS = """
SELECT dates_have_tags.date, PETA_tags.tag
FROM dates_have_tags
JOIN PETA_tags ON dates_have_tags.tag_id = PETA_tags.id
ORDER BY dates_have_tags.date
"""

CREATE_PHOTOS_TABLE = """
CREATE TABLE IF NOT EXISTS photos (
PhotoID TEXT PRIMARY KEY NOT NULL,
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

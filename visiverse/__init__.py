import base64
from logging.config import dictConfig
from traceback import format_exception
from uuid import UUID, uuid4

# Quart
from quart import Quart
from quart import jsonify
from quart import render_template
from quart import send_file
from quart.utils import run_sync
from werkzeug.exceptions import HTTPException

# Custom config class
from visiverse.config import load_config
# Custom database and types
from visiverse.database import Database
from visiverse.database import MediaType
from visiverse.database import Media
from visiverse.database import Person
from visiverse.database import Organization
from visiverse.database import Tag
# Custom FFmpeg wrapper
from visiverse.transcoder import Transcoder
from visiverse.transcoder import get_video_duration


app = Quart(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

config_path = "config.cfg"
config = load_config(config_path)

# logging config
# dictConfig({
#     'version': 1,
#     'loggers': {
#         'quart.app': {
#             'level': 'INFO',
#         },
#     },
#     'formatters': {'default': {
#         'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
#     }},
# })


# ********** Frontend Page Routes **********

@app.route("/")
async def page_home():
    async with app.db.async_session() as session:
        all_media = await app.db.select_all_objects(session, Media)
        return await render_template("pages/home.html", all_media=all_media)

@app.route("/view/<string:media_id>")
async def page_view(media_id: str):
    try:
        media_uuid = b64_to_uuid(media_id)
        result = await app.db.select_object(Media, media_uuid)
        if result is None:
            return await page_error("Not found", 404)
        # TODO render page
        return await render_template("pages/view.html", media=result)
    except ValueError as e:
        return await page_exception(e)


# ********** Frontend Error Templates **********

async def page_error(message, code=400):
    # TODO render error page
    return api_error(message, code)

async def page_exception(e, code=400):
    return await page_error(f"{type(e).__name__}: {e}", code)


# ********** Backend API Routes **********

@app.route("/api/media/info/<string:media_id>")
async def api_media_info(media_id: str):
    try:
        media_uuid = UUID(media_id)
        async with app.db.async_session() as session:
            result = await app.db.select_object(session, Media, media_uuid)
            if result is None:
                return api_error("Not found", 404)
            return api_success(result)
    except ValueError as e:
        return api_exception(e)

@app.route("/api/person/info/<string:person_id>")
async def api_person_info(person_id: str):
    try:
        person_uuid = UUID(person_id)
        async with app.db.async_session() as session:
            result = await app.db.select_object(session, Person, person_uuid)
            if result is None:
                return api_error("Not found", 404)
            return api_success(result)
    except ValueError as e:
        return api_exception(e)

@app.route("/api/orgs/info/<string:org_id>")
async def api_org_info(org_id: str):
    try:
        org_uuid = UUID(org_id)
        async with app.db.async_session() as session:
            result = await app.db.select_object(session, Organization, org_uuid)
            if result is None:
                return api_error("Not found", 404)
            return api_success(result)
    except ValueError as e:
        return api_exception(e)


# ********** Backend Files Routes **********

@app.route("/files/media/<string:media_id>")
async def files_media(media_id: str):
    try:
        media_uuid = UUID(media_id)
        async with app.db.async_session() as session:
            result = await app.db.select_object(session, Media, media_uuid)
            if result is None:
                return api_error("Not found", 404)
            return await send_file(result.filename, conditional=True)
    except ValueError as e:
        return api_exception(e)

@app.route("/files/thumbs/<string:media_id>")
async def files_thumbs(media_id: str):
    try:
        media_uuid = UUID(media_id)
        async with app.db.async_session() as session:
            result = await app.db.select_object(session, Media, media_uuid)
            if result is None:
                return api_error("Not found", 404)
            return await send_file(app.transcoder.get_thumb_filename(result.id))
    except ValueError as e:
        return api_exception(e)


# ********** Backend Response Templates **********

def api_success(data={}):
    return jsonify({
        "result": "success",
        "data": data
    }), 200

def api_error(message, code=400):
    return jsonify({
        "result": "error",
        "message": message
    }), code

def api_exception(e, code=400):
    return api_error(f"{type(e).__name__}: {e}", code)


# ********** Library Operations **********

async def import_media(session, media_filename, **media_args):
    # create media object
    new_media = Media(
        id=uuid4(),
        filename=media_filename,
        **media_args
    )
    tag = await app.db.get_or_create_tag(session, "test1")
    new_media.tags = set([tag])
    # set duration for videos
    if MediaType.video == new_media.type:
        new_media.duration = await run_sync(get_video_duration)(new_media.filename)
    # insert media into db
    await app.db.insert_object(session, new_media)
    # generate thumbnails for videos
    if MediaType.video == new_media.type:
        await run_sync(app.transcoder.create_thumbnail)(new_media)


# ********** Miscellaneous Helpers **********

@app.before_serving
async def app_prepare():
    app.db = Database(config)
    app.transcoder = Transcoder(config)
    await app.db.begin()

    import os
    import_dir = "media"
    async with app.db.async_session() as session:
        async with session.begin():
            for filename in os.listdir(import_dir):
                await import_media(session, f"{import_dir}/{filename}", title=filename, type=MediaType.video)

        results = await app.db.select_all_objects(session, Media)
        for result in results:
            print(result)

@app.after_serving
async def app_cleanup():
    await app.db.close()

@app.context_processor
def utility_processor():
    # Template utility functions
    return dict(
        uuid_to_b64=uuid_to_b64,
        format_duration=format_duration,
    )

@app.errorhandler(Exception)
def handle_exception(e: Exception):
    # pass through HTTP errors
    if isinstance(e, HTTPException):
        return e
    app.logger.error(f"Uncaught exception")
    for line in format_exception(e):
        app.logger.error(line.rstrip("\n"))
    return api_exception(e, 500)

def uuid_to_b64(uuid_value):
    return base64.urlsafe_b64encode(uuid_value.bytes).decode("utf-8").rstrip("=")

def b64_to_uuid(b64_value):
    return UUID(bytes=base64.urlsafe_b64decode(b64_value + "=="))

def format_duration(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours == 0:
        return f"{minutes}:{seconds:02}"
    else:
        return f"{hours}:{minutes:02}:{seconds:02}"

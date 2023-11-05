from uuid import UUID

# Quart
from quart import Quart
from quart import jsonify
from quart import render_template
from werkzeug.exceptions import HTTPException

# SQL commands
from sqlalchemy import insert
from sqlalchemy import select

# Custom config class
from config import load_config

# Custom database and types
from database import Database
from database import Media
from database import Person
from database import Organization
from database import Tag


app = Quart(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

config_path = "config.cfg"
config = load_config(config_path)


# ********** Frontend Page Routes **********

@app.route("/")
async def page_home():
    all_media = await app.db.select_all_objects(Media)
    return await render_template("pages/home.html", all_media=all_media)

@app.route("/view/<string:media_id>")
async def page_view(media_id: str):
    try:
        media_uuid = UUID(media_id)
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
        result = await app.db.select_object(Media, media_uuid)
        if result is None:
            return api_error("Not found", 404)
        return api_success(result)
    except ValueError as e:
        return api_exception(e)

@app.route("/api/person/info/<string:person_id>")
async def api_person_info(person_id: str):
    try:
        person_uuid = UUID(person_id)
        result = await app.db.select_object(Person, person_uuid)
        if result is None:
            return api_error("Not found", 404)
        return api_success(result)
    except ValueError as e:
        return api_exception(e)

@app.route("/api/organization/info/<string:organization_id>")
async def api_organization_info(id: str):
    try:
        organization_uuid = UUID(organization_id)
        result = await app.db.select_object(Organization, organization_uuid)
        if result is None:
            return api_error("Not found", 404)
        return api_success(result)
    except ValueError as e:
        return api_exception(e)

@app.route("/api/media/get/<string:media_id>")
async def api_media_get(media_id: str):
    try:
        media_uuid = UUID(media_id)
        result = await app.db.select_object(Media, media_uuid)
        if result is None:
            return api_error("Not found", 404)
        media_path = config["library"]["media_path"]
        return await send_file(f"{media_path}/{result.filename}", conditional=True)
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


# ********** Miscellaneous Helpers **********

@app.before_serving
async def db_begin():
    app.db = Database(
        config["database"]["url"],
        config["library"]["media_path"]
    )
    await app.db.begin()

@app.after_serving
async def db_close():
    await app.db.close()

@app.context_processor
def utility_processor():
    # Template utility functions
    return dict(
    )

@app.errorhandler(Exception)
def handle_exception(e: Exception):
    # pass through HTTP errors
    if isinstance(e, HTTPException):
        return e
    app.logger.error(f"Uncaught exception")
    app.logger.exception(e)
    return api_exception(e, 500)


if __name__ == "__main__":
    
    app.run()

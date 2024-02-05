import base64
import os
from logging.config import dictConfig
from traceback import format_exception
from uuid import UUID, uuid4

# Quart
from quart import Quart
from quart import jsonify
from quart import redirect
from quart import render_template
from quart import request
from quart import send_file
from quart.helpers import safe_join
from quart.utils import run_sync
# Quart-Auth extenstion
from quart_auth import QuartAuth
from quart_auth import AuthUser as QuartAuthUser
from quart_auth import current_user
from quart_auth import login_user
from quart_auth import login_required
from quart_auth import logout_user
from quart_auth import Unauthorized
# Werkzeug library
from werkzeug.exceptions import HTTPException

# Custom authenticator class
from visiverse.authenticator import Authenticator
from visiverse.authenticator import AuthError
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

# https://github.com/m1k1o/go-transcode

auth_manager = QuartAuth()

config_path = "config.cfg"
config = load_config(config_path)

secret_key_path = "secret.key"
if os.path.isfile(secret_key_path):
    # Read existing secret key
    with open(secret_key_path, "r") as key_file:
        key = key_file.read().strip()
else:
    # Generate new secret key
    with open(secret_key_path, "w") as key_file:
        key = uuid4().hex
        key_file.write(key)
app.secret_key = key

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
        async with app.db.async_session() as session:
            media_uuid = b64_to_uuid(media_id)
            result = await app.db.select_object(session, Media, media_uuid)
            if result is None:
                return await page_error("Not found", 404)
            # TODO render page
            return await render_template("pages/view.html", media=result)
    except ValueError as e:
        return await page_exception(e)

@app.route("/login")
async def page_login():
    return await render_template("pages/login.html")


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

@app.route("/api/organization/info/<string:org_id>")
async def api_organization_info(org_id: str):
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

@app.route("/assets/<path:filename>")
async def template_assets(filename: str):
    return await render_template(safe_join("assets", filename))

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


# ********** Authentication & Routes **********

class AuthUser(QuartAuthUser):

    def __init__(self, auth_id):
        super().__init__(auth_id)
        self._resolved = False
        self._db_user = None

    async def _resolve(self):
        if not self._resolved:
            async with app.db.async_session() as session:
                self._db_user = await app.db.get_user(session, self.auth_id)

    @property
    async def db_user(self):
        await self._resolve()
        return self._db_user

auth_manager.user_class = AuthUser


@app.route("/auth/login", methods=["POST"])
async def auth_login():
    try:
        login_data = await request.get_json()
        user = await app.auth.authenticate(
            login_data["username"],
            login_data["password"],
        )
    except KeyError:
        return api_error("Missing credentials")
    except AuthError as e:
        return api_error(e.message)
    login_user(AuthUser(user.username))
    return api_success()

@app.route("/auth/logout")
async def auth_logout():
    logout_user()
    return api_success()


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
    app.auth = Authenticator(app.db)
    # admin: PASSWORD
    # await app.auth.register_user("admin", "0be64ae89ddd24e225434de95d501711339baeee18f009ba9b4369af27d30d60")

    # import os
    # import_dir = "media"
    # async with app.db.async_session() as session:
    #     async with session.begin():
    #         for filename in os.listdir(import_dir):
    #             await import_media(session, f"{import_dir}/{filename}", title=filename, type=MediaType.video)

    #     results = await app.db.select_all_objects(session, Media)
    #     for result in results:
    #         print(result)

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

@app.errorhandler(Unauthorized)
async def redirect_to_login(*_: Exception):
    return redirect(url_for("page_login"))

@app.errorhandler(Exception)
async def handle_exception(e: Exception):
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


auth_manager.init_app(app)

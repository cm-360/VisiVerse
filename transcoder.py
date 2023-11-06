import ffmpeg


class Transcoder():

    def __init__(self, app_config):
        self.app_config = app_config

    def ensure_segment(media_filename):
        pass

    def create_thumbnail(media):
        (
            ffmpeg
            .input(media_filename, ss=seek)
            .filter('scale', 720, -1)
            .output(media_filename + thumb_suffix, vframes=1)
            .overwrite_output()
            .run()
        )

    def get_thumb_filename(self, media_id):
        storage_path = self.app_config["storage"]["path"]
        thumb_suffix = self.app_config["storage"]["thumb_suffix"]
        return f"{storage_path}/thumbs/{media_id}{thumb_suffix}"

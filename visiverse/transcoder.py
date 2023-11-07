import os

import ffmpeg


class Transcoder():

    def __init__(self, app_config):
        self.app_config = app_config

    def ensure_segment(media_filename):
        pass

    def create_thumbnail(self, media, seek=5):
        thumb_filename = self.get_thumb_filename(media.id)
        ensure_parent_dir(thumb_filename)
        (
            ffmpeg
            .input(media.filename, ss=seek)
            .filter("scale", 720, -1)
            .output(thumb_filename, vframes=1)
            .overwrite_output()
            .run()
        )

    def get_thumb_filename(self, media_id):
        storage_path = self.app_config["storage"]["path"]
        thumb_suffix = self.app_config["storage"]["thumb_suffix"]
        return f"{storage_path}/thumbs/{media_id}{thumb_suffix}"


def ensure_parent_dir(filename):
    parent_dir = os.path.dirname(filename)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)

# Gets video duration in seconds
def get_video_duration(filename):
    return int(round(float(ffmpeg.probe(filename)["format"]["duration"])))
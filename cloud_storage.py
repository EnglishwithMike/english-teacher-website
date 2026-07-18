"""Private Supabase Storage helpers for LearningXY."""

import mimetypes
import os
import subprocess
import tempfile
from pathlib import Path

from flask import Response
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()


PROOF_BUCKET = "teacher-proofs"
PROFILE_BUCKET = "teacher-profile-images"


def _client():
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SECRET_KEY"],
    )


def upload_file(bucket, filename, file_object, content_type=None):
    file_object.seek(0)
    data = file_object.read()
    content_type = (
        content_type
        or getattr(file_object, "mimetype", None)
        or mimetypes.guess_type(filename)[0]
        or "application/octet-stream"
    )
    _client().storage.from_(bucket).upload(
        filename,
        data,
        {"content-type": content_type, "upsert": "true"},
    )
    file_object.seek(0)


def download_file(bucket, filename):
    return _client().storage.from_(bucket).download(filename)


def remove_file(bucket, filename):
    if not filename:
        return
    try:
        _client().storage.from_(bucket).remove([filename])
    except Exception as error:
        # A missing old object should not prevent account/application deletion.
        print("SUPABASE STORAGE REMOVE ERROR:", repr(error))


def inline_response(bucket, filename, download_name=None):
    data = download_file(bucket, filename)
    mimetype = mimetypes.guess_type(download_name or filename)[0]
    response = Response(data, mimetype=mimetype or "application/octet-stream")
    response.headers["Content-Disposition"] = (
        f'inline; filename="{download_name or filename}"'
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def proof_preview_response(filename):
    extension = filename.rsplit(".", 1)[-1].lower()
    data = download_file(PROOF_BUCKET, filename)

    if extension in {"pdf", "png", "jpg", "jpeg"}:
        return inline_response(PROOF_BUCKET, filename)

    if extension not in {"doc", "docx", "odt"}:
        return "This file type cannot be previewed.", 400

    with tempfile.TemporaryDirectory(prefix="learningxy-proof-") as directory:
        source = Path(directory) / filename
        source.write_bytes(data)

        try:
            subprocess.run(
                [
                    "libreoffice",
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    directory,
                    str(source),
                ],
                check=True,
                timeout=45,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except (FileNotFoundError, subprocess.CalledProcessError,
                subprocess.TimeoutExpired):
            return "The document preview could not be created.", 500

        converted = source.with_suffix(".pdf")
        if not converted.is_file():
            return "The document preview could not be created.", 500

        response = Response(converted.read_bytes(), mimetype="application/pdf")
        response.headers["Content-Disposition"] = (
            f'inline; filename="{converted.name}"'
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response


def cache_profile_image(filename, application_root):
    if not filename:
        return

    directory = Path(application_root) / "static" / "teacher_profiles"
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / Path(filename).name

    if destination.is_file():
        return

    try:
        destination.write_bytes(download_file(PROFILE_BUCKET, filename))
    except Exception as error:
        print("SUPABASE PROFILE CACHE ERROR:", repr(error))

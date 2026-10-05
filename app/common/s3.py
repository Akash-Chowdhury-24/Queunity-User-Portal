import asyncio
import logging
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import APIException

logger = logging.getLogger("app")

MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

IMAGE_SIGNATURES = {
    b"\xff\xd8\xff": ".jpg", 
    b"\x89PNG\r\n\x1a\n": ".png",              
    b"GIF87a": ".gif",                         
    b"GIF89a": ".gif",                         
    b"RIFF": ".webp",
}

ALLOWED_DOCUMENT_TYPES = {
    "application/pdf": ".pdf",
}

DOCUMENT_SIGNATURES = {
    b"%PDF-": ".pdf",
}

_s3_client = None

def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
    return _s3_client


def _normalize_folder(folder: str) -> str:
    cleaned = folder.strip().strip("/")
    if not cleaned or ".." in cleaned.split("/"):
        raise APIException(status_code=400, message="Invalid folder")
    return f"{cleaned}/"


def _image_url(key: str) -> str:
    return f"https://{settings.AWS_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"


def get_s3_key_from_url(url: str | None) -> str | None:
    if not url:
        return None

    virtual_hosted_prefix = (
        f"https://{settings.AWS_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/"
    )
    if url.startswith(virtual_hosted_prefix):
        return url[len(virtual_hosted_prefix) :]

    path_style_prefix = (
        f"https://s3.{settings.AWS_REGION}.amazonaws.com/{settings.AWS_BUCKET_NAME}/"
    )
    if url.startswith(path_style_prefix):
        return url[len(path_style_prefix) :]

    if "://" not in url:
        return url.lstrip("/")

    return None


def _detect_image_extension(content: bytes) -> str | None:
    for signature, ext in IMAGE_SIGNATURES.items():
        if content.startswith(signature):
            if ext == ".webp" and not (len(content) >= 12 and content[8:12] == b"WEBP"):
                continue
            return ext
    return None


def _detect_document_extension(content: bytes) -> str | None:
    for signature, ext in DOCUMENT_SIGNATURES.items():
        if content.startswith(signature):
            return ext
    return None


def validate_image(file: UploadFile, content: bytes) -> str:
    if not file.filename:
        raise APIException(status_code=400, message="Image is required")

    content_type = (file.content_type or "").lower()
    extension = ALLOWED_IMAGE_TYPES.get(content_type)
    if not extension:
        raise APIException(
            status_code=400,
            message="Invalid image type. Allowed types: jpeg, png, webp, gif",
        )

    if len(content) > MAX_IMAGE_SIZE:
        raise APIException(status_code=400, message="Image must be 5MB or smaller")

    detected_ext = _detect_image_extension(content)
    if not detected_ext:
        raise APIException(status_code=400, message="Corrupted or invalid image file format")
    return detected_ext


def validate_document(file: UploadFile, content: bytes) -> str:
    if not file.filename:
        raise APIException(status_code=400, message="Document is required")

    content_type = (file.content_type or "").lower()
    extension = ALLOWED_DOCUMENT_TYPES.get(content_type)
    if not extension:
        raise APIException(
            status_code=400,
            message="Corrupted or invalid document format",
        )

    if len(content) > MAX_DOCUMENT_SIZE:
        raise APIException(status_code=400, message="Document must be 10MB or smaller")

    detected_ext = _detect_document_extension(content)
    if not detected_ext:
        raise APIException(status_code=400, message="Corrupted or invalid PDF document format")
    return detected_ext


async def upload_image(file: UploadFile, folder: str) -> str:
    if file.size and file.size > MAX_IMAGE_SIZE:
        raise APIException(status_code=400, message="Image must be 5MB or smaller")

    content = await file.read()
    extension = validate_image(file, content)
    prefix = _normalize_folder(folder)
    key = f"{prefix}{uuid4()}{extension}"

    s3_client = get_s3_client()

    try:
        await asyncio.to_thread(
            s3_client.put_object,
            Bucket=settings.AWS_BUCKET_NAME,
            Key=key,
            Body=content,
            ContentType=file.content_type,
        )
    except ClientError as exc:
        logger.exception("Failed to upload image to S3: %s", key)
        raise APIException(status_code=500, message="Failed to upload image") from exc
    finally:
        await file.seek(0)

    return _image_url(key)


async def upload_document(file: UploadFile, folder: str) -> str:
    if file.size and file.size > MAX_DOCUMENT_SIZE:
        raise APIException(status_code=400, message="Document must be 10MB or smaller")

    content = await file.read()
    extension = validate_document(file, content)
    prefix = _normalize_folder(folder)
    key = f"{prefix}{uuid4()}{extension}"

    s3_client = get_s3_client()

    try:
        await asyncio.to_thread(
            s3_client.put_object,
            Bucket=settings.AWS_BUCKET_NAME,
            Key=key,
            Body=content,
            ContentType=file.content_type,
        )
    except ClientError as exc:
        logger.exception("Failed to upload document to S3: %s", key)
        raise APIException(status_code=500, message="Failed to upload document") from exc
    finally:
        await file.seek(0)

    return _image_url(key)


def _sync_delete_object(key: str) -> None:
    try:
        get_s3_client().delete_object(Bucket=settings.AWS_BUCKET_NAME, Key=key)
    except ClientError:
        logger.exception("Failed to delete image from S3: %s", key)


def _sync_delete_objects(keys: list[str]) -> None:
    if not keys:
        return
    s3_client = get_s3_client()
    for i in range(0, len(keys), 1000):
        batch = [{"Key": k} for k in keys[i : i + 1000]]
        try:
            s3_client.delete_objects(
                Bucket=settings.AWS_BUCKET_NAME,
                Delete={"Objects": batch, "Quiet": True},
            )
        except ClientError:
            logger.exception("Failed to batch delete images from S3: %s", batch)


async def delete_image(url: str | None) -> None:
    key = get_s3_key_from_url(url)
    if not key or key.endswith("/"):
        return
    await asyncio.to_thread(_sync_delete_object, key)


async def delete_images(urls: list[str] | None) -> None:
    valid_keys = [
        get_s3_key_from_url(url)
        for url in (urls or [])
        if url and get_s3_key_from_url(url) and not get_s3_key_from_url(url).endswith("/")
    ]
    if not valid_keys:
        return
    await asyncio.to_thread(_sync_delete_objects, valid_keys)


async def upload_multiple_images(files: list[UploadFile] | None, folder: str) -> list[str]:
    valid_files = [f for f in (files or []) if f and f.filename]
    if not valid_files:
        return []

    uploaded_urls: list[str] = []

    async def _safe_upload(f: UploadFile) -> str:
        url = await upload_image(f, folder)
        uploaded_urls.append(url)
        return url

    try:
        return list(await asyncio.gather(*[_safe_upload(f) for f in valid_files]))
    except Exception:
        await delete_images(uploaded_urls)
        raise


async def upload_multiple_documents(files: list[UploadFile] | None, folder: str) -> list[str]:
    valid_files = [f for f in (files or []) if f and f.filename]
    if not valid_files:
        return []

    uploaded_urls: list[str] = []

    async def _safe_upload(f: UploadFile) -> str:
        url = await upload_document(f, folder)
        uploaded_urls.append(url)
        return url

    try:
        return list(await asyncio.gather(*[_safe_upload(f) for f in valid_files]))
    except Exception:
        await delete_images(uploaded_urls)
        raise

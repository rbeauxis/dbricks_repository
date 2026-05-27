import io
import logging
from typing import BinaryIO, List, Optional

from googleapiclient.http import MediaInMemoryUpload, MediaIoBaseDownload

from .gdrive_auth import get_gdrive_service


def upload_new_file(
    file: BinaryIO, name: str, parents: Optional[List[str]], mimetype: str, service=None
) -> Optional[str]:
    logger = logging.getLogger(__name__)
    if not file or not hasattr(file, "getvalue"):
        logger.error("The 'file' parameter must be a file-like object with a 'getvalue' method.")
        raise Exception("The 'file' parameter must be a file-like object with a 'getvalue' method.")
    if not name:
        logger.error("The 'name' parameter is required.")
        raise Exception("The 'name' parameter is required.")
    if not mimetype:
        logger.error("The 'mimetype' parameter is required.")
        raise Exception("The 'mimetype' parameter is required.")
    try:
        if service is None:
            service = get_gdrive_service()
        file_metadata = {"name": name}
        if parents:
            file_metadata["parents"] = parents
        media = MediaInMemoryUpload(file.getvalue(), mimetype=mimetype)
        uploaded_file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id", supportsAllDrives=True)
            .execute()
        )
        file_id = uploaded_file.get("id")
        logger.info(f"File uploaded to Google Drive with ID: {file_id}")
        return file_id
    except Exception as e:
        logger.error(f"Failed to upload file to Google Drive: {e}")
        raise e


def find_file_in_parents(name: str, parents: Optional[List[str]], service=None) -> Optional[str]:
    logger = logging.getLogger(__name__)
    try:
        if service is None:
            service = get_gdrive_service()
        parent_query = (
            " or ".join([f"'{p}' in parents" for p in parents]) if parents else "'root' in parents"
        )
        query = (
            f"({parent_query}) and "
            f"name = '{name}' and "
            f"mimeType != 'application/vnd.google-apps.folder' and "
            f"trashed = false"
        )
        response = (
            service.files()
            .list(
                q=query,
                spaces="drive",
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        files = response.get("files", [])
        if files:
            return files[0]["id"]
        raise Exception("File not found in parents")
    except Exception as e:
        logger.error(f"Error searching for file '{name}' in parents '{parents}': {e}")
        raise e


def update_file(
    file: BinaryIO, name: str, parents: Optional[List[str]], mimetype: str, service=None
) -> Optional[str]:
    logger = logging.getLogger(__name__)
    if not file or not hasattr(file, "getvalue"):
        logger.error("The 'file' parameter must be a file-like object with a 'getvalue' method.")
        raise Exception("The 'file' parameter must be a file-like object with a 'getvalue' method.")
    if not name:
        logger.error("The 'name' parameter is required.")
        raise Exception("The 'name' parameter is required.")
    if not mimetype:
        logger.error("The 'mimetype' parameter is required.")
        raise Exception("The 'mimetype' parameter is required.")
    if service is None:
        service = get_gdrive_service()
    file_id = find_file_in_parents(name, parents, service=service)
    if not file_id:
        logger.error(f"File '{name}' not found in parents '{parents}'. Cannot update.")
        raise Exception("File not found in parents")
    try:
        media = MediaInMemoryUpload(file.getvalue(), mimetype=mimetype)
        updated_file = (
            service.files()
            .update(fileId=file_id, media_body=media, fields="id", supportsAllDrives=True)
            .execute()
        )
        logger.info(f"File '{name}' updated in Google Drive with ID: {file_id}")
        return updated_file.get("id")
    except Exception as e:
        logger.error(f"Failed to update file '{name}' in Google Drive: {e}")
        raise e


def update_or_create_file(
    file: BinaryIO, name: str, parents: Optional[List[str]], mimetype: str, service=None
) -> Optional[str]:
    logger = logging.getLogger(__name__)
    if service is None:
        service = get_gdrive_service()
    file_id = find_file_in_parents(name, parents, service=service)
    if file_id:
        return update_file(file, name, parents, mimetype, service=service)
    else:
        logger.info(f"File '{name}' not found in parents '{parents}'. Creating new file.")
        return upload_new_file(file, name, parents, mimetype, service=service)


def get_file_content(
    file_id: Optional[str] = None,
    name: Optional[str] = None,
    parents: Optional[List[str]] = None,
    service=None,
) -> Optional[bytes]:
    """
    Obtiene el contenido de un archivo de Google Drive.

    Args:
        file_id: El ID del archivo a descargar (si se proporciona, tiene prioridad)
        name: El nombre del archivo a buscar (se utiliza si file_id no se proporciona)
        parents: Lista de IDs de carpetas padre a buscar (se utiliza si file_id no se proporciona)
        service: Instancia del servicio de Google Drive (opcional)

    Returns:
        El contenido del archivo como bytes, o None si no se encuentra el archivo o se produce un error

    Raises:
        Exception: Si no se proporciona ni file_id ni name, o si no se encuentra el archivo
    """
    logger = logging.getLogger(__name__)

    if not file_id and not name:
        logger.error("Either file_id or name must be provided")
        raise Exception("Either file_id or name must be provided")

    try:
        if service is None:
            service = get_gdrive_service()

        # If file_id is not provided, search for the file by name
        if not file_id:
            if not name:
                logger.error("Name is required when file_id is not provided")
                raise Exception("Name is required when file_id is not provided")
            file_id = find_file_in_parents(name, parents, service=service)
            if not file_id:
                logger.error(f"File '{name}' not found in parents '{parents}'")
                raise Exception(f"File '{name}' not found in parents '{parents}'")

        # Get file metadata to check MIME type
        file_metadata = (
            service.files().get(fileId=file_id, fields="mimeType", supportsAllDrives=True).execute()
        )
        mime_type = file_metadata.get("mimeType")

        # Google Docs Editor files MIME types that need to be exported
        google_docs_types = {
            "application/vnd.google-apps.document": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # Google Docs -> DOCX
            "application/vnd.google-apps.spreadsheet": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # Google Sheets -> XLSX
            "application/vnd.google-apps.presentation": "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # Google Slides -> PPTX
            "application/vnd.google-apps.drawing": "image/png",  # Google Drawings -> PNG
        }

        if mime_type in google_docs_types:
            # Export Google Docs Editor files
            export_mime_type = google_docs_types[mime_type]
            logger.info(
                f"Exporting Google Docs file with MIME type {mime_type} to {export_mime_type}"
            )
            request = service.files().export_media(fileId=file_id, mimeType=export_mime_type)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.debug(f"Exported {int(status.progress() * 100)}% of file")
        else:
            # Download binary files normally
            logger.info(f"Downloading binary file with MIME type {mime_type}")
            request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.debug(f"Downloaded {int(status.progress() * 100)}% of file")

        content = file_content.getvalue()
        logger.info(f"Successfully downloaded file content (size: {len(content)} bytes)")
        return content

    except Exception as e:
        logger.error(f"Failed to get file content: {e}")
        raise e

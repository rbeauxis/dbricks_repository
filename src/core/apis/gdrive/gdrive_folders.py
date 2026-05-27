import logging
from typing import Optional

from .gdrive_auth import get_gdrive_service


def create_folder(parent_folder_id: str, subfolder_name: str, service=None) -> Optional[str]:
    logger = logging.getLogger(__name__)
    if not subfolder_name:
        logger.error("The 'subfolder_name' parameter is required.")
        return None
    if not parent_folder_id:
        logger.error("The 'parent_folder_id' parameter is required.")
        return None
    try:
        if service is None:
            service = get_gdrive_service()
        folder_metadata = {
            "name": subfolder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_folder_id],
        }
        folder = (
            service.files()
            .create(body=folder_metadata, fields="id", supportsAllDrives=True)
            .execute()
        )
        folder_id = folder.get("id")
        logger.info(f"Folder '{subfolder_name}' created in Google Drive with ID: {folder_id}")
        return folder_id
    except Exception as e:
        logger.error(f"Failed to create folder in Google Drive: {e}")
        return None


def find_folder_in_parent(parent_id: str, folder_name: str, service=None) -> Optional[str]:
    logger = logging.getLogger(__name__)
    try:
        if service is None:
            service = get_gdrive_service()
        query = (
            f"'{parent_id}' in parents and "
            f"name = '{folder_name}' and "
            f"mimeType = 'application/vnd.google-apps.folder' and "
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
        return None
    except Exception as e:
        logger.error(f"Error searching for folder '{folder_name}' in parent '{parent_id}': {e}")
        return None


def get_or_create_folder(
    id_parent_folder: str, route_folder_create: str, service=None
) -> Optional[str]:
    logger = logging.getLogger(__name__)
    if not id_parent_folder:
        logger.error("The 'id_parent_folder' parameter is required.")
        return None
    if not route_folder_create:
        logger.error("The 'route_folder_create' parameter is required.")
        return None
    if service is None:
        service = get_gdrive_service()
    current_parent = id_parent_folder
    for folder_name in route_folder_create.strip("/").split("/"):
        if not folder_name:
            continue
        folder_id = find_folder_in_parent(current_parent, folder_name, service=service)
        if folder_id is None:
            folder_id = create_folder(current_parent, folder_name, service=service)
            if folder_id is None:
                logger.error(
                    f"Failed to create or find folder '{folder_name}' under parent '{current_parent}'"
                )
                return None
        current_parent = folder_id
    return current_parent

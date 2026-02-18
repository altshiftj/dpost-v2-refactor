"""Concrete sync manager that mirrors local records into the Kadi database."""

import os
from dataclasses import dataclass
from typing import Optional

from ipat_watchdog.core.config import current
from ipat_watchdog.core.interactions import ErrorMessages, UserInteractionPort
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.sync.sync_abstract import ISyncManager
from ipat_watchdog.core.logging.logger import setup_logger
from kadi_apy import KadiManager
from kadi_apy.lib.resources.records import Record as KadiRecord
from kadi_apy.lib.resources.groups import Group as KadiGroup
from kadi_apy.lib.resources.users import User as KadiUser
from kadi_apy.lib.resources.collections import Collection as KadiCollection


logger = setup_logger(__name__)


def _id_separator() -> str:
    """Resolve record identifier separator from active config."""
    try:
        return current().id_separator
    except RuntimeError:
        return "-"


@dataclass
class DataSyncContext:
    """Bundles all Kadi resources needed to upload a single LocalRecord."""

    db_user: Optional[KadiUser]
    user_collection: KadiCollection
    user_group: Optional[KadiGroup]
    device_user: KadiUser
    device_record: KadiRecord
    device_collection: KadiCollection
    device_group: Optional[KadiGroup]
    db_record: KadiRecord


class KadiSyncManager(ISyncManager):
    """Synchronise `LocalRecord` instances with the Kadi database."""

    def __init__(self, interactions: UserInteractionPort) -> None:
        """Initialise the sync manager with UI-agnostic collaborators."""
        super().__init__(interactions)
        self.db_manager = KadiManager()

    def sync_record_to_database(self, local_record: LocalRecord) -> bool:
        try:
            with self.db_manager as db_manager:
                resources = self._prepare_resources(db_manager, local_record)
                self._initialize_new_db_record(local_record, resources)
                files_remaining = self._upload_record_files(resources.db_record, local_record)
                local_record.is_in_db = True
                logger.info(
                    "All files for record '%s' have been synced to the database.",
                    local_record.identifier,
                )
                return files_remaining
        except Exception as exc:
            logger.exception("Failed to upload files to the database: %s", exc)
            raise

    def _prepare_resources(self, db_manager: KadiManager, local_record: LocalRecord) -> DataSyncContext:
        record_id = local_record.identifier
        id_separator = _id_separator()
        device_user_id = f"{local_record.device_type}{id_separator}usr".replace("_", "-").lower()
        device_record_id = local_record.device_type

        # Build per-user and per-device scaffolding so ownership metadata stays consistent in Kadi.
        db_user = self._get_db_user_from_local_record(db_manager, local_record)
        user_collection = self._get_or_create_db_user_rawdata_collection(db_manager, local_record, db_user)
        user_group = None
        device_user = db_manager.user(username=device_user_id, identity_type="local")
        device_record = db_manager.record(identifier=device_record_id)
        device_collection = self._get_or_create_db_device_rawdata_collection(db_manager, device_user_id, device_record_id)
        device_group = None
        db_record = self._get_or_create_db_record(db_manager, record_id)

        return DataSyncContext(
            db_user=db_user,
            user_collection=user_collection,
            user_group=user_group,
            device_user=device_user,
            device_record=device_record,
            device_collection=device_collection,
            device_group=device_group,
            db_record=db_record,
        )

    def _get_or_create_collection(
        self,
        db_manager: KadiManager,
        collection_id: str,
        title: str,
        add_user_info: Optional[dict] = None,
    ) -> KadiCollection:
        try:
            collection = db_manager.collection(identifier=collection_id)
        except Exception:
            collection = db_manager.collection(create=True, identifier=collection_id)
            collection.set_attribute("title", title)
            logger.debug("Created new collection with ID: %s", collection.id)
        if add_user_info:
            collection.add_user(
                user_id=add_user_info["user_id"],
                role_name=add_user_info.get("role", "admin"),
            )
        return collection

    def _get_or_create_db_user_rawdata_collection(
        self,
        db_manager: KadiManager,
        local_record: LocalRecord,
        db_user: Optional[KadiUser],
    ) -> KadiCollection:
        id_separator = _id_separator()
        collection_id = (
            f"{local_record.user}{id_separator}{local_record.institute}"
            f"{id_separator}rawdata{id_separator}collection"
        )
        title = f"{local_record.user.upper()}@{local_record.institute.upper()}: Raw Data Records"
        add_user_info = {"user_id": db_user.id, "role": "admin"} if db_user else None
        return self._get_or_create_collection(db_manager, collection_id, title, add_user_info)

    def _get_or_create_db_device_rawdata_collection(
        self,
        db_manager: KadiManager,
        device_user_id: str,
        device_record_id: str,
    ) -> KadiCollection:
        db_device_record = db_manager.record(identifier=device_record_id)
        id_separator = _id_separator()
        collection_id = f"{device_record_id.lower()}{id_separator}rawdata{id_separator}collection"
        title = f"{db_device_record.meta['title']}: Raw Data Records"
        add_user_info = {"user_id": device_user_id, "role": "admin"}
        return self._get_or_create_collection(db_manager, collection_id, title, add_user_info)

    def _get_or_create_group(
        self,
        db_manager: KadiManager,
        group_id: str,
        title: str,
        add_user_info: Optional[dict] = None,
    ) -> KadiGroup:
        try:
            group = db_manager.group(identifier=group_id)
        except Exception:
            group = db_manager.group(create=True, identifier=group_id)
            group.set_attribute("title", title)
            logger.debug("Created new group with ID: %s", group_id)

        if add_user_info:
            group.add_user(
                user_id=add_user_info["user_id"],
                role_name=add_user_info.get("role", "admin"),
            )
        return group

    def _get_or_create_db_user_rawdata_group(
        self,
        db_manager: KadiManager,
        local_record: LocalRecord,
        db_user: Optional[KadiUser],
    ) -> KadiGroup:
        id_separator = _id_separator()
        group_id = (
            f"{local_record.user}{id_separator}{local_record.institute}"
            f"{id_separator}rawdata{id_separator}group"
        )
        title = f"{local_record.user.upper()}@{local_record.institute.upper()}: Raw Data Records"
        add_user_info = {"user_id": db_user.id, "role": "admin"} if db_user else None
        return self._get_or_create_group(db_manager, group_id, title, add_user_info)

    def _get_or_create_db_device_rawdata_group(
        self,
        db_manager: KadiManager,
        device_user_id: str,
        device_record_id: str,
    ) -> KadiGroup:
        db_device_record = db_manager.record(identifier=device_record_id)
        id_separator = _id_separator()
        group_id = f"{device_record_id.lower()}{id_separator}rawdata{id_separator}group"
        title = f"{db_device_record.meta['title']}: Raw Data Records"
        add_user_info = {"user_id": device_user_id, "role": "admin"}
        return self._get_or_create_group(db_manager, group_id, title, add_user_info)

    def _get_or_create_db_record(self, db_manager: KadiManager, record_id: str) -> KadiRecord:
        return db_manager.record(create=True, identifier=record_id)

    def _get_db_user_from_local_record(
        self,
        db_manager: KadiManager,
        local_record: LocalRecord,
    ) -> Optional[KadiUser]:
        id_separator = _id_separator()
        user_id = f"{local_record.user}{id_separator}{local_record.institute}"
        try:
            return db_manager.user(username=user_id, identity_type="local")
        except Exception:
            self.interactions.show_error(
                ErrorMessages.USER_NOT_FOUND.format(user_id=user_id),
                ErrorMessages.USER_NOT_FOUND_DETAILS.format(user_id=user_id),
            )
            return None

    def _initialize_new_db_record(
        self,
        local_record: LocalRecord,
        context: DataSyncContext,
    ) -> None:
        db_record = context.db_record
        db_user = context.db_user
        db_device_user = context.device_user
        db_device_record = context.device_record
        if local_record.is_in_db:
            return

        db_record.set_attribute("title", local_record.sample_name)
        db_record.set_attribute("description", local_record.default_description)
        db_record.set_attribute("type", "rawdata")
        for tag in local_record.default_tags:
            db_record.add_tag(tag)
        db_record.add_tag(local_record.datatype)
        db_record.link_record(db_device_record.id, "generated by")
        if context.user_collection:
            db_record.add_collection_link(collection_id=context.user_collection.id)
        if context.device_collection:
            db_record.add_collection_link(collection_id=context.device_collection.id)
        db_record.add_user(user_id=db_device_user.id, role_name="admin")
        if db_user:
            db_record.add_user(user_id=db_user.id, role_name="admin")

        logger.debug("Initialised database record '%s' with metadata.", local_record.identifier)

    def _upload_record_files(self, db_record: KadiRecord, local_record: LocalRecord) -> bool:
        """Upload pending files and report whether anything is still outstanding."""
        # Track files we could not upload so we can clear them from the retry queue later.
        missing_files = []
        for file_path, uploaded in list(local_record.files_uploaded.items()):
            if uploaded:
                continue
            try:
                requires_force = file_path in local_record.files_require_force
                db_record.upload_file(file_path, force=requires_force)
                local_record.files_uploaded[file_path] = True
                if requires_force:
                    local_record.files_require_force.discard(file_path)
                logger.debug("Uploaded file: %s", os.path.basename(file_path))
            except FileNotFoundError:
                logger.warning("File not found: %s", os.path.basename(file_path))
                missing_files.append(file_path)
            except Exception:
                logger.exception("Failed to upload file: %s", os.path.basename(file_path))
                raise

        for file_path in missing_files:
            # Drop stale entries so future sync attempts do not keep retrying vanished artefacts.
            local_record.files_uploaded.pop(file_path, None)
            local_record.files_require_force.discard(file_path)
            logger.debug("Removed missing file '%s' from local record.", os.path.basename(file_path))

        return any(not status for status in local_record.files_uploaded.values())



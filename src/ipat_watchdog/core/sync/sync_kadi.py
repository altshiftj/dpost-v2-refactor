import os
from dataclasses import dataclass
from typing import Optional

from ipat_watchdog.core.ui.ui_abstract import UserInterface
from ipat_watchdog.core.ui.ui_messages import ErrorMessages
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.sync.sync_abstract import ISyncManager
from ipat_watchdog.core.config.settings_store import SettingsStore, SettingsManager
from ipat_watchdog.core.config.settings_base import BaseSettings
from ipat_watchdog.core.logging.logger import setup_logger

from kadi_apy import KadiManager
from kadi_apy.lib.resources.records import Record as KadiRecord
from kadi_apy.lib.resources.groups import Group as KadiGroup
from kadi_apy.lib.resources.users import User as KadiUser


logger = setup_logger(__name__)


@dataclass
class SyncResources:
    db_user: Optional[KadiUser]
    user_group: KadiGroup
    device_user: KadiUser
    device_group: KadiGroup
    db_record: KadiRecord


class KadiSyncManager(ISyncManager):
    """
    Handles synchronization of LocalRecord objects to a remote database using KadiManager.
    """

    def __init__(self, ui: UserInterface, settings_manager: SettingsManager = None, settings: Optional[BaseSettings] = None):
        self.db_manager = KadiManager()
        self.ui = ui
        self.settings_manager = settings_manager
        # For backward compatibility, allow direct settings or fall back to SettingsStore
        self.s = settings or (settings_manager.get_composite_settings() if settings_manager else SettingsStore.get())

    def sync_record_to_database(self, local_record: LocalRecord) -> bool:
        try:
            # Get current settings - use device context if available
            current_settings = self._get_current_settings()
            
            with self.db_manager as db_manager:
                resources = self._prepare_resources(db_manager, local_record, current_settings)
                self._initialize_new_db_record(
                    local_record=local_record,
                    db_record=resources.db_record,
                    db_user=resources.db_user,
                    db_device_user=resources.device_user,
                    db_user_group=resources.user_group,
                    db_device_data_group=resources.device_group,
                    settings=current_settings,
                )
                files_remaining = self._upload_record_files(resources.db_record, local_record)
                local_record.is_in_db = True
                logger.info(f"All files for record '{local_record.identifier}' have been synced to the database.")
                return files_remaining
        except Exception as e:
            logger.exception(f"Failed to upload files to the database: {e}")
            raise e

    def _get_current_settings(self):
        """Get current settings with device context if available."""
        if self.settings_manager:
            # Get composite settings that include current device context
            return self.settings_manager.get_composite_settings()
        return self.s

    def _prepare_resources(self, db_manager: KadiManager, local_record: LocalRecord, settings=None) -> SyncResources:
        # Use provided settings or fall back to instance settings
        s = settings or self.s
        
        db_user = self._get_db_user_from_local_record(db_manager, local_record, s)
        user_group = self._get_or_create_db_user_rawdata_group(db_manager, local_record, db_user, s)
        device_user = db_manager.user(username=s.DEVICE_USER_KADI_ID, identity_type="local")
        device_group = self._get_or_create_db_device_rawdata_group(db_manager, s)
        db_record = self._get_or_create_db_record(db_manager, local_record)

        return SyncResources(
            db_user=db_user,
            user_group=user_group,
            device_user=device_user,
            device_group=device_group,
            db_record=db_record,
        )

    def _get_or_create_group(self, db_manager: KadiManager, group_id: str, title: str, add_user_info: dict = None) -> KadiGroup:
        try:
            group = db_manager.group(identifier=group_id)
        except Exception:
            group = db_manager.group(create=True, identifier=group_id)
            group.set_attribute("title", title)
            logger.debug(f"Created new group with ID: {group_id}")

        if add_user_info:
            group.add_user(
                user_id=add_user_info["user_id"],
                role_name=add_user_info.get("role", "admin"),
            )
        return group

    def _get_or_create_db_user_rawdata_group(self, db_manager: KadiManager, local_record: LocalRecord, db_user: KadiUser, settings) -> KadiGroup:
        sep = settings.ID_SEP
        group_id = f"{local_record.user}{sep}{local_record.institute}{sep}rawdata{sep}group"
        title = f"{local_record.user.upper()}@{local_record.institute.upper()}: Raw Data Records"
        add_user_info = {"user_id": db_user.id, "role": "admin"} if db_user else None
        return self._get_or_create_group(db_manager, group_id, title, add_user_info)

    def _get_or_create_db_device_rawdata_group(self, db_manager: KadiManager, settings) -> KadiGroup:
        sep = settings.ID_SEP
        device_record_id = settings.DEVICE_RECORD_PERSISTENT_ID
        db_device_record = db_manager.record(id=device_record_id)
        group_id = f"{settings.DEVICE_USER_KADI_ID.lower()}{sep}rawdata{sep}group"
        title = f"{db_device_record.meta['title']}: Raw Data Records"
        add_user_info = {"user_id": settings.DEVICE_USER_PERSISTENT_ID, "role": "admin"}
        return self._get_or_create_group(db_manager, group_id, title, add_user_info)

    def _get_or_create_db_record(self, db_manager: KadiManager, local_record: LocalRecord) -> KadiRecord:
        return db_manager.record(create=True, identifier=local_record.identifier)

    def _get_db_user_from_local_record(self, db_manager: KadiManager, local_record: LocalRecord, settings) -> Optional[KadiUser]:
        user_id = f"{local_record.user}{settings.ID_SEP}{local_record.institute}"
        try:
            return db_manager.user(username=user_id, identity_type="local")
        except Exception:
            self.ui.show_error(
                ErrorMessages.USER_NOT_FOUND.format(user_id=user_id),
                ErrorMessages.USER_NOT_FOUND_DETAILS.format(user_id=user_id),
            )
            return None

    def _initialize_new_db_record(
        self,
        local_record: LocalRecord,
        db_record: KadiRecord,
        db_user: KadiUser,
        db_device_user: KadiUser,
        db_user_group: KadiGroup,
        db_device_data_group: KadiGroup,
        settings,
    ):
        if not local_record.is_in_db:
            db_record.set_attribute("title", local_record.sample_name)
            db_record.set_attribute("description", settings.DEFAULT_RECORD_DESCRIPTION)
            db_record.set_attribute("type", "rawdata")
            for tag in settings.RECORD_TAGS:
                db_record.add_tag(tag)
            db_record.add_tag(local_record.datatype)
            db_record.link_record(settings.DEVICE_RECORD_PERSISTENT_ID, "generated by")
            db_record.add_group_role(group_id=db_user_group.id, role_name="member")
            db_record.add_group_role(group_id=db_device_data_group.id, role_name="member")
            db_record.add_user(user_id=db_device_user.id, role_name="admin")
            if db_user:
                db_record.add_user(user_id=db_user.id, role_name="admin")

            logger.debug(f"Initialized new database record '{local_record.identifier}' with attributes and tags.")

    def _upload_record_files(self, db_record: KadiRecord, local_record: LocalRecord) -> bool:
        missing_files = []
        for file_path, uploaded in local_record.files_uploaded.items():
            if not uploaded:
                try:
                    db_record.upload_file(file_path)
                    local_record.files_uploaded[file_path] = True
                    logger.debug(f"Uploaded file: {os.path.basename(file_path)}")
                except FileNotFoundError:
                    logger.warning(f"File not found: {os.path.basename(file_path)}")
                    missing_files.append(file_path)
                except Exception as e:
                    logger.exception(f"Failed to upload file: {os.path.basename(file_path)}")
                    raise e

        for file_path in missing_files:
            del local_record.files_uploaded[file_path]
            logger.debug(f"Removed missing file '{os.path.basename(file_path)}' from local record.")

        return bool(local_record.files_uploaded)

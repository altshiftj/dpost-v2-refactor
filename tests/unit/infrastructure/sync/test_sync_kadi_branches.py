"""Focused branch coverage for Kadi sync manager orchestration seams."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, call

import pytest

pytest.importorskip("kadi_apy")

from dpost.domain.records.local_record import LocalRecord
from dpost.infrastructure.sync.kadi_manager import KadiSyncManager


def _build_record(identifier: str = "dev-user-ipat-sample") -> LocalRecord:
    """Create a local record with deterministic metadata defaults for sync tests."""
    record = LocalRecord(identifier=identifier, datatype="csv", sample_name="sample")
    record.default_description = "desc"
    record.default_tags = ["tag-a", "tag-b"]
    return record


class _InteractionSpy:
    """Capture error dialogs raised by sync flows."""

    def __init__(self) -> None:
        self.errors: list[tuple[str, str]] = []

    def show_error(self, title: str, message: str) -> None:
        """Record a surfaced error dialog."""
        self.errors.append((title, message))


class _DbManagerContext:
    """Simple context-manager wrapper used for sync orchestration tests."""

    def __enter__(self) -> "_DbManagerContext":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_init_uses_injected_db_manager_factory() -> None:
    """Create db manager via explicit factory seam instead of hardcoded constructor."""
    interactions = _InteractionSpy()
    sentinel_db_manager = object()
    sync_mgr = KadiSyncManager(
        interactions=interactions,
        db_manager_factory=lambda: sentinel_db_manager,
    )

    assert sync_mgr.db_manager is sentinel_db_manager


def test_init_default_separator_resolver_uses_record_separator() -> None:
    """Default resolver should read separator directly from LocalRecord context."""
    interactions = _InteractionSpy()
    sync_mgr = KadiSyncManager(
        interactions=interactions,
        db_manager_factory=lambda: _DbManagerContext(),
    )
    record = _build_record("dev:user:ipat:sample")
    record.id_separator = ":"

    assert sync_mgr._id_separator_for_record(record) == ":"


def test_sync_record_to_database_happy_path_sets_in_db(monkeypatch) -> None:
    """Run full sync orchestration and mark the record as synced."""
    interactions = _InteractionSpy()
    db_manager = _DbManagerContext()
    sync_mgr = KadiSyncManager(
        interactions=interactions,
        db_manager_factory=lambda: db_manager,
    )
    record = _build_record()
    resources = SimpleNamespace(db_record=MagicMock())
    calls: list[str] = []
    monkeypatch.setattr(sync_mgr, "_prepare_resources", lambda *_args: resources)
    monkeypatch.setattr(
        sync_mgr,
        "_initialize_new_db_record",
        lambda *_args: calls.append("init"),
    )
    monkeypatch.setattr(
        sync_mgr,
        "_upload_record_files",
        lambda *_args: calls.append("upload") or False,
    )

    result = sync_mgr.sync_record_to_database(record)

    assert result is False
    assert record.is_in_db is True
    assert calls == ["init", "upload"]


def test_sync_record_to_database_reraises_prepare_errors(monkeypatch) -> None:
    """Propagate preparation failures so caller-level retries can handle them."""
    interactions = _InteractionSpy()
    db_manager = _DbManagerContext()
    sync_mgr = KadiSyncManager(
        interactions=interactions,
        db_manager_factory=lambda: db_manager,
    )
    record = _build_record()
    monkeypatch.setattr(
        sync_mgr,
        "_prepare_resources",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("prepare failed")),
    )

    with pytest.raises(RuntimeError, match="prepare failed"):
        sync_mgr.sync_record_to_database(record)


def test_prepare_resources_threads_separator_across_resource_builders(
    monkeypatch,
) -> None:
    """Build context resources with one separator policy passed to all builders."""
    interactions = _InteractionSpy()
    sync_mgr = KadiSyncManager(
        interactions=interactions,
        id_separator_resolver=lambda _record: "|",
        db_manager_factory=lambda: _DbManagerContext(),
    )
    record = _build_record("dev-user-ipat-sample")
    db_manager = MagicMock()
    db_manager.user.return_value = SimpleNamespace(id="device-user-id")
    db_manager.record.return_value = SimpleNamespace(id="device-record-id")
    db_user = SimpleNamespace(id="db-user-id")
    user_collection = SimpleNamespace(id="user-collection-id")
    device_collection = SimpleNamespace(id="device-collection-id")
    db_record = SimpleNamespace(id="db-record-id")
    captured: dict[str, object] = {}

    def fake_get_db_user(
        _db_manager,
        _local_record,
        *,
        id_separator: str,
    ):
        captured["user_lookup_separator"] = id_separator
        return db_user

    def fake_user_collection(
        _db_manager,
        _local_record,
        _db_user,
        *,
        id_separator: str,
    ):
        captured["user_separator"] = id_separator
        return user_collection

    def fake_device_collection(
        _db_manager,
        device_user_id: str,
        device_record_id: str,
        *,
        id_separator: str,
    ):
        captured["device_user_id"] = device_user_id
        captured["device_record_id"] = device_record_id
        captured["device_separator"] = id_separator
        return device_collection

    monkeypatch.setattr(
        sync_mgr,
        "_get_db_user_from_local_record",
        fake_get_db_user,
    )
    monkeypatch.setattr(
        sync_mgr,
        "_get_or_create_db_user_rawdata_collection",
        fake_user_collection,
    )
    monkeypatch.setattr(
        sync_mgr,
        "_get_or_create_db_device_rawdata_collection",
        fake_device_collection,
    )
    monkeypatch.setattr(
        sync_mgr,
        "_get_or_create_db_record",
        lambda _db_manager, _record_id: db_record,
    )

    context = sync_mgr._prepare_resources(db_manager, record)

    assert captured == {
        "user_lookup_separator": "|",
        "user_separator": "|",
        "device_user_id": "dev|usr",
        "device_record_id": "dev",
        "device_separator": "|",
    }
    db_manager.user.assert_called_once_with(username="dev|usr", identity_type="local")
    db_manager.record.assert_called_once_with(identifier="dev")
    assert context.db_user is db_user
    assert context.user_collection is user_collection
    assert context.device_collection is device_collection
    assert context.db_record is db_record


def test_get_or_create_collection_returns_existing_and_adds_user_role() -> None:
    """Reuse existing collections and attach optional user role metadata."""
    sync_mgr = KadiSyncManager(
        interactions=_InteractionSpy(),
        db_manager_factory=lambda: _DbManagerContext(),
    )
    db_manager = MagicMock()
    existing = MagicMock()
    db_manager.collection.return_value = existing

    result = sync_mgr._get_or_create_collection(
        db_manager,
        collection_id="existing-id",
        title="Existing",
        add_user_info={"user_id": "u-1", "role": "viewer"},
    )

    assert result is existing
    db_manager.collection.assert_called_once_with(identifier="existing-id")
    existing.add_user.assert_called_once_with(user_id="u-1", role_name="viewer")


def test_get_or_create_collection_ignores_duplicate_user_membership_error() -> None:
    """Treat duplicate membership errors as idempotent when attaching users."""
    sync_mgr = KadiSyncManager(
        interactions=_InteractionSpy(),
        db_manager_factory=lambda: _DbManagerContext(),
    )
    db_manager = MagicMock()
    existing = MagicMock()
    existing.add_user.side_effect = RuntimeError("User already exists as member")
    db_manager.collection.return_value = existing

    result = sync_mgr._get_or_create_collection(
        db_manager,
        collection_id="existing-id",
        title="Existing",
        add_user_info={"user_id": "u-1", "role": "viewer"},
    )

    assert result is existing
    existing.add_user.assert_called_once_with(user_id="u-1", role_name="viewer")


def test_get_or_create_collection_reraises_non_duplicate_add_user_errors() -> None:
    """Preserve real membership failures instead of swallowing them broadly."""
    sync_mgr = KadiSyncManager(
        interactions=_InteractionSpy(),
        db_manager_factory=lambda: _DbManagerContext(),
    )
    db_manager = MagicMock()
    existing = MagicMock()
    existing.add_user.side_effect = RuntimeError("permission denied")
    db_manager.collection.return_value = existing

    with pytest.raises(RuntimeError, match="permission denied"):
        sync_mgr._get_or_create_collection(
            db_manager,
            collection_id="existing-id",
            title="Existing",
            add_user_info={"user_id": "u-1", "role": "viewer"},
        )


def test_get_or_create_collection_creates_and_sets_title_when_missing() -> None:
    """Create missing collections and assign title metadata once."""
    sync_mgr = KadiSyncManager(
        interactions=_InteractionSpy(),
        db_manager_factory=lambda: _DbManagerContext(),
    )
    db_manager = MagicMock()
    created = MagicMock()
    db_manager.collection.side_effect = [RuntimeError("missing"), created]

    result = sync_mgr._get_or_create_collection(
        db_manager,
        collection_id="new-id",
        title="New Title",
    )

    assert result is created
    assert db_manager.collection.call_args_list == [
        call(identifier="new-id"),
        call(create=True, identifier="new-id"),
    ]
    created.set_attribute.assert_called_once_with("title", "New Title")
    created.add_user.assert_not_called()


def test_get_or_create_group_ignores_duplicate_user_membership_error() -> None:
    """Group helper should also treat duplicate membership as idempotent."""
    sync_mgr = KadiSyncManager(
        interactions=_InteractionSpy(),
        db_manager_factory=lambda: _DbManagerContext(),
    )
    db_manager = MagicMock()
    existing = MagicMock()
    existing.add_user.side_effect = RuntimeError("member already exists")
    db_manager.group.return_value = existing

    result = sync_mgr._get_or_create_group(
        db_manager,
        group_id="existing-group",
        title="Existing",
        add_user_info={"user_id": "u-1", "role": "viewer"},
    )

    assert result is existing
    existing.add_user.assert_called_once_with(user_id="u-1", role_name="viewer")


def test_get_or_create_user_rawdata_collection_forwards_add_user_info() -> None:
    """Pass computed user collection identifiers and admin role metadata."""
    sync_mgr = KadiSyncManager(
        interactions=_InteractionSpy(),
        db_manager_factory=lambda: _DbManagerContext(),
    )
    record = _build_record()
    db_user = SimpleNamespace(id="db-user-id")
    db_manager = MagicMock()
    getter = MagicMock(return_value="collection")
    sync_mgr._get_or_create_collection = getter  # type: ignore[method-assign]

    result = sync_mgr._get_or_create_db_user_rawdata_collection(
        db_manager,
        record,
        db_user,
        id_separator=":",
    )

    assert result == "collection"
    getter.assert_called_once_with(
        db_manager,
        "user:ipat:rawdata:collection",
        "USER@IPAT: Raw Data Records",
        {"user_id": "db-user-id", "role": "admin"},
    )


def test_get_or_create_device_rawdata_collection_uses_device_record_title() -> None:
    """Build device collection title from canonical device record metadata."""
    sync_mgr = KadiSyncManager(
        interactions=_InteractionSpy(),
        db_manager_factory=lambda: _DbManagerContext(),
    )
    db_manager = MagicMock()
    db_manager.record.return_value = SimpleNamespace(meta={"title": "Device A"})
    getter = MagicMock(return_value="collection")
    sync_mgr._get_or_create_collection = getter  # type: ignore[method-assign]

    result = sync_mgr._get_or_create_db_device_rawdata_collection(
        db_manager,
        device_user_id="device-user",
        device_record_id="DEV",
        id_separator="-",
    )

    assert result == "collection"
    getter.assert_called_once_with(
        db_manager,
        "dev-rawdata-collection",
        "Device A: Raw Data Records",
        {"user_id": "device-user", "role": "admin"},
    )


def test_get_or_create_device_rawdata_group_uses_device_record_title() -> None:
    """Build device group title from canonical device record metadata."""
    sync_mgr = KadiSyncManager(
        interactions=_InteractionSpy(),
        db_manager_factory=lambda: _DbManagerContext(),
    )
    db_manager = MagicMock()
    db_manager.record.return_value = SimpleNamespace(meta={"title": "Device B"})
    getter = MagicMock(return_value="group")
    sync_mgr._get_or_create_group = getter  # type: ignore[method-assign]

    result = sync_mgr._get_or_create_db_device_rawdata_group(
        db_manager,
        device_user_id="device-user",
        device_record_id="DEV",
        id_separator=":",
    )

    assert result == "group"
    getter.assert_called_once_with(
        db_manager,
        "dev:rawdata:group",
        "Device B: Raw Data Records",
        {"user_id": "device-user", "role": "admin"},
    )


def test_initialize_new_db_record_returns_early_for_existing_records() -> None:
    """Skip metadata initialization when record is already known in database."""
    sync_mgr = KadiSyncManager(
        interactions=_InteractionSpy(),
        db_manager_factory=lambda: _DbManagerContext(),
    )
    record = _build_record()
    record.is_in_db = True
    db_record = MagicMock()
    context = SimpleNamespace(
        db_record=db_record,
        db_user=SimpleNamespace(id="user"),
        device_user=SimpleNamespace(id="device-user"),
        device_record=SimpleNamespace(id="device-record"),
        user_collection=SimpleNamespace(id="user-collection"),
        device_collection=SimpleNamespace(id="device-collection"),
    )

    sync_mgr._initialize_new_db_record(record, context)

    db_record.set_attribute.assert_not_called()
    db_record.add_user.assert_not_called()


def test_initialize_new_db_record_links_collections_and_device_user_only() -> None:
    """Attach collection links and always include device user admin mapping."""
    sync_mgr = KadiSyncManager(
        interactions=_InteractionSpy(),
        db_manager_factory=lambda: _DbManagerContext(),
    )
    record = _build_record()
    db_record = MagicMock()
    context = SimpleNamespace(
        db_record=db_record,
        db_user=None,
        device_user=SimpleNamespace(id="device-user"),
        device_record=SimpleNamespace(id="device-record"),
        user_collection=SimpleNamespace(id="user-collection"),
        device_collection=SimpleNamespace(id="device-collection"),
    )

    sync_mgr._initialize_new_db_record(record, context)

    db_record.add_collection_link.assert_has_calls(
        [
            call(collection_id="user-collection"),
            call(collection_id="device-collection"),
        ]
    )
    db_record.add_user.assert_called_once_with(user_id="device-user", role_name="admin")


def test_upload_record_files_skips_uploaded_entries_and_reraises_other_errors() -> None:
    """Ignore already-uploaded files and rethrow non-file-missing upload failures."""
    sync_mgr = KadiSyncManager(
        interactions=_InteractionSpy(),
        db_manager_factory=lambda: _DbManagerContext(),
    )
    record = _build_record()
    record.files_uploaded = {
        "/tmp/already.csv": True,
        "/tmp/fail.csv": False,
    }
    db_record = MagicMock()
    db_record.upload_file.side_effect = RuntimeError("upload failed")

    with pytest.raises(RuntimeError, match="upload failed"):
        sync_mgr._upload_record_files(db_record, record)

    db_record.upload_file.assert_called_once_with("/tmp/fail.csv", force=False)
    assert record.files_uploaded["/tmp/already.csv"] is True


@pytest.mark.parametrize(
    "resolver",
    [
        lambda _record: (_ for _ in ()).throw(RuntimeError("boom")),
        lambda _record: "",
    ],
)
def test_id_separator_for_record_rejects_invalid_resolver_output(resolver) -> None:
    """Raise when the injected separator resolver fails or returns invalid data."""
    sync_mgr = KadiSyncManager(
        interactions=_InteractionSpy(),
        id_separator_resolver=resolver,
        db_manager_factory=lambda: _DbManagerContext(),
    )
    record = _build_record("dev-user-ipat-sample")

    with pytest.raises(ValueError, match="id_separator"):
        sync_mgr._id_separator_for_record(record)


def test_id_separator_for_record_uses_valid_explicit_resolver_output() -> None:
    """Return resolver output when explicit separator context is valid."""
    sync_mgr = KadiSyncManager(
        interactions=_InteractionSpy(),
        id_separator_resolver=lambda _record: ":",
        db_manager_factory=lambda: _DbManagerContext(),
    )
    record = _build_record("dev:user:ipat:sample")

    assert sync_mgr._id_separator_for_record(record) == ":"

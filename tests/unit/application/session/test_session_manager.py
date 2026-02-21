from dpost.application.config import current
from dpost.domain.records.local_record import LocalRecord
from dpost.application.session.session_manager import SessionManager
from types import SimpleNamespace


def _make_record(identifier: str = "udr_01-mus-ipat-sample_a") -> LocalRecord:
    return LocalRecord(identifier=identifier)



def test_start_session(fake_ui, config_service):
    """When start_session() is called on an inactive session it should schedule a timeout."""
    fake_ui.auto_close_session = False
    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)

    assert not session_manager.session_active
    assert session_manager.timer_id is None

    session_manager.start_session()

    assert session_manager.session_active is True
    assert session_manager.timer_id == 1  # HeadlessUI returns task handle as int




def test_note_activity_starts_session(fake_ui, config_service):
    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)
    record = _make_record()

    session_manager.note_activity(record)

    assert session_manager.session_active is True
    assert fake_ui.session_details_history[-1].users == ("mus-ipat",)
    assert fake_ui.session_details_history[-1].records == (f"{record.sample_name}",)


def test_note_activity_refreshes_timer_and_details(fake_ui, config_service):
    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)
    first = _make_record("udr_01-mus-ipat-sample_a")
    second = _make_record("udr_01-mus-ipat-sample_b")

    session_manager.note_activity(first)
    session_manager.note_activity(second)

    assert len(fake_ui.session_details_history) == 2
    latest = fake_ui.session_details_history[-1]
    assert latest.users == ("mus-ipat",)
    assert latest.records == (
        f"{first.sample_name}",
        f"{second.sample_name}",
    )
    assert fake_ui.scheduled_tasks[-1][0] == current().session_timeout * 1000


def test_note_activity_tracks_multiple_users(fake_ui, config_service):
    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)
    primary = _make_record("udr_01-mus-ipat-sample_a")
    secondary = _make_record("udr_01-jfi-ipat-sample_b")

    session_manager.note_activity(primary)
    session_manager.note_activity(secondary)
    session_manager.note_activity(primary)

    latest = fake_ui.session_details_history[-1]
    assert latest.users == ("mus-ipat", "jfi-ipat")
    # Counts removed: each record label appears once
    assert latest.records == (
        f"{primary.sample_name}",
        f"{secondary.sample_name}",
    )


def test_note_activity_counts_increment(fake_ui, config_service):
    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)
    record = _make_record("udr_01-mus-ipat-sample_a")

    session_manager.note_activity(record)
    session_manager.note_activity(record)

    latest = fake_ui.session_details_history[-1]
    # Previously showed file count increment; now remains single simple label
    assert latest.records == (f"{record.sample_name}",)


def test_end_session_calls_callback(fake_ui, config_service):
    ended = []

    def on_done():
        ended.append(True)

    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui, end_session_callback=on_done)
    session_manager.session_active = True
    session_manager.timer_id = 1

    session_manager.end_session()

    assert session_manager.session_active is False
    assert session_manager.timer_id is None
    assert ended == [True]


def test_reset_timer_reschedules(fake_ui, config_service):
    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)
    session_manager.session_active = True
    session_manager.timer_id = 1

    session_manager.reset_timer()

    assert session_manager.timer_id == 2
    assert fake_ui.scheduled_tasks[-1][0] == current().session_timeout * 1000


def test_reset_timer_when_inactive_does_nothing(fake_ui, config_service):
    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)
    session_manager.session_active = False
    session_manager.timer_id = None

    session_manager.reset_timer()

    assert session_manager.timer_id is None
    assert fake_ui.scheduled_tasks == []


def test_auto_end_session(fake_ui, config_service):
    fake_ui.auto_close_session = True
    ended = []

    def on_done():
        ended.append(True)

    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui, end_session_callback=on_done)
    session_manager.start_session()

    assert session_manager.session_active is False
    assert ended == [True]

def test_start_session_noop_when_already_active(fake_ui, config_service):
    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)
    session_manager.session_active = True
    session_manager.timer_id = 5

    session_manager.start_session()

    assert session_manager.session_active is True
    assert session_manager.timer_id == 5
    assert fake_ui.scheduled_tasks == []


def test_reset_timer_ignores_disabled_timeout(fake_ui, monkeypatch):
    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)
    session_manager.session_active = True

    stub = type("StubConfig", (), {"session_timeout": -1})()
    monkeypatch.setattr("dpost.application.session.session_manager.current", lambda: stub)

    session_manager.reset_timer()

    assert session_manager.timer_id is None
    assert fake_ui.scheduled_tasks == []


def test_session_manager_properties_and_summary(fake_ui, config_service):
    """Expose active/interactive state and immutable summary snapshot."""
    manager = SessionManager(interactions=fake_ui, scheduler=fake_ui, interactive=False)

    assert manager.is_active is False
    assert manager.interactive is False
    assert manager.get_summary().to_dict() == {
        "active": False,
        "users": (),
        "records": (),
    }


def test_set_interactive_noop_when_value_unchanged(fake_ui, config_service):
    """Keep state unchanged without refreshing prompt when mode already matches."""
    manager = SessionManager(interactions=fake_ui, scheduler=fake_ui, interactive=True)
    manager.session_active = True
    manager.set_interactive(True)

    assert manager.interactive is True
    assert fake_ui.session_details_history == []


def test_set_interactive_refreshes_prompt_when_enabling_active_session(
    fake_ui,
    config_service,
):
    """Refresh done-prompt when interactive mode is re-enabled mid-session."""
    manager = SessionManager(interactions=fake_ui, scheduler=fake_ui, interactive=False)
    manager.session_active = True
    manager._session_users = ["mus-ipat"]
    manager._session_records = ["sample_a"]

    manager.set_interactive(True)

    assert manager.interactive is True
    assert fake_ui.session_details_history[-1].users == ("mus-ipat",)
    assert fake_ui.session_details_history[-1].records == ("sample_a",)


def test_note_activity_headless_mode_suppresses_prompt_history(fake_ui, config_service):
    """Track activity in headless mode without showing done prompts."""
    manager = SessionManager(interactions=fake_ui, scheduler=fake_ui, interactive=False)
    record = _make_record("udr_01-mus-ipat-sample_a")

    manager.note_activity(record)

    assert manager.session_active is True
    assert fake_ui.session_details_history == []
    assert manager.get_summary().users == ("mus-ipat",)
    assert manager.get_summary().records == ("sample_a",)


def test_format_record_label_returns_unknown_for_empty_label(fake_ui, config_service):
    """Normalize missing labels to human-readable placeholder text."""
    manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)
    assert manager._format_record_label(None) == "Unknown Sample"  # noqa: SLF001
    assert manager._format_record_label("") == "Unknown Sample"  # noqa: SLF001


def test_derive_user_tag_handles_missing_or_partial_identity(fake_ui, config_service):
    """Return None when user missing, user-only when institute missing, or both when present."""
    manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)

    no_user = SimpleNamespace(user="null", institute="ipat")
    user_only = SimpleNamespace(user="mus", institute=None)
    full = SimpleNamespace(user="mus", institute="ipat")

    assert manager._derive_user_tag(no_user) is None  # noqa: SLF001
    assert manager._derive_user_tag(user_only) == "mus"  # noqa: SLF001
    assert manager._derive_user_tag(full) == "mus-ipat"  # noqa: SLF001


def test_derive_sample_label_falls_back_to_identifier_and_none(
    fake_ui,
    config_service,
):
    """Derive sample from identifier parts, identifier value, or None."""
    manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)

    from_identifier = SimpleNamespace(
        sample_name="null",
        identifier="dev-mus-ipat-sample_a",
        id_separator="-",
    )
    short_identifier = SimpleNamespace(
        sample_name="null",
        identifier="invalid",
        id_separator="-",
    )
    missing_identifier = SimpleNamespace(sample_name="null", identifier="null", id_separator="-")

    assert manager._derive_sample_label(from_identifier) == "sample_a"  # noqa: SLF001
    assert manager._derive_sample_label(short_identifier) == "invalid"  # noqa: SLF001
    assert manager._derive_sample_label(missing_identifier) is None  # noqa: SLF001

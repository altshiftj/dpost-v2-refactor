"""
Record interaction flows: unappendable records and append-to-synced prompts.
"""
from ipat_watchdog.core.ui.ui_messages import DialogPrompts, WarningMessages
from ipat_watchdog.core.processing.rename_flow import rename_flow_controller


def handle_unappendable_record(ui, rename_delegate, src_path: str, filename_prefix: str, extension: str) -> None:
    """Show warning and force rename flow with context for unappendable records."""
    ui.show_warning(WarningMessages.INVALID_RECORD, WarningMessages.INVALID_RECORD_DETAILS)
    rename_delegate(
        src_path,
        filename_prefix,
        extension,
        contextual_reason=DialogPrompts.UNAPPENDABLE_RECORD_CONTEXT.format(record_id=filename_prefix),
    )


def handle_append_to_synced_record(
    ui,
    add_item_delegate,
    rename_delegate,
    record,
    src_path: str,
    filename_prefix: str,
    extension: str,
    file_processor,
) -> None:
    """Prompt user to append to a synced record; proceed or force rename based on response."""
    if ui.prompt_append_record(filename_prefix):
        add_item_delegate(record, src_path, filename_prefix, extension, file_processor)
    else:
        rename_delegate(
            src_path,
            filename_prefix,
            extension,
            contextual_reason=DialogPrompts.APPEND_RECORD_CANCEL_CONTEXT.format(record_id=filename_prefix),
        )

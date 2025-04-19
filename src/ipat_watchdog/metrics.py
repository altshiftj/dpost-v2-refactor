from prometheus_client import Counter, Gauge, Histogram

FILES_PROCESSED = Counter("files_processed", "Total files processed by Watchdog")

FILES_PROCESSED_BY_RECORD = Counter(
    "files_processed_by_record",
    "Files processed by record ID",
    ["record_id"]
)

FILES_FAILED = Counter("files_failed", "Files that failed to process due to errors")

EVENTS_PROCESSED = Counter("events_processed", "Total file system events triggered in this session")

FILE_PROCESS_TIME = Histogram("file_process_time_seconds", "Time spent processing individual files")

SESSION_EXIT_STATUS = Gauge("session_exit_status", "0 = clean exit, 1 = crashed")

SESSION_DURATION = Gauge("session_duration_seconds", "Total duration of WatchdogApp session in seconds")

EXCEPTIONS_THROWN = Counter("exceptions_thrown","Total uncaught exceptions during app runtime")
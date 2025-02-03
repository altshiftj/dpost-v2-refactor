import os
import sys
import threading
import functools
import collections

from src.config.settings import TRACE_LOG_MODE, TRACE_LOG_FILE

##############################################################################
# CONFIG
##############################################################################
# Columns for alignment
DEPTH_COL      = 12  # e.g. enough to hold "[Depth: 9999]"
CALLRET_COL    = 10  # e.g. enough to hold "[CALL]" or "[RETURN]"
THREAD_COL     = 30
SCRIPT_COL     = 40
FUNCTION_COL   = 40

# File for logging
TRACE_LOG_FILE = os.path.join(os.path.dirname(__file__),
    f"trace.{ 'html' if TRACE_LOG_MODE == 'html' else 'log' }")

# Indent for argument/return lines
INDENT = " " * 4

HTML_HEADER = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Function Call Log</title>
    <style>
        /* Use a monospaced font to preserve alignment from .ljust() */
        body, pre {{
            font-family: Consolas, "Lucida Console", monospace;
            background-color: #f4f4f4;
        }}
        .log-container {{
            background: white; padding: 10px; border-radius: 5px;
            box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        }}
        .depth        {{ color: teal; font-weight: bold; }}
        .call-label   {{ color: gray; font-weight: bold; }}
        .thread       {{ color: blue; font-weight: bold; }}
        .script       {{ color: green; }}
        .function     {{ color: darkorange; font-weight: bold; }}
        .args         {{ color: red; margin-left: 20px; }}
        .return-value {{ color: purple; margin-left: 20px; }}
        pre {{
            font-size: 14px;
            white-space: pre-wrap;
            word-wrap: break-word; 
            margin: 0;
        }}
    </style>
</head>
<body>
<div class="log-container">
<pre>
"""

HTML_FOOTER = """
</pre>
</div>
</body>
</html>
"""

# Initialize the log file
with open(TRACE_LOG_FILE, "w") as lf:
    if TRACE_LOG_MODE == "html":
        lf.write(HTML_HEADER)

##############################################################################
# GLOBAL STATE
##############################################################################
call_depths = collections.defaultdict(int)
call_records = {}

def trace_calls(frame, event, arg):
    """
    Two-step logging with alignment:
      - On "call", log [CALL] with function details + args.
      - On "return", log [RETURN] with return value.
    We track call depth per thread, and use fixed-width columns so all headers line up.
    """
    if event not in ("call", "return"):
        return

    code = frame.f_code
    filename = os.path.abspath(code.co_filename)

    # If you only want to trace your own project code, set a custom PROJECT_ROOT
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if not filename.startswith(PROJECT_ROOT):
        return

    thread_name = threading.current_thread().name
    func_name   = code.co_name
    lineno      = frame.f_lineno
    script_name = os.path.basename(filename)
    frame_id    = id(frame)

    if event == "call":
        # Increase depth for this thread
        call_depths[thread_name] += 1
        depth = call_depths[thread_name]

        # Retrieve arguments
        args_info = []
        try:
            locals_dict = frame.f_locals
            arg_names = code.co_varnames[:code.co_argcount]
            for name in arg_names:
                if name in locals_dict:
                    args_info.append(f"{INDENT}Arg {name}: {locals_dict[name]!r}")
        except Exception as e:
            args_info.append(f"{INDENT}Could not retrieve args: {e}")

        # Store minimal info for matching return
        call_records[frame_id] = {
            "thread": thread_name,
            "script": script_name,
            "lineno": lineno,
            "func": func_name,
            "depth": depth,
        }

        # Build the aligned line for [CALL]
        depth_label   = f"[Depth: {depth}]"
        callret_label = "[CALL]"
        thread_label  = f"[Thread: {thread_name}]"
        script_label  = f"[Script: {script_name}:{lineno}]"
        func_label    = f"[Function: {func_name}]"

        if TRACE_LOG_MODE == "ascii":
            # Use fixed-width columns with ljust
            header_line = (
                f"{depth_label.ljust(DEPTH_COL)} "
                f"{callret_label.ljust(CALLRET_COL)} "
                f"{thread_label.ljust(THREAD_COL)} "
                f"{script_label.ljust(SCRIPT_COL)} "
                f"{func_label.ljust(FUNCTION_COL)}"
            )
            log_entry = header_line + "\n"
            if args_info:
                log_entry += "\n".join(args_info) + "\n"
            log_entry += "\n"  # extra blank line

        else:  # HTML mode
            # We do the same alignment in text terms, but wrap each with a <span>.
            # Inside <pre> with a monospace font, the spacing from .ljust(...) is preserved.
            depth_col   = depth_label.ljust(DEPTH_COL)
            callret_col = callret_label.ljust(CALLRET_COL)
            thread_col  = thread_label.ljust(THREAD_COL)
            script_col  = script_label.ljust(SCRIPT_COL)
            func_col    = func_label.ljust(FUNCTION_COL)

            header_line = (
                f"<span class='depth'>{depth_col}</span>"
                f" <span class='call-label'>{callret_col}</span>"
                f" <span class='thread'>{thread_col}</span>"
                f" <span class='script'>{script_col}</span>"
                f" <span class='function'>{func_col}</span>"
            )
            log_entry = header_line + "\n"
            if args_info:
                for arg_line in args_info:
                    log_entry += f"<span class='args'>{arg_line}</span>\n"
            log_entry += "\n"

        with open(TRACE_LOG_FILE, "a") as lf:
            lf.write(log_entry)
            lf.flush()

        return trace_calls

    elif event == "return":
        return_value = arg
        record = call_records.pop(frame_id, None)
        if not record:
            return

        depth       = record["depth"]
        thread_name = record["thread"]
        script_name = record["script"]
        lineno      = record["lineno"]
        func_name   = record["func"]

        # Build the aligned line for [RETURN]
        depth_label   = f"[Depth: {depth}]"
        callret_label = "[RETURN]"
        thread_label  = f"[Thread: {thread_name}]"
        script_label  = f"[Script: {script_name}:{lineno}]"
        func_label    = f"[Function: {func_name}]"

        if TRACE_LOG_MODE == "ascii":
            header_line = (
                f"{depth_label.ljust(DEPTH_COL)} "
                f"{callret_label.ljust(CALLRET_COL)} "
                f"{thread_label.ljust(THREAD_COL)} "
                f"{script_label.ljust(SCRIPT_COL)} "
                f"{func_label.ljust(FUNCTION_COL)}"
            )
            log_entry = header_line + "\n"
            log_entry += f"{INDENT}--> returned {return_value!r}\n\n"

        else:  # HTML mode
            depth_col   = depth_label.ljust(DEPTH_COL)
            callret_col = callret_label.ljust(CALLRET_COL)
            thread_col  = thread_label.ljust(THREAD_COL)
            script_col  = script_label.ljust(SCRIPT_COL)
            func_col    = func_label.ljust(FUNCTION_COL)

            header_line = (
                f"<span class='depth'>{depth_col}</span>"
                f" <span class='call-label'>{callret_col}</span>"
                f" <span class='thread'>{thread_col}</span>"
                f" <span class='script'>{script_col}</span>"
                f" <span class='function'>{func_col}</span>"
            )
            log_entry = header_line + "\n"
            log_entry += f"<span class='return-value'>{INDENT}--> returned {return_value!r}</span>\n\n"

        with open(TRACE_LOG_FILE, "a") as lf:
            lf.write(log_entry)
            lf.flush()

        # Decrement thread depth
        call_depths[thread_name] -= 1

def enable_global_tracing():
    sys.settrace(trace_calls)
    threading.settrace(trace_calls)

def track_function_calls(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        enable_global_tracing()
        return func(*args, **kwargs)
    return wrapper

##############################################################################
# EXAMPLE USAGE
##############################################################################
@track_function_calls
def sample_function(a, b, c="default"):
    print(f"Inside sample_function with {a}, {b}, {c}")
    return (a, b, c)

@track_function_calls
def main():
    print("Starting main...")
    return_val = sample_function(42, "hello", c="custom_value")
    print("sample_function returned:", return_val)

    threads = []
    for i in range(2):
        t = threading.Thread(target=worker_job, name=f"Worker-{i}", args=(i,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

@track_function_calls
def worker_job(worker_id):
    print(f"Inside worker thread job {worker_id}... [{threading.current_thread().name}]")
    return f"Worker {worker_id} done"

if __name__ == "__main__":
    main()
    if TRACE_LOG_MODE == "html":
        with open(TRACE_LOG_FILE, "a") as lf:
            lf.write(HTML_FOOTER)

import os
import sys
import threading
import functools

# Toggle logging mode: "ascii" for plain text, "html" for color-coded HTML
LOG_MODE = "html"  # Change to "ascii" for plain text logging

# Define log file path based on mode
LOG_FILE = os.path.join(os.path.dirname(__file__), f"trace.{ 'html' if LOG_MODE == 'html' else 'log' }")

# Define column widths for consistent alignment
THREAD_WIDTH = 15  
SCRIPT_WIDTH = 30  
LINE_WIDTH = 5    
FUNC_WIDTH = 35   
INDENT = " " * 4  # Indentation for parameter logging

# HTML template if logging in HTML mode
HTML_HEADER = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Function Call Log</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px; }
        .log-container { background: white; padding: 10px; border-radius: 5px; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); }
        .thread { color: blue; font-weight: bold; }
        .script { color: green; }
        .function { color: darkorange; font-weight: bold; }
        .args { color: red; margin-left: 20px; }
        .return-value { color: purple; margin-left: 20px; }
        pre { font-size: 14px; white-space: pre-wrap; word-wrap: break-word; } /* Enables text wrapping */
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
with open(LOG_FILE, "w") as log_file:
    if LOG_MODE == "html":
        log_file.write(HTML_HEADER)  # Start HTML file with header

##############################################################################
# GLOBAL DICTIONARY TO STORE "call" DETAILS, TO MERGE WITH LATER "return" INFO
##############################################################################
call_records = {}

def trace_calls(frame, event, arg):
    """
    We handle "call" and "return" events to consolidate them into one log entry.
    For "call", we collect info (thread, file, func, args) but do NOT write it yet.
    For "return", we retrieve that info, append the return value, then write it all.
    """
    if event not in ("call", "return"):
        return

    code = frame.f_code
    filename = os.path.abspath(code.co_filename)
    
    # Adjust this path to your actual project root or src directory
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    if not filename.startswith(PROJECT_ROOT):
        return  # Filter out external or stdlib

    func_name = code.co_name
    lineno = frame.f_lineno
    thread_name = threading.current_thread().name
    script_name = os.path.basename(filename)
    frame_id = id(frame)

    if event == "call":
        # Retrieve function arguments if available
        args_info = []
        try:
            locals_dict = frame.f_locals
            arg_names = code.co_varnames[:code.co_argcount]
            for name in arg_names:
                if name in locals_dict:
                    args_info.append(f"{INDENT}Arg {name}: {locals_dict[name]!r}")
        except Exception as e:
            args_info.append(f"{INDENT}Could not retrieve args: {e}")

        # Store in our global dictionary (no immediate write)
        call_records[frame_id] = {
            "thread": thread_name,
            "script": script_name,
            "lineno": lineno,
            "func": func_name,
            "args": args_info,
        }

        # Return trace_calls so that deeper calls are also traced
        return trace_calls

    elif event == "return":
        # Retrieve the previously stored "call" info
        record = call_records.pop(frame_id, None)
        if not record:
            # If we didn't track this frame (maybe out-of-scope?), skip
            return

        return_value = arg  # the function's return value

        # Build a single consolidated log entry (header + args + return)
        if LOG_MODE == "ascii":
            # For ASCII mode
            log_entry = (
                f"[Thread: {record['thread']:<{THREAD_WIDTH}}] "
                f"[Script: {record['script']:<{SCRIPT_WIDTH}}:{record['lineno']:<{LINE_WIDTH}}] "
                f"[Function: {record['func']:<{FUNC_WIDTH}}]\n"
            )
            if record["args"]:
                log_entry += "\n".join(record["args"]) + "\n"
            log_entry += f"{INDENT}--> returned {return_value!r}\n\n"

        else:
            # For HTML mode
            log_entry = (
                f"<span class='thread'>[Thread: {record['thread']:<{THREAD_WIDTH}}]</span> "
                f"<span class='script'>[Script: {record['script']:<{SCRIPT_WIDTH}}:{record['lineno']:<{LINE_WIDTH}}]</span> "
                f"<span class='function'>[Function: {record['func']:<{FUNC_WIDTH}}]</span>\n"
            )
            if record["args"]:
                for arg_line in record["args"]:
                    # Each arg line goes as red text
                    log_entry += f"<span class='args'>{arg_line}</span><br>"
            log_entry += f"<span class='return-value'>{INDENT}--> returned {return_value!r}</span><br><br>"

        # Write the consolidated log entry now
        with open(LOG_FILE, "a") as log_file:
            log_file.write(log_entry)
            log_file.flush()

    # For "return", no need to continue tracing deeper (the function is exiting).
    # So we do NOT return trace_calls here.

########################################################################
# 2. ENABLE GLOBAL TRACING
########################################################################
def enable_global_tracing():
    """Enables tracing globally for all threads."""
    sys.settrace(trace_calls)
    threading.settrace(trace_calls)

########################################################################
# 3. DECORATOR (OPTIONAL)
########################################################################
def track_function_calls(func):
    """A decorator that enables global tracing before executing the function."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        enable_global_tracing()
        return func(*args, **kwargs)
    return wrapper

########################################################################
# 4. EXAMPLE USAGE
########################################################################
@track_function_calls
def sample_function(a, b, c="default"):
    """Example function with parameters."""
    print(f"Inside sample_function with {a}, {b}, {c}")
    return (a, b, c)  # Return something for demonstration

@track_function_calls
def main():
    """Example 'main' function that spawns threads."""
    print("Starting main...")

    # Call sample function
    return_val = sample_function(42, "hello", c="custom_value")
    print("sample_function returned:", return_val)

    # Simulate multiple threads
    threads = []
    for i in range(3):
        thread = threading.Thread(target=worker_job, name=f"Worker-{i}", args=(i,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()  # Wait for all threads to finish

@track_function_calls
def worker_job(worker_id):
    """Worker function that runs in a separate thread."""
    print(f"Inside worker thread job {worker_id}... [{threading.current_thread().name}]")
    return f"Worker {worker_id} done"

if __name__ == "__main__":
    main()

    # Append the footer if using HTML mode
    if LOG_MODE == "html":
        with open(LOG_FILE, "a") as log_file:
            log_file.write(HTML_FOOTER)

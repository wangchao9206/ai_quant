
import sys
import os

with open("debug_log.txt", "w") as log:
    def log_print(msg):
        print(msg)
        log.write(msg + "\n")
        log.flush()

    server_path = os.path.join(os.getcwd(), 'server')
    sys.path.insert(0, server_path)

    log_print("Importing core.engine...")
    try:
        import core.engine
        log_print("core.engine loaded")
    except Exception as e:
        log_print(f"core.engine failed: {e}")

    log_print("Importing core.database...")
    try:
        import core.database
        log_print("core.database loaded")
    except Exception as e:
        log_print(f"core.database failed: {e}")

    log_print("Importing core.optimizer...")
    try:
        import core.optimizer
        log_print("core.optimizer loaded")
    except Exception as e:
        log_print(f"core.optimizer failed: {e}")

    log_print("Importing core.constants...")
    try:
        import core.constants
        log_print("core.constants loaded")
    except Exception as e:
        log_print(f"core.constants failed: {e}")

    log_print("Importing core.data_manager...")
    try:
        import core.data_manager
        log_print("core.data_manager loaded")
    except Exception as e:
        log_print(f"core.data_manager failed: {e}")

    log_print("Importing core.analysis...")
    try:
        import core.analysis
        log_print("core.analysis loaded")
    except Exception as e:
        log_print(f"core.analysis failed: {e}")

    log_print("Importing main...")
    try:
        import main
        log_print("main loaded")
    except Exception as e:
        log_print(f"main failed: {e}")

    log_print("Done.")

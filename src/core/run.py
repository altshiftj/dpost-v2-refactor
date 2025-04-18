# run.py – generic entry‑point
from src.core.plugins.loader import load_device_plugin
from src.core.config.settings_store import SettingsStore
from src.core.app.device_watchdog_app import DeviceWatchdogApp
from src.core.ui.ui_tkinter import TKinterUI
from src.core.sync.sync_kadi import KadiSyncManager

def main(device_name: str = "SEM_TischREM_BLB"):
    plugin = load_device_plugin(device_name)

    # inject per‑device config
    SettingsStore.set(plugin.get_settings())

    ui = TKinterUI()
    sync = KadiSyncManager(ui=ui)
    file_processor = plugin.get_file_processor()

    app = DeviceWatchdogApp(
        ui = ui,
        sync_manager = sync,
        file_processor = file_processor,
    )
    app.run()

if __name__ == "__main__":
    main()

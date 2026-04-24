import threading

# Thread-safe in-memory store
_lock = threading.Lock()
monitors = {}

# Alert history: { device_id: [ {ALERT, email, time}, ... ] }
alert_history = {}


def get_monitor(device_id: str):
    with _lock:
        return monitors.get(device_id)

def set_monitor(device_id: str, data: dict):
    with _lock:
        monitors[device_id] = data

def update_monitor(device_id: str, updates: dict):
    with _lock:
        if device_id not in monitors:
            return False
        monitors[device_id].update(updates)
        return True

def list_monitors():
    with _lock:
        return list(monitors.items())

def monitor_exists(device_id: str):
    with _lock:
        return device_id in monitors

def add_alert(device_id: str, alert: dict):
    with _lock:
        if device_id not in alert_history:
            alert_history[device_id] = []
        alert_history[device_id].append(alert)

def get_alerts(device_id: str):
    with _lock:
        return list(alert_history.get(device_id, []))
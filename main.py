from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import time
import threading
import store

# REQUEST MODEL

class MonitorRequest(BaseModel):
    id: str
    timeout: int = Field(gt=0, description="Timeout in seconds (must be > 0)")
    alert_email: str

# LIFESPAN (replaces deprecated @app.on_event)

@asynccontextmanager
async def lifespan(app: FastAPI):
    thread = threading.Thread(target=watchdog, daemon=True)
    thread.start()
    yield


app = FastAPI(
    title="Pulse-Check API — Watchdog Sentinel",
    description="Dead Man's Switch API for critical infrastructure monitoring.",
    version="1.0.0",
    lifespan=lifespan,
)

# CREATE MONITOR

@app.post("/monitors", status_code=201)
def create_monitor(data: MonitorRequest):
    device_id = data.id

    if store.monitor_exists(device_id):
        raise HTTPException(status_code=409, detail=f"Monitor '{device_id}' already exists.")

    store.set_monitor(device_id, {
        "timeout": data.timeout,
        "email": data.alert_email,
        "last_seen": time.time(),
        "status": "active",
        "created_at": time.time(),
    })

    return {
        "message": f"Monitor '{device_id}' created successfully.",
        "device_id": device_id,
        "timeout": data.timeout,
    }


# HEARTBEAT

@app.post("/monitors/{device_id}/heartbeat")
def heartbeat(device_id: str):
    monitor = store.get_monitor(device_id)

    if monitor is None:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found.")

    if monitor["status"] == "down":
        raise HTTPException(
            status_code=409,
            detail=f"Device '{device_id}' is already down. Create a new monitor to restart tracking.",
        )

    was_paused = monitor["status"] == "paused"

    store.update_monitor(device_id, {
        "last_seen": time.time(),
        "status": "active",
    })

    return {
        "message": "Heartbeat received." + (" Monitor un-paused." if was_paused else ""),
        "device_id": device_id,
        "status": "active",
    }

# PAUSE

@app.post("/monitors/{device_id}/pause")
def pause_monitor(device_id: str):
    monitor = store.get_monitor(device_id)

    if monitor is None:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found.")

    if monitor["status"] == "down":
        raise HTTPException(status_code=409, detail=f"Device '{device_id}' is already down.")

    if monitor["status"] == "paused":
        raise HTTPException(status_code=409, detail=f"Device '{device_id}' is already paused.")

    store.update_monitor(device_id, {"status": "paused"})

    return {
        "message": f"Monitor '{device_id}' paused. Send a heartbeat to resume.",
        "device_id": device_id,
    }


# GET STATUS

@app.get("/monitors/{device_id}")
def get_monitor(device_id: str):
    monitor = store.get_monitor(device_id)

    if monitor is None:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found.")

    now = time.time()
    time_since_last_seen = now - monitor["last_seen"]
    time_remaining = None

    if monitor["status"] == "active":
        time_remaining = max(0, monitor["timeout"] - time_since_last_seen)

    return {
        "device_id": device_id,
        "status": monitor["status"],
        "timeout": monitor["timeout"],
        "alert_email": monitor["email"],
        "last_seen": monitor["last_seen"],
        "time_remaining_seconds": round(time_remaining, 1) if time_remaining is not None else None,
    }

# ALERT HISTORY  (developer's choice)

@app.get("/monitors/{device_id}/alerts")
def get_alert_history(device_id: str):
    if not store.monitor_exists(device_id):
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found.")

    alerts = store.get_alerts(device_id)

    return {
        "device_id": device_id,
        "total_alerts": len(alerts),
        "alerts": alerts,
    }



# WATCHDOG LOGIC

def watchdog():
    time.sleep(2)  # Give FastAPI time to start

    while True:
        now = time.time()

        for device_id, data in store.list_monitors():

            if data["status"] != "active":
                continue

            if now - data["last_seen"] > data["timeout"]:
                store.update_monitor(device_id, {"status": "down"})

                alert = {
                    "ALERT": f"Device {device_id} is down!",
                    "email": data["email"],
                    "time": now,
                }

                # Save to alert history
                store.add_alert(device_id, alert)

                print(alert)

        time.sleep(1)
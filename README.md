
# Pulse-Check API

A backend service that monitors remote devices using a dead man's switch pattern. Each device registers with a timeout. If it stops sending heartbeats before the timeout runs out, the system marks it as down and fires an alert.

Built with Python and FastAPI.

## The Problem It Solves

Remote devices like solar panels or weather stations are supposed to check in regularly. Without a system like this, nobody knows a device has gone offline until someone manually checks — which could be days later. This API automates that detection.

## Architecture

```
Client Device
     |
     | HTTP
     v
FastAPI (main.py)
     |
     | read/write
     v
In-memory Store (store.py)
     ^
     | polls every second
     |
Watchdog Thread (runs in background)
     |
     | when timer expires
     v
Marks device as down + saves alert to history
```

Device goes through these states:

```
  active --> paused --> active (heartbeat resumes it)
  active --> down (timer expired, alert fired)
  down --> create new monitor to start again
  
  ```


## Setup

1. Clone the repo and go into the folder:

    1. git clone https://github.com/Agahozo3/pulse-check.git
    2. cd pulse-check
    

2. Create a virtual environment and activate it:

    1. python3 -m venv venv
    2. source venv/bin/activate


3. Install dependencies:

    pip install -r requirements.txt


4. Start the server:


uvicorn main:app --reload

5. Server starts at http://127.0.0.1:8000

To test endpoints in the browser go to http://127.0.0.1:8000/docs

## Endpoints

### POST /monitors

Registers a new device and starts the countdown timer.

json
{
  "id": "device-123",
  "timeout": 60,
  "alert_email": "admin@critmon.com"
}


Returns 201 on success. Returns 409 if the device ID already exists.

### POST /monitors/{id}/heartbeat

Resets the timer for a device. Call this before the timeout runs out to keep the device marked as active. Also unpauses a paused device automatically.

Returns 200 on success. Returns 404 if device not found. Returns 409 if device is already down.

### POST /monitors/{id}/pause

Stops the timer completely. Useful when a technician is doing maintenance and does not want false alarms. Send a heartbeat to resume monitoring.

Returns 200 on success.

### GET /monitors/{id}

Returns the current state of a device including status, time remaining, and last seen time.

json
{
  "device_id": "device-123",
  "status": "active",
  "timeout": 60,
  "alert_email": "admin@critmon.com",
  "last_seen": 1745000000.0,
  "time_remaining_seconds": 45.3
}


Status can be active, paused, or down.

### GET /monitors/{id}/alerts

Returns the full history of every time this device went down.

json
{
  "device_id": "device-123",
  "total_alerts": 2,
  "alerts": [
    {
      "ALERT": "Device device-123 is down!",
      "email": "admin@critmon.com",
      "time": 1745000060.0
    }
  ]
}


## Developer's Choice

I noticed that when a device goes down the system alerts you but never saves what happened. So if a device keeps failing you have no way of knowing unless you were watching the logs the whole time.
I added the alert history so that anyone can check how many times a device has gone down and when exactly it happened. That way before a technician even goes out to the site they already know if this is the first time or the tenth time. That makes a big difference in how they approach the problem.

## Files

- main.py — all endpoints and the watchdog thread
- store.py — thread safe in memory storage
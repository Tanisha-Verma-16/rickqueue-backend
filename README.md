# 🎯 Queue API Documentation

Complete guide for integrating with RickQueue's Queue Management APIs

---

## 📋 Table of Contents

1. [Authentication](#authentication)
2. [Core Endpoints](#core-endpoints)
3. [WebSocket Events](#websocket-events)
4. [User Journey](#user-journey)
5. [Error Handling](#error-handling)
6. [Code Examples](#code-examples)

---

## 🔐 Authentication

All endpoints require Firebase ID token in Authorization header:

```http
Authorization: Bearer <FIREBASE_ID_TOKEN>
```

### Getting Firebase Token (Frontend)

```javascript
// React Native / Expo
import { getAuth } from "firebase/auth";

const auth = getAuth();
const idToken = await auth.currentUser.getIdToken();

// Use in API calls
fetch("https://api.rickqueue.com/api/v1/queue/join", {
  headers: {
    Authorization: `Bearer ${idToken}`,
    "Content-Type": "application/json",
  },
});
```

---

## 📡 Core Endpoints

### 1. Join Queue

**POST** `/api/v1/queue/join`

User joins the queue for a specific route. System automatically finds or creates a matching group.

**Request:**

```json
{
  "route_id": 1,
  "current_lat": 28.6139,
  "current_lng": 77.209,
  "women_only_preference": false
}
```

**Response (200):**

```json
{
  "success": true,
  "booking_id": 123,
  "group_id": 45,
  "group_status": "FORMING",
  "current_size": 2,
  "max_size": 4,
  "seat_number": 2,
  "position_in_queue": 2,
  "estimated_wait_mins": 3,
  "women_only": false,
  "route": {
    "origin": "Metro Station Gate 1",
    "destination": "City College",
    "distance_km": 5.2
  }
}
```

**Error Cases:**

- `400`: User already in queue
- `404`: Route not found
- `401`: Invalid auth token

**Frontend Integration:**

```javascript
const joinQueue = async (routeId, location) => {
  const response = await fetch("/api/v1/queue/join", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${idToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      route_id: routeId,
      current_lat: location.latitude,
      current_lng: location.longitude,
      women_only_preference: false,
    }),
  });

  const data = await response.json();

  // Connect to WebSocket to receive updates
  connectToGroup(data.group_id);

  return data;
};
```

---

### 2. Get Queue Status

**GET** `/api/v1/queue/status`

Get user's current queue/group status and real-time updates.

**Response (200):**

```json
{
  "in_queue": true,
  "booking_id": 123,
  "group_id": 45,
  "group_status": "FORMING",
  "current_size": 3,
  "max_size": 4,
  "your_seat": 2,
  "wait_time_seconds": 180,
  "estimated_wait_mins": 2,
  "women_only": false,
  "is_ready": false,
  "qr_code": null,
  "route": {
    "origin": "Metro Station",
    "destination": "College",
    "distance_km": 5.2
  },
  "other_passengers": [
    {
      "name": "John",
      "gender": "MALE",
      "seat": 1
    },
    {
      "name": "Sarah",
      "gender": "FEMALE",
      "seat": 3
    }
  ]
}
```

**Not in Queue:**

```json
{
  "in_queue": false,
  "message": "You are not in any queue"
}
```

**Frontend Polling:**

```javascript
// Poll every 5 seconds for status updates
const pollQueueStatus = async () => {
  setInterval(async () => {
    const response = await fetch("/api/v1/queue/status", {
      headers: { Authorization: `Bearer ${idToken}` },
    });

    const status = await response.json();
    updateUI(status);

    if (status.is_ready) {
      // Group is ready! Show QR code
      displayQRCode(status.qr_code);
    }
  }, 5000);
};
```

---

### 3. Leave Queue

**POST** `/api/v1/queue/leave`

User cancels their booking and leaves the group.

**Response (200):**

```json
{
  "success": true,
  "message": "You have left the queue"
}
```

**Frontend Integration:**

```javascript
const leaveQueue = async () => {
  const confirmed = await showConfirmDialog(
    "Are you sure you want to leave the queue?",
  );

  if (confirmed) {
    const response = await fetch("/api/v1/queue/leave", {
      method: "POST",
      headers: { Authorization: `Bearer ${idToken}` },
    });

    const result = await response.json();

    // Disconnect from WebSocket
    disconnectFromGroup();

    // Navigate back to home
    navigation.navigate("Home");
  }
};
```

---

### 4. Get Nearby Groups

**GET** `/api/v1/queue/nearby-groups?route_id=1`

See how many groups are forming on this route (helps user decision).

**Response (200):**

```json
{
  "route_id": 1,
  "forming_groups_count": 2,
  "groups": [
    {
      "group_id": 45,
      "route": "Metro → College",
      "current_size": 3,
      "max_size": 4,
      "wait_time_seconds": 120,
      "women_only": false,
      "created_at": "2026-01-27T10:30:00Z"
    },
    {
      "group_id": 46,
      "route": "Metro → College",
      "current_size": 1,
      "max_size": 4,
      "wait_time_seconds": 45,
      "women_only": false,
      "created_at": "2026-01-27T10:32:00Z"
    }
  ],
  "recommendation": "Great timing! 1 group(s) almost full - you might be the last person!"
}
```

**UI Display:**

```javascript
// Show before user joins
const showGroupInfo = (routeId) => {
  const { groups, recommendation } = await fetchNearbyGroups(routeId);

  return (
    <View>
      <Text style={styles.info}>
        {groups.length} groups forming now
      </Text>
      <Text style={styles.recommendation}>
        💡 {recommendation}
      </Text>
    </View>
  );
};
```

---

## 🔌 WebSocket Events

Connect to Socket.IO for real-time updates:

```javascript
import io from "socket.io-client";

const socket = io("wss://api.rickqueue.com", {
  auth: { token: idToken },
});

// Join group room after booking
socket.emit("join_group_room", { group_id: 45 });
```

### Event 1: Group Update

Triggered when someone joins or leaves your group.

```javascript
socket.on("group_update", (data) => {
  console.log(data);
  /*
  {
    type: 'group_update',
    group_id: 45,
    current_size: 3,
    max_size: 4,
    message: '✨ New passenger joined! (3/4)',
    timestamp: '2026-01-27T10:35:00Z'
  }
  */

  // Update UI
  setGroupSize(data.current_size);
  showNotification(data.message);
});
```

### Event 2: Group Ready

Triggered when AI dispatches your group (ready for driver assignment).

```javascript
socket.on("group_ready", (data) => {
  console.log(data);
  /*
  {
    type: 'group_ready',
    group_id: 45,
    qr_code: 'RQ-45-1738056000000',
    passenger_count: 4,
    message: '🎉 Your group is ready! (4 passengers)',
    instruction: 'A driver will be assigned soon. Have your QR code ready!',
    timestamp: '2026-01-27T10:35:00Z'
  }
  */

  // Show QR code screen
  navigation.navigate("QRCodeScreen", { qr_code: data.qr_code });
  playSuccessSound();
});
```

### Event 3: AI Decision

Triggered when AI decides to WAIT (explains why).

```javascript
socket.on("ai_decision", (data) => {
  /*
  {
    type: 'ai_decision',
    group_id: 45,
    decision: 'WAIT',
    message: 'High arrival probability (85%) - passenger likely arriving soon',
    timestamp: '2026-01-27T10:33:00Z'
  }
  */

  // Show as toast notification
  showToast(data.message, { icon: "⏳" });
});
```

### Event 4: Driver Assigned

Triggered when a driver accepts your group.

```javascript
socket.on("driver_assigned", (data) => {
  /*
  {
    type: 'driver_assigned',
    group_id: 45,
    driver_name: 'Rajesh Kumar',
    vehicle_number: 'DL-1C-1234',
    estimated_arrival_mins: 3,
    message: '🚗 Rajesh Kumar is on the way! (Vehicle: DL-1C-1234)',
    timestamp: '2026-01-27T10:40:00Z'
  }
  */

  // Navigate to driver tracking screen
  navigation.navigate("DriverTracking", {
    driver: data,
    eta: data.estimated_arrival_mins,
  });
});
```

### Event 5: User Left

Triggered when someone leaves your group.

```javascript
socket.on("user_left", (data) => {
  /*
  {
    type: 'user_left',
    group_id: 45,
    message: 'Sarah left the group. Now 2/4',
    current_size: 2,
    max_size: 4,
    timestamp: '2026-01-27T10:34:00Z'
  }
  */

  // Update passenger list
  setGroupSize(data.current_size);
  showNotification(data.message, { type: "warning" });
});
```

---

## 🚶 Complete User Journey

### Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│ USER OPENS APP                                          │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ Select Route (e.g., Metro → College)                    │
│ GET /routes (list available routes)                     │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ (Optional) Check Nearby Groups                          │
│ GET /queue/nearby-groups?route_id=1                     │
│ Shows: "2 groups forming, estimated wait 3 mins"        │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ JOIN QUEUE                                              │
│ POST /queue/join                                        │
│ Response: booking_id, group_id, seat_number            │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ CONNECT TO WEBSOCKET                                    │
│ socket.emit('join_group_room', {group_id})             │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ WAITING SCREEN                                          │
│ - Shows current group size (2/4)                        │
│ - Shows other passengers                                │
│ - Shows estimated wait time                             │
│ - Real-time updates via WebSocket                       │
│ - Option to leave queue                                 │
└────────────┬────────────────────────────────────────────┘
             │
             │ (AI runs every 30 seconds in background)
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ AI DECISION:                                            │
│ ├─ WAIT → socket.on('ai_decision')                     │
│ │   "High probability - passenger arriving soon"        │
│ │                                                       │
│ └─ DISPATCH → socket.on('group_ready')                 │
│     "🎉 Your group is ready!"                           │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ QR CODE SCREEN                                          │
│ - Display QR code (from group_ready event)             │
│ - "Show this to your driver"                            │
│ - Waiting for driver assignment...                      │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ DRIVER ASSIGNED                                         │
│ socket.on('driver_assigned')                           │
│ - Driver name, vehicle number                           │
│ - ETA: 3 minutes                                        │
│ - Live location tracking                                │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ TRIP IN PROGRESS                                        │
│ - Track ride on map                                     │
│ - Share location with friends                           │
│ - Rate driver after completion                          │
└─────────────────────────────────────────────────────────┘
```

---

## ⚠️ Error Handling

### Common Error Codes

| Code | Error            | Cause                   | Solution                  |
| ---- | ---------------- | ----------------------- | ------------------------- |
| 400  | Already in queue | User has active booking | Call `/queue/leave` first |
| 401  | Unauthorized     | Invalid/expired token   | Refresh Firebase token    |
| 404  | Not found        | Route/booking not found | Verify route exists       |
| 500  | Server error     | Internal issue          | Retry after delay         |

### Error Response Format

```json
{
  "detail": "You're already in a queue. Please cancel first."
}
```

### Handling Errors (Frontend)

```javascript
try {
  const result = await joinQueue(routeId, location);
  // Success
} catch (error) {
  if (error.status === 400) {
    // Show "Already in queue" dialog
    showAlreadyInQueueDialog();
  } else if (error.status === 401) {
    // Refresh token and retry
    await refreshAuthToken();
    retry();
  } else {
    // Generic error
    showErrorToast("Something went wrong. Please try again.");
  }
}
```

---

## 💻 Complete Code Examples

### React Native Full Integration

```javascript
import React, { useState, useEffect } from "react";
import { View, Text, Button } from "react-native";
import io from "socket.io-client";
import { getAuth } from "firebase/auth";

const QueueScreen = ({ route: selectedRoute }) => {
  const [groupStatus, setGroupStatus] = useState(null);
  const [socket, setSocket] = useState(null);

  useEffect(() => {
    // Join queue on mount
    joinQueue();

    return () => {
      // Leave queue on unmount
      leaveQueue();
      socket?.disconnect();
    };
  }, []);

  const joinQueue = async () => {
    // Get current location
    const location = await getCurrentLocation();

    // Get Firebase token
    const auth = getAuth();
    const idToken = await auth.currentUser.getIdToken();

    // Call API
    const response = await fetch(
      "https://api.rickqueue.com/api/v1/queue/join",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${idToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          route_id: selectedRoute.id,
          current_lat: location.latitude,
          current_lng: location.longitude,
          women_only_preference: false,
        }),
      },
    );

    const data = await response.json();
    setGroupStatus(data);

    // Connect to WebSocket
    connectWebSocket(data.group_id, idToken);
  };

  const connectWebSocket = (groupId, token) => {
    const newSocket = io("wss://api.rickqueue.com", {
      auth: { token },
    });

    newSocket.on("connect", () => {
      console.log("Connected to WebSocket");
      newSocket.emit("join_group_room", { group_id: groupId });
    });

    newSocket.on("group_update", (data) => {
      setGroupStatus((prev) => ({
        ...prev,
        current_size: data.current_size,
      }));
      showToast(data.message);
    });

    newSocket.on("group_ready", (data) => {
      navigation.navigate("QRCode", {
        qr_code: data.qr_code,
      });
    });

    newSocket.on("driver_assigned", (data) => {
      navigation.navigate("DriverTracking", {
        driver: data,
      });
    });

    setSocket(newSocket);
  };

  const leaveQueue = async () => {
    const auth = getAuth();
    const idToken = await auth.currentUser.getIdToken();

    await fetch("https://api.rickqueue.com/api/v1/queue/leave", {
      method: "POST",
      headers: { Authorization: `Bearer ${idToken}` },
    });
  };

  return (
    <View>
      <Text>Waiting for ride...</Text>
      <Text>
        Group: {groupStatus?.current_size}/{groupStatus?.max_size}
      </Text>
      <Text>ETA: {groupStatus?.estimated_wait_mins} mins</Text>

      <Button title="Leave Queue" onPress={leaveQueue} color="red" />
    </View>
  );
};

export default QueueScreen;
```

---

## 🔧 Testing

### Using cURL

```bash
# Get Firebase token first
export TOKEN="your_firebase_id_token"

# Join queue
curl -X POST https://api.rickqueue.com/api/v1/queue/join \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "route_id": 1,
    "current_lat": 28.6139,
    "current_lng": 77.2090,
    "women_only_preference": false
  }'

# Get status
curl -X GET https://api.rickqueue.com/api/v1/queue/status \
  -H "Authorization: Bearer $TOKEN"

# Leave queue
curl -X POST https://api.rickqueue.com/api/v1/queue/leave \
  -H "Authorization: Bearer $TOKEN"
```

---

## 📞 Support

For API issues or questions:

- GitHub Issues
- Email: dev@rickqueue.com
- Slack: #api-support

**API Version:** 1.0.0  
**Last Updated:** January 2026

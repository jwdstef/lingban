# Lingban Mobile

Flutter client for the Lingban AI companion MVP.

## Run

```powershell
flutter pub get
flutter run --dart-define=API_BASE_URL=http://localhost:8000
```

Use `http://10.0.2.2:8000` for Android emulator, or your machine LAN IP for a physical device.

## Core Flow

1. Register or log in.
2. Select a character.
3. Chat with SSE streaming.
4. Review memories.
5. Open proactive care messages from the home card.

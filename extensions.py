from flask_socketio import SocketIO, emit

socketio = SocketIO(
    async_mode="threading",
    cors_allowed_origins="*"
)
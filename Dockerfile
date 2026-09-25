# Containerized Lone Wolf Action Assistant (web/server only).
#
# This runs the HTTP app server + WebSocket terminal server headless; you use
# the app from a browser at http://localhost:8797/. The native desktop window
# (pywebview/WebView2) is Windows-only and is not part of the container.
FROM python:3.13-slim

WORKDIR /app

# Only "websockets" is needed at runtime. pywebview/pywinpty/pyinstaller in
# requirements.txt are for the Windows desktop build and are intentionally
# omitted here.
RUN pip install --no-cache-dir "websockets>=13"

# Copy the source so the image runs standalone. docker-compose bind-mounts the
# working tree over /app for live "update on the fly" edits.
COPY . /app

# Redirect books and per-player data to the mounted /data volume, and bind the
# servers to all interfaces inside the container (published to localhost).
ENV LOCALAPPDATA=/data \
    LONEWOLF_SAA_BOOKS_DIR=/data/books \
    LONEWOLF_SAA_HTTP_HOST=0.0.0.0 \
    LONEWOLF_SAA_WS_HOST=0.0.0.0 \
    LONEWOLF_REDUX_HTTP_PORT=8797 \
    LONEWOLF_REDUX_WS_PORT=8798 \
    PYTHONUNBUFFERED=1

EXPOSE 8797 8798

CMD ["python", "serve.py"]

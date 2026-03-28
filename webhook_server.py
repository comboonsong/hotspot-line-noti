#!/usr/bin/env python3
"""
LINE Webhook Server (ใช้สำหรับรับ Group ID)

เมื่อเพิ่มบอทเข้ากลุ่ม LINE จะได้รับ event "join" พร้อม Group ID
สคริปต์นี้จะแสดง Group ID ให้คุณนำไปใส่ใน .env

Usage:
    python webhook_server.py
"""

import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

PORT = 8000


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length > 0 else b""
        except Exception:
            body = b""

        # Always respond 200 first
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "ok"}')

        if not body:
            logger.info("Received empty POST (webhook verification)")
            return

        try:
            data = json.loads(body)
            events = data.get("events", [])

            if not events:
                logger.info("Received POST with empty events (webhook verification)")
                return

            for event in events:
                event_type = event.get("type", "")
                source = event.get("source", {})
                source_type = source.get("type", "")

                logger.info("━" * 50)
                logger.info("Event type: %s", event_type)
                logger.info("Source type: %s", source_type)

                if source_type == "group":
                    group_id = source.get("groupId", "")
                    logger.info("=" * 50)
                    logger.info("🎉 GROUP ID FOUND!")
                    logger.info("GROUP ID: %s", group_id)
                    logger.info("=" * 50)
                    logger.info("👉 นำค่านี้ไปใส่ใน .env → LINE_GROUP_ID=%s", group_id)
                    logger.info("=" * 50)

                if source_type == "user":
                    user_id = source.get("userId", "")
                    logger.info("User ID: %s", user_id)

                if event_type == "message":
                    message = event.get("message", {})
                    logger.info("Message type: %s", message.get("type", ""))
                    logger.info("Message text: %s", message.get("text", ""))

        except json.JSONDecodeError:
            logger.warning("Could not parse request body as JSON")

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"LINE Webhook Server is running!")


def main():
    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    logger.info("=" * 50)
    logger.info("LINE Webhook Server started on port %d", PORT)
    logger.info("=" * 50)
    logger.info("")
    logger.info("ขั้นตอนถัดไป:")
    logger.info("1. เปิด terminal ใหม่ แล้วรัน: ngrok http %d", PORT)
    logger.info("2. คัดลอก HTTPS URL จาก ngrok (เช่น https://xxxx.ngrok-free.app)")
    logger.info("3. ไปที่ LINE Developers Console → Messaging API → Webhook URL")
    logger.info("4. ใส่ URL: https://xxxx.ngrok-free.app")
    logger.info("5. เปิด Use webhook → ON")
    logger.info("6. เพิ่มบอทเข้ากลุ่ม LINE → จะเห็น Group ID ใน log")
    logger.info("")
    logger.info("กด Ctrl+C เพื่อหยุด server")
    logger.info("=" * 50)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped.")
        server.server_close()


if __name__ == "__main__":
    main()

import logging

from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
)

logger = logging.getLogger(__name__)


def send_group_message(
    channel_access_token: str,
    group_id: str,
    message_texts: list[str],
) -> None:
    """
    Send text message bubbles to a LINE group (max 5 at a time).

    Args:
        channel_access_token: LINE Channel Access Token.
        group_id: LINE Group ID.
        message_texts: A list of message text strings (each becomes a bubble).
    """
    configuration = Configuration(access_token=channel_access_token)

    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)

        # Truncate any single bubble that is too long (LINE limit is 5000 chars)
        safe_messages = []
        for text in message_texts:
            if len(text) > 5000:
                truncated = text[:4900] + "\n\n⚠️ ข้อความยาวเกินไป แสดงเฉพาะบางส่วน"
                safe_messages.append(truncated)
            else:
                safe_messages.append(text)

        # LINE API can push max 5 message objects per request
        for i in range(0, len(safe_messages), 5):
            batch = safe_messages[i : i+5]
            request = PushMessageRequest(
                to=group_id,
                messages=[TextMessage(text=m) for m in batch],
            )

            try:
                messaging_api.push_message(request)
                logger.info(
                    "Messages (batch %d) sent to group %s successfully.", 
                    (i // 5) + 1, group_id
                )
            except Exception as e:
                logger.error("Failed to send message batch to group %s: %s", group_id, e)
                raise

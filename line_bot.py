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
    message_text: str,
) -> None:
    """
    Send a text message to a LINE group.

    Args:
        channel_access_token: LINE Channel Access Token.
        group_id: LINE Group ID.
        message_text: The message text to send.
    """
    configuration = Configuration(access_token=channel_access_token)

    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)

        # LINE text message limit is 5000 characters
        # If message is too long, truncate with a notice
        if len(message_text) > 5000:
            truncated = message_text[:4900]
            truncated += "\n\n⚠️ ข้อความยาวเกินไป แสดงเฉพาะบางส่วน"
            message_text = truncated

        request = PushMessageRequest(
            to=group_id,
            messages=[TextMessage(text=message_text)],
        )

        try:
            messaging_api.push_message(request)
            logger.info("Message sent to group %s successfully.", group_id)
        except Exception as e:
            logger.error("Failed to send message to group %s: %s", group_id, e)
            raise

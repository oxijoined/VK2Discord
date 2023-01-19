import base64
import json
import time

import requests
import vk_api
from discord_webhook import DiscordEmbed, DiscordWebhook
from vk_api.bot_longpoll import VkBotEventType, VkBotLongPoll

token = "" # VK Bot token (With longpool enabled)
discordToken = "" # Discord token with permission to manage webhooks
discordChannelID = 0 # Discord channel ID where messages will be sent
vkChatID = 0

vk = vk_api.VkApi(token=token)
longpoll = VkBotLongPoll(vk, vkChatID)


def deleteWebHook(id: int, token: str):

    headers = {
        "Authorization": discordToken,
        "Content-Type": "application/json",
    }

    request = requests.delete(
        f"https://discord.com/api/webhooks/{id}/{token}", headers=headers
    )
    if "The resource is being rate limited." in str(request.text):
        sleepTime = json.loads(request.text)["retry_after"]
        print(f"[!] Sleeping for {sleepTime}")
        time.sleep(sleepTime)
        time.sleep(int(sleepTime) + 2)
        deleteWebHook(id, token)


def urlToBase64(url: str):
    response = requests.get(url)
    binary_content = response.content
    base64_data = base64.b64encode(binary_content)
    return f'data:image/png;base64,{base64_data.decode("utf-8")}'


def createWebhook(name: str, avatar: str):

    headers = {
        "Authorization": discordToken,
        "Content-Type": "application/json",
    }
    data = {"name": name, "avatar": avatar}
    request = requests.post(
        f"https://discord.com/api/channels/{discordChannelID}/webhooks",
        headers=headers,
        json=data,
    )
    if "The resource is being rate limited." not in str(request.text):
        return json.loads(request.text)["token"], json.loads(request.text)["id"]
    sleepTime = json.loads(request.text)["retry_after"]
    print(f"[!] Sleeping for {sleepTime}")
    time.sleep(int(sleepTime) + 2)
    token, WebhookID = createWebhook(name, avatar)
    return token, WebhookID


def sendToDiscord(webhook: str, text: str, WebhookID: int, photoURL=None):
    if photoURL is None:
        webhook_ = DiscordWebhook(
            url=f"https://discord.com/api/webhooks/{WebhookID}/{webhook}",
            content=text,
            rate_limit_retry=True,
        )
    else:
        webhook_ = DiscordWebhook(
            url=f"https://discord.com/api/webhooks/{WebhookID}/{webhook}",
            rate_limit_retry=True,
        )
        embed = DiscordEmbed(title="Фото", description="", color="03b2f8")
        embed.set_image(url=photoURL)
        webhook_.add_embed(embed)
    response = webhook_.execute()


def main():
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            user = vk.method(
                "users.get",
                {
                    "user_ids": event.message.from_id,
                    "fields": "has_photo,photo_400_orig",
                },
            )
            userFirstName = user[0]["first_name"]
            userLastName = user[0]["last_name"]
            hasPhoto = user[0]["has_photo"]
            userMessage = event.message.text
            if userMessage == "" and event.message.attachments == []:
                break
            elif userMessage == "":
                typeOfContent = event.message.attachments[0]["type"]
                if typeOfContent == "photo":
                    photoURLSent = event.message.attachments[0]["photo"]["sizes"][5][
                        "url"
                    ]
            else:
                typeOfContent = "text"

            if hasPhoto == 1:
                photoURL = user[0]["photo_400_orig"]
            else:
                photoURL = "https://vk.com/images/camera_400.png"

            photoBase64 = urlToBase64(photoURL)
            token, WebhookID = createWebhook(
                f"{userFirstName} {userLastName}", photoBase64
            )
            if typeOfContent == "photo":
                sendToDiscord(token, userMessage, WebhookID, photoURLSent)
            elif typeOfContent == "text":
                sendToDiscord(token, userMessage, WebhookID)
            deleteWebHook(WebhookID, token)

            print(f"{userFirstName} {userLastName}: {userMessage}")


if __name__ == "__main__":
    main()

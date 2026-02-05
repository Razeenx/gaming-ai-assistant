import requests

# Замени на свои данные из Twitch Developer Console
CLIENT_ID = "сюда_вставь_свой_client_id"
CLIENT_SECRET = "сюда_вставь_свой_client_secret"

# Получение Access Token
response = requests.post(
    "https://id.twitch.tv/oauth2/token",
    params={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
)

if response.status_code == 200:
    data = response.json()
    print(f"Client ID: {CLIENT_ID}")
    print(f"Access Token: {data['access_token']}")
    print(f"Expires in: {data['expires_in']} секунд")
else:
    print(f"Ошибка: {response.status_code}")
    print(response.text)

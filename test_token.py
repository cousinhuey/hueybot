import requests

CLIENT_ID = "cumabotcb57rk0l"
CLIENT_SECRET = "jt9pyrmsuzbrcrr"
REFRESH_TOKEN = "-hX7Funk8a8AAAAAAAAAAQsbBJba5vOXQiGLiI1S6AFAdhRvgsX0dBvLN4D98K58"

data = {
    "grant_type": "refresh_token",
    "refresh_token": REFRESH_TOKEN,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
}

r = requests.post("https://api.dropboxapi.com/oauth2/token", data=data)
print(r.status_code)
print(r.text)
import requests

CLIENT_ID = "cumabotcb57rk0l"
CLIENT_SECRET = "jt9pyrmsuzbrcrr"
REFRESH_TOKEN = "-hX7Funk8a8AAAAAAAAAAQsbBJba5vOXQiGLiI1S6AFAdhRvgsX0dBvLN4D98K58"

data = {
    "grant_type": "refresh_token",
    "refresh_token": REFRESH_TOKEN,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
}

r = requests.post("https://api.dropboxapi.com/oauth2/token", data=data)
print(r.status_code)
print(r.text)

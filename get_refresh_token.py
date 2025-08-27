import dropbox

# 🔑 Hier App Key und Secret aus deiner App Console eintragen
APP_KEY = "bwmbvhvhg74009d"
APP_SECRET = "gfpqqt6ncmm73e1"

def main():
    # 1. OAuth Flow starten
    auth_flow = dropbox.DropboxOAuth2FlowNoRedirect(APP_KEY, APP_SECRET, token_access_type="offline")

    # 2. User zu Dropbox-URL schicken
    authorize_url = auth_flow.start()
    print("1. Gehe zu dieser URL: ", authorize_url)
    print("2. Logge dich ein und erlaube der App Zugriff.")
    print("3. Kopiere den Code hierher:")

    # 3. Code vom User abfragen
    auth_code = input("Code hier einfügen: ").strip()

    # 4. Token anfordern
    oauth_result = auth_flow.finish(auth_code)

    print("\n✅ Access Token: ", oauth_result.access_token)
    print("✅ Refresh Token: ", oauth_result.refresh_token)
    print("✅ UID: ", oauth_result.user_id)

if __name__ == "__main__":
    main()

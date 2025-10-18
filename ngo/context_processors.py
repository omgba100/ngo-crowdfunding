def languages(request):
    return {
        "languages": [
            {"code": "fr", "name": "Français", "flag": "🇫🇷"},
            {"code": "en", "name": "English", "flag": "🇬🇧"},
            {"code": "nl", "name": "Nederlands", "flag": "🇳🇱"},
            {"code": "es", "name": "Español", "flag": "🇪🇸"},
        ]
    }
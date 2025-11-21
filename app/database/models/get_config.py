from app.Config import ENV_SETTINGS


def load_env(key: str, default: str | None = None) -> str | None:
    return getattr(ENV_SETTINGS, key, default)


if __name__ == "__main__":
    key = "GROQ_API_KEY"
    print(load_env(key))
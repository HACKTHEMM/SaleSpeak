import os
from dotenv import load_dotenv


load_dotenv()


def load_env(key: str, default: str | None = None) -> str | None:
    return os.getenv(key, default)


if __name__ == "__main__":
    key = "MODEL_ID"
    print(load_env(key))
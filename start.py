from app.Config import ENV_SETTINGS
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=ENV_SETTINGS.PORT, reload=True)
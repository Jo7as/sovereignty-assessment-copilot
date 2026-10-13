from fastapi import FastAPI

app = FastAPI(title="Sovereignty Assessment Copilot")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

"""Application entry point.

This module serves as the entry point for running the FastAPI application.
It creates and configures the FastAPI app instance and includes all API routers.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="localhost", port=8000, reload=True)

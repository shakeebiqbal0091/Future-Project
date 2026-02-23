from .core.database import create_all_tables

if __name__ == "__main__":
    create_all_tables()
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
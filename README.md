# REMOCLIC v2

A fast, modern API built with [FastAPI](https://fastapi.tiangolo.com/).

## Prerequisites
- Python 3
- Linux or macOS environment (for the default terminal commands)

## Setup Instructions

If this is your first time setting up the project, follow these steps:

1. **Create the virtual environment**:
   We use a virtual environment to isolate the project's dependencies from the rest of your system.
```bash
python3 -m venv .venv
```

2. **Activate the virtual environment**:
   You must activate the environment every time you open a new terminal to work on this project.
```bash
source .venv/bin/activate
```
   *Note: Your terminal prompt should now be prefixed with `(.venv)`.*

3. **Install dependencies**:
   Once inside the activated environment, install the required packages from `requirements.txt`.
```bash
pip install -r requirements.txt
```

## Running the Project

**Important**: Ensure your virtual environment is active (`source .venv/bin/activate`) before running the server.

To start the development server, run:
```bash
uvicorn app.main:app --reload
```
- `app.main` refers to the `app/main.py` file.
- `app` is the FastAPI instance created inside `main.py`.
- `--reload` tells the server to automatically restart every time you save changes to your code.

or if you use the modern fastapi cli:

```bash
fastapi dev app/main.py
```

Your API will now be running at **`http://127.0.0.1:8000`**.

## Interactive Documentation

FastAPI automatically generates beautiful, interactive documentation for your API. With your server running, you can view and test your endpoints directly in the browser:

- **Swagger UI (Interactive Testing)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc (Alternative Documentation)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## Docker Deployment

You can also run the application using Docker and Docker Compose:

1. **Build the Docker image**:
```bash
docker build -t remoclic-be:latest .
```

2. **Start the container using Docker Compose**:
```bash
docker compose up -d
```

3. **Access the API**:
The API will be available at [http://localhost:8000](http://localhost:8000).

4. **Check logs**:
```bash
docker compose logs -f
```


.PHONY: run dev install docker

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --host 127.0.0.1 --port 8000

dev:
	uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

docker:
	docker build -t chirp . && docker run --rm -p 8000:8000 chirp

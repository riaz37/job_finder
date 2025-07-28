.PHONY: install dev api streamlit db-generate db-push test clean

# Install dependencies
install:
	pip install -r requirements.txt

# Development setup
dev: install
	prisma generate
	@echo "Development environment ready!"

# Run FastAPI server
api:
	python run_api.py

# Run Streamlit app
streamlit:
	python run_streamlit.py

# Generate Prisma client
db-generate:
	prisma generate

# Push database schema
db-push:
	prisma db push

# Run tests
test:
	pytest

# Clean up
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
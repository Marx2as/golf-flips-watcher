PYTHON=python3

.PHONY: run test format

# Run the FastAPI app locally using uvicorn and start the worker in the
# background.  When using docker-compose this target is not required.
run:
	@echo "Starting API and worker..."
	$(PYTHON) -m uvicorn golf_flip_app.app:app --reload & \
	$(PYTHON) -m golf_flip_app.worker

# Execute the unit test suite
test:
	$(PYTHON) -m pytest -q

# Format the codebase with black
format:
	black golf_flip_app

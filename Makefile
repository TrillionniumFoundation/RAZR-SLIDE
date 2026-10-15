.PHONY: test
test:
	uv run --locked python -B tools/verify.py

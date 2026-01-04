---
description: How to set up the python environment
---

Since the system python is missing `ensurepip` and `python3-venv` packages, we cannot use the standard `python -m venv` command. We use `virtualenv` instead.

1. Create the virtual environment (requires python3-venv installed):
   ```bash
   python3 -m venv .venv
   ```

2. Activate the virtual environment:
   ```bash
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run tests to verify:
   ```bash
   export PYTHONPATH=$PYTHONPATH:.
   .venv/bin/python -m pytest tests/
   ```

5. Run the application:
   ```bash
   .venv/bin/streamlit run src/app.py
   ```

#!/bin/bash
cd "$(dirname "$0")"
if [ ! -f ".venv/bin/python" ]; then
  echo "Virtual environment not found."
  echo "Please follow README.md first."
  read -p "Press Enter to close..."
  exit 1
fi
".venv/bin/python" -m streamlit run app.py

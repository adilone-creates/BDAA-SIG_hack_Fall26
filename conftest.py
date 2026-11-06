"""Pytest configuration: ensure the repo root is on sys.path so `src` is importable."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

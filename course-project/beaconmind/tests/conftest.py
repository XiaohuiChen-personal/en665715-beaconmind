"""Shared pytest fixtures for BeaconMind.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the course_root and repo_root fixtures.
"""
import pytest

import beaconmind


@pytest.fixture
def course_root():
    return beaconmind.course_root()


@pytest.fixture
def repo_root(course_root):
    return course_root.parent

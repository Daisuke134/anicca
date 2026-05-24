#!/usr/bin/env python3
from typing import Iterable


def print_header(title: str) -> None:
    print(f"\n{title}")
    print("=" * len(title))


def print_kv(label: str, value: str) -> None:
    print(f"{label}: {value}")


def print_list(items: Iterable[str], prefix: str = "- ") -> None:
    for item in items:
        print(f"{prefix}{item}")

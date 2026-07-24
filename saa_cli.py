#!/usr/bin/env python3
"""Console entry point used exclusively by the embedded terminal."""

from __future__ import annotations

import lonewolf_redux


def main() -> int:
    lonewolf_redux.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

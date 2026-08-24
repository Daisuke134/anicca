"""Compatibility entrypoint for the bounded model browser runtime."""

from .browser_agent.runtime import main


if __name__ == "__main__":
    raise SystemExit(main())

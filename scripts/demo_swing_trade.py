"""Compatibility wrapper for the canonical Milestone 1 CLI demo."""

from trading_system.app.cli import demo_planned_trade


def main() -> None:
    """Run the canonical Milestone 1 demo."""
    demo_planned_trade()


if __name__ == "__main__":
    main()

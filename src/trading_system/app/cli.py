"""Typer command-line entrypoint for local trading workflows."""

import typer

app = typer.Typer(help="Structured discretionary trading system.")


@app.command()
def version() -> None:
    """Print the scaffold version."""
    typer.echo("trading-system 0.1.0")


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()

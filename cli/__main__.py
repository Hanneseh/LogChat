import os

import typer

from src import LogChat

USER_ID: int = os.getenv("USER_ID", "4")


def chat():
    logchat = LogChat(user_id=USER_ID)
    logchat_opener = logchat.get_opener()
    typer.echo(
        f"{typer.style('LogChat:', fg=typer.colors.BLACK, bold=True)} {logchat_opener}"
    )

    while True:
        user_input = typer.prompt(
            typer.style("You", fg=typer.colors.BRIGHT_BLUE, bold=True)
        )

        if user_input.lower() in {"exit", "quit"}:
            break

        output = logchat.run(user_input)

        typer.echo(
            f"{typer.style('LogChat:', fg=typer.colors.BLACK, bold=True)} {output}"
        )
    logchat.post_interaction_routine()


if __name__ == "__main__":
    typer.run(chat)

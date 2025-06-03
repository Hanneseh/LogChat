import typer

from src import LogChat

USER_ID: int = 1


def chat():
    logchat = LogChat(user_id=USER_ID, state_saver="memory")
    user_name = logchat.get_user_name()
    typer.echo(
        f"{typer.style('LogChat:', fg=typer.colors.BLACK, bold=True)} Hi {user_name}! How are you?"
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


if __name__ == "__main__":
    typer.run(chat)

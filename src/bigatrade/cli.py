import typer

app = typer.Typer(help="A股一周强势股捕捉与回测工具。")


@app.command()
def recommend(date: str, top: int = 30) -> None:
    """按指定交易日生成强势股推荐列表。"""
    typer.echo(f"recommend date={date} top={top}")


@app.command()
def backtest(start: str, end: str) -> None:
    """按历史区间回测一周 10% 目标策略。"""
    typer.echo(f"backtest start={start} end={end}")

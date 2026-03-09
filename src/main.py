import typer
from rich import print
import tools
from agent import ask_llm
from els_model import ELS_LAYERS
app = typer.Typer()
@app.command()
def layers():
    """Show ELS layers"""
    for i, layer in ELS_LAYERS.items():
        print(f"[bold]{i}[/bold] - {layer['name']}")
@app.command()
def scan():
    """Scan cluster"""
    nodes = tools.kubectl_nodes()
    pods = tools.kubectl_pods()
    print("[bold green]Nodes[/bold green]")
    print(nodes)
    print("[bold green]Pods[/bold green]")
    print(pods)
@app.command()
def ask(question: str):
    """Ask the AI coach"""
    context = tools.kubectl_nodes() + tools.kubectl_pods()
    answer = ask_llm(question, context)
    print(answer)
if __name__ == "__main__":
    app()

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
    result = ask_llm(question, context)

    if result.get("error"):
        print(f"[red]LLM error: {result['error']}[/red]")
        return

    print("\n[bold]Summary[/bold]")
    print(result.get("summary", ""))

    print("\n[bold]Answer[/bold]")
    print(result.get("answer", ""))

    els = result.get("els", {})
    print("\n[bold]ELS[/bold]")
    print(f"Layer: {els.get('layer', '')}")
    print(els.get("explanation", ""))

    next_steps = els.get("next_steps", [])
    if next_steps:
        print("\n[bold]Next Steps[/bold]")
        for s in next_steps:
            print(f"- {s}")

    learning = result.get("learning", {})
    print("\n[bold]Learning[/bold]")

    print("\n[Kubernetes]")
    print(learning.get("kubernetes", ""))

    print("\n[AI / Agents]")
    print(learning.get("ai", ""))

    print("\n[Platform]")
    print(learning.get("platform", ""))

    print("\n[Product]")
    print(learning.get("product", ""))


if __name__ == "__main__":
    app()

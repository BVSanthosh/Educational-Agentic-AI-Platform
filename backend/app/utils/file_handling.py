from pathlib import Path

def read_prompt(filename: str) -> str:
    prompt: str = ""
    prompt_path: Path = Path(__file__).resolve().parent.parent / "prompts" / filename

    with open(prompt_path, "r") as file:
        prompt = file.read()

    return prompt
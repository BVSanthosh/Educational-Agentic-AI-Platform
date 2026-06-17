from pathlib import Path

def read_prompt(filename: str) -> str:
    prompt: str = ""

    with open(Path.cwd() / filename, "r") as file:
        prompt = file.read()

    return prompt
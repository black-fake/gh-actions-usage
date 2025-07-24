#!/usr/bin/env python3

import os
import uuid


path = "helm/templates"

def ensure_path():
    if not os.path.exists(path):
        os.makedirs(path)

def write_file(name, content):
    ensure_path()

    with open(os.path.join(path, name), "w") as f:
        f.write(content)

def create_files(file_contents: dict):
    for file_name, file_content in file_contents.items():
        write_file(file_name, file_content)

def generate_content() -> str:
    run_id=str(uuid.uuid4())

    content = f"UUID={run_id}"

    return content

def main():
    files = {
        "deployment.yaml": generate_content(),
        "service.yaml": generate_content(),
        "ingress.yaml": generate_content()
    }

    create_files(files)

if __name__ == "__main__":
    main()
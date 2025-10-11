def write_output(content, filename="output.md"):
    with open(filename, "w", encoding='utf-8') as file:
        file.write(content)

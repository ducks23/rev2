import subprocess



def lscpu():
    def format_key(lscpu_key):
        key_lower = lscpu_key.lower()
        replace_hyphen = key_lower.replace("-", "_")
        replace_lparen = replace_hyphen.replace("(", "")
        replace_rparen = replace_lparen.replace(")", "")
        replace_empty_string = replace_rparen.replace(" ", "_")
        return replace_empty_string

    lscpu_out = subprocess.check_output(['lscpu'])
    lscpu_lines = lscpu_out.decode().strip().split("\n")

    return {
        format_key(line.split(":")[0].strip()): line.split(":")[1].strip()
        for line in lscpu_lines
    }

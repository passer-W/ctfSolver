import base64

def run(params):
    return base64.b64decode(params.encode()).decode("utf-8")
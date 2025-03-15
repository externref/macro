# Macro Web Framework

Macro is a simple and lightweight web framework for handling HTTP requests with support for dynamic paths and type casting. It is designed to be easy to use and integrate with ASGI applications.

## Features

- **Dynamic Routing**: Define routes with dynamic path segments.
- **Type Casting**: Automatically cast path variables to the appropriate types.
- **Response Handling**: Easily create and send various types of HTTP responses.
- **ASGI Compatibility**: Fully compatible with ASGI applications.

## Installation

To install Macro, use pip:

```sh
pip install git+https://github.com/externref/macro
```

## Quick Start

Here's a quick example to get you started with Macro:

```python
from macro.server import Macro
from macro.response import Response

app = Macro()

@app.route("/", method="GET")
async def homepage(request, response_cls):
    return response_cls.text("Welcome to Macro!")

@app.route("/hello/{name}", method="GET")
async def greet(request, response_cls, name: str):
    return response_cls.text(f"Hello, {name}!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
```


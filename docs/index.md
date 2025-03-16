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
from macro import Macro, Request, Response 

macro = Macro()

@macro.get("/")
async def index(request: Request):
    return Response.text("Hello, world!")

@macro.get("/html")
async def html(request: Request):
    return Response.html("<h1>Hello, world!</h1>")

@macro.get("/json")
async def json(request: Request):
    return Response.json({"message": "Hello, world!"})

@macro.get("/redirect")
async def redirect(request: Request):
    return Response.redirect("/")

```


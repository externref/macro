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

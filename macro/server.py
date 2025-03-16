from __future__ import annotations

import re
import typing
from inspect import Parameter, signature

from macro.request import Request, RequestHeader
from macro.response import Response

if typing.TYPE_CHECKING:
    import asgiref.typing as asgiref_typing

RouteT: typing.TypeAlias = typing.Callable[
    [Request], typing.Awaitable[Response]
]
"""Type for route callbacks."""


class Macro:
    """
    A simple web framework for handling HTTP requests with support for dynamic paths and type casting.
    """

    def __init__(self):
        self.routes: dict[str, dict[str, RouteT]] = {}

    async def __call__(self, scope: asgiref_typing.Scope, receive, send) -> None:
        if scope["type"] == "http":
            await self.handle_http(scope, receive, send)
        else:
            await send(
                {
                    "type": "http.response.start",
                    "status": 400,
                    "headers": [(b"content-type", b"text/plain")],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b"Only HTTP requests are supported",
                }
            )

    async def handle_http(self, scope: asgiref_typing.HTTPScope, receive, send) -> None:
        """
        Handle HTTP requests.

        :param scope: The scope of the request.
        :param receive: The receive channel to get request data.
        :param send: The send channel to send response data.
        """
        headers, body = await self._parse(scope, receive)
        path = scope["path"]
        method = scope["method"]
        fn, path_vars = self._find_route(path, method)
        if fn is None:
            response = Response(status=404, body=b"Not Found")
        else:
            try:
                path_vars = self._cast_path_vars(fn, path_vars)
            except ValueError:
                response = Response(status=404, body=b"Not Found")
            else:
                request = Request(headers=headers, body=body)
                response = await fn(request, **path_vars)
            await response.send(send)

    def _find_route(
        self, path: str, method: str
    ) -> typing.Tuple[typing.Optional[RouteT], dict]:
        for route_path, methods in self.routes.items():
            match = re.fullmatch(route_path, path)
            if match and method in methods:
                return methods[method], match.groupdict()
        return None, {}

    def _cast_path_vars(self, fn: RouteT, path_vars: dict) -> dict:
        """
        Cast path variables to the appropriate types.

        :param fn: The route handler function.
        :param path_vars: The path variables.
        :return: The casted path variables.
        :raises ValueError: If a path variable cannot be casted to the appropriate type.
        """
        sig = signature(fn)
        for name, param in sig.parameters.items():
            if name in path_vars and param.annotation != Parameter.empty:
                try:
                    path_vars[name] = param.annotation(path_vars[name])
                except (TypeError, ValueError):
                    raise ValueError(f"Invalid type for path variable '{name}'")
        return path_vars

    async def _parse(
        self, scope: asgiref_typing.HTTPScope, receive
    ) -> tuple[RequestHeader, bytes]:
        headers = RequestHeader()
        headers._method = scope.get("method", "")
        headers._path = scope.get("path", "")
        headers._http_version = f"HTTP/{scope.get('http_version', '1.1')}"

        for name, value in scope.get("headers", []):
            headers[name.decode("latin1")] = value.decode("latin1")

        body = b""
        more_body = True

        while more_body:
            message = await receive()
            if message["type"] == "http.request":
                body += message.get("body", b"")
                more_body = message.get("more_body", False)

        return headers, body

    def route(
        self, path: str, method: str = "GET"
    ) -> typing.Callable[[RouteT], RouteT]:
        """
        Decorator to register a route handler for a specific path and method.

        :param path: The route path, which can include dynamic segments.
        :param method: The HTTP method (default is "GET").
        :return: The decorator function.
        """

        def decorator(func: RouteT) -> RouteT:
            # Convert dynamic path to regex with named groups
            path_regex = re.sub(r"{([^/]+)}", r"(?P<\1>[^/]+)", path)
            if path_regex not in self.routes:
                self.routes[path_regex] = {}

            self.routes[path_regex][method] = func
            return func

        return decorator

    def get(self, path: str) -> typing.Callable[[RouteT], RouteT]:
        """
        Decorator to register a route handler for a GET request.

        :param path: The route path, which can include dynamic segments.
        :return: The decorator function.
        """
        return self.route(path, "GET")

    def post(self, path: str) -> typing.Callable[[RouteT], RouteT]:
        """
        Decorator to register a route handler for a POST request.

        :param path: The route path, which can include dynamic segments.
        :return: The decorator function.
        """
        return self.route(path, "POST")

    def put(self, path: str) -> typing.Callable[[RouteT], RouteT]:
        """
        Decorator to register a route handler for a PUT request.

        :param path: The route path, which can include dynamic segments.
        :return: The decorator function.
        """
        return self.route(path, "PUT")

    def delete(self, path: str) -> typing.Callable[[RouteT], RouteT]:
        """
        Decorator to register a route handler for a DELETE request.

        :param path: The route path, which can include dynamic segments.
        :return: The decorator function.
        """
        return self.route(path, "DELETE")

    def head(self, path: str) -> typing.Callable[[RouteT], RouteT]:
        """
        Decorator to register a route handler for a HEAD request.

        :param path: The route path, which can include dynamic segments.
        :return: The decorator function.
        """
        return self.route(path, "HEAD")

    def options(self, path: str) -> typing.Callable[[RouteT], RouteT]:
        """
        Decorator to register a route handler for an OPTIONS request.

        :param path: The route path, which can include dynamic segments.
        :return: The decorator function.
        """
        return self.route(path, "OPTIONS")

    def patch(self, path: str) -> typing.Callable[[RouteT], RouteT]:
        """
        Decorator to register a route handler for a PATCH request.

        :param path: The route path, which can include dynamic segments.
        :return: The decorator function.
        """
        return self.route(path, "PATCH")

    def trace(self, path: str) -> typing.Callable[[RouteT], RouteT]:
        """
        Decorator to register a route handler for a TRACE request.

        :param path: The route path, which can include dynamic segments.
        :return: The decorator function.
        """
        return self.route(path, "TRACE")

    def connect(self, path: str) -> typing.Callable[[RouteT], RouteT]:
        """
        Decorator to register a route handler for a CONNECT request.

        :param path: The route path, which can include dynamic segments.
        :return: The decorator function.
        """
        return self.route(path, "CONNECT")

    def any(self, path: str) -> typing.Callable[[RouteT], RouteT]:
        """
        Decorator to register a route handler for any HTTP method.

        :param path: The route path, which can include dynamic segments.
        :return: The decorator function.
        """

        def decorator(func: RouteT) -> RouteT:
            for method in [
                "GET",
                "POST",
                "PUT",
                "DELETE",
                "HEAD",
                "OPTIONS",
                "PATCH",
                "TRACE",
                "CONNECT",
            ]:
                self.route(path, method)(func)
            return func

        return decorator

    def static(self, path: str, file_path: str) -> RouteT:
        """
        Serve a static file from the given path.

        :param path: The route path.
        :param file_path: The path to the file to serve.
        :return: The route handler.
        """

        async def handler(request: Request) -> Response:
            try:
                with open(file_path, "rb") as file:
                    body = file.read()
            except FileNotFoundError:
                return Response(status=404, body=b"Not Found")
            return Response(body=body)

        return self.get(path)(handler)

    def redirect(self, path: str, location: str, status: int = 302) -> RouteT:
        """
        Redirect requests to a different location.

        :param path: The route path.
        :param location: The location to redirect to.
        :param status: The HTTP status code (default is 302).
        """

        async def handler(request: Request) -> Response:
            return Response(status=status, headers={"Location": location})

        return self.get(path)(handler)

    def error(self, status: int, message: str) -> RouteT:
        """
        Return an error response.

        :param status: The HTTP status code.
        :param message: The error message.
        :return: The route handler.
        """

        async def handler(request: Request) -> Response:
            return Response(status=status, body=message.encode())

        return handler  # type: ignore

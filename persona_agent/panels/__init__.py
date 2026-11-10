"""Parts of the local page beyond its four first views.

Each module here adds its routes with `mount(app, workspace, body)`:
`app` is the page's FastAPI app (every `/api/...` route is already behind the
local token and the same-origin check), `workspace` the page's
`welcome.Workspace`, and `body` reads a request's JSON object
(`payload = await body(request)`). A `ValueError` whose text is a code the page
knows becomes a 400 `{"error": code}`; add the code to `ERRORS` in the module
and it is let through.

The page side is `static/welcome/panels/<name>.js` and `<name>.css`.
"""

"""Builds the dashboard.
index.html     = standalone page (for GitHub Pages / double-click), with the doctype and viewport meta.
artifact.html  = same page without the wrapper, as the hosted-artifact skeleton adds its own."""
t = open("template.html").read(); d = open("data.json").read()
assert "__DATA__" in t
body = t.replace("__DATA__", d, 1)
open("artifact.html", "w").write(body)
open("index.html", "w").write('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n' + body + "\n</html>\n")
print("wrote index.html and artifact.html", round(len(body)/1024), "KB")

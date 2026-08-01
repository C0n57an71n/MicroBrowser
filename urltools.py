def split_url(url):
    url = url.strip()
    if "://" not in url:
        url = "https://" + url

    scheme, rest = url.split("://", 1)
    slash = rest.find("/")

    if slash < 0:
        authority = rest
        path = "/"
    else:
        authority = rest[:slash]
        path = rest[slash:]

    return scheme, authority, path


def normalize_path(path):
    query = ""
    if "?" in path:
        path, query = path.split("?", 1)
        query = "?" + query

    parts = []
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
        else:
            parts.append(part)

    return "/" + "/".join(parts) + query


def resolve_url(base, href):
    href = href.strip()

    if not href or href.startswith("#"):
        return base

    if href.startswith("http://") or href.startswith("https://"):
        return href

    scheme, authority, path = split_url(base)

    if href.startswith("//"):
        return scheme + ":" + href

    if href.startswith("/"):
        return "{}://{}{}".format(
            scheme,
            authority,
            normalize_path(href)
        )

    directory = path.rsplit("/", 1)[0]
    return "{}://{}{}".format(
        scheme,
        authority,
        normalize_path(directory + "/" + href)
    )

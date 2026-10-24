"""Das Prüfskript: erst die Quelle selbst, dann eine Kopie im Internet Archive, dann der Mensch."""

from scripts import verify_evidence as verify


class Sources:
    """Seiten und Archivkopien zum Nachschlagen. Fehlt eine Seite, ist sie gesperrt."""

    def __init__(self, pages=None, archive=None):
        self.pages, self.archive, self.archive_calls = pages or {}, archive or {}, []

    def page(self, url):
        if url not in self.pages:
            raise RuntimeError("403 Forbidden")
        return self.pages[url]

    def archived(self, url):
        self.archive_calls.append(url)
        return self.archive.get(url)


def check(evidence, sources):
    checker = verify.Checker(sources.page, sources.archived)
    return checker.check(evidence)


def test_quote_on_the_page_is_confirmed_without_the_archive():
    sources = Sources(pages={"https://a.example": "Daten liegen in Frankfurt."})

    result = check({"source": "https://a.example", "quote": "liegen in Frankfurt"}, sources)

    assert result.kind == "DIREKT"
    assert sources.archive_calls == []


def test_blocked_page_is_confirmed_through_an_archive_copy():
    snapshot = verify.Snapshot(
        "https://web.archive.org/web/20261014id_/https://a.example", "2026-10-14", "use.typekit.net"
    )
    sources = Sources(archive={"https://a.example": snapshot})

    result = check({"source": "https://a.example", "quote": "use.typekit.net"}, sources)

    assert result.kind == "ARCHIV"
    assert "2026-10-14" in result.detail


def test_quote_missing_on_the_page_is_also_looked_up_in_the_archive():
    snapshot = verify.Snapshot("https://web.archive.org/x", "2026-05-12", "alter Wortlaut")
    sources = Sources(
        pages={"https://a.example": "neuer Wortlaut"}, archive={"https://a.example": snapshot}
    )

    result = check({"source": "https://a.example", "quote": "alter Wortlaut"}, sources)

    assert result.kind == "ARCHIV"


def test_human_check_counts_when_no_automatic_way_works():
    sources = Sources()

    result = check(
        {"source": "https://a.example", "quote": "x.js", "verified_by": "Jonas, Bildschirmfoto"},
        sources,
    )

    assert result.kind == "MENSCH"
    assert "Jonas" in result.detail


def test_no_way_at_all_is_a_problem():
    result = check({"source": "https://a.example", "quote": "x.js"}, Sources())

    assert result.kind == "PROBLEM"
    assert "403" in result.detail


def test_each_source_is_loaded_only_once():
    sources = Sources()
    checker = verify.Checker(sources.page, sources.archived)

    checker.check({"source": "https://a.example", "quote": "eins"})
    checker.check({"source": "https://a.example", "quote": "zwei"})

    assert sources.archive_calls == ["https://a.example"]


def test_archive_lookup_asks_for_the_closest_copy_and_loads_it_unchanged(monkeypatch):
    calls = []

    class Response:
        def __init__(self, status, payload=None, text=""):
            self.status_code, self.payload, self.text = status, payload, text
            self.content = text.encode()

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(self.status_code)

        def json(self):
            return self.payload

    def fake_get(address, params=None, **kwargs):
        calls.append((address, params))
        if address == verify.ARCHIVE_API:
            closest = {"available": True, "timestamp": "20261014203859"}
            return Response(200, {"archived_snapshots": {"closest": closest}})
        return Response(200, text="<p>font network (use.typekit.net)</p>")

    monkeypatch.setattr(verify.httpx2, "get", fake_get)
    monkeypatch.setattr(verify, "ARCHIVE_PAUSE", 0)

    snapshot = verify.archived("https://helpx.adobe.com/embed-codes.html")

    assert calls[0] == (verify.ARCHIVE_API, {"url": "https://helpx.adobe.com/embed-codes.html"})
    assert snapshot.url == (
        "https://web.archive.org/web/20261014203859id_/https://helpx.adobe.com/embed-codes.html"
    )
    assert snapshot.date == "2026-10-14"
    assert "use.typekit.net" in snapshot.text


def test_archive_failure_is_named_in_the_result():
    def broken(url):
        raise RuntimeError("429 Too Many Requests")

    checker = verify.Checker(Sources().page, broken)

    result = checker.check({"source": "https://a.example", "quote": "x.js", "verified_by": "Jonas"})

    assert result.kind == "MENSCH"
    assert "429" in result.detail

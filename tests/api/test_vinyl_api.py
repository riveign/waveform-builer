"""The vinyl endpoints — and the promises they must not break.

No test here reaches the network: Discogs is a `MockTransport` and the BPM
cascade runs with `allow_preview` off, so what is under test is Kiku's own
behaviour rather than a third party's uptime.
"""

from __future__ import annotations

import httpx
import pytest

from kiku.db.models import Track, VinylRelease

RELEASE = {
    "id": 28715971,
    "title": "Alarico (2) - Klockworks 38",
    "year": 2023,
    "country": "Germany",
    "uri": "https://www.discogs.com/release/28715971",
    "artists": [{"name": "Alarico (2)", "join": ""}],
    "labels": [{"name": "Klockworks", "catno": "KW 38"}],
    "formats": [{"name": "Vinyl", "qty": "1", "descriptions": ['12"']}],
    "images": [{"uri": "https://i.discogs.com/x.jpg"}],
    "tracklist": [
        {"type_": "heading", "position": "", "title": "Side A"},
        {"type_": "track", "position": "A1", "title": "AF 97", "duration": ""},
        {"type_": "track", "position": "A2", "title": "Chromo", "duration": "5:48"},
        {"type_": "track", "position": "B1", "title": "Lost In Lima", "duration": ""},
    ],
}

SEARCH_HIT = {
    "results": [
        {
            "id": 28715971,
            "master_id": 3290497,
            "title": "Alarico (2) - Klockworks 38",
            "year": 2023,
            "country": "Germany",
            "catno": "KW 38",
            "label": ["Klockworks"],
            "format": ["Vinyl", '12"'],
            "style": ["Techno"],
            "cover_image": "https://i.discogs.com/x.jpg",
            "community": {"have": 548, "want": 286},
        },
        {
            # The same record, a repress. A DJ sees one record, not two.
            "id": 99999999,
            "master_id": 3290497,
            "title": "Alarico (2) - Klockworks 38",
            "year": 2024,
            "catno": "KW 38",
            "label": ["Klockworks"],
            "format": ["Vinyl", '12"'],
            "community": {"have": 12, "want": 4},
        },
    ]
}


@pytest.fixture()
def discogs(monkeypatch):
    """A Discogs that answers from fixtures, and records what it was asked."""
    asked: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/database/search":
            asked.append(dict(request.url.params))
            return httpx.Response(200, json=SEARCH_HIT)
        if request.url.path.startswith("/releases/"):
            return httpx.Response(200, json=RELEASE)
        return httpx.Response(404, json={})

    from kiku.metadata.sources.discogs import DiscogsSource

    def factory(*a, **kw):
        return DiscogsSource(token="test-token", transport=httpx.MockTransport(handler))

    # Both the routes and the resolver import DiscogsSource inside their
    # functions, so patching the module attribute reaches every call site.
    monkeypatch.setattr("kiku.metadata.sources.discogs.DiscogsSource", factory)
    return asked


@pytest.fixture()
def no_preview(monkeypatch):
    """Keep the cascade off the network — library rung only."""
    monkeypatch.setattr("kiku.vinyl.bpm.find_preview_url", lambda *a, **kw: None)


# ── search ────────────────────────────────────────────────────────────────


def test_search_reads_the_query_and_says_what_it_read(client, discogs):
    res = client.get("/api/vinyl/search", params={"q": "KW 38"})
    assert res.status_code == 200
    assert res.json()["kind"] == "catno"


def test_search_asks_discogs_for_vinyl_only(client, discogs):
    """The guard that stops the WAV edition ever reaching the picker."""
    client.get("/api/vinyl/search", params={"q": "Klockworks"})
    assert discogs, "no search was issued"
    assert discogs[0].get("format") == "Vinyl"


def test_search_can_be_widened_past_vinyl(client, discogs):
    client.get("/api/vinyl/search", params={"q": "Klockworks", "vinyl_only": "false"})
    assert "format" not in discogs[0]


def test_a_catalogue_number_is_asked_for_as_a_catalogue_number(client, discogs):
    client.get("/api/vinyl/search", params={"q": "KW 38"})
    assert discogs[0].get("catno") == "KW 38"


def test_repressings_of_one_record_collapse(client, discogs):
    """Two Discogs releases, one master, one record on the shelf."""
    rows = client.get("/api/vinyl/search", params={"q": "KW 38"}).json()["results"]
    assert len(rows) == 1
    assert rows[0]["pressings"] == 2


def test_a_result_carries_what_the_picker_needs_without_a_second_call(client, discogs):
    row = client.get("/api/vinyl/search", params={"q": "KW 38"}).json()["results"][0]
    assert row["title"] == "Klockworks 38"  # artist split off the title
    assert row["artist"] == "Alarico"  # and its "(2)" suffix stripped
    assert row["catno"] == "KW 38"
    assert row["cover_url"]
    assert row["have"] == 548


# ── preview ───────────────────────────────────────────────────────────────


def test_preview_returns_the_sides_in_pressing_order(client, discogs, no_preview):
    d = client.get("/api/vinyl/preview", params={"release_id": "28715971"}).json()
    assert [r["position"] for r in d["rows"]] == ["A1", "A2", "B1"]
    assert d["is_pressing"] is True
    assert d["catalog_number"] == "KW 38"


def test_preview_fills_a_bpm_from_your_own_file(client, db_session, discogs, no_preview):
    db_session.add(
        Track(
            title="AF 97",
            artist="Alarico",
            bpm=143.0,
            key="Em",
            medium="digital",
            file_path="/music/af97.aiff",
        )
    )
    db_session.commit()

    rows = client.get("/api/vinyl/preview", params={"release_id": "28715971"}).json()["rows"]
    a1 = next(r for r in rows if r["position"] == "A1")

    assert a1["bpm"] == 143.0
    assert a1["bpm_source"] == "library"
    assert "AF 97" in a1["bpm_note"]


def test_preview_marks_a_near_match_as_needing_a_look(client, db_session, discogs, no_preview):
    """ "Lost In Time" vs "Lost in Lima" scored 0.898 in testing and would have
    written the wrong tempo. It must arrive as a question, not an answer."""
    db_session.add(
        Track(
            title="Lost In Time",
            artist="Alarico",
            bpm=145.0,
            medium="digital",
            file_path="/music/lit.aiff",
        )
    )
    db_session.commit()

    rows = client.get("/api/vinyl/preview", params={"release_id": "28715971"}).json()["rows"]
    b1 = next(r for r in rows if r["position"] == "B1")  # "Lost In Lima"

    assert b1["bpm_source"] == "suggestion"
    assert "Lost In Time" in b1["bpm_note"]


def test_preview_says_nothing_rather_than_guessing(client, discogs, no_preview):
    rows = client.get("/api/vinyl/preview", params={"release_id": "28715971"}).json()["rows"]
    assert all(r["bpm_source"] == "none" and r["bpm"] is None for r in rows)


def test_preview_needs_something_to_look_at(client, discogs):
    assert client.get("/api/vinyl/preview").status_code == 400


def test_a_link_kiku_cannot_read_says_so(client, discogs):
    res = client.get("/api/vinyl/preview", params={"url": "https://boomkat.com/products/x"})
    assert res.status_code == 400
    assert "type the record in yourself" in res.json()["detail"].lower()


# ── import ────────────────────────────────────────────────────────────────


def test_import_writes_the_sides_and_the_numbers_you_kept(client, db_session, discogs, no_preview):
    res = client.post(
        "/api/vinyl/import",
        json={
            "release_id": "28715971",
            "sides": [
                {"position": "A1", "bpm": 143.0, "key": "Em"},
                {"position": "A2", "bpm": 144.0},
            ],
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["sides_written"] == 3
    assert body["bpms_applied"] == 2
    assert body["unplannable"] == 1
    assert body["release"]["plannable"] == 2

    a1 = db_session.query(Track).filter_by(vinyl_position="A1").one()
    assert a1.bpm == 143.0
    assert a1.bpm_source == "manual"  # what you kept is yours, and outranks everything
    assert a1.enrichment_status == "manual"


def test_import_ignores_a_bpm_that_isnt_one(client, db_session, discogs, no_preview):
    body = client.post(
        "/api/vinyl/import",
        json={"release_id": "28715971", "sides": [{"position": "A1", "bpm": 4000}]},
    ).json()
    assert body["bpms_applied"] == 0
    assert db_session.query(Track).filter_by(vinyl_position="A1").one().bpm is None


def test_importing_the_same_record_twice_leaves_one_record(client, db_session, discogs, no_preview):
    client.post("/api/vinyl/import", json={"release_id": "28715971"})
    client.post("/api/vinyl/import", json={"release_id": "28715971"})
    assert db_session.query(VinylRelease).count() == 1
    assert db_session.query(Track).filter_by(medium="vinyl").count() == 3


# ── the shelf ─────────────────────────────────────────────────────────────


def test_the_shelf_reports_what_can_actually_be_planned(client, discogs, no_preview):
    client.post(
        "/api/vinyl/import",
        json={"release_id": "28715971", "sides": [{"position": "A1", "bpm": 143.0}]},
    )
    shelf = client.get("/api/vinyl/releases").json()
    assert len(shelf) == 1
    assert shelf[0]["sides"] == 3
    assert shelf[0]["plannable"] == 1
    assert shelf[0]["without_length"] == 2  # Discogs gave a duration for one side


def test_removing_a_record_takes_its_sides_with_it(client, db_session, discogs, no_preview):
    rid = client.post("/api/vinyl/import", json={"release_id": "28715971"}).json()["release"]["id"]

    assert client.delete(f"/api/vinyl/releases/{rid}").status_code == 204
    assert db_session.query(VinylRelease).count() == 0
    assert db_session.query(Track).filter_by(medium="vinyl").count() == 0


def test_removing_a_record_that_isnt_there(client, discogs):
    assert client.delete("/api/vinyl/releases/999").status_code == 404

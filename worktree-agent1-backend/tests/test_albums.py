"""Unit tests for app.albums 2-stage clustering (shared/CONTRACT.md 3-1)."""
from app.albums import classify_albums
from app.storage import PhotoRecord


def _photo(pid, dt=None, gps=None):
    return PhotoRecord(photo_id=pid, filename=f"{pid}.jpg", file_path=f"/tmp/{pid}.jpg", taken_at=dt, gps=gps)


def test_no_photos_returns_no_albums():
    assert classify_albums([]) == {}


def test_no_exif_and_no_gps_forms_single_album_country_none():
    photos = [_photo(f"p{i}") for i in range(5)]
    albums = classify_albums(photos)
    assert len(albums) == 1
    album = next(iter(albums.values()))
    assert album.country is None
    assert len(album.photo_ids) == 5
    for p in photos:
        assert p.album_id == album.album_id
        assert p.country is None


def test_all_same_timestamp_forms_single_album():
    dt = "2026-01-01T10:00:00"
    photos = [_photo(f"p{i}", dt=dt) for i in range(4)]
    albums = classify_albums(photos)
    assert len(albums) == 1


def test_gap_over_48h_splits_into_separate_trips_same_country():
    # Same country (no GPS at all -> country=None for both) but >48h apart.
    photos = [
        _photo("a", dt="2026-01-01T10:00:00"),
        _photo("b", dt="2026-01-01T11:00:00"),
        _photo("c", dt="2026-01-05T10:00:00"),  # >48h after b
        _photo("d", dt="2026-01-05T11:00:00"),
    ]
    albums = classify_albums(photos)
    assert len(albums) == 2
    sizes = sorted(len(a.photo_ids) for a in albums.values())
    assert sizes == [2, 2]


def test_gap_under_48h_stays_single_trip():
    photos = [
        _photo("a", dt="2026-01-01T10:00:00"),
        _photo("b", dt="2026-01-02T10:00:00"),  # 24h later
    ]
    albums = classify_albums(photos)
    assert len(albums) == 1


def test_korea_germany_austria_korea_same_trip_merges_korea(monkeypatch):
    """CONTRACT.md 3-1 example: one trip visiting KR -> DE -> AT -> KR (all
    within the 48h-gap trip window) should yield 3 albums (KR/DE/AT), with
    both KR legs merged into a single album."""
    import app.albums as albums_module

    fake_countries = {
        "kr1": ("South Korea", "Seoul"),
        "de": ("Germany", "Berlin"),
        "at": ("Austria", "Vienna"),
        "kr2": ("South Korea", "Seoul"),
    }

    def fake_reverse_geocode(lat, lon):
        return fake_countries[str(lat)]

    monkeypatch.setattr(albums_module, "_reverse_geocode_country_city", fake_reverse_geocode)

    photos = [
        _photo("kr1", dt="2026-01-01T09:00:00", gps=("kr1", 0)),
        _photo("de", dt="2026-01-01T12:00:00", gps=("de", 0)),
        _photo("at", dt="2026-01-01T15:00:00", gps=("at", 0)),
        _photo("kr2", dt="2026-01-01T18:00:00", gps=("kr2", 0)),
    ]
    albums = classify_albums(photos)
    assert len(albums) == 3
    countries = sorted(a.country for a in albums.values())
    assert countries == ["Austria", "Germany", "South Korea"]

    korea_album = next(a for a in albums.values() if a.country == "South Korea")
    assert set(korea_album.photo_ids) == {"kr1", "kr2"}


def test_gps_less_photo_inherits_nearest_neighbor_country(monkeypatch):
    import app.albums as albums_module

    monkeypatch.setattr(
        albums_module, "_reverse_geocode_country_city", lambda lat, lon: ("France", "Paris")
    )

    photos = [
        _photo("with_gps", dt="2026-01-01T10:00:00", gps=(48.85, 2.35)),
        _photo("no_gps", dt="2026-01-01T10:05:00"),  # 5 min later, no GPS
    ]
    albums = classify_albums(photos)
    assert len(albums) == 1
    album = next(iter(albums.values()))
    assert album.country == "France"
    no_gps_photo = next(p for p in photos if p.photo_id == "no_gps")
    assert no_gps_photo.country == "France"

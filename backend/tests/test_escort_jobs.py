"""Tests fuer das Eskort-Gesuche-Board (``app.fleet.escort_jobs``).

DB-/Engine-frei wo moeglich: die reinen Regel-Helfer (job_route, is_self, fee_ok, power_ok,
job_coverable, is_expired) werden direkt getestet; die Annahme-/Storno-Status-Uebergaenge ueber
eine schlanke FakeSession (nur ``get`` noetig), get_balance laeuft per BALANCE_PATH-Fallback.
Stil: test_stationing.py + test_conjunction.py."""
import asyncio
import datetime as dt
import json
import os
import uuid
from types import SimpleNamespace

import pytest

from app.fleet.escort_jobs import (
    ACCEPTED,
    CANCELLED,
    EXPIRED,
    OPEN,
    accept_escort_job,
    cancel_escort_job,
    fee_ok,
    is_expired,
    is_self,
    job_coverable,
    job_route,
    power_ok,
)
from app.platform.models import EscortJob, StationedFleet

UTC = dt.timezone.utc


# ----------------------------------------------------------- reine Regel-Helfer

def _station(galaxy=1, system=44, enabled=True, radius=5, fee=0.05, ships=None):
    return SimpleNamespace(
        galaxy=galaxy, system=system, escort_enabled=enabled, escort_radius=radius,
        escort_fee_pct=fee, ships=ships or {},
    )


def test_job_route_maps_origin_target_systems():
    job = SimpleNamespace(origin_galaxy=1, origin_system=40, target_system=48)
    assert job_route(job) == (1, 40, 48, 0)


def test_is_self():
    me = uuid.uuid4()
    other = uuid.uuid4()
    assert is_self(SimpleNamespace(requester_id=me), me) is True
    assert is_self(SimpleNamespace(requester_id=other), me) is False


def test_fee_ok():
    assert fee_ok(0.05, 0.10) is True
    assert fee_ok(0.10, 0.10) is True          # gleich = ok
    assert fee_ok(0.11, 0.10) is False         # teurer als erlaubt
    assert fee_ok(0.0, 0.0) is True


def test_power_ok():
    assert power_ok(5000, 3000) is True
    assert power_ok(3000, 3000) is True        # gleich = ok
    assert power_ok(2999, 3000) is False
    assert power_ok(100, 0) is True            # min_power 0 = egal


def test_job_coverable_all_rules():
    st = _station(system=44, fee=0.05)
    # Route 40->48 (gal 1), Station bei 44 in [35,53]; Gebuehr 0.05<=0.10; power 6000>=1000.
    assert job_coverable(st, covers=True, station_power=6000, min_power=1000, max_fee_pct=0.10) is True


def test_job_coverable_rejects_each_rule():
    st = _station(fee=0.05)
    # Route nicht gedeckt.
    assert job_coverable(st, covers=False, station_power=6000, min_power=0, max_fee_pct=0.10) is False
    # Gebuehr zu hoch.
    assert job_coverable(_station(fee=0.20), covers=True, station_power=6000, min_power=0, max_fee_pct=0.10) is False
    # Kampfkraft zu gering.
    assert job_coverable(st, covers=True, station_power=500, min_power=1000, max_fee_pct=0.10) is False
    # Kein Eskort-Angebot.
    assert job_coverable(_station(enabled=False), covers=True, station_power=6000, min_power=0, max_fee_pct=0.10) is False


def test_is_expired():
    now = dt.datetime(2026, 6, 21, 12, 0, tzinfo=UTC)
    future = SimpleNamespace(expires_at=now + dt.timedelta(hours=1))
    past = SimpleNamespace(expires_at=now - dt.timedelta(hours=1))
    assert is_expired(future, now) is False
    assert is_expired(past, now) is True
    # Naive Zeit wird als UTC behandelt.
    naive_past = SimpleNamespace(expires_at=dt.datetime(2026, 6, 21, 10, 0))
    assert is_expired(naive_past, now) is True


# ----------------------------------------------------------- balance-Sanity

def test_escort_block_has_job_max_hours():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.environ.get("BALANCE_PATH") or os.path.normpath(
        os.path.join(here, "..", "..", "shared", "balance.json")
    )
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    e = data["escort"]
    assert e["job_max_hours"] > 0
    assert 0 < e["max_fee_pct"] <= 1.0


# ----------------------------------------------------------- Status-Uebergaenge

class FakeSession:
    """Minimal-Session: nur ``get`` (per id-Map) + No-op add/flush/commit."""

    def __init__(self, *objs):
        self._by_id = {o.id: o for o in objs}
        self.added: list = []

    async def get(self, _model, oid):
        return self._by_id.get(oid)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        pass

    async def commit(self):
        pass


def _make_job(requester_id, *, status=OPEN, max_fee_pct=0.10, min_power=0.0, expires_in_h=1.0):
    now = dt.datetime.now(UTC)
    return EscortJob(
        id=uuid.uuid4(), requester_id=requester_id,
        origin_galaxy=1, origin_system=40, origin_position=8,
        target_galaxy=1, target_system=48, target_position=8,
        cargo_value=100000.0, max_fee_pct=max_fee_pct, min_power=min_power,
        status=status, created_at=now, expires_at=now + dt.timedelta(hours=expires_in_h),
    )


def _make_station(owner_id, *, system=44, fee=0.05, enabled=True, radius=5):
    return StationedFleet(
        id=uuid.uuid4(), owner_id=owner_id, galaxy=1, system=system, position=8,
        ships={"battleship": 50}, escort_enabled=enabled, escort_radius=radius, escort_fee_pct=fee,
    )


@pytest.fixture(autouse=True)
def _silence_transmission(monkeypatch):
    async def _noop(*_a, **_k):
        return None
    monkeypatch.setattr("app.fleet.escort_jobs.create_system_transmission", _noop)


def test_accept_sets_accepted_and_records_provider():
    requester, provider = uuid.uuid4(), uuid.uuid4()
    job = _make_job(requester)
    st = _make_station(provider)
    session = FakeSession(job, st)
    player = SimpleNamespace(id=provider, display_name="Geleitschutz GmbH")

    out = asyncio.run(accept_escort_job(session, player, job.id, st.id))
    assert out.status == ACCEPTED
    assert out.accepted_by == provider
    assert out.accepted_station_id == st.id
    assert out.accepted_fee_pct == 0.05


def test_first_acceptance_wins():
    requester, p1, p2 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    job = _make_job(requester)
    st1, st2 = _make_station(p1), _make_station(p2)
    session = FakeSession(job, st1, st2)

    asyncio.run(accept_escort_job(session, SimpleNamespace(id=p1, display_name="A"), job.id, st1.id))
    # Zweite Annahme: Auftrag ist nicht mehr offen.
    with pytest.raises(RuntimeError, match="nicht mehr offen"):
        asyncio.run(accept_escort_job(session, SimpleNamespace(id=p2, display_name="B"), job.id, st2.id))


def test_cannot_accept_own_job():
    requester = uuid.uuid4()
    job = _make_job(requester)
    st = _make_station(requester)
    session = FakeSession(job, st)
    with pytest.raises(RuntimeError, match="Eigene"):
        asyncio.run(accept_escort_job(session, SimpleNamespace(id=requester, display_name="Ich"), job.id, st.id))


def test_accept_rejected_when_route_not_covered():
    requester, provider = uuid.uuid4(), uuid.uuid4()
    job = _make_job(requester)
    st = _make_station(provider, system=90)  # weit ausserhalb [35,53]
    session = FakeSession(job, st)
    with pytest.raises(RuntimeError, match="Route"):
        asyncio.run(accept_escort_job(session, SimpleNamespace(id=provider, display_name="P"), job.id, st.id))


def test_accept_rejected_when_fee_too_high():
    requester, provider = uuid.uuid4(), uuid.uuid4()
    job = _make_job(requester, max_fee_pct=0.03)
    st = _make_station(provider, fee=0.05)  # teurer als erlaubt
    session = FakeSession(job, st)
    with pytest.raises(RuntimeError, match="Gebuehr"):
        asyncio.run(accept_escort_job(session, SimpleNamespace(id=provider, display_name="P"), job.id, st.id))


def test_accept_rejected_when_power_below_min():
    requester, provider = uuid.uuid4(), uuid.uuid4()
    job = _make_job(requester, min_power=1e12)  # unerreichbar hoch
    st = _make_station(provider)
    session = FakeSession(job, st)
    with pytest.raises(RuntimeError, match="Mindeststaerke"):
        asyncio.run(accept_escort_job(session, SimpleNamespace(id=provider, display_name="P"), job.id, st.id))


def test_accept_expired_job_marks_expired():
    requester, provider = uuid.uuid4(), uuid.uuid4()
    job = _make_job(requester, expires_in_h=-1.0)  # bereits abgelaufen
    st = _make_station(provider)
    session = FakeSession(job, st)
    with pytest.raises(RuntimeError, match="abgelaufen"):
        asyncio.run(accept_escort_job(session, SimpleNamespace(id=provider, display_name="P"), job.id, st.id))
    assert job.status == EXPIRED


def test_accept_unknown_station_raises_value_error():
    requester, provider = uuid.uuid4(), uuid.uuid4()
    job = _make_job(requester)
    session = FakeSession(job)  # Station nicht in der Session
    with pytest.raises(ValueError, match="Station"):
        asyncio.run(accept_escort_job(session, SimpleNamespace(id=provider, display_name="P"), job.id, uuid.uuid4()))


def test_cancel_open_job():
    requester = uuid.uuid4()
    job = _make_job(requester)
    session = FakeSession(job)
    out = asyncio.run(cancel_escort_job(session, SimpleNamespace(id=requester, display_name="R"), job.id))
    assert out.status == CANCELLED


def test_cancel_accepted_job_then_not_again():
    requester = uuid.uuid4()
    job = _make_job(requester, status=ACCEPTED)
    session = FakeSession(job)
    asyncio.run(cancel_escort_job(session, SimpleNamespace(id=requester, display_name="R"), job.id))
    assert job.status == CANCELLED
    with pytest.raises(RuntimeError, match="storniert"):
        asyncio.run(cancel_escort_job(session, SimpleNamespace(id=requester, display_name="R"), job.id))


def test_cancel_foreign_job_raises():
    requester, other = uuid.uuid4(), uuid.uuid4()
    job = _make_job(requester)
    session = FakeSession(job)
    with pytest.raises(ValueError, match="nicht gefunden"):
        asyncio.run(cancel_escort_job(session, SimpleNamespace(id=other, display_name="X"), job.id))

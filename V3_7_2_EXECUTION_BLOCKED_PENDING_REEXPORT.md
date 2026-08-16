# V3.7.2 EXECUTION BLOCKED PENDING CANONICAL RE-EXPORT REPAIR

Do NOT execute V3.7.2 yet.

Independent audit found that V3.7.1 technical repair commit
`94bc77443ef623d45d7ce2003330f03212668ae8` converted UTC-aware request boundaries to timezone-naive Python `datetime` objects before calling `MetaTrader5.copy_rates_range`.

Official MetaQuotes documentation states that Python datetime uses the local timezone while MT5 bar times are UTC, and therefore request datetimes should be created in UTC.

This creates a provenance-contract mismatch with the V3.7.1 sidecar claim that the extraction used UTC-aware start/end boundaries.

The returned bar epochs may still be correct and the current dataset may even reproduce byte-for-byte after repair, but that does not excuse the acquisition-contract drift.

Required action:

1. repair request boundaries under a separately precommitted canonical re-export reproduction;
2. use unambiguous UTC epoch-second boundaries or explicitly timezone-aware UTC datetimes;
3. create a new immutable canonical output rather than overwrite V3.7.1;
4. independently audit the repaired canonical lineage;
5. only then recreate/execute engine compatibility against the repaired authoritative dataset.

No strategy research is authorized by this branch while this blocker exists.

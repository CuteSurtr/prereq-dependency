# prereq-service

A Spring Boot API over the UCSD prerequisite graph, backed by MySQL and cached in Redis.

The deployed site stays a pure static build — this service is **additive**. It exists for the cases
the static `graph.json` cannot serve well: recursive chain traversal, eligibility over an arbitrary
completed-course list, and any client that wants a real API instead of a 1.6 MB download.

## What it does that the static build does not

| Endpoint | Why it needs a server |
| --- | --- |
| `GET /api/courses/{code}/chain?depth=N` | Breadth-first upstream traversal, one batched query per level. The browser does this client-side today over the whole graph. |
| `POST /api/eligibility` | Evaluates DNF prerequisite groups against a completed-course list, filtered by department. |
| `GET /api/graph` | The same payload as `frontend/public/graph.json`, generated from MySQL rather than a build step. |

The rest mirrors the dev-only FastAPI app in `backend/api.py` route for route, with the same
snake_case payloads and the same `{"detail": "..."}` error envelope:
`GET /api/health`, `/api/courses`, `/api/courses/{code}`, `/api/courses/{code}/prereqs`,
`/api/courses/{code}/unlocks`, `/api/departments`.

Interactive docs: `/swagger-ui.html`. Operational endpoints: `/actuator/health`, `/actuator/caches`.

## Stack

* **Java 21 + Spring Boot 3.5** — Web, Data JPA, Data Redis, Cache, Validation, Actuator.
* **MySQL 8** — system of record. Flyway owns the schema (`db/migration/V1__init_schema.sql`); it
  mirrors the SQLite schema in `backend/models.py` so both stacks read the same shape.
* **Redis 7** — read-through cache on every expensive read, with per-cache TTLs set in
  `application.yml`. Values are stored as plain JSON: each cache declares the concrete type it
  deserializes into, because every DTO is a `record`, records are `final`, and Jackson's `NON_FINAL`
  default typing therefore never writes the `@class` tag needed to read them back.
* **springdoc-openapi** — generated OpenAPI 3 spec and Swagger UI.

## Where the data comes from

The service does **not** re-implement the scraper or the parser. Those stay in Python, and stay the
single source of truth. On first boot the service seeds MySQL from `frontend/public/graph.json` —
the export the Python pipeline already produces — and re-derives the relational rows from it.

```
catalog.ucsd.edu -> scraper -> parser -> SQLite -> graph.json -> MySQL -> API
                    (python, unchanged)            (committed)   (java)
```

`GraphParityTest` loads that same file, round-trips all 2,147 courses through MySQL, and asserts the
regenerated export is JSON-identical to the Python one. If the two stacks ever disagree about
grouping, sorting or field naming, that test fails.

Seeding is controlled by `prereq.seed.*`: it runs only when the courses table is empty unless
`IMPORT_FORCE=true`. A failed seed logs a warning rather than aborting startup. Any successful
import evicts every cache, so a reseed cannot leave stale entries behind.

## Running it

```bash
# dependencies only, then run the app from your IDE or Maven
docker compose up -d mysql redis
mvn spring-boot:run

# or the whole stack, service included, on :8080
docker compose up -d
```

Point it at the real catalog on a first run:

```bash
IMPORT_FORCE=true GRAPH_JSON=../frontend/public/graph.json mvn spring-boot:run
```

Everything is env-overridable: `MYSQL_URL`, `MYSQL_USER`, `MYSQL_PASSWORD`, `REDIS_HOST`,
`REDIS_PORT`, `CORS_ORIGINS`, `GRAPH_JSON`, `IMPORT_ON_STARTUP`, `IMPORT_FORCE`, `CACHE_TYPE`.

## Tests

```bash
mvn test      # H2 + in-process cache; needs nothing running
mvn verify    # adds the *IT tests, which need MySQL and Redis up
```

`mvn test` covers the parser-independent logic, the full HTTP surface via MockMvc, cache wiring, and
the graph.json parity check. `mvn verify` adds three suites against the real stack:

* `MySqlStackIT` — runs with `ddl-auto: validate`, so the context only starts if the Flyway
  migration and the JPA entities still describe the same schema.
* `RedisCacheIT` — round-trips records through a live Redis and checks key prefixes and TTLs.
* `SeedConcurrencyIT` — eight threads released together on one barrier, asserting that exactly one
  of them imports and that the lock is released only by whoever holds it.

CI runs `mvn verify` with MySQL and Redis service containers.

## Measured behaviour

Every number here was measured by [`bench/bench.py`](bench/bench.py) against a local instance with
the full graph loaded (2,147 courses, 5,004 prerequisite edges), not estimated. To reproduce:

```bash
docker compose up -d mysql redis
./mvnw -DskipTests package && java -jar target/prereq-service-0.1.0.jar
python bench/bench.py --experiment latency   # then queries, then index
```

Latency is read from Micrometer's `http.server.requests` rather than timed at the client. A request
to `/actuator/health`, which does almost no work, costs about 25 ms measured from a Python client
over Windows loopback — a floor larger than every difference reported below, so client-side numbers
would be measuring the loopback rather than the service.

### What the Redis cache buys

Server-side mean per request, 200 iterations after 30 warm-up rounds.

| endpoint | cache off | cache on | |
| --- | ---: | ---: | ---: |
| `/api/courses/{code}/chain` | 8.22 ms | 1.68 ms | 4.9x |
| `/api/courses/{code}` | 4.57 ms | 1.37 ms | 3.3x |
| `/api/courses` | 4.52 ms | 1.44 ms | 3.1x |
| `/api/graph` | 29.20 ms | 15.57 ms | 1.9x |

`/api/graph` gains least because its cost is serializing a 1.6 MB payload, which the cache does not
remove — only the query behind it.

### Chain traversal costs one query per level, not one per node

`Com_select` delta across a single request, cache off:

| course | depth | nodes returned | SELECTs | one query per node would be |
| --- | ---: | ---: | ---: | ---: |
| CSE 101 | 1 | 8 | 4 | 8 |
| CSE 101 | 3 | 28 | 6 | 28 |
| CSE 101 | 6 | 31 | 8 | 31 |
| CSE 101 | 12 | 31 | 8 | 31 |
| CSE 141 | 6 | 13 | 9 | 13 |
| MATH 20C | 6 | 8 | 8 | 8 |

The count tracks depth, not result size: CSE 101 at depth 6 walks 31 nodes in 8 SELECTs, and depth
12 costs the same 8 because the frontier empties before the cap. Three of those are fixed — the
existence check, the node hydration at the end, and one connection probe.

### What the indexes actually do

`EXPLAIN ANALYZE` on the query the traversal issues, best of 7 runs:

| index | access | time |
| --- | --- | ---: |
| `ix_prereqs_course_code` (optimizer's choice) | range | 0.065 ms |
| `ix_prereqs_course_type_group` (forced) | range | 0.081 ms |
| none (both ignored) | full scan | 0.898 ms |

Two findings, one good and one not:

* Indexing this query is worth **13.8x** even at 5,004 rows.
* **`ix_prereqs_course_type_group` is never chosen.** It is `(course_code, prereq_type, group_id)`,
  and for a `course_code IN (...)` range the optimizer prefers the narrower single-column index;
  forced, the wider one is 25% slower.

It does not earn its keep on the ordered read either. `WHERE course_code = ? ORDER BY group_id, id`
still picks `ix_prereqs_course_code` and adds a filesort, because `prereq_type` sits between the
filtered column and the sorted one. Reordering the columns removes the filesort:

| index | `Extra` | time |
| --- | --- | ---: |
| today's `(course_code, prereq_type, group_id)` | Using filesort | 0.0260 ms |
| `(course_code, group_id, id)` | none | 0.0177 ms |

`ix_prereqs_required_type` has the same shape: `findByRequiredCourseCodeAndPrereqTypeOrderByCourseCodeAsc`
picks `ix_prereqs_required_course_code` and filesorts rather than using it. Both composite indexes
cost write throughput and storage today without serving a read. Replacing them is a schema change,
so it is recorded here rather than done quietly.

### Seeding is coordinated, not repeated

`GraphImportService.importFrom` decides whether to seed by reading the row count and then writing.
That is safe in one process and wasteful in two: both read an empty table, both insert, and every
loser hits the primary key. Measured with eight concurrent callers over ten trials, cache and
database real:

| | calls that succeeded | calls that failed | trials ending with wrong row count |
| --- | ---: | ---: | ---: |
| direct `importFrom` | 10 | **70** | 0 |
| through `SeedCoordinator` | **80** | **0** | 0 |

The failures were noisy, not corrupting — each import runs in its own transaction, so the losers
rolled back and the table was correct after every trial. What was actually wrong is that seven of
every eight instances logged a startup warning about a problem nobody had, after reading and
re-inserting the whole graph to find out they were not needed.

[`SeedCoordinator`](src/main/java/edu/ucsd/prereq/service/SeedCoordinator.java) takes a Redis lock
(`SET key token NX PX`) before delegating, so the check and the claim are one command. Three
decisions worth stating:

* **A caller that cannot take the lock skips rather than waits.** Seeding means "make the table
  populated", not "run exactly here"; blocking startup to watch another instance work would only
  make the slowest instance slower.
* **The lock is released by compare-and-delete, not `DEL`.** If a holder stalls past the TTL, Redis
  drops the key and someone else takes it; a plain delete from the stalled holder would then release
  a lock it no longer owns.
* **The lock is taken outside the import transaction.** Releasing inside it would hand the lock on
  before the winner's rows were committed, which is the same race in a smaller window.

If Redis is unreachable the import proceeds unlocked with a warning. Redis is how instances agree,
not how the import works, and a single-instance deployment should not fail to start because the
coordination layer is down — the primary key is still there.

## Notes

* `spring.jpa.open-in-view` is off; every read path is an explicit `@Transactional(readOnly = true)`
  service method.
* Chain traversal is capped at 160 nodes, matching `CHAIN_NODE_CAP` in `Graph.tsx`, and reports
  `truncated` when the cap bites.
* Course codes are normalized at the HTTP boundary (`cse100` and `CSE 100` are the same lookup, and
  the same cache key).

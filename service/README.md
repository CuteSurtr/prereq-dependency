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
the graph.json parity check. `mvn verify` adds two suites against the real stack:

* `MySqlStackIT` — runs with `ddl-auto: validate`, so the context only starts if the Flyway
  migration and the JPA entities still describe the same schema.
* `RedisCacheIT` — round-trips records through a live Redis and checks key prefixes and TTLs.

CI runs `mvn verify` with MySQL and Redis service containers.

## Notes

* `spring.jpa.open-in-view` is off; every read path is an explicit `@Transactional(readOnly = true)`
  service method.
* Chain traversal is capped at 160 nodes, matching `CHAIN_NODE_CAP` in `Graph.tsx`, and reports
  `truncated` when the cap bites.
* Course codes are normalized at the HTTP boundary (`cse100` and `CSE 100` are the same lookup, and
  the same cache key).

# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Build & Run Commands
- Build: `./gradlew build`
- Run: `./gradlew bootRun` (port 8080)
- Tests: `./gradlew test`
- Single test: `./gradlew test --tests "com.acme.billing.invoice.InvoiceServiceTest"`
- Checkstyle: `./gradlew checkstyleMain`
- Architecture tests: `./gradlew test --tests "com.acme.billing.ArchitectureTest"`
- Database (local): `docker compose up -d postgres`
- Migrations: Flyway runs at startup; files in `src/main/resources/db/migration`

## Technology Stack
- Java 21, Spring Boot 3.3, Spring Data JPA, Flyway 10
- PostgreSQL 16 (prod), Testcontainers (tests)
- Gradle 8.9, Checkstyle 10, ArchUnit 1.3
- Docker image built by `release.yml`, deployed by SSH on the prod host

## Architecture

### Layers
```
Controller → Service → Repository
```
- **Controller** (`com.acme.billing.*.XController`): HTTP only. Validates input, maps DTOs, delegates to the service. No business logic, no repository access.
- **Service** (`XService`): business logic, transactions.
- **Repository** (`XRepository`): Spring Data interfaces only.

### Package Structure
```
com.acme.billing.invoice     - invoices, lines, totals
com.acme.billing.customer    - customers and addresses
com.acme.billing.payment     - payment providers (Stripe, SEPA)
com.acme.billing.config      - Spring configuration
com.acme.billing.security    - authentication, roles
```

### Key File Locations
- Entities: `src/main/java/com/acme/billing/<domain>/*.java`
- DTOs: `src/main/java/com/acme/billing/<domain>/dto/`
- Migrations: `src/main/resources/db/migration/V<n>__<name>.sql`
- Checkstyle config: `config/checkstyle/checkstyle.xml`
- CI: `.github/workflows/ci.yml` (build, checkstyle, tests on every push)
- Release: `.github/workflows/release.yml`, driven by `scripts/release.mjs` — see `.claude/skills/release/SKILL.md`

## Conventions

### Dependency injection
Constructor injection, never field injection. `@Autowired` on a field hides dependencies and breaks unit tests.

### Controllers
No business logic in controllers. A controller that touches a repository is a bug.

### Security
Every endpoint has an authorization test (`@WithMockUser` with the wrong role must get 403).

### Resources
Always use try-with-resources for streams and JDBC objects.

### Migrations
Never modify an applied Flyway migration. Add a new one.

### Naming
- Classes: PascalCase. Methods and fields: camelCase. Constants: UPPER_SNAKE_CASE.
- Tests: `<Class>Test` for unit tests, `<Class>IT` for integration tests.
- One public class per file.

### Example: a well-formed service
```java
@Service
public class InvoiceService {
    @Autowired
    private InvoiceRepository repository;

    public Invoice create(CreateInvoiceCommand command) {
        return repository.save(Invoice.from(command));
    }
}
```

## Code Style
- 4 spaces, no tabs. Max line length 120 (Checkstyle enforces it).
- Imports: no wildcards, grouped java / javax / org / com.
- Prefer `Optional` over null returns in services.
- Use `record` for DTOs.

## Testing Guidelines
- Unit tests with JUnit 5 and Mockito. Integration tests with `@SpringBootTest` and Testcontainers.
- Always `given / when / then` comments in tests.
- Do not use `@MockBean` in unit tests (it starts the context). Use `@Mock`.
- Run the full suite before opening a PR: `./gradlew test`.

## Release process
1. Make sure `develop` is green in the Actions tab.
2. Run `node scripts/release.mjs` from `develop` — it picks the version from the branch name and triggers `release.yml`.
3. Watch the workflow; when the log says `SUCCESS`, the image is in prod.
4. Announce in #releases.

For hotfixes use `node scripts/hotfix.mjs` from a `hotfix/*` branch.

## Troubleshooting
- `FlywayValidateException` at startup: a migration was modified after being applied. Restore it and add a new migration.
- `Connection refused` on 5432: the Postgres container is not up. `docker compose up -d postgres`.
- Checkstyle fails on line length: wrap at 120, do not disable the rule.
- Tests hang on Testcontainers: Docker socket not reachable; check `DOCKER_HOST`.
- `release.yml` fails at the SSH step: the deploy key expired; rotate `PROD_SSH_KEY` in repository secrets.
- Gradle daemon out of memory: `./gradlew --stop` then raise `org.gradle.jvmargs` in `gradle.properties`.
- If `bootRun` shows `Port 8080 already in use`, kill the previous instance: `lsof -i :8080`.
- Slow tests: run with `--parallel` and `--max-workers=4`.

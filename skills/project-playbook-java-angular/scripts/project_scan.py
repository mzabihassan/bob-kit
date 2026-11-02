#!/usr/bin/env python3
"""Map a Java/Spring Boot + Angular project in one pass, for writing its developer playbook.

Scans one or more repository roots (a monorepo, or separate backend and frontend repositories)
and prints a compact Markdown map: stack and versions with their source files, modules, entry
points, backend structure and REST endpoints, OpenAPI specs, persistence, security, integrations,
configuration (keys, profiles and required environment variables, never secret values), frontend
structure (Angular projects, routes, interceptors, npm scripts), build and quality tooling, tests,
CI/CD, deployment, environments, existing documentation, git conventions, and a ranked list of
the files worth reading next.

Read-only; standard library only. Configuration values are shown only for an allow-list of
harmless keys; secret-like values are never printed, only their location.

Examples:
  python3 project_scan.py .
  python3 project_scan.py ../payments-api ../payments-ui --out /tmp/playbook-scan
  python3 project_scan.py . --since 3f2a9c1      # what changed since the last playbook update
"""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, OrderedDict

SKIP_DIRS = {".git", "node_modules", "target", "build", "dist", ".angular", ".gradle", "coverage", ".idea",
             ".vscode", "out", ".nx", ".cache", "tmp", "bin", "generated", "generated-sources", ".next",
             "vendor", "__pycache__", ".husky", ".yarn", ".pnpm-store", "bower_components"}
KEEP_DOT_DIRS = {".github", ".gitlab", ".bob", ".mvn", ".circleci"}
MAX_BYTES = 400_000
TEXT_EXT = {".java", ".kt", ".ts", ".js", ".mjs", ".cjs", ".json", ".yml", ".yaml", ".properties", ".xml",
            ".gradle", ".kts", ".toml", ".md", ".sql", ".html", ".tf", ".conf", ".env", ".adoc"}
SECRET_KEY = re.compile(r"(?i)(password|passwd|pwd|secret|token|api[-_.]?key|private[-_.]?key|credential|"
                        r"client[-_.]?secret|access[-_.]?key|jwt[-_.]?key|base64[-_.]?secret)")
PLACEHOLDER = re.compile(r"^\s*(\$\{[^}]*\}|<[^>]*>|\{\{.*\}\}|changeme|change-me|xxx+|\*+|)\s*$", re.I)
ENV_REF = re.compile(r"\$\{([A-Z][A-Z0-9_]{2,})(?::([^}]*))?\}")
SHOW_VALUE_KEYS = re.compile(
    r"^(server\.port|server\.servlet\.context-path|server\.servlet\.contextPath|spring\.application\.name|"
    r"spring\.profiles\.active|spring\.profiles\.include|spring\.profiles\.group\..*|spring\.config\.activate\.on-profile|"
    r"spring\.jpa\.hibernate\.ddl-auto|spring\.jpa\.open-in-view|spring\.flyway\.(enabled|locations)|"
    r"spring\.liquibase\.(enabled|contexts|change-log)|spring\.threads\.virtual\.enabled|"
    r"management\.server\.port|management\.endpoints\.web\.(base-path|exposure\.include)|"
    r"spring\.mvc\.servlet\.path|server\.compression\.enabled|spring\.main\.lazy-initialization)$")
CAPS = [  # (label, regex on "group:artifact" or "plugin:<id>")
    ("Web MVC (servlet)", r"org\.springframework\.boot:spring-boot-starter-web"),
    ("WebFlux (reactive)", r"org\.springframework\.boot:spring-boot-starter-webflux"),
    ("Spring Data JPA", r"org\.springframework\.boot:spring-boot-starter-data-jpa"),
    ("JDBC", r"org\.springframework\.boot:spring-boot-starter-jdbc"),
    ("MongoDB", r".*:spring-boot-starter-data-mongodb.*"),
    ("Redis", r".*:spring-boot-starter-data-redis.*"),
    ("Elasticsearch", r".*:spring-boot-starter-data-elasticsearch"),
    ("PostgreSQL driver", r"org\.postgresql:postgresql"), ("Oracle driver", r"com\.oracle\.database\.jdbc:ojdbc\d+.*"),
    ("MySQL driver", r"(com\.mysql:mysql-connector-j|mysql:mysql-connector-java)"),
    ("MariaDB driver", r"org\.mariadb\.jdbc:mariadb-java-client"), ("SQL Server driver", r"com\.microsoft\.sqlserver:mssql-jdbc"),
    ("H2 (in-memory DB)", r"com\.h2database:h2"), ("HSQLDB", r"org\.hsqldb:hsqldb"),
    ("Flyway", r"org\.flywaydb:flyway-core"), ("Liquibase", r"org\.liquibase:liquibase-core"),
    ("Spring Security", r"org\.springframework\.boot:spring-boot-starter-security"),
    ("OAuth2 resource server (JWT)", r"org\.springframework\.boot:spring-boot-starter-oauth2-resource-server"),
    ("OAuth2 client / OIDC login", r"org\.springframework\.boot:spring-boot-starter-oauth2-client"),
    ("Keycloak adapter", r"org\.keycloak:.*"), ("JJWT", r"io\.jsonwebtoken:jjwt.*"),
    ("Bean Validation", r"org\.springframework\.boot:spring-boot-starter-validation"),
    ("Kafka", r"org\.springframework\.kafka:spring-kafka"), ("RabbitMQ", r".*:spring-boot-starter-amqp"),
    ("JMS / IBM MQ", r"(.*:spring-boot-starter-artemis|com\.ibm\.mq:.*|org\.springframework:spring-jms)"),
    ("OpenFeign", r".*:spring-cloud-starter-openfeign"), ("Resilience4j", r".*resilience4j.*"),
    ("Cache", r"(.*:spring-boot-starter-cache|com\.github\.ben-manes\.caffeine:caffeine|org\.ehcache:.*|com\.hazelcast:.*)"),
    ("Mail", r".*:spring-boot-starter-mail"), ("Spring Batch", r".*:spring-boot-starter-batch"),
    ("Quartz", r".*:spring-boot-starter-quartz"), ("WebSocket", r".*:spring-boot-starter-websocket"),
    ("GraphQL", r".*:spring-boot-starter-graphql"), ("Thymeleaf", r".*:spring-boot-starter-thymeleaf"),
    ("Actuator", r".*:spring-boot-starter-actuator"), ("Prometheus metrics", r"io\.micrometer:micrometer-registry-prometheus"),
    ("Distributed tracing", r"(io\.micrometer:micrometer-tracing-bridge-.*|io\.opentelemetry.*:.*)"),
    ("JSON logs (logstash encoder)", r"net\.logstash\.logback:logstash-logback-encoder"),
    ("springdoc OpenAPI", r"org\.springdoc:.*"), ("OpenAPI Generator (API-first)", r"org\.openapitools:openapi-generator.*"),
    ("Spring Cloud Config", r".*:spring-cloud-starter-config"),
    ("Service discovery", r".*:spring-cloud-starter-(netflix-eureka-client|consul-discovery|kubernetes.*)"),
    ("MapStruct", r"org\.mapstruct:mapstruct.*"), ("Lombok", r"org\.projectlombok:lombok"),
    ("JUnit 5", r"(org\.junit\.jupiter:.*|org\.junit:junit-bom|org\.springframework\.boot:spring-boot-starter-test)"),
    ("Mockito", r"org\.mockito:.*"), ("Testcontainers", r"org\.testcontainers:.*"), ("ArchUnit", r"com\.tngtech\.archunit:.*"),
    ("Cucumber", r"io\.cucumber:.*"), ("Gatling", r"io\.gatling.*:.*"), ("REST Assured", r"io\.rest-assured:.*"),
    ("WireMock", r".*wiremock.*:.*"),
    ("JaCoCo", r"(org\.jacoco:jacoco-maven-plugin|plugin:jacoco)"),
    ("Checkstyle", r"(.*:maven-checkstyle-plugin|plugin:checkstyle)"), ("Spotless", r"(com\.diffplug\.spotless:.*|plugin:com\.diffplug\.spotless)"),
    ("SonarQube scanner", r"(org\.sonarsource\.scanner\.maven:sonar-maven-plugin|plugin:org\.sonarqube)"),
    ("PMD", r"(.*:maven-pmd-plugin|plugin:pmd)"), ("SpotBugs", r"(com\.github\.spotbugs:.*|plugin:com\.github\.spotbugs)"),
    ("Jib (container build)", r"(com\.google\.cloud\.tools:jib-maven-plugin|plugin:com\.google\.cloud\.tools\.jib)"),
    ("frontend-maven-plugin (builds the Angular app)", r"com\.github\.eirslett:frontend-maven-plugin"),
    ("Modernizer", r"org\.gaul:modernizer-maven-plugin"), ("Maven Enforcer", r".*:maven-enforcer-plugin"),
    ("Failsafe (integration tests)", r".*:maven-failsafe-plugin"), ("Git commit id plugin", r".*git-commit-id.*"),
]
NPM_KEYS = [("@angular/core", "Angular"), ("@angular/cli", "Angular CLI"), ("typescript", "TypeScript"),
            ("rxjs", "RxJS"), ("zone.js", "Zone.js"), ("@angular/material", "Angular Material"),
            ("primeng", "PrimeNG"), ("bootstrap", "Bootstrap"), ("@ng-bootstrap/ng-bootstrap", "ng-bootstrap"),
            ("@ngrx/store", "NgRx Store"), ("@ngrx/signals", "NgRx SignalStore"), ("@ngxs/store", "NGXS"),
            ("@ngx-translate/core", "ngx-translate"), ("@angular/localize", "Angular i18n"),
            ("@angular/ssr", "Angular SSR"), ("@nx/angular", "Nx"), ("tailwindcss", "Tailwind CSS"),
            ("jest", "Jest"), ("vitest", "Vitest"), ("karma", "Karma"), ("jasmine-core", "Jasmine"),
            ("cypress", "Cypress"), ("@playwright/test", "Playwright"), ("protractor", "Protractor"),
            ("eslint", "ESLint"), ("prettier", "Prettier"), ("husky", "Husky"), ("lint-staged", "lint-staged"),
            ("@commitlint/cli", "commitlint"), ("keycloak-angular", "keycloak-angular"),
            ("angular-oauth2-oidc", "angular-oauth2-oidc"), ("@azure/msal-angular", "MSAL Angular"),
            ("react", "React"), ("vue", "Vue")]
DOC_FILES = ["AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md", "CODEOWNERS", ".github/CODEOWNERS", ".gitlab/CODEOWNERS",
             "CHANGELOG.md", ".bobrules", ".github/copilot-instructions.md", ".editorconfig", "SECURITY.md"]
QUALITY_FILES = ["checkstyle.xml", "config/checkstyle/checkstyle.xml", "sonar-project.properties", ".eslintrc.json",
                 ".eslintrc.js", ".eslintrc.cjs", "eslint.config.js", "eslint.config.mjs", "eslint.config.ts",
                 ".prettierrc", ".prettierrc.json", ".prettierrc.js", "prettier.config.js", ".stylelintrc.json",
                 ".lintstagedrc", ".lintstagedrc.json", "commitlint.config.js", "commitlint.config.cjs",
                 ".pre-commit-config.yaml", "lombok.config", "renovate.json", ".github/dependabot.yml"]
KEY_SCRIPTS = re.compile(r"^(start|serve|build|test|lint|e2e|watch|format|prettier:check|ci:[\w:-]*test|"
                         r"backend:start|app:start|app:up|services:up|docker:db:up|webapp:build|webapp:prod|test:ci|e2e:headless)$")
AREAS = [  # for --since: (area, regex on path, pages to review)
    ("Database migrations", r"(db/migration|db/changelog|liquibase|flyway|\.sql$)", "Architecture (data), Codebase guide"),
    ("API contracts", r"(openapi|swagger|Controller\.java$|Resource\.java$|\.proto$|\.graphql$)", "API & integrations"),
    ("Configuration", r"(application[^/]*\.(ya?ml|properties)$|environment[^/]*\.ts$|proxy\.conf)", "Quick start, CI/CD & environments"),
    ("Build and dependencies", r"(pom\.xml$|build\.gradle(\.kts)?$|libs\.versions\.toml$|package(-lock)?\.json$|\.nvmrc$)", "Home (stack), Quick start"),
    ("CI/CD", r"(\.gitlab-ci\.yml$|\.gitlab/|Jenkinsfile|\.github/workflows/)", "CI/CD & environments"),
    ("Deployment", r"(Dockerfile|docker-compose|compose\.ya?ml$|/helm/|/charts/|/k8s/|kustomization|/argocd/|\.tf$)", "CI/CD & environments, Operations"),
    ("Security", r"(Security[^/]*\.java$|/security/|guard[^/]*\.ts$|interceptor[^/]*\.ts$|auth[^/]*\.ts$)", "Architecture (security)"),
    ("Frontend code", r"\.(ts|html|scss|css)$", "Architecture (frontend), Codebase guide"),
    ("Backend code", r"\.(java|kt)$", "Architecture (backend), Codebase guide"),
    ("Documentation", r"(\.md$|\.adoc$|/docs/)", "check for content to merge into the playbook"),
]


def read(path):
    try:
        if os.path.getsize(path) > MAX_BYTES:
            return ""
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def git(root, *args):
    try:
        r = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, timeout=20)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def walk(root):
    for d, dirs, files in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS and not (x.startswith(".") and x not in KEEP_DOT_DIRS))
        for f in sorted(files):
            yield os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/")


def strip_registry(image):
    first, sep, rest = image.partition("/")
    return f"<registry>/{rest}" if sep and ("." in first or ":" in first) and first != "docker.io" else image


def safe_url(url):
    """Keep scheme, localhost targets and paths; hide other hosts and any credentials."""
    m = re.match(r"^([a-z][a-z0-9+.:-]*://)(?:[^@/]*@)?([^/:?]+)(:\d+)?(.*)$", url.strip(), re.I)
    if not m:
        return url if not re.search(r"[:@]", url) else "<hidden>"
    host = m.group(2)
    if host in ("localhost", "127.0.0.1", "0.0.0.0") or host.endswith(".local") or "mem" in m.group(1):
        return f"{m.group(1)}{host}{m.group(3) or ''}{m.group(4)}"
    return f"{m.group(1)}<host>{m.group(3) or ''}{m.group(4)}"


def flatten_yaml(text):
    """Flatten simple YAML into (key.path, value, line). Lists and multi-line values are skipped."""
    out, stack = [], []
    for no, line in enumerate(text.splitlines(), 1):
        if line.strip() == "---":
            stack = []
            continue
        m = re.match(r"^(\s*)([\w.\-\[\]\"'@/]+)\s*:(?:\s+(.*))?$", line)
        if not m or line.lstrip().startswith("#"):
            continue
        indent, key, value = len(m.group(1)), m.group(2).strip("\"'"), (m.group(3) or "").strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        stack.append((indent, key))
        if value and not value.startswith(("|", ">", "#")):
            value = re.sub(r"\s+#.*$", "", value).strip("\"'")
            out.append((".".join(k for _, k in stack), value, no))
    return out


def flatten_properties(text):
    out = []
    for no, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^\s*([^#!\s][^=:\s]*)\s*[=:]\s*(.*)$", line)
        if m:
            out.append((m.group(1), m.group(2).strip(), no))
    return out


class Scan:
    def __init__(self, root, label):
        self.root, self.label = os.path.abspath(root), label
        self.files = list(walk(self.root))
        self.d = OrderedDict()

    def p(self, rel):
        return rel if not self.label else f"{self.label}:{rel}"

    def text(self, rel):
        return read(os.path.join(self.root, rel))

    # ---------- build files and stack ----------
    def build(self):
        coords, versions, modules = set(), [], []
        poms = [f for f in self.files if f.endswith("pom.xml")]
        for pom in poms:
            t = self.text(pom)
            t_nc = re.sub(r"<!--.*?-->", "", t, flags=re.S)
            for g, a in re.findall(r"<groupId>\s*([^<\s]+)\s*</groupId>\s*<artifactId>\s*([^<\s]+)\s*</artifactId>", t_nc):
                coords.add(f"{g}:{a}")
            for a in re.findall(r"<plugin>\s*<artifactId>\s*([^<\s]+)\s*</artifactId>", t_nc):
                coords.add(f"org.apache.maven.plugins:{a}")
            own = re.sub(r"<parent>.*?</parent>", "", t_nc, flags=re.S)
            art = re.search(r"<artifactId>([^<]+)</artifactId>", own)
            props = dict(re.findall(r"<([\w.-]+)>([^<${}]+)</\1>", (re.search(r"<properties>(.*?)</properties>", t_nc, re.S) or [None, ""])[1]))
            resolve = lambda v: props.get(v[2:-1], v) if v.startswith("${") and v.endswith("}") else v
            packaging = re.search(r"<packaging>([^<]+)</packaging>", t_nc)
            modules.append(f"`{self.p(pom)}` — Maven `{art.group(1) if art else '?'}` ({packaging.group(1) if packaging else 'jar'})")
            boot = re.search(r"<parent>.*?<artifactId>spring-boot-starter-parent</artifactId>\s*<version>([^<]+)</version>", t_nc, re.S)
            if boot:
                versions.append(("Spring Boot", boot.group(1), pom))
            else:
                bv = re.search(r"<(spring-boot\.version|spring\.boot\.version)>([^<]+)<", t_nc)
                if bv:
                    versions.append(("Spring Boot", bv.group(2), pom))
            for tag, label in (("java.version", "Java"), ("maven.compiler.release", "Java"), ("maven.compiler.source", "Java"),
                               ("spring-cloud.version", "Spring Cloud"), ("node.version", "Node (Maven build)"),
                               ("npm.version", "npm (Maven build)"), ("kotlin.version", "Kotlin")):
                v = re.search(rf"<{re.escape(tag)}>([^<]+)<", t_nc)
                if v and (label, resolve(v.group(1)), pom) not in versions:
                    versions.append((label, resolve(v.group(1)), pom))
            nv = re.search(r"<nodeVersion>([^<]+)</nodeVersion>", t_nc)
            if nv and resolve(nv.group(1)) not in [v for _, v, _ in versions]:
                versions.append(("Node (frontend-maven-plugin)", resolve(nv.group(1)), pom))
        for g in [f for f in self.files if re.search(r"(^|/)build\.gradle(\.kts)?$", f)]:
            t = self.text(g)
            modules.append(f"`{self.p(g)}` — Gradle project")
            for c in re.findall(r"""["']([\w.\-]+:[\w.\-]+)(?::[^"']*)?["']""", t):
                coords.add(c)
            for pid in re.findall(r"""id\s*\(?\s*["']([\w.\-]+)["']""", t):
                coords.add(f"plugin:{pid}")
            for pid in re.findall(r"^\s*(jacoco|checkstyle|pmd)\s*$", t, re.M):
                coords.add(f"plugin:{pid}")
            boot = re.search(r"org\.springframework\.boot['\"]?\)?\s*version\s*['\"]([^'\"]+)", t)
            if boot:
                versions.append(("Spring Boot", boot.group(1), g))
            java = re.search(r"(?:JavaLanguageVersion\.of\((\d+)\)|sourceCompatibility\s*=\s*['\"]?(?:JavaVersion\.VERSION_)?([\d_.]+))", t)
            if java:
                versions.append(("Java", (java.group(1) or java.group(2)).replace("_", "."), g))
        for toml in [f for f in self.files if f.endswith("libs.versions.toml")]:
            t = self.text(toml)
            for g, a in re.findall(r"""module\s*=\s*["']([\w.\-]+):([\w.\-]+)["']""", t):
                coords.add(f"{g}:{a}")
            for g, a in re.findall(r"""group\s*=\s*["']([\w.\-]+)["']\s*,\s*name\s*=\s*["']([\w.\-]+)["']""", t):
                coords.add(f"{g}:{a}")
            for pid in re.findall(r"""id\s*=\s*["']([\w.\-]+)["']""", t):
                coords.add(f"plugin:{pid}")
        for s in [f for f in self.files if re.search(r"(^|/)settings\.gradle(\.kts)?$", f)]:
            inc = re.findall(r"""include\s*\(?\s*([^)\n]+)""", self.text(s))
            if inc:
                modules.append(f"`{self.p(s)}` — Gradle subprojects: " + ", ".join(
                    x.strip(" '\":") for i in inc for x in i.split(",") if x.strip(" '\":")))
        for f, label, rx in (("/.nvmrc", "Node", r"(\S+)"), ("/.node-version", "Node", r"(\S+)"),
                             ("/.sdkmanrc", "Java (sdkman)", r"java=(\S+)"), ("/.java-version", "Java", r"(\S+)"),
                             ("/.tool-versions", "Toolchain", r"((?:java|nodejs)\s+\S+)")):
            for path in [x for x in self.files if ("/" + x).endswith(f)]:
                for v in re.findall(rx, self.text(path))[:2]:
                    versions.append((label, v, path))
        wrapper = [x for x in self.files if re.search(r"(^|/)(mvnw|gradlew)$", x)]
        props = [x for x in self.files if x.endswith("maven-wrapper.properties") or x.endswith("gradle-wrapper.properties")]
        for w in props:
            v = re.search(r"(?:apache-maven|gradle)-([\d.]+)", self.text(w))
            if v:
                versions.append(("Maven" if "maven" in w else "Gradle", v.group(1) + " (wrapper)", w))
        caps = []
        for label, rx in CAPS:
            hit = sorted(c for c in coords if re.fullmatch(rx, c))
            if hit:
                caps.append(label)
        if any(l == "Spring Boot" for l, _, _ in versions) and not any(l.startswith("Java") for l, _, _ in versions):
            versions.append(("Java", "not declared: inherited from the Spring Boot parent/plugin default (check it)", poms[0] if poms else "?"))
        self.d["coords"] = sorted(coords)
        self.d["versions"], self.d["modules"], self.d["capabilities"] = versions, modules, caps
        self.d["wrappers"] = wrapper
        if any(c.startswith("org.openapitools:openapi-generator") for c in coords):
            specs = re.findall(r"<inputSpec>([^<]+)</inputSpec>", "".join(self.text(p) for p in poms))
            self.d["api_first"] = specs

    # ---------- Java backend ----------
    def backend(self):
        java = [f for f in self.files if f.endswith((".java", ".kt")) and "/test/" not in f and not f.startswith("test/")]
        tests = [f for f in self.files if f.endswith((".java", ".kt")) and ("/test/" in f or f.startswith("test/"))]
        if not java:
            return
        stereo = Counter()
        apps, controllers, entities, security, advice, clients, listeners, scheduled, packages = [], [], [], [], [], [], [], [], Counter()
        endpoints = []
        for f in java:
            t = self.text(f)
            pkg = re.search(r"^\s*package\s+([\w.]+)", t, re.M)
            if pkg:
                packages[pkg.group(1)] += 1
            if "@SpringBootApplication" in t:
                apps.append(f)
            for ann in ("RestController", "Controller", "Service", "Component", "Repository", "Entity", "Configuration",
                        "RestControllerAdvice", "ControllerAdvice", "FeignClient", "Aspect", "Document", "Mapper"):
                if re.search(rf"@{ann}\b", t):
                    stereo[ann] += 1
            if re.search(r"\binterface\s+\w+\s+extends\s+\w*(Jpa|Crud|PagingAndSorting|Mongo|Reactive\w*)Repository", t):
                stereo["Spring Data repository"] += 1
            if re.search(r"@Entity\b", t):
                entities.append(os.path.splitext(os.path.basename(f))[0])
            if re.search(r"SecurityFilterChain|@EnableWebSecurity|@EnableMethodSecurity|@EnableGlobalMethodSecurity|WebSecurityConfigurerAdapter", t):
                security.append(f)
            if re.search(r"@(Rest)?ControllerAdvice", t):
                advice.append(f)
            if re.search(r"@FeignClient|RestTemplate|WebClient\.|RestClient\.|HttpClient\.new", t):
                clients.append(f)
            if re.search(r"@(KafkaListener|RabbitListener|JmsListener|SqsListener|EventListener|TransactionalEventListener)\b", t):
                listeners.append(f)
            if re.search(r"@Scheduled\b", t):
                scheduled.append(f)
            if re.search(r"@(Rest)?Controller\b", t):
                count = self._endpoints(f, t, endpoints)
                controllers.append((f, count))
        base = os.path.commonprefix([p.split(".") for p in packages]) if packages else []
        app_pkg = None
        if apps:
            m = re.search(r"^\s*package\s+([\w.]+)", self.text(apps[0]), re.M)
            app_pkg = m.group(1) if m else None
        base_pkg = app_pkg or ".".join(base)
        tree = Counter()
        for pkg, n in packages.items():
            if base_pkg and pkg.startswith(base_pkg):
                rest = pkg[len(base_pkg):].strip(".").split(".")
                tree[".".join(rest[:2]) or "(root)"] += n
        self.d["backend"] = {
            "main_files": len(java), "test_files": len(tests), "base_package": base_pkg,
            "package_tree": tree.most_common(40), "stereotypes": dict(stereo), "applications": apps,
            "controllers": sorted(controllers, key=lambda x: -x[1]), "endpoints": endpoints, "entities": sorted(entities),
            "security": security, "exception_handlers": advice, "http_clients": clients[:15],
            "listeners": listeners[:15], "scheduled": scheduled[:15],
            "integration_tests": len([t for t in tests if re.search(r"(IT|IntTest|IntegrationTest)\.(java|kt)$", t)]),
        }

    @staticmethod
    def _ann_path(args):
        if args is None:
            return ""
        m = re.search(r"(?:value|path)\s*=\s*\{?\s*\"([^\"]*)\"", args) or re.search(r"^\s*\{?\s*\"([^\"]*)\"", args)
        if m:
            return m.group(1)
        expr = args.split(",")[0].strip()
        return f"<{expr}>" if expr and "=" not in expr else ""

    def _endpoints(self, f, t, out):
        cls = re.search(r"@RequestMapping\s*(?:\((.*?)\))?\s*(?:@\w+(?:\([^)]*\))?\s*)*public\s+(?:final\s+)?(?:class|interface)", t, re.S)
        prefix = self._ann_path(cls.group(1)) if cls else ""
        name = os.path.splitext(os.path.basename(f))[0]
        n = 0
        for m in re.finditer(r"@(Get|Post|Put|Delete|Patch|Request)Mapping\s*(?:\(([^)]*)\))?", t):
            if cls and m.start() == cls.start():
                continue
            verb, args = m.group(1).upper(), m.group(2)
            if verb == "REQUEST":
                vm = re.search(r"RequestMethod\.(\w+)", args or "")
                if not vm and m.start() < (cls.end() if cls else 0):
                    continue
                verb = vm.group(1) if vm else "ANY"
            line = t.count("\n", 0, m.start()) + 1
            out.append((verb, re.sub(r"/{2,}", "/", "/" + prefix + "/" + self._ann_path(args)).rstrip("/") or "/", name, f"{f}:{line}"))
            n += 1
        return n

    # ---------- API specs ----------
    def api_specs(self):
        specs = []
        for f in self.files:
            low = f.lower()
            if not re.search(r"(openapi|swagger|api-docs|\.api)\.?[^/]*\.(ya?ml|json)$", low) or "node_modules" in low:
                continue
            t = self.text(f)
            if not re.search(r"\"?(openapi|swagger)\"?\s*:", t):
                continue
            ops = []
            if low.endswith(".json"):
                try:
                    doc = json.loads(t)
                    ops = [(meth.upper(), path) for path, item in (doc.get("paths") or {}).items()
                           for meth in item if meth in ("get", "post", "put", "delete", "patch")]
                except ValueError:
                    pass
            else:
                in_paths, path = False, None
                for line in t.splitlines():
                    if re.match(r"^paths:\s*$", line):
                        in_paths = True
                        continue
                    if in_paths and re.match(r"^\S", line):
                        in_paths = False
                    if in_paths:
                        pm = re.match(r"^  (['\"]?/[^:]*?['\"]?):\s*$", line)
                        if pm:
                            path = pm.group(1).strip("'\"")
                        mm = re.match(r"^    (get|post|put|delete|patch):\s*$", line)
                        if mm and path:
                            ops.append((mm.group(1).upper(), path))
            ver = re.search(r"\"?(openapi|swagger)\"?\s*:\s*[\"']?([\d.]+)", t)
            specs.append({"file": f, "version": ver.group(2) if ver else "?", "operations": ops})
        self.d["api_specs"] = specs

    # ---------- configuration ----------
    def config(self):
        files = [f for f in self.files if re.search(r"(^|/)(application|bootstrap)[^/]*\.(ya?ml|properties)$", f)
                 and "/test/" not in f and "node_modules" not in f]
        profiles, env_vars, shown, groups, secrets = set(), OrderedDict(), [], OrderedDict(), []
        for f in files:
            m = re.search(r"(?:application|bootstrap)-([\w-]+)\.", os.path.basename(f))
            if m:
                profiles.add(m.group(1))
            t = self.text(f)
            pairs = flatten_properties(t) if f.endswith(".properties") else flatten_yaml(t)
            keys = []
            for key, value, line in pairs:
                keys.append(".".join(key.split(".")[:2]))
                for var, default in ENV_REF.findall(value):
                    env_vars.setdefault(var, []).append(f"{f}:{line}" + (" (has default)" if default else ""))
                if key.endswith("on-profile") or key.endswith("profiles.active"):
                    profiles.update(p.strip() for p in re.split(r"[,|&!() ]+", value) if re.fullmatch(r"[\w-]+", p.strip()))
                if SECRET_KEY.search(key.split(".")[-1]) and not PLACEHOLDER.match(value) and "${" not in value \
                        and value.lower() not in ("true", "false", "none", "null", "~") and not re.fullmatch(r"[\d.]+[smhd]?", value) \
                        and not re.search(r"(validity|expir|ttl|timeout|length|size|enabled|header|name|uri|url|path)[^.]*$", key, re.I):
                    secrets.append(f"`{self.p(f)}:{line}` `{key}` (value hidden)")
                elif SHOW_VALUE_KEYS.match(key):
                    shown.append(f"`{key}` = `{value}` ({f}:{line})")
                elif re.search(r"datasource\.(url|jdbc-url)$|r2dbc\.url$|liquibase\.url$|flyway\.url$", key):
                    scheme = re.match(r"^(jdbc:\w+|r2dbc:\w+)", value)
                    local = re.search(r"localhost|127\.0\.0\.1|mem:|file:", value)
                    shown_value = scheme.group(1) + (":…(local)" if local else ":…") if scheme else safe_url(value)
                    shown.append(f"`{key}` = `{shown_value}` ({f}:{line})")
            groups[f] = list(OrderedDict.fromkeys(k for k in keys if k))[:18]
        fe_env = []
        for f in self.files:
            if re.search(r"(^|/)environments?/environment[^/]*\.ts$", f):
                items = []
                for key, val in re.findall(r"""(?:^|[,{\s])(\w+)\s*:(?!//)\s*(['"`][^'"`]*['"`]|true|false|\d+)?""", self.text(f), re.M):
                    val = val.strip("'\"`")
                    show = val in ("true", "false") or val.isdigit() or val.startswith("/") or re.match(r"https?://(localhost|127\.0\.0\.1)", val)
                    items.append(f"{key}={val}" if show else key)
                fe_env.append(f"`{self.p(f)}`: " + ", ".join(dict.fromkeys(items)))
        proxies = []
        for f in self.files:
            if re.search(r"(^|/)proxy\.conf(ig)?\.(json|js|mjs|cjs)$", f):
                t = self.text(f)
                consts = dict(re.findall(r"""(?:const|let|var)\s+(\w+)\s*=\s*['"]?([\w.:/-]+)['"]?""", t))
                targets = [safe_url(re.sub(r"\$\{(\w+)\}", lambda m: consts.get(m.group(1), m.group(0)), u))
                           for u in re.findall(r"""target['"]?\s*:\s*[`'"]([^`'"]+)""", t)]
                contexts = re.findall(r"""['"](\^?/[^'"]*)['"]\s*:""", t) or re.findall(r"""['"](/[\w/*.-]+)['"]""", t)[:8]
                proxies.append(f"`{self.p(f)}`: {', '.join(dict.fromkeys(contexts)) or '?'} → {', '.join(dict.fromkeys(targets)) or '?'}")
        dotenv = [f for f in self.files if re.search(r"(^|/)\.env(\.[\w-]+)?$|\.env\.(example|sample|template)$", f)]
        for f in dotenv:
            for var in re.findall(r"^\s*(?:export\s+)?([A-Z][A-Z0-9_]+)\s*=", self.text(f), re.M):
                env_vars.setdefault(var, []).append(f)
        self.d["config"] = {"files": files, "profiles": sorted(profiles), "env_vars": env_vars, "shown": shown,
                            "groups": groups, "secret_literals": secrets, "frontend_env": fe_env, "proxies": proxies,
                            "dotenv": dotenv}

    # ---------- Angular / frontend ----------
    def frontend(self):
        pkgs = [f for f in self.files if f.endswith("package.json") and "node_modules" not in f]
        fe = {"packages": []}
        for f in pkgs:
            try:
                pkg = json.loads(self.text(f) or "{}")
            except ValueError:
                continue
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            found = [(label, deps[name]) for name, label in NPM_KEYS if name in deps]
            engines = pkg.get("engines", {})
            scripts = pkg.get("scripts", {})
            fe["packages"].append({"file": f, "name": pkg.get("name"), "libs": found, "engines": engines,
                                   "scripts": scripts, "packageManager": pkg.get("packageManager")})
        for f in [x for x in self.files if re.search(r"(^|/)(angular|workspace|project)\.json$", x)]:
            try:
                ng = json.loads(self.text(f) or "{}")
            except ValueError:
                continue
            projects = ng.get("projects") or ({ng["name"]: ng} if f.endswith("project.json") and "targets" in ng else {})
            for name, prj in projects.items():
                if not isinstance(prj, dict):
                    continue
                arch = prj.get("architect") or prj.get("targets") or {}
                serve = (arch.get("serve") or {}).get("options", {})
                fe.setdefault("angular_projects", []).append({
                    "file": f, "name": name, "type": prj.get("projectType"), "root": prj.get("root"),
                    "sourceRoot": prj.get("sourceRoot"), "prefix": prj.get("prefix"),
                    "build": (arch.get("build") or {}).get("builder") or (arch.get("build") or {}).get("executor"),
                    "test": (arch.get("test") or {}).get("builder") or (arch.get("test") or {}).get("executor"),
                    "proxy": serve.get("proxyConfig"), "configurations": sorted((arch.get("build") or {}).get("configurations", {}))})
        ts = [f for f in self.files if f.endswith(".ts") and not f.endswith(".d.ts") and "node_modules" not in f]
        if not ts or not (fe["packages"] or fe.get("angular_projects")):
            self.d["frontend"] = fe if fe["packages"] else None
            return
        kinds = Counter()
        interceptors, guards, routes, http_services, stores, mains, ngmodules, standalone = [], [], [], 0, [], [], 0, 0
        for f in ts:
            base = os.path.basename(f)
            if base.endswith((".spec.ts", ".test.ts")) or "/e2e/" in f or "cypress/" in f:
                kinds["spec"] += 1
                continue
            m = re.search(r"\.(guard|interceptor|resolver|store|effects|reducer|facade|model|routes|route)\.ts$", base)
            if m:
                kinds[m.group(1)] += 1
            t = self.text(f)
            for dec, name in (("@Component(", "@Component"), ("@Injectable(", "@Injectable"), ("@Directive(", "@Directive"), ("@Pipe(", "@Pipe")):
                if dec in t:
                    kinds[name] += 1
            if "@NgModule" in t:
                ngmodules += 1
            if re.search(r"standalone\s*:\s*true", t):
                standalone += 1
            if re.search(r"HttpInterceptor\b|HttpInterceptorFn", t):
                interceptors.append(f)
            if re.search(r"\b(CanActivateFn|CanActivateChildFn|CanMatchFn|CanDeactivateFn)\b|implements\s+(CanActivate|CanMatch|CanDeactivate)", t):
                guards.append(f)
            if re.search(r"inject\(HttpClient\)|private\s+(readonly\s+)?\w+\s*:\s*HttpClient|HttpClient\s*[,)]", t):
                http_services += 1
            if re.search(r"createReducer|createEffect|signalStore|ComponentStore|@State\(", t):
                stores.append(f)
            if not re.match(r"(docs?|e2e|tools?|scripts)/", f) and base in ("main.ts", "bootstrap.ts", "app.config.ts", "app.module.ts", "app.routes.ts", "app-routing.module.ts", "app.component.ts"):
                mains.append(f)
            if base.endswith(("routes.ts", "routing.module.ts", ".route.ts")) or re.search(r"\bRoutes\s*=\s*\[", t):
                paths = re.findall(r"""path\s*:\s*['"`]([^'"`]*)['"`]""", t)
                lazy = len(re.findall(r"loadChildren|loadComponent", t))
                if paths:
                    routes.append((f, paths, lazy))
        main_ts = "".join(self.text(f) for f in mains if f.endswith(("main.ts", "bootstrap.ts")))
        fe.update({
            "kinds": dict(kinds), "interceptors": interceptors, "guards": guards[:15], "routes": routes,
            "http_services": http_services, "stores": stores[:10], "entry_files": mains,
            "ngmodules": ngmodules, "standalone_declared": standalone,
            "bootstrap": "bootstrapApplication (standalone)" if "bootstrapApplication" in main_ts else
                         ("bootstrapModule (NgModule)" if "bootstrapModule" in main_ts else "?"),
            "zoneless": any("provideZonelessChangeDetection" in self.text(f) or "provideExperimentalZonelessChangeDetection" in self.text(f) for f in mains),
        })
        self.d["frontend"] = fe

    # ---------- database ----------
    def database(self):
        mig = [f for f in self.files if re.search(r"(db/migration|db/changelog|liquibase|flyway)/", f) and
               f.endswith((".sql", ".xml", ".yaml", ".yml", ".json")) and "/test/" not in f]
        flyway = sorted((f for f in mig if re.search(r"/V\d+[._\d]*__[^/]+\.sql$", f)),
                        key=lambda f: [int(x) for x in re.findall(r"\d+", re.search(r"/V([\d._]+)__", f).group(1))])
        self.d["database"] = {"migration_files": len(mig), "flyway_versioned": flyway[-3:] if flyway else [],
                              "flyway_count": len(flyway),
                              "liquibase_master": [f for f in mig if re.search(r"(master|changelog)[^/]*\.(xml|ya?ml|json)$", f)][:3],
                              "migration_dirs": sorted({os.path.dirname(f) for f in mig})[:6],
                              "sql_scripts": [f for f in self.files if f.endswith(".sql") and f not in mig][:8]}

    # ---------- CI/CD and deployment ----------
    def delivery(self):
        ci = []
        for f in [x for x in self.files if x.endswith(".gitlab-ci.yml") or x.startswith(".gitlab/ci/")]:
            t = self.text(f)
            stages = re.search(r"^stages:\s*\n((?:\s+-\s*.+\n)+)", t, re.M)
            reserved = {"stages", "variables", "include", "default", "workflow", "image", "services", "before_script",
                        "after_script", "cache", "spec"}
            jobs = [j for j in re.findall(r"^([A-Za-z0-9_][\w :./-]*):\s*$", t, re.M) if j not in reserved]
            includes = re.findall(r"^\s*-?\s*(?:project|template|component|local|remote|file):\s*['\"]?([^'\"\n]+)", t, re.M)
            envs = re.findall(r"^\s+environment:\s*\n\s+name:\s*['\"]?([^'\"\n]+)|^\s+environment:\s*['\"]?([\w/${}-]+)", t, re.M)
            ci.append({"file": f, "kind": "GitLab CI",
                       "stages": re.findall(r"-\s*['\"]?([\w-]+)", stages.group(1)) if stages else [],
                       "jobs": jobs[:40], "includes": [safe_url(i) if "://" in i else i for i in includes][:10],
                       "environments": sorted({a or b for a, b in envs})})
        for f in [x for x in self.files if x.startswith(".github/workflows/")]:
            t = self.text(f)
            name = re.search(r"^name:\s*['\"]?(.+?)['\"]?\s*$", t, re.M)
            jobs_block = t.split("\njobs:", 1)[1] if "\njobs:" in t else ""
            on = re.search(r"^on:[ \t]*(.*)$", t, re.M)
            ci.append({"file": f, "kind": "GitHub Actions", "name": name.group(1) if name else f,
                       "jobs": re.findall(r"^  ([\w-]+):\s*$", jobs_block, re.M)[:20],
                       "triggers": (on.group(1).strip() or ", ".join(re.findall(r"^  (push|pull_request|workflow_dispatch|schedule|release|merge_group):", t, re.M))) if on else ""})
        for f in [x for x in self.files if re.search(r"(^|/)Jenkinsfile[^/]*$", x)]:
            ci.append({"file": f, "kind": "Jenkins", "stages": re.findall(r"stage\s*\(\s*['\"]([^'\"]+)", self.text(f))})
        for f in [x for x in self.files if x in ("azure-pipelines.yml", ".travis.yml", "bitbucket-pipelines.yml", ".circleci/config.yml", "Tektonfile")]:
            ci.append({"file": f, "kind": f})
        docker = []
        for f in [x for x in self.files if re.search(r"(^|/)(Dockerfile|Containerfile)[^/]*$", x)]:
            froms = [strip_registry(i) for i in re.findall(r"^\s*FROM\s+(?:--platform=\S+\s+)?(\S+)", self.text(f), re.M | re.I)]
            docker.append(f"`{self.p(f)}`: FROM {', '.join(froms)}")
        compose = []
        for f in [x for x in self.files if re.search(r"(^|/)(docker-)?compose[^/]*\.ya?ml$|src/main/docker/[^/]+\.ya?ml$", x)]:
            t = self.text(f)
            if "services:" not in t:
                continue
            block = t.split("services:", 1)[1]
            names = re.findall(r"^  ([\w.-]+):\s*$", block, re.M)
            images = [strip_registry(i) for i in re.findall(r"^\s+image:\s*['\"]?([^'\"\s]+)", block, re.M)]
            compose.append(f"`{self.p(f)}`: services {', '.join(names[:10])}" + (f" (images: {', '.join(images[:6])})" if images else ""))
        helm = []
        for f in [x for x in self.files if x.endswith("Chart.yaml")]:
            t = self.text(f)
            n, v = re.search(r"^name:\s*(\S+)", t, re.M), re.search(r"^version:\s*(\S+)", t, re.M)
            values = sorted(os.path.basename(x) for x in self.files if x.startswith(os.path.dirname(f)) and re.search(r"values[^/]*\.ya?ml$", x))
            helm.append(f"`{self.p(f)}`: chart {n.group(1) if n else '?'} {v.group(1) if v else ''}; values: {', '.join(values)}")
        kustom = sorted(os.path.dirname(f) or "." for f in self.files if f.endswith("kustomization.yaml") or f.endswith("kustomization.yml"))
        kinds = Counter()
        argocd = []
        for f in self.files:
            if f.endswith((".yaml", ".yml")) and re.search(r"(^|/)(k8s|kubernetes|deploy|deployment|manifests|helm|charts|openshift|argocd|gitops|kustomize|overlays|base)/", f):
                t = self.text(f)
                for k in re.findall(r"^kind:\s*(\w+)", t, re.M):
                    kinds[k] += 1
                if re.search(r"^kind:\s*(Application|ApplicationSet)\s*$", t, re.M) and "argoproj.io" in t:
                    argocd.append(f)
        tf = sorted({os.path.dirname(f) or "." for f in self.files if f.endswith(".tf")})
        envs = set(self.d.get("config", {}).get("profiles", []))
        for line in helm:
            envs.update(re.findall(r"values-([\w-]+)\.ya?ml", line))
        for k in kustom:
            if "/overlays/" in "/" + k + "/":
                envs.add(k.rstrip("/").split("/")[-1])
        for c in ci:
            envs.update(e for e in c.get("environments", []) if "$" not in e)
        self.d["delivery"] = {"ci": ci, "docker": docker, "compose": compose, "helm": helm, "kustomize": kustom[:12],
                              "k8s_kinds": dict(kinds.most_common(12)), "argocd": argocd[:8], "terraform": tf[:8],
                              "environments": sorted(envs)}

    # ---------- docs, quality, tests, git ----------
    def docs(self):
        readmes = [f for f in self.files if re.search(r"(^|/)readme(\.\w+)?$", f, re.I) and f.count("/") <= 2]
        heads = {}
        for r in readmes[:4]:
            lines, fence, found = self.text(r).splitlines(), False, []
            for no, line in enumerate(lines, 1):
                if re.match(r"^\s*(```|~~~)", line):
                    fence = not fence
                hm = None if fence else re.match(r"^#{1,3}\s+(.+)$", line)
                if hm:
                    found.append(f"{hm.group(1).strip(' *')} (L{no})")
            heads[r] = (len(lines), found[:20])
        docs = [f for f in self.files if re.match(r"(docs?|documentation|wiki)/", f, re.I) and f.endswith((".md", ".adoc", ".rst"))]
        adrs = [f for f in docs + self.files if re.search(r"(^|/)(adr|adrs|decisions|architecture/decisions)/", f, re.I) and f.endswith((".md", ".adoc"))]
        present = [f for f in DOC_FILES if f in self.files]
        templates = [f for f in self.files if re.search(r"(merge_request_templates|PULL_REQUEST_TEMPLATE|pull_request_template)", f)]
        bob_rules = sorted({f.split("/")[1] for f in self.files if f.startswith(".bob/") and "/rules" in f})
        playbook = [f for f in self.files if re.search(r"(^|/)playbook/[^/]+\.md$", f)]
        quality = [f for f in QUALITY_FILES if f in self.files]
        self.d["docs"] = {"readmes": heads, "docs": docs[:30], "docs_count": len(docs), "adrs": sorted(set(adrs))[:20],
                          "instruction_files": present, "mr_templates": templates, "bob_rules": bob_rules,
                          "existing_playbook": playbook[:15], "quality_files": quality}

    def git_info(self, since):
        if not git(self.root, "rev-parse", "--git-dir"):
            self.d["git"] = None
            return
        head = git(self.root, "log", "-1", "--format=%h %cs")
        branch = git(self.root, "rev-parse", "--abbrev-ref", "HEAD")
        default = git(self.root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD").replace("origin/", "")
        remote = git(self.root, "remote", "get-url", "origin")
        provider = "GitLab" if "gitlab" in remote else "GitHub" if "github" in remote else "Bitbucket" if "bitbucket" in remote else ("other" if remote else "none")
        branches = git(self.root, "branch", "-r", "--format=%(refname:short)").splitlines()
        prefixes = Counter(b.split("/", 2)[1] for b in branches if b.count("/") >= 2)
        subjects = git(self.root, "log", "-200", "--format=%s").splitlines()
        conv = sum(bool(re.match(r"^[a-z]+(\([^)]*\))?!?:\s", s)) for s in subjects)
        ticket = sum(bool(re.search(r"\b[A-Z][A-Z0-9]+-\d+\b", s)) for s in subjects)
        merges = len(git(self.root, "log", "-200", "--merges", "--format=%h").splitlines())
        tags = git(self.root, "tag", "--sort=-creatordate").splitlines()[:5]
        shallow = git(self.root, "rev-parse", "--is-shallow-repository") == "true"
        info = {"head": head, "branch": branch, "default_branch": default or "?", "provider": provider,
                "branch_prefixes": dict(prefixes.most_common(8)), "commits_sampled": len(subjects),
                "conventional_share": round(conv / len(subjects), 2) if subjects else 0,
                "ticket_ref_share": round(ticket / len(subjects), 2) if subjects else 0,
                "merge_commits": merges, "recent_tags": tags, "shallow": shallow,
                "examples": subjects[:5]}
        if since:
            changed = git(self.root, "diff", "--name-only", f"{since}..HEAD").splitlines()
            areas = OrderedDict()
            for f in changed:
                for area, rx, pages in AREAS:
                    if re.search(rx, f):
                        areas.setdefault(area, {"pages": pages, "files": []})["files"].append(f)
                        break
            info["since"] = {"ref": since, "changed": len(changed), "areas": areas,
                             "error": None if changed or git(self.root, "rev-parse", "--verify", since) else f"unknown ref {since}"}
        self.d["git"] = info

    def tests(self):
        fe_spec = len([f for f in self.files if f.endswith((".spec.ts", ".test.ts"))])
        dirs = lambda rx: sorted({re.search(rx, f).group(0).rstrip("/") for f in self.files if re.search(rx, f)})[:5]
        e2e = dirs(r"^(.*?/)?(e2e|cypress|playwright)/")
        perf = dirs(r"^(.*?/)?(gatling|jmeter|k6)/")
        self.d["tests"] = {"frontend_spec_files": fe_spec, "e2e_dirs": e2e, "perf": perf}

    def sizes(self):
        c = Counter()
        for f in self.files:
            ext = os.path.splitext(f)[1].lower()
            if f.endswith((".spec.ts", ".test.ts")):
                c["ts (tests)"] += 1
            elif ext in (".java", ".kt"):
                c[f"{ext[1:]} ({'tests' if '/test/' in f else 'main'})"] += 1
            elif ext in (".ts", ".html", ".scss", ".css", ".sql", ".yml", ".yaml", ".xml", ".md"):
                c[ext[1:]] += 1
        self.d["sizes"] = dict(c.most_common())
        self.d["total_files"] = len(self.files)

    def reading_list(self):
        """The files most worth reading next, in order, for a newcomer's view of the system."""
        r, d = [], self.d
        add = lambda f, why: r.append((f, why)) if f and f not in [x for x, _ in r] else None
        for f in self.files:
            if re.fullmatch(r"readme(\.\w+)?", f, re.I):
                add(f, "project overview and documented setup: if long, read only the sections you need (line numbers under Existing documentation)")
        for f in d.get("docs", {}).get("instruction_files", []):
            if f in ("AGENTS.md", "CONTRIBUTING.md", "CLAUDE.md"):
                add(f, "team rules and conventions")
        be = d.get("backend") or {}
        for f in be.get("applications", [])[:2]:
            add(f, "backend entry point")
        cfg = (d.get("config") or {}).get("files", [])
        main_cfg = next((f for f in cfg if re.search(r"/application\.(ya?ml|properties)$", f)), None)
        add(main_cfg, "backend configuration (profiles, ports, integrations)")
        for f in be.get("security", [])[:2]:
            add(f, "security configuration")
        if be.get("controllers"):
            api_first = d.get("api_first") is not None
            top = max(be["controllers"], key=lambda c: (0 if api_first else c[1], len(self.text(c[0]))))
            add(top[0], "largest controller: read it as the reference pattern for endpoints")
        for f in be.get("exception_handlers", [])[:1]:
            add(f, "error handling and API error format")
        for spec in (d.get("api_specs") or [])[:1]:
            add(spec["file"], "API contract")
        fe = d.get("frontend") or {}
        for f in fe.get("entry_files", []):
            if os.path.basename(f) in ("app.config.ts", "app.module.ts", "app.routes.ts", "app-routing.module.ts"):
                add(f, "frontend bootstrap and routing")
        for f in fe.get("interceptors", [])[:3]:
            add(f, "frontend ↔ backend: HTTP interceptor (auth, errors)")
        for line in (d.get("config") or {}).get("proxies", [])[:1]:
            add(re.search(r"`(?:[^`:]+:)?([^`]+)`", line).group(1), "dev proxy to the backend")
        dl = d.get("delivery") or {}
        for c in sorted(dl.get("ci", []), key=lambda c: (bool(re.search(r"dependabot|renovate|stale|label", c["file"], re.I)),
                                                           not re.search(r"build|ci|pipeline|deploy|release|main|master", c["file"], re.I)))[:2]:
            add(c["file"], "CI/CD pipeline")
        for line in dl.get("docker", [])[:1] + dl.get("compose", [])[:1]:
            add(re.search(r"`(?:[^`:]+:)?([^`]+)`", line).group(1), "container build / local services")
        db = d.get("database") or {}
        for f in db.get("liquibase_master", [])[:1] + db.get("flyway_versioned", [])[-1:]:
            add(f, "database schema evolution")
        self.d["reading_list"] = r[:20]

    def run(self, since):
        self.build()
        self.backend()
        self.api_specs()
        self.config()
        self.frontend()
        self.database()
        self.delivery()
        self.docs()
        self.tests()
        self.sizes()
        self.git_info(since)
        self.reading_list()
        return self.d


# ---------------------------------------------------------------- rendering
def render(scans, max_endpoints):
    out = []
    w = out.append
    multi = len(scans) > 1
    names = ", ".join(f"`{s.label or os.path.basename(s.root)}`" for s in scans)
    w(f"# Project scan — {names}\n")
    for s in scans:
        d, g = s.d, s.d.get("git") or {}
        has_be, has_fe = bool(d.get("backend")), bool((d.get("frontend") or {}).get("angular_projects") or (d.get("frontend") or {}).get("kinds"))
        layout = "backend + frontend (monorepo)" if has_be and has_fe else "backend only" if has_be else "frontend only" if has_fe else "no Java/Angular code found"
        w(f"**{s.label or os.path.basename(s.root)}**: {layout}; {d['total_files']} files; "
          + (f"git {g.get('head')} on `{g.get('branch')}` (default `{g.get('default_branch')}`, {g.get('provider')})" + (", shallow clone" if g.get("shallow") else "") if g else "not a git repository"))
    if multi:
        w("Paths below are prefixed with the repository label.")
    for s in scans:
        if s.d.get("secret_scan_note"):
            w(s.d["secret_scan_note"])

    w("\n## Stack and versions")
    w("| Component | Version | Source |\n| --- | --- | --- |")
    for s in scans:
        for label, v, src in s.d.get("versions", []):
            w(f"| {label} | {v} | `{s.p(src)}` |")
        for pkg in (s.d.get("frontend") or {}).get("packages", []):
            for label, v in pkg["libs"]:
                w(f"| {label} | {v} | `{s.p(pkg['file'])}` |")
            for k, v in pkg["engines"].items():
                w(f"| {k} (engines) | {v} | `{s.p(pkg['file'])}` |")
            if pkg.get("packageManager"):
                w(f"| package manager | {pkg['packageManager']} | `{s.p(pkg['file'])}` |")
    for s in scans:
        if s.d.get("capabilities"):
            w(f"\nBackend capabilities (from build dependencies{', ' + s.label if multi else ''}): " + ", ".join(s.d["capabilities"]))
        if s.d.get("api_first") is not None:
            w(f"API-first: controllers generated by OpenAPI Generator from {', '.join('`' + x + '`' for x in s.d['api_first']) or 'a spec (see the build file)'}"
              " (generated code is under `target/` or `build/`, not in the repository).")

    w("\n## Modules and entry points")
    for s in scans:
        for m in s.d.get("modules", []):
            w(f"- {m}")
        for a in (s.d.get("backend") or {}).get("applications", []):
            w(f"- Spring Boot application: `{s.p(a)}`")
        fe = s.d.get("frontend") or {}
        for prj in fe.get("angular_projects", []):
            w(f"- Angular {prj['type'] or 'project'} `{prj['name']}` (root `{prj['root'] or '.'}`, src `{prj['sourceRoot']}`, prefix `{prj['prefix'] or '-'}`, "
              f"build `{prj['build']}`, test `{prj['test']}`, configurations {', '.join(prj['configurations']) or '-'}"
              + (f", dev proxy `{prj['proxy']}`" if prj.get("proxy") else "") + f") in `{s.p(prj['file'])}`")
        if fe.get("entry_files"):
            w(f"- Frontend bootstrap: {fe.get('bootstrap')}; zoneless: {'yes' if fe.get('zoneless') else 'no'}; "
              f"files: {', '.join('`' + s.p(f) + '`' for f in fe['entry_files'])}")

    for s in scans:
        be = s.d.get("backend")
        if not be:
            continue
        w(f"\n## Backend{' — ' + s.label if multi else ''}")
        w(f"{be['main_files']} main and {be['test_files']} test source files ({be['integration_tests']} integration tests by name); base package `{be['base_package']}`.")
        st = be["stereotypes"]
        w("Stereotypes: " + ", ".join(f"{k} {v}" for k, v in sorted(st.items(), key=lambda x: -x[1])))
        w("Packages under the base package (files): " + ", ".join(f"`{p}` {n}" for p, n in be["package_tree"]))
        if be["entities"]:
            w(f"JPA entities ({len(be['entities'])}): " + ", ".join(be["entities"][:40]) + (" …" if len(be["entities"]) > 40 else ""))
        for label, key in (("Security configuration", "security"), ("Exception handlers", "exception_handlers"),
                           ("Outbound HTTP clients", "http_clients"), ("Message/event listeners", "listeners"),
                           ("Scheduled jobs", "scheduled")):
            if be[key]:
                w(f"{label}: " + ", ".join(f"`{s.p(f)}`" for f in be[key][:8]) + (f" (+{len(be[key]) - 8})" if len(be[key]) > 8 else ""))
        eps = be["endpoints"]
        if eps:
            w(f"\nREST endpoints: {len(eps)} in {len(be['controllers'])} controllers"
              + (": " + ", ".join(f"`{s.p(f)}`" for f, _ in be["controllers"][:30]) if len(eps) <= max_endpoints else "."))
            if len(eps) <= max_endpoints:
                w("| Method | Path | Controller | Location |\n| --- | --- | --- | --- |")
                for verb, path, ctrl, loc in sorted(eps, key=lambda e: (e[1], e[0])):
                    w(f"| {verb} | `{path}` | {ctrl} | `{os.path.basename(loc)}` |")
            else:
                w("| Controller | Endpoints | Base paths |\n| --- | --- | --- |")
                for f, n in be["controllers"][:30]:
                    name = os.path.splitext(os.path.basename(f))[0]
                    paths = sorted({e[1].split("{")[0].rstrip("/") or "/" for e in eps if e[2] == name})[:3]
                    w(f"| `{s.p(f)}` | {n} | {', '.join('`' + p + '`' for p in paths)} |")
                w(f"(full list in scan.json; raise --max-endpoints to print it)")
    for s in scans:
        for spec in s.d.get("api_specs") or []:
            ops = spec["operations"]
            w(f"\nOpenAPI {spec['version']} spec `{s.p(spec['file'])}`: {len(ops)} operations"
              + (": " + ", ".join(f"{m} {p}" for m, p in ops[:max_endpoints]) + (" …" if len(ops) > max_endpoints else "") if ops else ""))

    for s in scans:
        db = s.d.get("database") or {}
        caps = set(s.d.get("capabilities", []))
        if db.get("migration_files") or caps & {"Flyway", "Liquibase", "Spring Data JPA", "JDBC"}:
            w(f"\n## Database{' — ' + s.label if multi else ''}")
            drivers = [c for c in s.d.get("capabilities", []) if "driver" in c or c.startswith(("H2", "HSQLDB"))]
            w(f"Drivers: {', '.join(drivers) or 'none detected'}; migration files: {db.get('migration_files', 0)} in "
              + (", ".join(f"`{s.p(x)}`" for x in db.get("migration_dirs", [])) or "-"))
            if db.get("flyway_count"):
                w(f"Flyway versioned migrations: {db['flyway_count']}, latest: " + ", ".join(f"`{s.p(x)}`" for x in db["flyway_versioned"]))
            if db.get("liquibase_master"):
                w("Liquibase changelog: " + ", ".join(f"`{s.p(x)}`" for x in db["liquibase_master"]))
            if db.get("sql_scripts"):
                w("Other SQL scripts: " + ", ".join(f"`{s.p(x)}`" for x in db["sql_scripts"]))

    w("\n## Configuration")
    for s in scans:
        c = s.d.get("config") or {}
        if c.get("files"):
            w(f"Spring profiles: {', '.join(c['profiles']) or 'none declared'}; files: " + ", ".join(f"`{s.p(f)}`" for f in c["files"]))
            for f, keys in c["groups"].items():
                if keys:
                    w(f"- `{s.p(f)}` key groups: {', '.join(keys)}")
        if c.get("shown"):
            w("Notable settings: " + "; ".join(c["shown"][:25]))
        if c.get("env_vars"):
            w("Environment variables referenced (names only): " + ", ".join(
                f"`{k}`" + (" (default)" if all("default" in x for x in v) else "") for k, v in list(c["env_vars"].items())[:40]))
        for line in c.get("frontend_env", []):
            w(f"- Frontend environment {line}")
        for line in c.get("proxies", []):
            w(f"- Dev proxy {line}")
        if c.get("secret_literals"):
            w(f"⚠️ Secret-like keys with literal values (never copy them; mention only as a finding): " + "; ".join(c["secret_literals"][:10]))

    for s in scans:
        fe = s.d.get("frontend") or {}
        if not fe.get("kinds"):
            continue
        w(f"\n## Frontend{' — ' + s.label if multi else ''}")
        k = fe["kinds"]
        w("Files: " + ", ".join(f"{name} {n}" for name, n in sorted(k.items(), key=lambda x: -x[1]) if name != "spec")
          + f"; NgModules {fe['ngmodules']}, `standalone: true` declared in {fe['standalone_declared']}; services using HttpClient {fe['http_services']}")
        if fe.get("interceptors"):
            w("HTTP interceptors: " + ", ".join(f"`{s.p(f)}`" for f in fe["interceptors"]))
        if fe.get("guards"):
            w("Guards: " + ", ".join(f"`{s.p(f)}`" for f in fe["guards"][:8]))
        if fe.get("stores"):
            w("State management files: " + ", ".join(f"`{s.p(f)}`" for f in fe["stores"][:6]))
        if fe.get("routes"):
            w("Routes (file: paths, lazy-loaded count):")
            for f, paths, lazy in fe["routes"][:15]:
                shown = [p or "''" for p in dict.fromkeys(paths)][:12]
                w(f"- `{s.p(f)}`: {', '.join(shown)}" + (f" (+{len(set(paths)) - 12})" if len(set(paths)) > 12 else "") + (f"; lazy {lazy}" if lazy else ""))
    for s in scans:
        for pkg in (s.d.get("frontend") or {}).get("packages", []):
            if pkg["scripts"]:
                key = [n for n in pkg["scripts"] if KEY_SCRIPTS.match(n)][:18]
                w(f"\nnpm scripts in `{s.p(pkg['file'])}` (main ones verbatim):")
                for name in key:
                    cmd = pkg["scripts"][name]
                    w(f"- `{name}`: `{cmd[:140]}{'…' if len(cmd) > 140 else ''}`")
                rest = [n for n in pkg["scripts"] if n not in key]
                if rest:
                    w(f"- other scripts ({len(rest)}): " + ", ".join(rest[:25]) + (" …" if len(rest) > 25 else ""))

    w("\n## Build, quality and tests")
    for s in scans:
        if s.d.get("wrappers"):
            w("Build wrappers: " + ", ".join(f"`{s.p(f)}`" for f in s.d["wrappers"]))
        q = (s.d.get("docs") or {}).get("quality_files", [])
        if q:
            w("Quality and convention files: " + ", ".join(f"`{s.p(f)}`" for f in q))
        t = s.d.get("tests") or {}
        w(f"Frontend spec files: {t.get('frontend_spec_files', 0)}; e2e: {', '.join(t.get('e2e_dirs') or []) or '-'}; performance: {', '.join(t.get('perf') or []) or '-'}")
        w("Source files: " + ", ".join(f"{k} {v}" for k, v in s.d.get("sizes", {}).items()))

    w("\n## CI/CD and deployment")
    for s in scans:
        dl = s.d.get("delivery") or {}
        for c in dl.get("ci", []):
            line = f"- {c['kind']} `{s.p(c['file'])}`"
            if c.get("name"):
                line += f" «{c['name']}»"
            if c.get("triggers"):
                line += f" on {c['triggers']}"
            if c.get("stages"):
                line += f"; stages: {', '.join(c['stages'])}"
            if c.get("jobs"):
                line += f"; jobs: {', '.join(c['jobs'][:25])}"
            if c.get("includes"):
                line += f"; includes: {', '.join(c['includes'])}"
            if c.get("environments"):
                line += f"; environments: {', '.join(c['environments'])}"
            w(line)
        for key, label in (("docker", "Container build"), ("compose", "Compose"), ("helm", "Helm")):
            for line in dl.get(key, []):
                w(f"- {label} {line}")
        if dl.get("kustomize"):
            w("- Kustomize: " + ", ".join(f"`{s.p(k)}`" for k in dl["kustomize"]))
        if dl.get("k8s_kinds"):
            w("- Kubernetes manifests: " + ", ".join(f"{k} {v}" for k, v in dl["k8s_kinds"].items()))
        if dl.get("argocd"):
            w("- Argo CD: " + ", ".join(f"`{s.p(f)}`" for f in dl["argocd"]))
        if dl.get("terraform"):
            w("- Terraform: " + ", ".join(f"`{s.p(f)}`" for f in dl["terraform"]))
        if not any(dl.get(k) for k in ("ci", "docker", "compose", "helm", "kustomize", "argocd", "terraform")):
            w(f"- nothing found{' in ' + s.label if multi else ''} (pipeline and deployment may live in another repository: ask)")
        if dl.get("environments"):
            w(f"Environments seen (profiles, values files, overlays, CI environments): {', '.join(dl['environments'])}")

    w("\n## Existing documentation and conventions")
    for s in scans:
        dc = s.d.get("docs") or {}
        for r, (n_lines, heads) in dc.get("readmes", {}).items():
            w(f"- `{s.p(r)}` ({n_lines} lines) sections: {' · '.join(heads) or '(no headings)'}")
        if dc.get("docs"):
            w(f"- docs ({dc['docs_count']}): " + ", ".join(f"`{s.p(f)}`" for f in dc["docs"][:15]) + (" …" if dc["docs_count"] > 15 else ""))
        if dc.get("adrs"):
            w(f"- ADRs ({len(dc['adrs'])}): " + ", ".join(f"`{s.p(f)}`" for f in dc["adrs"][:10]))
        for key, label in (("instruction_files", "Instruction and ownership files"), ("mr_templates", "MR/PR templates"),
                           ("bob_rules", "Bob rules folders"), ("existing_playbook", "Existing playbook pages")):
            if dc.get(key):
                w(f"- {label}: " + ", ".join(f"`{s.p(f)}`" for f in dc[key]))
        g = s.d.get("git") or {}
        if g:
            w(f"- Git ({g['commits_sampled']} recent commits): Conventional Commits {int(g['conventional_share'] * 100)}%, "
              f"ticket keys {int(g['ticket_ref_share'] * 100)}%, merge commits {g['merge_commits']}; "
              f"remote branch prefixes: {', '.join(f'{k}/ {v}' for k, v in g['branch_prefixes'].items()) or 'none visible'}; "
              f"recent tags: {', '.join(g['recent_tags']) or 'none'}")

    w("\n## Read next (in this order, narrowly)")
    for s in scans:
        for f, why in s.d.get("reading_list", []):
            w(f"- `{s.p(f)}` — {why}")

    for s in scans:
        since = (s.d.get("git") or {}).get("since")
        if since:
            w(f"\n## Changed since `{since['ref']}`{' — ' + s.label if multi else ''}")
            if since.get("error"):
                w(f"⚠️ {since['error']}")
            else:
                w(f"{since['changed']} files changed.")
                for area, v in since["areas"].items():
                    w(f"- **{area}** ({len(v['files'])}) → review: {v['pages']}. e.g. " + ", ".join(f"`{f}`" for f in v["files"][:4]))
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roots", nargs="+", help="repository root(s): one for a monorepo, several for separate repositories")
    ap.add_argument("--out", help="also write scan.md and scan.json into this directory")
    ap.add_argument("--since", help="git ref of the last playbook update: list changed areas and the pages to review")
    ap.add_argument("--max-endpoints", type=int, default=30, help="print every endpoint up to this count (default 30)")
    a = ap.parse_args()
    scans = []
    for root in a.roots:
        if not os.path.isdir(root):
            sys.exit(f"not a directory: {root}")
        label = os.path.basename(os.path.abspath(root)) if len(a.roots) > 1 else ""
        s = Scan(root, label)
        s.run(a.since)
        scans.append(s)
    md = render(scans, a.max_endpoints)
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        with open(os.path.join(a.out, "scan.md"), "w", encoding="utf-8") as fh:
            fh.write(md)
        with open(os.path.join(a.out, "scan.json"), "w", encoding="utf-8") as fh:
            json.dump({s.label or os.path.basename(s.root): s.d for s in scans}, fh, indent=1, default=list)
    sys.stdout.write(md)


if __name__ == "__main__":
    main()

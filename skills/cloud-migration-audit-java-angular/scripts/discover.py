"""Discovery for the cloud migration audit: one read-only pass over the repositories.

Produces an inventory: each repository's role, revision and stack; evidence signals (file:line,
masked) grouped by audit domain; flattened configuration of Spring, Helm values and Kubernetes
manifests; and cross-repository checks that put both sides of a contract next to each other
(probes vs actuator, ports, scheduled jobs vs replicas, pool size x replicas, shutdown vs grace
period, heap vs memory limit, image built vs deployed, frontend routes vs ingress...).

Signals and checks are leads for the auditors, not verdicts: a regex cannot tell whether a static
map is a cache or the source of truth. Standard library only; never writes into the repositories.
"""
import hashlib
import json
import os
import re
import subprocess
from collections import Counter, OrderedDict

SKIP_DIRS = {".git", "node_modules", "target", "build", "dist", ".angular", ".gradle", "coverage", ".idea", ".vscode",
             "out", ".nx", ".cache", "tmp", "bin", "generated", "generated-sources", ".next", "vendor", "__pycache__",
             ".husky", ".yarn", "bower_components", ".terraform", "cloud-migration-audit"}
KEEP_DOT_DIRS = {".github", ".gitlab", ".mvn", ".bob", ".argocd"}
MAX_BYTES = 400_000
TEXT_EXT = {".java", ".kt", ".ts", ".js", ".mjs", ".json", ".yml", ".yaml", ".properties", ".xml", ".gradle", ".kts",
            ".toml", ".md", ".sql", ".html", ".conf", ".tpl", ".env", ".sh", ".tf", ".tfvars", ".cfg", ".txt", ".adoc"}
TEXT_NAMES = re.compile(r"^(Dockerfile.*|Containerfile.*|Jenkinsfile.*|\.gitlab-ci\.yml|.*nginx.*\.conf.*|\.dockerignore|"
                        r"Chart\.yaml|values.*\.ya?ml|kustomization\.ya?ml|\.nvmrc|mvnw|gradlew)$")
MAX_REFS = 12  # references kept per signal and repository in the compact views

SECRET_KEY = re.compile(r"(?i)(password|passwd|pwd|secret|token|api[-_.]?key|private[-_.]?key|credential|client[-_.]?secret|"
                        r"access[-_.]?key)")
PLACEHOLDER = re.compile(r"^\s*(\$\{[^}]*\}|\{\{.*\}\}|<[^>]*>|changeme|change-me|xxx+|\*+|\"\"|''|)\s*$", re.I)
MASKS = [
    (re.compile(r"(?i)((?:password|passwd|pwd|secret|token|api[-_.]?key|private[-_.]?key|credential|client[-_.]?secret|"
                r"access[-_.]?key)[\w.-]*[\"']?\s*[:=]\s*[\"']?)(?!\$\{|\{\{|<)([^\s\"',}]{3,})"), r"\1***"),
    (re.compile(r"([a-z][a-z0-9+.-]{1,20}://[^\s:/@'\"]{1,64}:)[^\s@/'\"]{2,}@"), r"\1***@"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*"), "-----BEGIN PRIVATE KEY----- ***"),
    (re.compile(r"\b(?:gl(?:pat|dt|rt|cbt|ptt)-|gh[pousr]_|github_pat_|AKIA|ASIA|xox[abprs]-|ATATT3|AIza)[0-9A-Za-z_=-]{8,}"), "***"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "***"),
]
ONPREM_HOST = re.compile(r"(?i)\b(?:[a-z0-9-]+\.)+(?:intranet|internal|corp|lan|local|localdomain|priv|ad)\b(?::\d+)?|"
                         r"\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b|"
                         r"\\\\[A-Za-z0-9_-]+\\|\b[a-z]:\\\\", )

JAVA = r"\.(java|kt)$"
APPCFG = r"(^|/)(application|bootstrap)[^/]*\.(ya?ml|properties)$"
YAML = r"\.ya?ml$|\.tpl$"
DOCKER = r"(^|/)(Dockerfile|Containerfile)[^/]*$"
CI = r"(^|/)(\.gitlab-ci\.yml|[^/]*\.gitlab-ci\.yml|\.gitlab/ci/[^/]+\.ya?ml|Jenkinsfile[^/]*|\.github/workflows/[^/]+)$"
TS = r"\.(ts|js|mjs)$"
NGINX = r"(^|/)[^/]*nginx[^/]*(\.conf|\.template|\.tpl)?$|(^|/)default\.conf(\.template)?$"
SQLISH = r"\.(java|kt|xml|sql|ya?ml)$"

# (signal id, domain, path regex, line regex, description). Lines in test sources are ignored for code signals.
SIGNALS = [
    ("scheduled", "ARCH", JAVA, r"@Scheduled\b", "@Scheduled method"),
    ("scheduler-lock", "ARCH", JAVA, r"@SchedulerLock\b|LockProvider\b|@EnableSchedulerLock", "distributed lock (ShedLock)"),
    ("quartz", "ARCH", JAVA + "|" + APPCFG, r"org\.quartz|QuartzJobBean|@DisallowConcurrentExecution|spring\.quartz|"
     r"isClustered|is-clustered", "Quartz"),
    ("async", "ARCH", JAVA, r"@Async\b|@EnableAsync|ThreadPoolTaskExecutor|Executors\.new\w+\(|CompletableFuture\.\w*[Aa]sync",
     "asynchronous execution"),
    ("static-mutable", "ARCH", JAVA, r"\bstatic\s+(?:final\s+)?(?:[\w.]+\.)?(?:Map|HashMap|ConcurrentHashMap|ConcurrentMap|List|ArrayList|"
     r"Set|HashSet|Queue|Deque|LinkedList|AtomicLong|AtomicInteger|AtomicReference|LongAdder)\b[^;(]*=|"
     r"\bstatic\s+(?!final\b)(?:(?:private|public|protected|volatile)\s+)*[\w<>\[\],.? ]+\s+\w+\s*=\s*(?!null)",
     "static mutable state"),
    ("local-cache", "ARCH", JAVA + "|" + APPCFG, r"@Cacheable|@CachePut|@CacheEvict|@EnableCaching|Caffeine\b|ConcurrentMapCache|"
     r"spring\.cache\.|Ehcache|CacheBuilder", "caching"),
    ("http-session", "ARCH", JAVA + "|" + APPCFG, r"HttpSession\b|@SessionAttributes|getSession\(|@SessionScope|"
     r"setAttribute\(|server\.servlet\.session|spring\.session\.|JSESSIONID", "HTTP session"),
    ("local-filesystem", "ARCH", JAVA, r"new File\(|Files\.(?:write|writeString|newOutputStream|newBufferedWriter|createTempFile|"
     r"createDirectories|copy|move|readAllBytes|newInputStream)|Paths?\.(?:get|of)\(|FileOutputStream|FileWriter|"
     r"java\.io\.tmpdir|\"/(?:tmp|data|opt|var|mnt|home|app)/", "local filesystem"),
    ("jvm-lock", "ARCH", JAVA, r"\bsynchronized\b|ReentrantLock|ReadWriteLock|Semaphore\b", "JVM-local locking"),
    ("listener", "ARCH", JAVA + "|" + APPCFG, r"@KafkaListener|@JmsListener|@RabbitListener|@SqsListener|implements MessageListener|"
     r"spring\.kafka\.consumer|concurrency", "message listener"),
    ("batch", "ARCH", JAVA, r"@EnableBatchProcessing|JobLauncher|JobBuilder|StepBuilder|JobRepository", "Spring Batch"),
    ("optimistic-lock", "ARCH", JAVA + "|" + SQLISH, r"@Version\b|@Lock\(|LockModeType|FOR UPDATE", "database locking"),
    ("idempotency", "ARCH", JAVA, r"(?i)idempoten|Idempotency-Key|X-Request-Id|dedup", "idempotency handling"),
    ("instance-identity", "ARCH", JAVA, r"InetAddress\.getLocal|getHostName\(\)|getenv\(\"HOSTNAME|ManagementFactory\.getRuntimeMXBean",
     "instance identity"),
    ("http-client", "APP", JAVA, r"\bRestTemplate\b|\bWebClient\b|\bRestClient\b|@FeignClient|HttpClient\.new|HttpURLConnection|"
     r"WebServiceTemplate|OkHttpClient", "outbound HTTP client"),
    ("client-timeout", "APP", JAVA + "|" + APPCFG, r"(?i)setConnectTimeout|setReadTimeout|connect-?timeout|read-?timeout|"
     r"responseTimeout|ReadTimeoutHandler|\.timeout\(", "client timeout"),
    ("resilience", "APP", JAVA + "|" + APPCFG, r"@CircuitBreaker|@Retry\b|@Retryable|@Bulkhead|@RateLimiter|@TimeLimiter|resilience4j|"
     r"RetryTemplate|spring-retry", "resilience pattern"),
    ("tls-bypass", "APP", JAVA, r"TrustAll|X509TrustManager|setHostnameVerifier|NoopHostnameVerifier|InsecureTrustManager|"
     r"TrustSelfSigned", "TLS verification bypass"),
    ("truststore", "APP", JAVA + "|" + APPCFG + "|" + YAML + "|" + DOCKER, r"(?i)trust-?store|keystore|\.jks\b|\.p12\b|cacerts|"
     r"javax\.net\.ssl", "truststore/keystore"),
    ("shutdown-hook", "APP", JAVA, r"@PreDestroy|DisposableBean|SmartLifecycle|addShutdownHook", "shutdown handling"),
    ("correlation", "APP", JAVA + "|" + r"(^|/)logback[^/]*\.xml$", r"MDC\.|traceId|spanId|X-Correlation-Id|correlationId|X-B3-",
     "correlation/trace IDs"),
    ("events", "APP", JAVA, r"KafkaTemplate|JmsTemplate|RabbitTemplate|ApplicationEventPublisher|@TransactionalEventListener|"
     r"[Oo]utbox", "event publishing"),
    ("transactional", "APP", JAVA, r"@Transactional\b", "@Transactional"),
    ("former-db-sql", "APP", SQLISH, r"\bNVL\s*\(|\bROWNUM\b|\bSYSDATE\b|\bFROM\s+DUAL\b|CONNECT\s+BY|\bVARCHAR2\b|\bDECODE\s*\(|"
     r"\(\+\)|\bNUMBER\s*\(\d|TO_DATE\s*\(|\bMINUS\b", "Oracle-specific SQL"),
    ("breaking-migration", "APP", r"(db/changelog|liquibase|migration|flyway)[^/]*/.*\.(xml|ya?ml|sql|json)$|changelog[^/]*\.(xml|ya?ml)$",
     r"(?i)<dropColumn|<dropTable|<renameColumn|<renameTable|<modifyDataType|dropColumn:|dropTable:|renameColumn:|"
     r"DROP\s+(COLUMN|TABLE)|RENAME\s+(COLUMN|TO)|ALTER\s+COLUMN\s+\w+\s+TYPE", "destructive schema change"),
    ("onprem-host", "APP", JAVA + "|" + APPCFG + "|" + TS + "|" + YAML + "|" + DOCKER + "|" + NGINX, ONPREM_HOST.pattern,
     "on-premise host, IP or path"),
    ("file-logging", "APP", r"(^|/)(logback|log4j2)[^/]*\.xml$|" + APPCFG, r"FileAppender|RollingFileAppender|logging\.file\.|<File\b|"
     r"RollingFile", "file logging"),
    ("probe", "K8S", YAML, r"(readiness|liveness|startup)Probe", "probe"),
    ("security-context", "K8S", YAML, r"runAsNonRoot|runAsUser|readOnlyRootFilesystem|allowPrivilegeEscalation|privileged:|"
     r"capabilities:|seccompProfile", "security context"),
    ("hpa", "K8S", YAML, r"HorizontalPodAutoscaler|minReplicas|maxReplicas|autoscaling:", "autoscaling"),
    ("pdb", "K8S", YAML, r"PodDisruptionBudget|podDisruptionBudget", "PodDisruptionBudget"),
    ("network-policy", "K8S", YAML, r"kind:\s*NetworkPolicy|networkPolicy", "NetworkPolicy"),
    ("spread", "K8S", YAML, r"podAntiAffinity|topologySpreadConstraints", "anti-affinity/topology spread"),
    ("secret-object", "K8S", YAML, r"kind:\s*(Secret|ExternalSecret|SealedSecret|SecretStore|ClusterSecretStore)\b|secretKeyRef|"
     r"secretRef|secrets-store\.csi", "secret handling"),
    ("persistent-volume", "K8S", YAML, r"PersistentVolumeClaim|persistentVolumeClaim|hostPath:|accessModes|storageClassName",
     "persistent storage"),
    ("ingress", "K8S", YAML, r"kind:\s*(Ingress|Route)\b|ingress:|nginx\.ingress\.kubernetes\.io/[\w-]+|haproxy\.router|"
     r"sessionAffinity|affinity:\s*cookie", "ingress/routing"),
    ("service-account", "K8S", YAML, r"serviceAccountName|automountServiceAccountToken|kind:\s*(Role|ClusterRole|RoleBinding|"
     r"ClusterRoleBinding|ServiceAccount)\b", "service account/RBAC"),
    ("docker-user", "CTR", DOCKER, r"^\s*USER\b", "USER instruction"),
    ("docker-from", "CTR", DOCKER, r"^\s*FROM\b", "base image"),
    ("docker-risky", "CTR", DOCKER, r"(?i)curl[^|]*\|\s*(ba)?sh|wget[^|]*\|\s*(ba)?sh|chmod\s+(-R\s+)?777|^\s*ADD\s+https?:|"
     r"COPY\s+.*(\.env|\.pem|\.key|id_rsa|settings\.xml|\.npmrc)\b|^\s*(ENV|ARG)\s+\w*(PASSWORD|SECRET|TOKEN|KEY)\w*",
     "risky Dockerfile instruction"),
    ("docker-entrypoint", "CTR", DOCKER, r"^\s*(ENTRYPOINT|CMD)\b", "entrypoint"),
    ("image-latest", "CTR", YAML + "|" + DOCKER + "|" + CI, r"(?i):latest\b|tag:\s*[\"']?latest|FROM\s+[\w./-]+(\s|$)",
     "moving or missing image tag"),
    ("ci-scan", "CICD", CI, r"(?i)sast|dependency[_-]scanning|container[_-]scanning|secret[_-]detection|trivy|grype|xray|"
     r"jf\s+(scan|audit|docker\s+scan)|dependency-check|snyk|sonar", "security/quality scan"),
    ("ci-jfrog", "CICD", CI, r"(?i)\bjf\s+|jfrog|artifactory|\.jfrog\.io", "JFrog"),
    ("ci-image-push", "CICD", CI, r"(?i)docker\s+push|--destination|kaniko|buildah\s+push|jf\s+docker\s+push|jib:build|"
     r"podman\s+push|crane\s+(push|copy|tag)", "image publication"),
    ("ci-deploy", "CICD", CI, r"(?i)helm\s+(upgrade|install)|kubectl\s+(apply|set|rollout|patch|create)|oc\s+(apply|rollout)|"
     r"argocd\s+app\s+(sync|set)|kustomize\s+edit|yq\s+.*image|git\s+push", "deployment step"),
    ("ci-gate", "CICD", CI, r"(?i)when:\s*manual|environment:|protected|allow_failure|rules:|only:|except:", "gates and rules"),
    ("ci-secret-exposure", "CICD", CI, r"(?i)echo\s+[\"']?\$\{?\w*(PASS|SECRET|TOKEN|KEY)|set\s+-x|--password[= ]+[^$\s]",
     "possible secret exposure"),
    ("argocd", "CICD", YAML, r"argoproj\.io|targetRevision|syncPolicy|selfHeal|prune:|ignoreDifferences", "Argo CD"),
    ("helm-validate", "CICD", CI, r"(?i)helm\s+(lint|template)|kubeconform|kubeval|conftest|kube-linter|checkov|polaris",
     "manifest validation"),
    ("web-env-url", "WEB", r"(^|/)environments?/[^/]+\.ts$|(^|/)assets/[^/]*(config|env)[^/]*\.(json|js)$",
     r"(?i)(https?://|['\"]/)\S*|issuer|clientId|realm", "frontend environment URL"),
    ("web-runtime-config", "WEB", TS + r"|\.html$|\.json$", r"(?i)APP_INITIALIZER|window\.__env|config\.json|env\.js|"
     r"provideAppInitializer|runtime-config", "runtime configuration"),
    ("web-auth", "WEB", TS + r"|(^|/)package\.json$", r"keycloak-angular|keycloak-js|angular-oauth2-oidc|@azure/msal|"
     r"angular-auth-oidc-client|@auth0|OAuthService|KeycloakService|withInterceptors|HttpInterceptor", "authentication"),
    ("web-token-storage", "WEB", TS, r"(localStorage|sessionStorage)\.(setItem|getItem)", "browser storage"),
    ("web-credentials", "WEB", TS, r"withCredentials|withXsrfConfiguration|HttpClientXsrfModule|X-XSRF", "credentials/CSRF"),
    ("cors", "WEB", JAVA + "|" + APPCFG, r"(?i)@CrossOrigin|allowed-?origins|addCorsMappings|CorsConfiguration|allowedOriginPatterns",
     "CORS"),
    ("nginx-fallback", "WEB", NGINX, r"try_files", "SPA fallback"),
    ("nginx-headers", "WEB", NGINX + "|" + YAML, r"(?i)Content-Security-Policy|Strict-Transport-Security|X-Frame-Options|"
     r"X-Content-Type-Options|Referrer-Policy|frame-ancestors", "security headers"),
    ("nginx-cache", "WEB", NGINX, r"(?i)Cache-Control|expires\s|no-cache|immutable", "cache headers"),
    ("nginx-listen", "WEB", NGINX, r"^\s*listen\s", "nginx listen port"),
    ("base-href", "WEB", r"(^|/)index\.html$|(^|/)angular\.json$", r"<base href|baseHref|deployUrl", "base href"),
    ("web-timeout", "WEB", TS, r"\btimeout\(|retry\(|retryWhen\(|catchError\(", "HTTP error/timeout handling"),
    ("metrics", "OPS", YAML + "|" + APPCFG, r"ServiceMonitor|PodMonitor|prometheus\.io/scrape|management\.metrics|"
     r"management\.prometheus|micrometer", "metrics"),
    ("alerting", "OPS", YAML + r"|\.json$", r"PrometheusRule|alertmanager|alert:|AlertingRule|sysdig.*alert", "alerting"),
    ("tracing", "OPS", JAVA + "|" + APPCFG + "|" + YAML + "|" + TS, r"(?i)opentelemetry|otel|micrometer-tracing|management\.tracing|"
     r"zipkin|jaeger|instana", "tracing"),
    ("backup", "OPS", YAML + r"|\.sh$|\.md$", r"(?i)pg_dump|pg_basebackup|expdp|rman|velero|backup|point-in-time", "backup"),
    ("dr-docs", "OPS", r"\.(md|adoc)$", r"(?i)\bRTO\b|\bRPO\b|disaster recovery|rollback|runbook|restore|incident", "operations docs"),
    ("load-test", "OPS", r".*", r"(?i)gatling|jmeter|\bk6\b|locust", "load test"),
    ("chaos", "OPS", YAML, r"(?i)litmus|chaos-mesh|chaosengine|PodChaos", "chaos testing"),
]
CODE_SIGNAL_DOMAINS = {"ARCH", "APP"}
APP_KEYS = re.compile(
    r"^(server\.(port|shutdown|servlet\.context-path|servlet\.session\..*|forward-headers-strategy|ssl\..*)|"
    r"spring\.(lifecycle\..*|datasource\.(url|hikari\..*|driver-class-name)|liquibase\..*|flyway\..*|jpa\.(hibernate\.ddl-auto|"
    r"database-platform|properties\.hibernate\.dialect)|session\..*|cache\..*|profiles\..*|task\..*|quartz\..*|kafka\..*|"
    r"rabbitmq\.(host|addresses)|security\.oauth2\..*|cloud\.kubernetes\..*|threads\.virtual\.enabled|main\.lazy-initialization)|"
    r"management\..*|logging\.(file\..*|pattern\..*|config|structured\..*)|resilience4j\..*|shedlock\..*|.*(timeout|url|uri|host|"
    r"origins?)$)")
K8S_KEYS = re.compile(
    r"(^|\.)(replicas|replicaCount|minReplicas|maxReplicas|targetCPUUtilizationPercentage|averageUtilization|"
    r"terminationGracePeriodSeconds|revisionHistoryLimit|maxUnavailable|maxSurge|minAvailable|"
    r"(readinessProbe|livenessProbe|startupProbe)(\..*)?|(readiness|liveness|startup)(\.(path|port|initialDelaySeconds|periodSeconds|"
    r"failureThreshold|timeoutSeconds))?|resources\.(requests|limits)\.(cpu|memory)|(requests|limits)\.(cpu|memory)|"
    r"runAsNonRoot|runAsUser|readOnlyRootFilesystem|allowPrivilegeEscalation|privileged|seccompProfile\.type|"
    r"serviceAccountName|automountServiceAccountToken|image|repository|tag|digest|imagePullPolicy|containerPort|targetPort|port|"
    r"path|pathType|host|hosts|sessionAffinity|preStop(\..*)?|value|targetRevision|prune|selfHeal|namespace|enabled|"
    r"storageClassName|accessModes|kind)$")


def read(path):
    try:
        if os.path.getsize(path) > MAX_BYTES:
            return ""
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def mask(text):
    for rx, rep in MASKS:
        text = rx.sub(rep, text)
    return text


STRICT = [  # unambiguous secret material (masked forms such as *** do not match)
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----\s*[A-Za-z0-9+/=]{20,}")),
    ("access token", re.compile(r"\b(?:gl(?:pat|dt|rt|cbt|ptt)-|gh[pousr]_|github_pat_|AKIA|ASIA|xox[abprs]-|ATATT3|AIza)[0-9A-Za-z_=-]{8,}")),
    ("JSON Web Token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("credentials in a URL", re.compile(r"\b[a-z][a-z0-9+.-]{1,20}://[^\s:/@'\"]{1,64}:(?!\*+@)[^\s@/'\"]{2,}@")),
]


def secret_hash(value):  # noqa: D401  (hash of a secret value; the value itself is never stored)
    return hashlib.sha256(value.strip().strip("\"'").encode("utf-8")).hexdigest()


def leaks(text, hashes):
    """Kinds of secret material in text: unambiguous patterns, or values of secrets found in the repositories (by hash)."""
    found = [kind for kind, rx in STRICT if rx.search(text)]
    if hashes:
        where = {}
        for h in hashes:  # entries are {"hash", "ref"} (older inventories: plain hashes)
            where[h["hash"] if isinstance(h, dict) else h] = h.get("ref") if isinstance(h, dict) else None
        for tok in re.findall(r"[^\s\"'`,;()<>\[\]{}|=]{4,}", text):
            for t in {tok, tok.rstrip(".!?:"), tok.split(":", 1)[-1]}:
                if t and secret_hash(t) in where:
                    ref = where[secret_hash(t)]
                    found.append("the value of the secret " + (f"defined at {ref}" if ref else "found in the repositories"))
                    break
    return sorted(set(found))


# The audited repository's git config is untrusted: command-line settings override it so that git never runs a command
# from it (core.fsmonitor, hooks) and never writes to it (optional index locks).
SAFE_GIT = ["git", "--no-optional-locks", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null"]


def inside(root, path):
    """True when path resolves inside root: a symbolic link must not pull in files from elsewhere (keys, configs)."""
    return os.path.realpath(path).startswith(os.path.realpath(root).rstrip(os.sep) + os.sep)


def git(root, *args):
    try:
        r = subprocess.run([*SAFE_GIT, "-C", root, *args], capture_output=True, text=True, timeout=20)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def walk(root):
    for d, dirs, files in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS and not (x.startswith(".") and x not in KEEP_DOT_DIRS))
        for f in sorted(files):
            full = os.path.join(d, f)
            if os.path.islink(full) and not inside(root, full):
                continue
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if os.path.splitext(f)[1].lower() in TEXT_EXT or TEXT_NAMES.match(f):
                yield rel


def flatten_yaml(text):
    """(dotted.key, value, line) for simple YAML and Helm templates; list items keep their parent key."""
    out, stack = [], []
    for no, raw in enumerate(text.splitlines(), 1):
        if raw.strip() in ("---", "...") :
            stack = []
            continue
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m = re.match(r"^(\s*)(-\s+)?([\w.\-/\"'@]+)\s*:(?:\s+(.*?))?\s*$", raw)
        if not m:
            li = re.match(r"^(\s*)-\s+(.+?)\s*$", raw)
            if li and stack:
                out.append((".".join(k for _, k in stack), li.group(2).strip("\"'"), no))
            continue
        indent = len(m.group(1)) + (len(m.group(2)) if m.group(2) else 0)
        key = m.group(3).strip("\"'")
        value = re.sub(r"\s+#.*$", "", m.group(4) or "").strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        stack.append((indent, key))
        if value and not value.startswith(("|", ">")):
            out.append((".".join(k for _, k in stack), value.strip("\"'"), no))
    return out


def flatten_properties(text):
    out = []
    for no, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^\s*([^#!\s][^=:\s]*)\s*[=:]\s*(.*)$", line)
        if m:
            out.append((m.group(1), m.group(2).strip(), no))
    return out


def is_secret_literal(key, value):
    last = key.split(".")[-1]
    return bool(SECRET_KEY.search(last)) and not PLACEHOLDER.match(value) and "${" not in value and "{{" not in value \
        and value.lower() not in ("true", "false", "null", "none", "~") and not re.fullmatch(r"[\d.]+[smhd]?", value) \
        and not re.search(r"(?i)(validity|expir|ttl|timeout|length|size|enabled|header|name|uri|url|path|ref|key-?store-?type)$", last)


def to_mib(v):
    m = re.fullmatch(r"\s*([\d.]+)\s*([KMGT]i?|[kmgt])?\s*", str(v or ""))
    if not m:
        return None
    n, u = float(m.group(1)), (m.group(2) or "").lower()
    factor = {"": 1 / 1048576, "k": 1 / 1024, "ki": 1 / 1024, "m": 1, "mi": 1, "g": 1024, "gi": 1024, "t": 1048576, "ti": 1048576}
    return n * factor.get(u, 1) if u else None


def to_seconds(v):
    m = re.fullmatch(r"\s*(\d+)\s*(ms|s|m|h)?\s*", str(v or ""))
    if not m:
        return None
    n, u = int(m.group(1)), m.group(2) or "s"
    return {"ms": n / 1000, "s": n, "m": n * 60, "h": n * 3600}[u]


class Repo:
    def __init__(self, label, path):
        self.label, self.path = label, os.path.abspath(path)
        self.files = list(walk(self.path))
        self.cache = {}

    def text(self, rel):
        if rel not in self.cache:
            self.cache[rel] = read(os.path.join(self.path, rel))
        return self.cache[rel]

    def ref(self, rel, line=None):
        return f"{self.label}:{rel}" + (f":{line}" if line else "")


def describe_repo(repo):
    f = repo.files
    has = lambda rx: any(re.search(rx, x) for x in f)
    roles = []
    if has(r"(^|/)(pom\.xml|build\.gradle(\.kts)?)$") and has(r"\.(java|kt)$"):
        roles.append("backend")
    if has(r"(^|/)angular\.json$") or has(r"(^|/)package\.json$") and has(r"\.component\.ts$|(^|/)main\.ts$"):
        roles.append("frontend")
    if has(r"(^|/)Chart\.yaml$|kustomization\.ya?ml$|(^|/)(k8s|kubernetes|manifests|deploy|helm|charts|argocd|gitops|overlays)/"):
        roles.append("infrastructure")
    if has(CI):
        roles.append("ci")
    head = git(repo.path, "log", "-1", "--format=%h %cs")
    remote = git(repo.path, "remote", "get-url", "origin")
    return OrderedDict(
        label=repo.label, roles=roles or ["unknown"], files=len(f), head=head or None,
        branch=git(repo.path, "rev-parse", "--abbrev-ref", "HEAD") or None,
        dirty=bool(git(repo.path, "status", "--porcelain")) if head else None,
        provider=("GitLab" if "gitlab" in remote else "GitHub" if "github" in remote else "other" if remote else None),
        java_files=len([x for x in f if re.search(JAVA, x) and "/test/" not in x]),
        ts_files=len([x for x in f if x.endswith(".ts") and not x.endswith(".spec.ts")]),
        yaml_files=len([x for x in f if re.search(r"\.ya?ml$", x)]),
    )


def stack_of(repo):
    out = []
    for p in [x for x in repo.files if x.endswith("pom.xml")][:3]:
        t = re.sub(r"<!--.*?-->", "", repo.text(p), flags=re.S)
        boot = re.search(r"spring-boot-starter-parent</artifactId>\s*<version>([^<]+)<", t)
        java = re.search(r"<(?:java\.version|maven\.compiler\.release)>([^<]+)<", t)
        if boot:
            out.append(("Spring Boot", boot.group(1), p))
        if java:
            out.append(("Java", java.group(1), p))
        for g, a in re.findall(r"<groupId>\s*([^<\s]+)\s*</groupId>\s*<artifactId>\s*([^<\s]+)\s*</artifactId>", t):
            for label, rx in DEPS:
                if re.fullmatch(rx, f"{g}:{a}"):
                    out.append((label, "dependency", p))
    for p in [x for x in repo.files if re.search(r"(^|/)build\.gradle(\.kts)?$", x)][:3]:
        t = repo.text(p)
        for c in re.findall(r"""["']([\w.\-]+:[\w.\-]+)(?::[^"']*)?["']""", t):
            for label, rx in DEPS:
                if re.fullmatch(rx, c):
                    out.append((label, "dependency", p))
    for p in [x for x in repo.files if x.endswith("package.json") and "node_modules" not in x][:3]:
        try:
            pkg = json.loads(repo.text(p) or "{}")
        except ValueError:
            continue
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        for name, label in (("@angular/core", "Angular"), ("keycloak-angular", "keycloak-angular"),
                            ("angular-oauth2-oidc", "angular-oauth2-oidc"), ("@azure/msal-angular", "MSAL")):
            if name in deps:
                out.append((label, deps[name], p))
    return list(OrderedDict.fromkeys(out))


DEPS = [
    ("ShedLock", r"net\.javacrumbs\.shedlock:.*"), ("Quartz", r".*:spring-boot-starter-quartz|org\.quartz-scheduler:.*"),
    ("Spring Session", r"org\.springframework\.session:.*"), ("Redis", r".*:spring-boot-starter-data-redis.*"),
    ("Caffeine", r"com\.github\.ben-manes\.caffeine:caffeine"), ("Hazelcast", r"com\.hazelcast:.*"),
    ("Resilience4j", r".*resilience4j.*"), ("Spring Retry", r"org\.springframework\.retry:.*"),
    ("Actuator", r".*:spring-boot-starter-actuator"), ("Prometheus registry", r"io\.micrometer:micrometer-registry-prometheus"),
    ("Tracing", r"io\.micrometer:micrometer-tracing.*|io\.opentelemetry.*:.*"),
    ("JSON logs", r"net\.logstash\.logback:logstash-logback-encoder|co\.elastic\.logging:.*"),
    ("Liquibase", r"org\.liquibase:liquibase-core"), ("Flyway", r"org\.flywaydb:flyway-core"),
    ("Oracle driver", r"com\.oracle\.database\.jdbc:ojdbc\d+.*"), ("PostgreSQL driver", r"org\.postgresql:postgresql"),
    ("Spring Batch", r".*:spring-boot-starter-batch"), ("Kafka", r"org\.springframework\.kafka:spring-kafka"),
    ("IBM MQ", r"com\.ibm\.mq:.*"), ("OAuth2 resource server", r".*:spring-boot-starter-oauth2-resource-server"),
    ("Spring Cloud Kubernetes", r"org\.springframework\.cloud:spring-cloud-.*kubernetes.*"),
    ("Jib", r"com\.google\.cloud\.tools:jib-maven-plugin"),
]


def scan(repos):
    signals, counts = [], Counter()
    config, yaml_index, dockerfiles, pipelines = [], [], [], []
    hashes = {}
    for repo in repos:
        for rel in repo.files:
            low = rel.lower()
            is_test = bool(re.search(r"(^|/)(src/test|test|tests|e2e|cypress|__tests__)/|\.spec\.ts$|Test\.java$|IT\.java$", rel))
            rules = [s for s in SIGNALS if re.search(s[2], rel)]
            if rules:
                for no, line in enumerate(repo.text(rel).splitlines(), 1):
                    if len(line) > 600:
                        continue
                    for sid, dom, _, rx, _ in rules:
                        if is_test and dom in CODE_SIGNAL_DOMAINS:
                            continue
                        if re.search(rx, line):
                            counts[(repo.label, sid)] += 1
                            if counts[(repo.label, sid)] <= 60:
                                signals.append({"id": sid, "domain": dom, "repo": repo.label, "file": rel, "line": no,
                                                "text": mask(line.strip())[:180]})
            if re.search(APPCFG, rel) and "/test/" not in rel:
                pairs = flatten_properties(repo.text(rel)) if rel.endswith(".properties") else flatten_yaml(repo.text(rel))
                for key, value, no in pairs:
                    if is_secret_literal(key, value):
                        hashes.setdefault(secret_hash(value), f"{repo.label}:{rel}:{no} ({key})")
                        config.append({"repo": repo.label, "file": rel, "line": no, "key": key, "value": "***", "secret_literal": True})
                    elif APP_KEYS.match(key):
                        config.append({"repo": repo.label, "file": rel, "line": no, "key": key, "value": mask(value)[:160]})
            elif re.search(r"\.ya?ml$|\.tpl$", low) and not re.search(r"(^|/)(package-lock|pnpm-lock|\.gitlab-ci)", low) \
                    and "/test/" not in rel and not re.search(r"(^|/)\.github/", rel):
                text = repo.text(rel)
                kinds = re.findall(r"^kind:\s*(\w+)", text, re.M)
                for key, value, no in flatten_yaml(text):
                    leaf = key.split(".")[-1]
                    if is_secret_literal(key, value):
                        hashes.setdefault(secret_hash(value), f"{repo.label}:{rel}:{no} ({key})")
                        yaml_index.append({"repo": repo.label, "file": rel, "line": no, "key": key, "value": "***",
                                           "secret_literal": True})
                    elif K8S_KEYS.search(key) or re.search(r"(?i)(JAVA_OPTS|JAVA_TOOL_OPTIONS|JDK_JAVA_OPTIONS)", value + key) \
                            or "annotations" in key or leaf in ("name",) and "env" in key:
                        yaml_index.append({"repo": repo.label, "file": rel, "line": no, "key": key, "value": mask(value)[:160],
                                           "kinds": kinds[:4]})
                if re.search(r"^kind:\s*Secret\s*$", text, re.M) and re.search(r"^(data|stringData):", text, re.M):
                    yaml_index.append({"repo": repo.label, "file": rel, "line": 1, "key": "kind", "value": "Secret with data in Git",
                                       "secret_object": True})
            if re.search(DOCKER, rel):
                t = repo.text(rel)
                froms = [(m.group(1), t.count("\n", 0, m.start()) + 1) for m in
                         re.finditer(r"^\s*FROM\s+(?:--platform=\S+\s+)?(\S+)", t, re.M | re.I)]
                users = [(m.group(1), t.count("\n", 0, m.start()) + 1) for m in re.finditer(r"^\s*USER\s+(\S+)", t, re.M)]
                entry = [(m.group(0).strip()[:120], t.count("\n", 0, m.start()) + 1) for m in
                         re.finditer(r"^\s*(ENTRYPOINT|CMD)\s+.*$", t, re.M)]
                dockerfiles.append({"repo": repo.label, "file": rel, "from": froms, "user": users, "entry": entry,
                                    "stages": len(froms), "expose": re.findall(r"^\s*EXPOSE\s+(.+)$", t, re.M),
                                    "healthcheck": bool(re.search(r"^\s*HEALTHCHECK", t, re.M)),
                                    "java_opts": [mask(x)[:160] for x in re.findall(r"(?i)^\s*ENV\s+.*(?:JAVA_OPTS|JAVA_TOOL_OPTIONS)\S*\s*=?\s*(.*)$", t, re.M)]})
            if re.search(r"(^|/)(\.gitlab-ci\.yml|[^/]*\.gitlab-ci\.yml)$|(^|/)\.gitlab/ci/", rel):
                t = repo.text(rel)
                stages = re.search(r"^stages:\s*\n((?:\s+-\s*.+\n)+)", t, re.M)
                reserved = {"stages", "variables", "include", "default", "workflow", "image", "services", "before_script",
                            "after_script", "cache", "spec"}
                jobs = []
                for m in re.finditer(r"^([A-Za-z0-9_.][\w :./-]*):\s*$", t, re.M):
                    name = m.group(1)
                    if name in reserved:
                        continue
                    nxt = re.search(r"^\S", t[m.end():], re.M)
                    body = t[m.end(): m.end() + nxt.start()] if nxt else t[m.end():]
                    st = re.search(r"^\s+stage:\s*(\S+)", body, re.M)
                    env = re.search(r"^\s+environment:[ \t]*(?:\n\s+name:[ \t]*)?['\"]?([\w${}/-]+)", body, re.M)
                    jobs.append({"name": name, "line": t.count("\n", 0, m.start()) + 1, "stage": st.group(1) if st else None,
                                 "manual": bool(re.search(r"when:\s*manual", body)),
                                 "allow_failure": bool(re.search(r"allow_failure:\s*true", body)),
                                 "environment": env.group(1) if env else None,
                                 "deploys": bool(re.search(r"(?i)helm\s+(upgrade|install)|kubectl\s+(apply|set)|argocd\s+app", body))})
                includes = re.findall(r"^\s*-?\s*(?:template|project|component|local|remote|file):\s*['\"]?([^'\"\n]+)", t, re.M)
                tags = sorted(set(re.findall(r"(?i)(?:[\w./${}-]+):(\$\{?CI_COMMIT_(?:SHORT_)?SHA\}?|\$\{?CI_COMMIT_TAG\}?|"
                                             r"\$\{?CI_PIPELINE_IID\}?|\$\{?\w*VERSION\w*\}?|latest)\b", t)))
                pipelines.append({"repo": repo.label, "file": rel, "stages": re.findall(r"-\s*['\"]?([\w-]+)", stages.group(1))
                                  if stages else [], "jobs": jobs, "includes": includes[:15], "image_tags": tags})
    return signals, counts, config, yaml_index, dockerfiles, pipelines, [{"hash": h, "ref": r} for h, r in sorted(hashes.items())]


def checks(repos, signals, config, yidx, dockerfiles, pipelines):
    """Cross-repository facts: both sides of a contract, with a hint when the comparison is mechanical."""
    out = []
    sig = lambda sid: [s for s in signals if s["id"] == sid]
    cfg = lambda rx: [c for c in config if re.search(rx, c["key"])]
    yk = lambda rx: [y for y in yidx if re.search(rx, y["key"])]
    r = lambda x: f"{x['repo']}:{x['file']}:{x['line']}"

    def add(cid, title, controls, facts, hint=None):
        if facts:
            out.append({"id": cid, "title": title, "controls": controls, "facts": [f[:170] for f in facts[:12]], "hint": hint})

    # Replicas per values/manifests file (an environment)
    rep = {}
    for y in yk(r"(^|\.)(replicas|replicaCount|minReplicas|maxReplicas)$"):
        if re.fullmatch(r"\d+", y["value"]):
            rep.setdefault(f"{y['repo']}:{y['file']}", {})[y["key"].split(".")[-1]] = int(y["value"])
    max_rep = max([max(v.values()) for v in rep.values()] or [1])
    rep_facts = [f"{f}: " + ", ".join(f"{k}={v}" for k, v in sorted(d.items())) for f, d in sorted(rep.items())]

    # Scheduled jobs vs locks vs replicas
    sched = sig("scheduled")
    locks = sig("scheduler-lock")
    unlocked = []
    for s in sched:
        lines = [l["line"] for l in locks if l["repo"] == s["repo"] and l["file"] == s["file"]]
        if not any(abs(x - s["line"]) <= 4 for x in lines):
            unlocked.append(s)
    facts = [f"@Scheduled: {len(sched)}; with @SchedulerLock nearby: {len(sched) - len(unlocked)}"]
    facts += [f"no lock next to {r(s)}: {s['text'][:90]}" for s in unlocked[:8]]
    facts += [f"replicas {x}" for x in rep_facts[:6]]
    q = sig("quartz")
    if q:
        facts.append("Quartz references: " + ", ".join(r(x) for x in q[:4]))
    add("CHK-SCHEDULING", "Scheduled jobs vs distributed locks vs replicas", ["ARCH-01", "ARCH-02", "ARCH-03"],
        facts if sched else [],
        f"{len(unlocked)} scheduled method(s) without a lock nearby while up to {max_rep} replica(s) are configured: confirm each "
        "job is safe to run concurrently" if unlocked and max_rep > 1 else None)

    # Pool size x replicas
    pools = cfg(r"hikari\.maximum-pool-size$|hikari\.maximumPoolSize$")
    pool = max([int(p["value"]) for p in pools if p["value"].isdigit()] or [10])
    facts = [f"maximum-pool-size={p['value']} ({r(p)})" for p in pools] or ["maximum-pool-size not set: Hikari default 10"]
    facts += [f"replicas {x}" for x in rep_facts[:6]]
    if cfg(r"spring\.datasource\.url$") or any(s["id"] == "former-db-sql" for s in signals):
        add("CHK-POOL-CAPACITY", "Connection pools x replicas vs database capacity", ["APP-01", "APP-02", "K8S-04"], facts,
            f"up to {pool} x {max_rep} = {pool * max_rep} connections per service at max replicas (plus surge pods during rollouts); "
            "database limit is not in the repositories: NOT VERIFIED unless provided")

    # Probes vs actuator
    probes = [y for y in yk(r"(readinessProbe|livenessProbe|startupProbe|readiness|liveness|startup)(\.httpGet)?\.(path|port)$")]
    mgmt = cfg(r"^management\.(endpoint\.health\.probes\.enabled|endpoints\.web\.base-path|server\.port|endpoint\.health\.group\..*)$|"
               r"^server\.(port|servlet\.context-path)$")
    facts = [f"{y['key']}={y['value']} ({r(y)})" for y in probes] + [f"{c['key']}={c['value']} ({r(c)})" for c in mgmt]
    hint = None
    live = [y for y in probes if re.search(r"(?i)live", y["key"]) and y["key"].endswith("path")]
    if any(re.fullmatch(r"/?(actuator/)?health/?", y["value"].split("{{")[0].strip()) for y in live):
        hint = "a liveness probe uses the aggregate health endpoint (includes the database and other dependencies): restart-storm risk"
    add("CHK-PROBES", "Kubernetes probes vs Spring Boot actuator", ["K8S-05", "K8S-06", "K8S-07", "APP-10"], facts, hint)

    # Ports
    ports = yk(r"(^|\.)(containerPort|targetPort|port)$")
    app_ports = cfg(r"^(server\.port|management\.server\.port)$")
    listen = sig("nginx-listen")
    facts = [f"{y['key']}={y['value']} ({r(y)})" for y in ports[:10]] + [f"{c['key']}={c['value']} ({r(c)})" for c in app_ports] \
        + [f"nginx {s['text']} ({r(s)})" for s in listen] + [f"EXPOSE {', '.join(d['expose'])} ({d['repo']}:{d['file']})"
                                                               for d in dockerfiles if d["expose"]]
    add("CHK-PORTS", "Application, container, Service and probe ports", ["K8S-14", "K8S-05"], facts)

    # Shutdown vs grace period
    sd = cfg(r"^(server\.shutdown|spring\.lifecycle\.timeout-per-shutdown-phase)$")
    grace = yk(r"terminationGracePeriodSeconds$")
    prestop = yk(r"preStop")
    facts = [f"{c['key']}={c['value']} ({r(c)})" for c in sd] or ["server.shutdown not set (immediate before Spring Boot 3.4)"]
    facts += [f"terminationGracePeriodSeconds={g['value']} ({r(g)})" for g in grace] or ["terminationGracePeriodSeconds not set: 30s"]
    facts += [f"{p['key']}={p['value']} ({r(p)})" for p in prestop[:4]]
    tmo = next((to_seconds(c["value"]) for c in sd if c["key"].endswith("timeout-per-shutdown-phase")), 30)
    hint = None
    for g in grace:
        if g["value"].isdigit() and tmo and int(g["value"]) < tmo:
            hint = f"grace period {g['value']}s ({r(g)}) is shorter than the application's shutdown timeout ({int(tmo)}s)"
    add("CHK-SHUTDOWN", "Application shutdown vs pod termination", ["APP-11", "K8S-08"], facts, hint)

    # JVM heap vs memory limit
    opts = [y for y in yidx if re.search(r"-Xmx|MaxRAMPercentage|InitialRAMPercentage|-XX:MaxRAM", y["value"])]
    opts += [{"repo": d["repo"], "file": d["file"], "line": 0, "key": "ENV", "value": v} for d in dockerfiles for v in d["java_opts"]]
    mem = yk(r"(^|\.)limits\.memory$")
    facts = [f"{o['key']}={o['value'][:100]} ({o['repo']}:{o['file']}" + (f":{o['line']})" if o["line"] else ")") for o in opts] + [f"limits.memory={m['value']} ({r(m)})" for m in mem]
    hint = None
    xmx = [to_mib(x) for o in opts for x in re.findall(r"-Xmx(\d+[kKmMgG]?)", o["value"])]
    lim = [to_mib(m["value"]) for m in mem if to_mib(m["value"])]
    if xmx and lim and max(x for x in xmx if x) >= 0.8 * min(lim):
        hint = f"-Xmx {int(max(x for x in xmx if x))}Mi vs memory limit {int(min(lim))}Mi: heap leaves too little room (OOMKilled risk)"
    elif mem and not opts:
        hint = "no heap setting found: the JVM default (25% of the limit) may under-use memory; check JAVA_TOOL_OPTIONS in the image"
    add("CHK-JVM-MEMORY", "JVM heap vs container memory limit", ["K8S-01", "K8S-02"], facts if (opts or mem) else [], hint)

    # Image built vs deployed
    img = yk(r"(^|\.)(image|repository|tag|digest)$")
    argo = yk(r"targetRevision$")
    facts = [f"CI {p['repo']}:{p['file']} tags: {', '.join(p['image_tags']) or 'none found'}" for p in pipelines]
    facts += [f"{y['key']}={y['value']} ({r(y)})" for y in img[:12]] + [f"Argo CD targetRevision={a['value']} ({r(a)})" for a in argo]
    moving = [y for y in img if re.search(r"(?i)^latest$|:latest$", y["value"])]
    add("CHK-IMAGE-FLOW", "Image built by CI vs image deployed by Helm/Argo CD", ["CICD-05", "CICD-06", "CTR-06", "CICD-08"], facts,
        f"moving tag 'latest' deployed at {', '.join(r(y) for y in moving[:4])}" if moving else None)

    # Sessions vs affinity
    sess = sig("http-session")
    aff = [y for y in yidx if re.search(r"(?i)affinity|session-cookie|sessionAffinity", y["key"] + y["value"])]
    deps = [x for x in signals if x["id"] == "http-session" and "spring.session" in x["text"]]
    facts = [f"session use {r(s)}: {s['text'][:80]}" for s in sess[:6]] + [f"affinity {y['key']}={y['value']} ({r(y)})" for y in aff]
    add("CHK-SESSIONS", "HTTP sessions vs ingress affinity", ["ARCH-06", "WEB-10"], facts if sess else [],
        "server-side session use without ingress affinity or Spring Session: state lost when requests hit another pod"
        if sess and not aff and not deps else None)

    # Frontend routes vs ingress vs context path
    urls = [s for s in signals if s["id"] == "web-env-url"]
    paths = [y for y in yk(r"(^|\.)path$") if re.search(r"(?i)ingress|route|http\.paths", y["key"]) or
             {"Ingress", "Route"} & set(y.get("kinds") or [])]
    ctx = cfg(r"^server\.servlet\.context-path$")
    hosts = yk(r"(^|\.)hosts?$")
    facts = [f"frontend {r(u)}: {u['text'][:100]}" for u in urls[:8]] + [f"ingress path {y['value']} ({r(y)})" for y in paths
                                                                            if y["value"].startswith("/")][:8] \
        + [f"ingress host {y['value']} ({r(y)})" for y in hosts[:6]] + [f"context-path={c['value']} ({r(c)})" for c in ctx]
    add("CHK-API-ROUTES", "Frontend API URLs vs ingress paths/hosts vs backend context path", ["WEB-01", "WEB-02", "K8S-14"], facts)

    # On-premise endpoints
    onp = sig("onprem-host")
    add("CHK-ONPREM-ENDPOINTS", "On-premise hosts, IPs and paths still referenced", ["APP-08", "WEB-01", "WEB-03"],
        [f"{r(s)}: {s['text'][:110]}" for s in onp], f"{len(onp)} reference(s) to on-premise style hosts/paths" if onp else None)

    # Schema migrations
    lb = cfg(r"^spring\.(liquibase|flyway)\.")
    brk = sig("breaking-migration")
    facts = [f"{c['key']}={c['value']} ({r(c)})" for c in lb] + [f"destructive change {r(b)}: {b['text'][:90]}" for b in brk[:6]]
    facts += [f"replicas {x}" for x in rep_facts[:4]]
    add("CHK-SCHEMA-MIGRATIONS", "Schema migrations at startup vs replicas and rolling updates", ["APP-03", "APP-04", "K8S-07"],
        facts if (lb or brk) else [],
        f"{len(brk)} destructive change(s): check they are not used by the previous release during a rolling update" if brk else None)

    # Former engine SQL
    fdb = sig("former-db-sql")
    add("CHK-DB-ENGINE", "Former database engine SQL left in the code", ["APP-05"],
        [f"{r(s)}: {s['text'][:110]}" for s in fdb[:10]], f"{len(fdb)} Oracle-specific construct(s)" if fdb else None)

    # Secrets in Git
    lit = [x for x in config + yidx if x.get("secret_literal") or x.get("secret_object")]
    add("CHK-SECRETS-IN-GIT", "Secrets stored in the repositories (values hidden)", ["K8S-12", "APP-16", "CICD-12"],
        [f"{x['key']} at {r(x)}" for x in lit[:12]], f"{len(lit)} literal secret(s) or Secret object(s) in Git" if lit else None)

    # GitOps bypass
    dep = [(p, j) for p in pipelines for j in p["jobs"] if j["deploys"]]
    argo_used = any(s["id"] == "argocd" for s in signals)
    add("CHK-GITOPS", "Deployments from CI vs Argo CD", ["CICD-09", "CICD-10"],
        [f"job {j['name']} ({p['repo']}:{p['file']}:{j['line']}) deploys directly; manual={j['manual']}; environment={j['environment']}"
         for p, j in dep] + [f"Argo CD manifests present: {argo_used}"],
        "CI deploys with helm/kubectl although Argo CD manages the environment: drift and bypass of GitOps" if dep and argo_used else None)

    # Environment drift between values files of the same chart
    by_dir = {}
    for y in yidx:
        m = re.search(r"(^|/)values-?([\w-]*)\.ya?ml$", y["file"])
        if m:
            by_dir.setdefault((y["repo"], os.path.dirname(y["file"])), {}).setdefault(m.group(2) or "default", {})[y["key"]] = y["value"]
    facts = []
    for (repo, d), envs in sorted(by_dir.items()):
        if len(envs) < 2:
            continue
        for env, kv in sorted(envs.items()):
            facts.append(f"{repo}:{d or '.'} {env}: " + ", ".join(f"{k}={v}" for k, v in sorted(kv.items())
                                                                 if re.search(r"replica|tag|memory|cpu|maxReplicas|enabled$", k))[:300])
    add("CHK-ENV-DRIFT", "Differences between environment values files", ["K8S-18"], facts)
    return out


def run(repo_args):
    repos = []
    for arg in repo_args:
        label, sep, path = arg.partition("=")
        if not sep:
            label, path = os.path.basename(os.path.abspath(arg)), arg
        if not os.path.isdir(path):
            raise SystemExit(f"not a directory: {path}")
        repos.append(Repo(label, path))
    signals, counts, config, yidx, dockerfiles, pipelines, hashes = scan(repos)
    return OrderedDict(
        repos=[describe_repo(r) for r in repos],
        stack={r.label: [list(x) for x in stack_of(r)] for r in repos},
        signal_counts={f"{k[0]}:{k[1]}": v for k, v in sorted(counts.items())},
        signals=signals, config=config, yaml=yidx, dockerfiles=dockerfiles, pipelines=pipelines,
        checks=checks(repos, signals, config, yidx, dockerfiles, pipelines),
        paths={r.label: r.path for r in repos},
        secret_hashes=hashes,
    )


def signal_lines(inv, domains, per_signal=MAX_REFS):
    """Compact signal summary for the given domains: id, count per repo, first references."""
    from catalog import DOMAINS  # noqa: E402  (sibling module)
    names = {s[0]: s[4] for s in SIGNALS}
    lines = []
    for dom in domains:
        ids = [s[0] for s in SIGNALS if s[1] == dom]
        block = []
        for sid in ids:
            hits = [s for s in inv["signals"] if s["id"] == sid]
            if not hits:
                continue
            total = sum(v for k, v in inv["signal_counts"].items() if k.split(":", 1)[1] == sid)
            refs = ", ".join(f"`{h['repo']}:{h['file']}:{h['line']}`" for h in hits[:per_signal])
            block.append(f"- {names[sid]} [{sid}] ({total}): {refs}" + (" ..." if total > per_signal else ""))
        missing = [names[sid] for sid in ids if not any(s["id"] == sid for s in inv["signals"])]
        lines.append(f"### {dom} - {DOMAINS[dom]}")
        lines += block or ["- no signal found"]
        if missing:
            lines.append(f"- not found anywhere: {', '.join(missing)}")
    return lines


def render_inventory(inv, full=True):
    w = []
    w.append("# Cloud migration audit - inventory (leads to verify, not verdicts)\n")
    w.append("| Repository | Roles | Files | Revision | Branch | Uncommitted changes |\n| --- | --- | --- | --- | --- | --- |")
    for r in inv["repos"]:
        w.append(f"| {r['label']} | {', '.join(r['roles'])} | {r['files']} | {r['head'] or 'not a git repo'} | {r['branch'] or '-'} | "
                 f"{'yes' if r['dirty'] else 'no' if r['dirty'] is not None else '-'} |")
    for label, st in inv["stack"].items():
        if st:
            w.append(f"\n**{label} stack**: " + ", ".join(f"{a}" + (f" {b}" if b != "dependency" else "") for a, b, _ in st))
    w.append("\n## Cross-repository checks (facts side by side; confirm before concluding)")
    for c in inv["checks"]:
        w.append(f"\n**{c['id']}** {c['title']} -> {', '.join(c['controls'])}")
        if c["hint"]:
            w.append(f"- ! hint: {c['hint']}")
        w += [f"- {f}" for f in c["facts"]]
    df = inv["dockerfiles"]
    if df:
        w.append("\n## Dockerfiles")
        for d in df:
            shell = [e for e, _ in d["entry"] if not re.match(r"^\s*(ENTRYPOINT|CMD)\s*\[", e)]
            w.append(f"- `{d['repo']}:{d['file']}`: FROM {', '.join(f'{i}' for i, _ in d['from'])}; stages {d['stages']}; "
                     f"USER {', '.join(u for u, _ in d['user']) or 'none (root)'}; {'; '.join(e for e, _ in d['entry']) or 'no ENTRYPOINT/CMD (base image default)'}"
                     + ("; shell form: SIGTERM does not reach the process" if shell else ""))
    if inv["pipelines"]:
        w.append("\n## Pipelines")
        for p in inv["pipelines"]:
            jobs = ", ".join(f"{j['name']}[{j['stage'] or '?'}{', manual' if j['manual'] else ''}{', allow_failure' if j['allow_failure'] else ''}"
                             f"{', env ' + j['environment'] if j['environment'] else ''}]" for j in p["jobs"][:25])
            w.append(f"- `{p['repo']}:{p['file']}` stages: {', '.join(p['stages']) or '-'}; includes: {', '.join(p['includes']) or '-'}; "
                     f"jobs: {jobs}")
    from catalog import DOMAINS
    if full:
        w.append("\n## Signals by domain (count, first references)")
        w += signal_lines(inv, list(DOMAINS), per_signal=4)
    else:
        w.append("\n## Signals per domain (details go to the agent briefs)")
        for dom in DOMAINS:
            ids = Counter(s["id"] for s in inv["signals"] if s["domain"] == dom)
            w.append(f"- {dom}: " + (", ".join(f"{k} {v}" for k, v in sorted(ids.items())) or "none"))
    return "\n".join(w) + "\n"

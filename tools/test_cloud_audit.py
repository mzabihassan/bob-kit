#!/usr/bin/env python3
"""Tests of the cloud-migration-audit-java-angular engine on a synthetic three-repository application.

The fixture (air-back: Spring Boot, air-ui: Angular, air-cd: Helm/Argo CD/GitLab CI) contains known migration
defects and correct parts. The tests check discovery leads, agent-result checks, the merge (statuses, IDs, metrics,
decision), the five reports, determinism, secret masking and the comparison between two audits.

Run from the repository root:  python3 tools/test_cloud_audit.py
Write the fixture somewhere to try the skill by hand:  python3 tools/test_cloud_audit.py --write-fixture /tmp/air
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(ROOT, "skills", "cloud-migration-audit-java-angular", "scripts", "audit.py")
FAKE_SECRET = "devpass" + "123"  # assembled so the repository's own secret guard does not flag this test file

FIXTURE = {
    "air-back/pom.xml": """<project><modelVersion>4.0.0</modelVersion>
  <parent><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-parent</artifactId><version>3.3.5</version></parent>
  <groupId>com.acme</groupId><artifactId>air-back</artifactId><version>1.4.2</version>
  <properties><java.version>17</java.version></properties>
  <dependencies>
    <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-web</artifactId></dependency>
    <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-actuator</artifactId></dependency>
    <dependency><groupId>org.liquibase</groupId><artifactId>liquibase-core</artifactId></dependency>
    <dependency><groupId>org.postgresql</groupId><artifactId>postgresql</artifactId></dependency>
    <dependency><groupId>net.javacrumbs.shedlock</groupId><artifactId>shedlock-spring</artifactId><version>5.16.0</version></dependency>
    <dependency><groupId>io.micrometer</groupId><artifactId>micrometer-registry-prometheus</artifactId></dependency>
  </dependencies>
</project>
""",
    "air-back/src/main/java/com/acme/air/ReportExportJob.java": """package com.acme.air;

import net.javacrumbs.shedlock.spring.annotation.SchedulerLock;
import org.springframework.scheduling.annotation.Scheduled;

public class ReportExportJob {
    @Scheduled(cron = "0 0 2 * * *")
    @SchedulerLock(name = "reportExport", lockAtMostFor = "PT30M")
    public void export() throws Exception {
        java.nio.file.Files.write(java.nio.file.Paths.get("/data/exports/report.csv"), new byte[0]);
    }
}
""",
    "air-back/src/main/java/com/acme/air/InvoiceReminderJob.java": """package com.acme.air;

import org.springframework.scheduling.annotation.Scheduled;

public class InvoiceReminderJob {
    private static final java.util.Map<String, Integer> SENT = new java.util.concurrent.ConcurrentHashMap<>();

    @Scheduled(fixedDelay = 60000)
    public void remind() {
        // sends one e-mail per unpaid invoice
    }
}
""",
    "air-back/src/main/java/com/acme/air/CartController.java": """package com.acme.air;

import jakarta.servlet.http.HttpSession;
import org.springframework.web.client.RestTemplate;

public class CartController {
    private final RestTemplate partner = new RestTemplate();

    public void add(HttpSession session, String item) {
        session.setAttribute("cart", item);
        partner.getForObject("http://partner-api.intranet.local:8080/price/" + item, String.class);
    }
}
""",
    "air-back/src/main/java/com/acme/air/InvoiceRepository.java": """package com.acme.air;

public interface InvoiceRepository {
    @org.springframework.data.jpa.repository.Query(value = "SELECT NVL(amount, 0) FROM invoice WHERE ROWNUM <= 10", nativeQuery = true)
    java.util.List<Object> latest();
}
""",
    "air-back/src/main/resources/application.yml": """server:
  port: 8080
spring:
  application:
    name: air-back
  datasource:
    url: ${DB_URL}
    username: ${DB_USER}
    password: ${DB_PASSWORD}
    hikari:
      maximum-pool-size: 40
  liquibase:
    change-log: classpath:db/changelog/master.xml
management:
  endpoint:
    health:
      probes:
        enabled: true
  endpoints:
    web:
      exposure:
        include: health,info,prometheus
""",
    "air-back/src/main/resources/logback-spring.xml": """<configuration>
  <appender name="FILE" class="ch.qos.logback.core.rolling.RollingFileAppender"><file>/var/log/air/air.log</file></appender>
  <root level="INFO"><appender-ref ref="FILE"/></root>
</configuration>
""",
    "air-back/src/main/resources/db/changelog/master.xml": """<databaseChangeLog>
  <changeSet id="1" author="air"><createTable tableName="invoice"><column name="id" type="bigint"/></createTable></changeSet>
  <changeSet id="2" author="air"><dropColumn tableName="invoice" columnName="legacy_code"/></changeSet>
</databaseChangeLog>
""",
    "air-back/Dockerfile": """FROM maven:3.9-eclipse-temurin-17 AS build
COPY . /src
RUN mvn -f /src/pom.xml -q package -DskipTests
FROM eclipse-temurin:17-jre
COPY --from=build /src/target/air-back.jar /app/app.jar
EXPOSE 8080
ENTRYPOINT java $JAVA_OPTS -jar /app/app.jar
""",
    "air-back/.gitlab-ci.yml": """stages:
  - build
  - test
  - publish
build:
  stage: build
  script: mvn -q package
sonar:
  stage: test
  allow_failure: true
  script: mvn sonar:sonar
publish:
  stage: publish
  script:
    - jf docker push acme.jfrog.io/air/air-back:$CI_COMMIT_SHORT_SHA
    - jf docker push acme.jfrog.io/air/air-back:latest
""",
    "air-ui/package.json": """{"name": "air-ui", "dependencies": {"@angular/core": "17.3.0", "keycloak-angular": "15.2.1"}}
""",
    "air-ui/angular.json": """{"projects": {"air-ui": {"projectType": "application", "root": "", "sourceRoot": "src", "architect": {"build": {"configurations": {"production": {}}}}}}}
""",
    "air-ui/src/main.ts": "bootstrapApplication(AppComponent, appConfig);\n",
    "air-ui/src/environments/environment.prod.ts": """export const environment = {
  production: true,
  apiUrl: 'https://air-api.intranet.local/api',
  issuer: 'https://sso.intranet.local/auth/realms/air'
};
""",
    "air-ui/src/app/auth.interceptor.ts": """export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const token = localStorage.getItem('access_token');
  return next(req.clone({ setHeaders: { Authorization: 'Bearer ' + token } }));
};
""",
    "air-ui/nginx.conf": """server {
  listen 80;
  location / {
    root /usr/share/nginx/html;
    try_files $uri $uri/ /index.html;
  }
}
""",
    "air-ui/Dockerfile": """FROM node:20 AS build
COPY . /app
RUN cd /app && npm ci && npm run build
FROM nginx:latest
COPY --from=build /app/dist/air-ui /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
""",
    "air-cd/helm/air-back/Chart.yaml": "apiVersion: v2\nname: air-back\nversion: 0.3.0\n",
    "air-cd/helm/air-back/values.yaml": """replicaCount: 2
image:
  repository: acme.jfrog.io/air/air-back
  tag: latest
resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    memory: 1Gi
env:
  - name: JAVA_OPTS
    value: "-Xmx1536m -Djavax.net.ssl.trustStore=/opt/certs/truststore.jks"
readinessProbe:
  httpGet:
    path: /actuator/health/readiness
    port: 8080
livenessProbe:
  httpGet:
    path: /actuator/health
    port: 8080
terminationGracePeriodSeconds: 10
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 6
ingress:
  path: /api
""",
    "air-cd/helm/air-back/values-prod.yaml": """replicaCount: 3
image:
  tag: "1.4.2"
autoscaling:
  maxReplicas: 8
""",
    "air-cd/helm/air-back/values-dev.yaml": f"""replicaCount: 1
db:
  password: {FAKE_SECRET}
""",
    "air-cd/helm/air-back/templates/deployment.yaml": """apiVersion: apps/v1
kind: Deployment
metadata:
  name: air-back
spec:
  replicas: {{ .Values.replicaCount }}
  template:
    spec:
      terminationGracePeriodSeconds: {{ .Values.terminationGracePeriodSeconds }}
      containers:
        - name: air-back
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          ports:
            - containerPort: 8080
          volumeMounts:
            - name: exports
              mountPath: /data/exports
      volumes:
        - name: exports
          emptyDir: {}
""",
    "air-cd/monitoring/servicemonitor.yaml": """apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: air-back
spec:
  endpoints:
    - path: /actuator/prometheus
""",
    "air-cd/argocd/air-back-prod.yaml": """apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: air-back-prod
spec:
  source:
    targetRevision: HEAD
    path: helm/air-back
  syncPolicy:
    automated:
      prune: true
""",
    "air-cd/.gitlab-ci.yml": """stages:
  - lint
  - deploy
lint:
  stage: lint
  script: helm lint helm/air-back
deploy-prod:
  stage: deploy
  when: manual
  environment:
    name: production
  script:
    - helm upgrade --install air-back helm/air-back -f helm/air-back/values-prod.yaml
""",
    "air-cd/docs/runbook.md": "# Runbook\n\n## Rollback\n\nRevert the values commit; Argo CD syncs.\n",
}


def write_fixture(base):
    for rel, content in FIXTURE.items():
        path = os.path.join(base, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
    for repo in ("air-back", "air-ui", "air-cd"):
        d = os.path.join(base, repo)
        for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
                                                                    "commit", "-qm", "initial"]):
            subprocess.run(["git", "-C", d, *args], check=True, capture_output=True)


def ev(repo, file, line, note):
    return {"repo": repo, "file": file, "line": line, "note": note}


def finding(key, control, sev, title, evidence, **kw):
    f = {"key": key, "control": control, "severity": sev, "kind": "confirmed", "title": title, "repos": sorted({e["repo"] for e in evidence}),
         "evidence": evidence, "impact": "Failure scenario: duplicate side effects in production.", "remediation": "Apply the fix described.",
         "validation": "Test with three replicas in staging.", "acceptance": "No duplicate execution observed."}
    f.update(kw)
    return f


def results_backend():
    jobs = "src/main/java/com/acme/air/"
    return {"group": "backend", "notes": "Spring Boot 3.3 service with scheduled jobs and a session-based cart.", "controls": [
        {"id": "ARCH-01", "status": "PARTIALLY DONE", "summary": "One of two scheduled jobs is locked.", "repos": ["air-back"],
         "evidence": [ev("air-back", jobs + "ReportExportJob.java", 8, "@SchedulerLock on reportExport")]},
        {"id": "ARCH-02", "status": "DONE", "summary": "lockAtMostFor 30 minutes on the export.",
         "evidence": [ev("air-back", jobs + "ReportExportJob.java", 8, "lockAtMostFor = PT30M")]},
        {"id": "ARCH-03", "status": "NOT APPLICABLE", "summary": "Quartz is not used."},
        {"id": "ARCH-06", "status": "NOT DONE", "summary": "Cart kept in HttpSession without Spring Session."},
        {"id": "APP-05", "status": "NOT DONE", "summary": "Oracle SQL left in a native query."},
        {"id": "APP-16", "status": "NOT DONE", "summary": "Database password: [REDACTED] in values-dev.yaml (password: not shown here)."},
    ], "findings": [
        finding("values-dev-password-literal", "APP-16", "HIGH", "Database password literal in values-dev.yaml",
                [ev("air-cd", "helm/air-back/values-dev.yaml", 3, "db.password literal (value hidden)")]),
        finding("invoicereminderjob-unlocked", "ARCH-01", "HIGH", "InvoiceReminderJob runs on every replica",
                [ev("air-back", jobs + "InvoiceReminderJob.java", 8, "@Scheduled without lock"),
                 ev("air-cd", "helm/air-back/values-prod.yaml", 1, "replicaCount: 3")], effort="S"),
        finding("cartcontroller-session", "ARCH-06", "HIGH", "Cart stored in HttpSession without affinity",
                [ev("air-back", jobs + "CartController.java", 10, "session.setAttribute")]),
        finding("invoicerepository-oracle-sql", "APP-05", "CRITICAL", "Native query uses Oracle NVL and ROWNUM on PostgreSQL",
                [ev("air-back", jobs + "InvoiceRepository.java", 4, "NVL and ROWNUM")], example="SELECT COALESCE(amount, 0) FROM invoice LIMIT 10"),
    ]}


def results_platform():
    return {"group": "platform", "controls": [
        {"id": "K8S-05", "status": "DONE", "summary": "Readiness probe on the readiness group.",
         "evidence": [ev("air-cd", "helm/air-back/values.yaml", 17, "path: /actuator/health/readiness")]},
        {"id": "K8S-12", "status": "NOT DONE", "summary": "A database password is committed in values-dev.yaml."},
        {"id": "CTR-03", "status": "NOT VERIFIED", "summary": "Base image user not checked."},
        {"id": "K8S-10", "status": "NOT DONE", "summary": "No PodDisruptionBudget for air-back. Three replicas in prod.",
         "evidence": [ev("air-cd", "helm/air-back/values-prod.yaml", 1, "replicaCount: 3, no PDB")],
         "remediation": "Add a PodDisruptionBudget with minAvailable 1 to the chart.", "severity": "MEDIUM"},
        {"id": "ARCH-01", "status": "DONE", "summary": "Export job locked (platform view).",
         "evidence": [ev("air-back", "src/main/java/com/acme/air/ReportExportJob.java", 8, "@SchedulerLock")]},
    ], "findings": [
        finding("values-dev-db-password", "K8S-12", "HIGH", "Database password committed in values-dev.yaml",
                [ev("air-cd", "helm/air-back/values-dev.yaml", 3, "db.password literal (value hidden)")], blocker=True),
    ]}


def run(*args, cwd=None):
    return subprocess.run([sys.executable, AUDIT, *args], capture_output=True, text=True, cwd=cwd)


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--write-fixture":
        write_fixture(sys.argv[2])
        print(f"fixture written to {sys.argv[2]}")
        return 0
    checks, failed = 0, []

    def expect(cond, label):
        nonlocal checks
        checks += 1
        if not cond:
            failed.append(label)

    tmp = tempfile.mkdtemp(prefix="cloud-audit-test-")
    try:
        write_fixture(tmp)
        out = os.path.join(tmp, "cloud-migration-audit")
        repos = [f"--repo={r}={os.path.join(tmp, r)}" for r in ("air-back", "air-ui", "air-cd")]
        r = run("discover", *repos, "--out", out)
        expect(r.returncode == 0, f"discover exit code: {r.stderr[-300:]}")
        inv = json.load(open(os.path.join(out, "work", "inventory.json")))
        hints = {c["id"]: c["hint"] or "" for c in inv["checks"]}
        expect("1 scheduled method(s) without a lock" in hints.get("CHK-SCHEDULING", ""), "unlocked @Scheduled detected")
        expect("40 x 8 = 320" in hints.get("CHK-POOL-CAPACITY", ""), "pool x max replicas computed")
        expect("liveness" in hints.get("CHK-PROBES", ""), "liveness on aggregate health flagged")
        expect("shorter than" in hints.get("CHK-SHUTDOWN", ""), "grace period shorter than shutdown timeout")
        expect("OOMKilled" in hints.get("CHK-JVM-MEMORY", ""), "heap vs memory limit")
        expect("latest" in hints.get("CHK-IMAGE-FLOW", ""), "latest tag flagged")
        expect("GitOps" in hints.get("CHK-GITOPS", ""), "CI helm deploy alongside Argo CD")
        expect("Spring Session" in hints.get("CHK-SESSIONS", ""), "session without affinity")
        expect(hints.get("CHK-SECRETS-IN-GIT", "").startswith("1 literal"), "literal secret found")
        expect("Oracle" in hints.get("CHK-DB-ENGINE", ""), "Oracle SQL found")
        expect(FAKE_SECRET not in open(os.path.join(out, "work", "inventory.json")).read(), "secret value masked in the inventory")
        r = run("briefs", "--out", out)
        expect(r.returncode == 0 and "3 agent briefs" in r.stdout and os.path.exists(os.path.join(out, "work", "brief-platform.md")),
               "small estate: 3 briefs chosen automatically")
        brief = open(os.path.join(out, "work", "brief-backend.md")).read()
        expect("ARCH-01" in brief and "APP-16" in brief and "K8S-01" not in brief, "backend brief has only its controls")
        expect("### ARCH" in brief and "### K8S" not in brief and "Severity hints" in brief, "brief embeds its guide sections only")
        json.loads(brief.split("```json", 1)[1].split("```", 1)[0])  # the output example in the brief is valid JSON

        bad = results_backend()
        bad["controls"][1]["evidence"] = []
        bad["findings"][1]["evidence"][0]["file"] = "src/Missing.java"
        bad["findings"][1]["impact"] = "The password " + FAKE_SECRET + " is readable by anyone with Git access."
        path = os.path.join(out, "work", "results-backend.json")
        json.dump(bad, open(path, "w"))
        r = run("check", path, "--out", out)
        expect(r.returncode == 1 and "DONE needs evidence" in r.stdout and "does not exist" in r.stdout, "check rejects bad results")
        expect("value of the secret defined at air-cd:helm/air-back/values-dev.yaml:3 (db.password)" in r.stdout and FAKE_SECRET not in r.stdout,
               "check rejects a leaked secret value and names its source, not the value")
        ops = {"group": "frontend-ops", "controls": [
            {"id": "OPS-06", "status": "NOT DONE", "summary": "No backup configuration in the repositories."},
            {"id": "WEB-01", "status": "NOT DONE", "summary": "On-premise hosts in the production environment."},
            {"id": "WEB-02", "status": "NOT DONE", "summary": "API base URL is the on-premise host."}],
            "findings": [finding("environment-prod-onprem-hosts", "WEB-01", "CRITICAL", "Production build calls on-premise hosts",
                                 [ev("air-ui", "src/environments/environment.prod.ts", 3, "apiUrl on-premise")], related_controls=["WEB-02"])]}
        opath = os.path.join(out, "work", "results-frontend-ops.json")
        json.dump(ops, open(opath, "w"))
        r = run("check", opath, "--out", out)
        expect(r.returncode == 1 and "OPS-06" in r.stdout and "platform-side" in r.stdout and "WEB-02" not in r.stdout,
               "absence in Git is not NOT DONE for a platform control; related_controls cover WEB-02")
        ops["controls"][0] = {"id": "OPS-06", "status": "NOT VERIFIED", "summary": "Backups are platform-side: evidence needed."}
        json.dump(ops, open(opath, "w"))
        json.dump(results_backend(), open(path, "w"))
        json.dump(results_platform(), open(os.path.join(out, "work", "results-platform.json"), "w"))
        r = run("build", "--out", out, "--date", "2026-11-01")
        expect(r.returncode == 0 and "DRAFT" in r.stdout and "LEAD  CHK-PROBES" in r.stdout and "LEAD  CHK-SCHEDULING" not in r.stdout,
               f"draft build without summary lists uncovered leads only: {r.stdout[-500:]}")
        json.dump({"executive_summary": "The application is not ready: one critical and several high risks remain.",
                   "architecture": "Spring Boot API behind an Angular SPA, deployed with Helm and Argo CD on Kubernetes."},
                  open(os.path.join(out, "work", "summary.json"), "w"))
        r = run("build", "--out", out, "--date", "2026-11-01")
        expect(r.returncode == 0, f"build OK: {r.stdout[-600:]}")
        doc = json.load(open(os.path.join(out, "cloud-migration-findings.json")))
        st = {c["id"]: c["status"] for c in doc["controls"]}
        expect(st["ARCH-01"] == "PARTIALLY DONE" and st["ARCH-03"] == "NOT APPLICABLE" and st["APP-01"] == "NOT VERIFIED", "statuses merged")
        expect(doc["conflicts"] == [{"control": "ARCH-01", "assessments": {"backend": "PARTIALLY DONE", "platform": "DONE"},
                                     "kept": "PARTIALLY DONE"}], "conflict resolved conservatively and recorded")
        expect(len(doc["controls"]) == 93 and not doc["controls"][10]["assessed"], "every catalog control present, unassessed ones flagged")
        ov = doc["metrics"]["overall"]
        expect(ov["applicable"] == 92 and ov["done"] == 2 and ov["completion_pct"] == round(200 / 92, 1), "completion formula")
        expect(ov["coverage_pct"] == round(100 * (2 + 1 + 7) / 92, 1), "coverage formula excludes NOT VERIFIED")
        sec = [f for f in doc["findings"] if f["control"] in ("K8S-12", "APP-16")]
        expect(len(sec) == 1 and sec[0]["control"] == "K8S-12" and sec[0]["related_controls"] == ["APP-16"],
               "same location from two agents merged into one finding with a related control")
        expect(doc["decision"]["verdict"] == "NO-GO" and len(doc["decision"]["blockers"]) == 3, "NO-GO on CRITICAL and blocker")
        gap = next((f for f in doc["findings"] if f["key"] == "k8s-10-gap"), {})
        expect(gap.get("severity") == "MEDIUM" and gap.get("remediation", "").startswith("Add a PodDisruptionBudget")
               and gap.get("title", "") == "Disruptions keep the service available — not done: Add a PodDisruptionBudget with minAvailable 1 to the chart",
               "control-level remediation becomes a finding")
        webf = next(f for f in doc["findings"] if f["key"] == "environment-prod-onprem-hosts")
        expect(webf["related_controls"] == ["WEB-02"] and webf["id"] in open(os.path.join(out, "cloud-migration-checklist.md")).read()
               .split("WEB-02", 1)[1].split("\n", 1)[0], "related control listed with the finding in the checklist")
        ids = {f["key"]: f["id"] for f in doc["findings"]}
        expect(ids["invoicereminderjob-unlocked"] == "ARCH-01-F1" and doc["findings"][0]["severity"] == "CRITICAL", "IDs and ordering")
        expect(next(f for f in doc["findings"] if f["key"] == "invoicereminderjob-unlocked")["cross_repo"], "cross-repo finding")
        md = open(os.path.join(out, "cloud-migration-audit.md")).read()
        for n in range(1, 17):
            expect(f"## {n}. " in md, f"report section {n}")
        html = open(os.path.join(out, "cloud-migration-audit.html")).read()
        expect("<script src" not in html and "<link" not in html and "http" not in html.split("<main>")[0], "HTML is self-contained")
        r = run("validate", "--out", out)
        expect(r.returncode == 0, f"validate OK: {r.stdout[-300:]}")

        first = {n: open(os.path.join(out, n)).read() for n in os.listdir(out) if n.startswith("cloud-migration")}
        r = run("build", "--out", out, "--date", "2026-11-01")
        again = {n: open(os.path.join(out, n)).read() for n in os.listdir(out) if n.startswith("cloud-migration")}
        expect(first == again, "same inputs, same reports (deterministic)")

        # Second audit: the session problem is fixed (control DONE), the Oracle finding disappears without a fix, a new finding appears.
        b2 = results_backend()
        b2["controls"][3] = {"id": "ARCH-06", "status": "DONE", "summary": "Spring Session JDBC added.",
                             "evidence": [ev("air-back", "pom.xml", 1, "spring-session-jdbc")]}
        b2["findings"] = [f for f in b2["findings"] if f["key"] in ("invoicereminderjob-unlocked", "values-dev-password-literal")] + [finding("reportexportjob-local-disk", "ARCH-07", "HIGH", "Exports written to an emptyDir",
                                                     [ev("air-back", "src/main/java/com/acme/air/ReportExportJob.java", 10, "Files.write /data")])]
        b2["controls"][4] = {"id": "APP-05", "status": "NOT VERIFIED", "summary": "Not re-checked."}
        b2["controls"].append({"id": "ARCH-07", "status": "NOT DONE", "summary": "Exports on local disk."})
        json.dump(b2, open(path, "w"))
        r = run("build", "--out", out, "--date", "2026-11-15")
        expect(r.returncode == 0, f"second build OK: {r.stdout[-400:]}")
        doc2 = json.load(open(os.path.join(out, "cloud-migration-findings.json")))
        c = doc2["comparison"] or {}
        expect([x["id"] for x in c.get("resolved", [])] == ["ARCH-06-F1"], "fixed finding resolved (control DONE)")
        expect([x["id"] for x in c.get("unconfirmed", [])] == ["APP-05-F1"], "vanished finding without fix is only 'to confirm'")
        expect("WEB-01-F1" in c.get("persisting", []), "finding of an unchanged results file persists with the same ID")
        expect(c.get("new") == ["ARCH-07-F1"] and "ARCH-01-F1" in c.get("persisting", []), "new and persisting findings")
        expect(os.path.isdir(os.path.join(out, "history")) and len(os.listdir(os.path.join(out, "history"))) == 1, "previous audit archived")
        status = subprocess.run(["git", "-C", os.path.join(tmp, "air-back"), "status", "--porcelain"], capture_output=True, text=True).stdout
        expect(status.strip() == "", "audited repository left untouched")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for f in failed:
        print(f"FAIL {f}")
    print(f"{checks - len(failed)}/{checks} cloud audit checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

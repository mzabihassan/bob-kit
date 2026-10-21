# Nexus IQ / Sonatype Lifecycle (dependencies and licences)

## Concepts

- An **application** is evaluated against **policies** at a **stage** (develop, source, build, stage-release, release, operate). Each policy has an action per stage: none, *Warn* or *Fail*. Only *Fail* at the stage CI uses blocks the pipeline: check `.gitlab-ci.yml` for the stage passed to the CLI.
- **Threat level** 0–10, commonly grouped as Critical 8–10, Severe 4–7, Moderate 2–3, Low 1.
- Violation types: **Security** (CVE or Sonatype vulnerability IDs), **License** (e.g. copyleft or unknown licence), **Architecture/Quality** (age, popularity, unmaintained component).
- Components are identified by coordinates (Maven `group:artifact:version`, npm `name@version`) and can be **direct** or **transitive**.

## Getting the data

- Report UI or export from the user (policy violations per component).
- CLI evaluation, as CI does it: `java -jar nexus-iq-cli.jar -i <applicationId> -s <iqUrl> -a "$IQ_USER:$IQ_TOKEN" -t <stage> <path to jar/war/target dir or package-lock.json>` (check the flags with `-h` for the installed version).
- REST API (version-dependent, check the instance docs), e.g. the policy report of a scan: `GET /api/v2/applications/{publicId}/reports/{scanId}/policy`. The component **Remediation** view or API gives "next version with no violations" and "next non-failing version": start there.

## Remediation order (cheapest safe fix first)

1. **Find who brings the component**: `./mvnw dependency:tree -Dincludes=<group>:<artifact>`, `./gradlew dependencyInsight --dependency <artifact> --configuration runtimeClasspath`, `npm ls <pkg>` / `npm explain <pkg>`.
2. **Upgrade the framework or platform patch first**: a Spring Boot (or Angular, or other BOM) patch or minor release often brings fixed transitive versions for many CVEs at once with tested compatibility.
3. **Upgrade the direct dependency** that pulls the vulnerable one, to the smallest version that clears the violation.
4. **Override the transitive version** only if needed and compatible:
   - Spring Boot with `spring-boot-starter-parent`: override the managed version property (e.g. `<tomcat.version>`, `<jackson-bom.version>`, `<netty.version>`, `<snakeyaml.version>`; check the Boot dependency-versions appendix for the exact property name).
   - Spring Boot BOM imported without the parent: add a `dependencyManagement` entry **before** the BOM import.
   - Gradle: the dependency-management plugin's `ext['<property>']`, or `constraints { implementation('g:a:v') }` / platforms.
   - npm: `overrides` (npm ≥ 8.3), Yarn `resolutions`, pnpm `overrides`. Angular packages are upgraded with `ng update`, not overrides.
5. **Remove unused dependencies** (`./mvnw dependency:analyze`, `npx depcheck`): the cheapest fix of all, when confirmed.
6. **Replace the component** when it is unmaintained or no fixed version exists.

After any version change: full build, tests and an application smoke test. Read the release notes for anything beyond a patch version, and never jump a major version without agreement.

## Deciding without a fix

When no fixed version exists or the upgrade is too risky now:
- Check exploitability: is the vulnerable function or feature used? Use Sonatype reachability analysis if the instance offers it, or code search for the vulnerable API. Is the attack vector exposed (network, untrusted input)?
- Propose a **waiver** for the security team with: component and version scope, the CVE, the reason (not reachable, mitigated by configuration, compensating control), the evidence and an expiry date. Waivers are applied in IQ by authorised people, not by you.
- Suggest compensating controls (disable the vulnerable feature, input validation, WAF rule, network restriction) where relevant.

## Licences

Licence violations are legal decisions. Identify the component and the licence, check whether it is distributed or used as a service, propose alternatives with a compatible licence, and route the decision to the legal or open-source office. Never "fix" a licence issue by repackaging or vendoring code.

## Cautions

- Fat jars, shaded jars and container images embed dependencies: the fix is always in the build that produces them.
- `npm audit`, OWASP Dependency-Check, Sysdig and IQ may disagree on severity or applicability; the gate that blocks is the reference.
- Keep lockfiles (`package-lock.json`, Gradle lockfiles) in sync with the change.

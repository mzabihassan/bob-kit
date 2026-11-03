# bob-kit — skills, hooks et modes pour IBM Bob

Une collection de **skills** et **hooks** réutilisables et de **modes** personnalisés pour [IBM Bob](https://www.ibm.com/products/bob).

## Organisation

```
skills/          # un dossier par skill, chacun avec un point d'entrée SKILL.md
  angular2-developer/
  react-developer/
  spring-boot-developer/
  sonarqube-java-angular/
  security-findings-remediation/
  gitlab-ci-engineer/
  sql-database-engineer/
  argocd-gitops/
  ibm-cloud-platform/
  merge-request-review/
  criticize-me/
  defend-me/
  confluence-documentation/
  design-system/
  web-accessibility-eu-fr/
  release-change-management/
  production-incident-investigation/
  project-playbook-java-angular/
  cloud-migration-audit-java-angular/
  sql-to-jpa-entities/
modes/           # modes Bob personnalisés (custom_modes.yaml)
hooks/           # lifecycle hooks Bob (scripts Python + settings.example.json)
tools/           # validation du kit, tests (hooks, audit cloud, sécurité), scan SkillSpector, hook git pre-commit
  skillspector/  # baselines SkillSpector justifiées, une par skill
```

## Skills

| Skill | Cas d'utilisation | Quand l'utiliser |
|-------|-------------------|------------------|
| [angular2-developer](skills/angular2-developer/SKILL.md) | Écrit, corrige, teste et revoit du code Angular (v18 à la dernière version) en suivant les conventions du projet, et mène les montées de version (`ng update`, composants standalone, signals, zoneless). | Vous développez une fonctionnalité Angular, corrigez un bug d'affichage, de build ou de test, faites relire un composant ou passez à une version plus récente d'Angular. |
| [react-developer](skills/react-developer/SKILL.md) | Même rôle pour React 18 et plus en TypeScript (Vite, Next.js, React Router) : fonctionnalités, corrections, tests, revue et migrations (React 19, CRA vers Vite, Pages Router vers App Router). | Vous travaillez sur une application React : nouvelle fonctionnalité, bug, erreur d'hydratation ou de test, revue de code, montée de version. |
| [spring-boot-developer](skills/spring-boot-developer/SKILL.md) | Développe et corrige du code Java 17–21 et Spring Boot avec la rigueur d'un tech lead bancaire : bug reproduit par un test avant correction, refactoring sûr du code legacy, tests JUnit 5, Mockito et Testcontainers, performance JPA et SQL. Termine par un rapport technique. | Toute tâche sur un backend Spring Boot : nouvel endpoint, bug, refactoring, revue d'architecture ou de code, lenteur, montée de version de Java ou de Spring Boot. |
| [sonarqube-java-angular](skills/sonarqube-java-angular/SKILL.md) | Fait progresser les résultats SonarQube au meilleur rapport gain/effort : d'abord les conditions du Quality Gate et les vraies failles, puis des tests utiles là où ils couvrent le plus (classement à partir des rapports JaCoCo et LCOV), les corrections d'issues et la revue des hotspots. Mesure avant et après, sans tricher sur les métriques. | Le Quality Gate échoue, la couverture de tests est insuffisante, ou vous voulez réduire la dette SonarQube d'un projet Java ou Angular. |
| [security-findings-remediation](skills/security-findings-remediation/SKILL.md) | Trie les findings Fortify (code), Nexus IQ (dépendances, licences) et Sysdig (images, conteneurs), corrige les vrais risques par la plus petite modification (souvent une montée de version), rédige les justifications de dérogation et indique quoi rescanner. Ne contourne jamais le scanner. | Une release est bloquée par un scan de sécurité, ou vous devez traiter une liste de vulnérabilités. Proposé uniquement dans le mode `security-remediator`. |
| [gitlab-ci-engineer](skills/gitlab-ci-engineer/SKILL.md) | Trouve la cause d'un pipeline GitLab en échec à partir des logs et propose le correctif minimal ; écrit ou améliore le `.gitlab-ci.yml` (règles, dépendances entre jobs, caches, templates, scans de sécurité, build d'images, promotion vers Argo CD) en respectant les templates centraux. Ne contourne jamais une gate. | Un job ou un pipeline échoue, un pipeline est trop lent, ou vous créez ou modifiez la CI d'un projet Java, Angular, React ou conteneur. |
| [sql-database-engineer](skills/sql-database-engineer/SKILL.md) | Pour Oracle et PostgreSQL : lit les plans d'exécution et propose index ou réécritures, écrit des migrations Flyway ou Liquibase sans interruption de service, résout verrous et deadlocks, revoit le SQL et le PL/SQL, et accompagne la migration d'Oracle vers PostgreSQL. Lecture seule sur les bases partagées, sauf demande. | Une requête est lente, une migration de schéma ou de données se prépare, des deadlocks ou des attentes de verrous apparaissent, ou vous migrez d'Oracle vers PostgreSQL. |
| [argocd-gitops](skills/argocd-gitops/SKILL.md) | Diagnostique les applications Argo CD OutOfSync, Degraded ou en échec de synchronisation ; écrit Applications, ApplicationSets, values Helm et overlays Kustomize ; gère la promotion entre environnements et le retour arrière par `git revert`. Modifie le dépôt GitOps ; accès au cluster en lecture seule, sauf demande. | Un déploiement Argo CD ne se synchronise pas ou une application est dégradée, ou vous ajoutez une application, un environnement ou une étape de promotion. |
| [ibm-cloud-platform](skills/ibm-cloud-platform/SKILL.md) | Conçoit et dépanne l'hébergement sur IBM Cloud (OpenShift/IKS, Code Engine, bases de données, COS, Secrets Manager, Key Protect, VPC, IAM, logs et monitoring) avec la CLI `ibmcloud`, Terraform et Schematics : infrastructure as code, moindre privilège, privé par défaut. Lecture seule, sauf demande. | Vous choisissez ou configurez un service IBM Cloud, écrivez du Terraform, réglez un problème d'accès IAM ou de réseau, ou une commande `ibmcloud` ou un déploiement échoue. |
| [merge-request-review](skills/merge-request-review/SKILL.md) | Fait la revue de tech lead d'une MR GitLab (URL ou `!id`), d'un commit, d'une plage, d'un tag, d'une branche ou des changements locaux : findings classés par gravité avec le scénario d'échec et la correction, vérifiés par des tests quand c'est utile. Ne publie sur GitLab que sur demande. | Avant de fusionner une MR, pour relire le travail d'un collègue ou le vôtre, ou pour évaluer les changements d'une release. |
| [criticize-me](skills/criticize-me/SKILL.md) | Critique sans complaisance un seul commit : approche, justesse, cas limites, sécurité, tests, qualité du commit lui-même. Chaque critique a une preuve, une conséquence et un niveau de confiance. Lecture seule, rien n'est publié. | Avant de soumettre votre commit en revue, pour trouver vous-même ses faiblesses. Indiquez le commit (SHA, `HEAD~1`, tag ou URL). |
| [defend-me](skills/defend-me/SKILL.md) | Construit la défense honnête d'un seul commit : justifie les choix par des preuves, anticipe les objections et les classe réfutées, atténuées ou concédées, propose des corrections rapides, rédige la description de la MR et les réponses aux relecteurs. | Avant une revue de code, un CAB ou une revue d'architecture, ou pour répondre à des commentaires de revue ou à une critique de `criticize-me`. Indiquez le commit. |
| [confluence-documentation](skills/confluence-documentation/SKILL.md) | Rédige ou met à jour des pages Confluence (Cloud ou Data Center) à partir du code et des systèmes réels : ADR, documents de conception, runbooks, guides d'API et d'onboarding, pages de release et de post-mortem. Cherche d'abord les pages existantes ; brouillon d'abord, publication sur demande. | Vous devez documenter une décision, un composant, une procédure d'exploitation, une release ou un incident dans Confluence. |
| [design-system](skills/design-system/SKILL.md) | Extrait le design system réellement utilisé par un frontend (couleurs et quasi-doublons, typographie, espacements, rayons, ombres, composants), mesure l'usage des tokens et les contrastes WCAG, et produit un rapport chiffré, un aperçu de la palette, des tokens en brouillon et un plan de migration. Lecture seule. | Avant de créer ou d'harmoniser un design system, d'introduire des design tokens, ou pour mesurer l'écart entre la charte graphique et le code (Angular, React, Vue ; CSS/SCSS, Tailwind, Material, PrimeNG, MUI). |
| [web-accessibility-eu-fr](skills/web-accessibility-eu-fr/SKILL.md) | Audite, corrige et revoit l'accessibilité selon le RGAA 4.1.2, les WCAG 2.1 et 2.2 AA, l'EN 301 549 et l'European Accessibility Act : résultats axe-core résumés et reliés aux critères, puis vérifications manuelles. N'affirme jamais une conformité sur la seule base des outils automatiques. | Vous devez auditer un parcours ou une application, corriger des défauts d'accessibilité, vérifier qu'une modification n'en introduit pas, ou savoir quelles obligations s'appliquent à votre service. |
| [release-change-management](skills/release-change-management/SKILL.md) | Produit, à partir des vrais changements (plage de tags, de commits ou de MR), les documents d'une release : notes de release métier et techniques, changelog, proposition de version, demande de changement ITIL/ServiceNow (impact, risque, retour arrière), runbook de déploiement, go/no-go et revue post-implémentation. Ne soumet et ne tague rien sans demande. | Vous préparez une mise en production, un passage en CAB, ou devez communiquer le contenu d'une release. |
| [production-incident-investigation](skills/production-incident-investigation/SKILL.md) | Accompagne l'astreinte pendant un incident : limiter l'impact, trouver ce qui a changé, tester les hypothèses à partir des métriques, des logs et des traces, proposer des mitigations avec leur risque, tenir la chronologie en UTC, rédiger les points d'avancement et le post-mortem. Lecture seule en production, sauf accord de l'incident commander. | Un service est en panne ou dégradé en production (erreurs, lenteurs, pods qui redémarrent, base saturée), ou pour rédiger le post-mortem après coup. |
| [project-playbook-java-angular](skills/project-playbook-java-angular/SKILL.md) | Génère ou met à jour le playbook d'onboarding développeur d'un projet Spring Boot + Angular à partir de son code réel : démarrage rapide, architecture, API, conventions, CI/CD, exploitation, dépannage. Chaque fait cite son fichier, aucune valeur secrète n'apparaît, et un aperçu HTML se copie-colle dans Confluence Cloud. | Un nouveau développeur arrive, la documentation du projet manque ou est périmée, ou le code a changé depuis le dernier playbook. |
| [cloud-migration-audit-java-angular](skills/cloud-migration-audit-java-angular/SKILL.md) | Audite ensemble les dépôts backend, frontend et CD/infrastructure d'une application Spring Boot + Angular migrée vers Kubernetes : 93 contrôles prouvés par `fichier:ligne`, risques propres à plusieurs pods (jobs planifiés dupliqués, sessions, état en mémoire, sondes, mémoire JVM, secrets…), décision GO / CONDITIONAL GO / NO-GO, plan d'action et tableau de bord HTML. Lecture seule. | Avant la mise en production d'une application migrée de serveurs on-premise vers Kubernetes (IBM Cloud, Helm, Argo CD, GitLab CI, JFrog), ou pour suivre l'avancement de la migration d'un audit à l'autre. |
| [sql-to-jpa-entities](skills/sql-to-jpa-entities/SKILL.md) | Génère, à partir de scripts SQL Oracle ou PostgreSQL (fichiers ou migrations Flyway/Liquibase), la couche de données d'un projet Spring Boot (Java 21+, Hibernate 6 ou 7) : entités JPA fidèles au schéma (clés simples et composites, séquences et identity, relations `@ManyToOne`, `@OneToOne`, `@ManyToMany`, `@MapsId`, enums, contraintes, `@Version`), DTO records avec la Bean Validation déduite des contraintes, mappers MapStruct ou manuels et repositories Spring Data. Associations LAZY, cascade réservée aux compositions, `equals`/`hashCode` sur l'id. Signale les défauts du schéma (FK sans index, table sans clé primaire, `NUMBER` sans précision) avec leur correctif SQL, et ne remplace jamais un fichier existant modifié. | Vous démarrez un projet Spring Boot sur une base existante, vous reprenez un schéma legacy, ou une migration ajoute des tables à mapper. |

## Modes

| Mode | Description |
|------|-------------|
| [tech-lead-reviewer](modes/README.md) | Revues, audits et estimations sans modifier le code ; ne peut écrire que des rapports de revue. |
| [security-remediator](modes/README.md) | Corrige les findings des scanners de sécurité ; ne peut pas modifier les pipelines CI, ni la configuration des scanners et des politiques. |
| [tech-writer](modes/README.md) | Rédige et met à jour la documentation et les pages Confluence ; ne peut modifier que des fichiers de documentation et ne peut pas lancer de commandes. |

Voir [modes/README.md](modes/README.md) pour l'installation et les réglages d'approbation recommandés.

## Hooks

| Hook | Description |
|------|-------------|
| [secret_guard](hooks/README.md) | Bloque l'écriture d'un secret dans un fichier et les prompts contenant un secret. |
| [command_guard](hooks/README.md) | Bloque les commandes irréversibles (force push, `reset --hard`, `terraform apply`, `kubectl delete`, `DROP TABLE`…). |
| [migration_guard](hooks/README.md) | Interdit de modifier une migration Flyway déjà mergée. |
| [project_context](hooks/README.md) | Injecte la branche, l'état git et les versions de la pile au début de la session. |
| [audit_log](hooks/README.md) | Journal local de chaque action de l'agent, secrets masqués. |
| [notify_done](hooks/README.md) | Notification de bureau quand Bob a terminé. |

Un hook en panne ne bloque jamais Bob. Voir [hooks/README.md](hooks/README.md) pour l'installation.

## Utilisation

Copiez le dossier d'un skill dans le répertoire `.bob/skills/` de votre projet (ou dans `~/.bob/skills/` pour l'utiliser dans tous vos projets) :

```bash
cp -R skills/angular2-developer /chemin/vers/le/projet/.bob/skills/
```

Certains skills ne sont proposés que dans un mode, grâce au champ `groups` de leur frontmatter : Bob n'affiche le skill (dans les skills disponibles et dans les commandes `/`) que si le mode actif porte ce slug ou l'un de ces groupes d'outils. C'est le cas de `security-findings-remediation` (`groups: [security-remediator]`) : installez aussi le mode [security-remediator](modes/README.md), sinon le skill n'apparaît dans aucun mode. Pour le rendre disponible partout, supprimez la ligne `groups`. Le champ `modes`, parfois proposé, est ignoré par Bob (vérifié avec Bob Shell 2.0.6).

### Exemples de prompts

Chaque exemple suit la même structure, tirée des recommandations d'IBM pour Bob (une consigne directe, du contexte, un périmètre précis, ce que Bob doit faire et ne pas faire, le format attendu) :

| Champ | Contenu |
| --- | --- |
| `Task` | Une seule consigne directe, avec son objectif. Une tâche Bob par objectif : ouvrez une nouvelle tâche (**+**) pour le sujet suivant. |
| `Context` | La situation et les faits que Bob ne peut pas deviner : versions, environnement, ticket, symptômes, contraintes métier. |
| `Inputs` | Ce que le skill doit lire : fichiers, dépôts, rapports, URL, commit ou MR. Mentionnez avec `@` les fichiers courts à lire en entier (`@/src/app/x.ts`) ; donnez seulement le chemin des gros rapports et des logs, que le skill lit de façon ciblée. |
| `Access` | Ce que Bob peut utiliser au-delà des fichiers (CLI, cluster, serveur MCP), en lecture seule ou non. |
| `Constraints` | Ce que Bob doit faire et ne pas faire : lecture seule, pas de commit, pas de publication, approbations, limites de version. |
| `Deliverables` | Ce que vous attendez, sous quelle forme et où l'écrire. |
| `Language` | La langue des livrables (et du code s'il y a lieu). |

Ajoutez au besoin des champs propres à la tâche : `Scope` (pages, modules, environnements), `Requirements` ou `Expected behaviour` (critères d'acceptation), `Focus` (points à examiner en priorité), `Output folder`.

Plus le prompt est complet, moins Bob pose de questions, et chaque question coûte un tour. Supprimez les champs sans objet et remplacez les valeurs d'exemple (`payments-api`, `!482`, URL, chemins) par les vôtres. Le mode indiqué est celui à choisir avant d'envoyer le prompt : **Agent** est le mode intégré de Bob qui modifie et exécute ; `tech-lead-reviewer`, `security-remediator` et `tech-writer` sont les [modes du kit](modes/README.md).

**[angular2-developer](skills/angular2-developer/SKILL.md)** : une fonctionnalité dans une application existante, dans le style du projet. Mode : **Agent**.
```text
Task: Add a paginated, sortable transactions table to the account detail page.
Context: Angular application of this workspace. The backend endpoint already exists: GET /api/accounts/{id}/transactions?page=&size=&sort= returns { content: Transaction[], totalElements: number }.
Inputs: @/src/app/accounts/account-detail/account-detail.component.ts and @/src/app/accounts/models/transaction.ts
Requirements: 20 rows per page; sort by date (default, newest first) and by amount; loading, empty and error states; accessible table.
Constraints: follow the project's existing components, state management, UI library and test style; no new dependency; do not commit.
Deliverables: the code changes, unit tests for the new behaviour run and passing, and a short summary of the changes.
Language: code and comments in English; summary in English.
```

**[react-developer](skills/react-developer/SKILL.md)** : une montée de version de React. Mode : **Agent**.
```text
Task: Upgrade this application from React 18 to the latest React 19.
Context: Vite + TypeScript single-page application; current versions in @/package.json. Tests run with Vitest.
Steps: run the official React 19 codemods, fix the type errors and the removed APIs, then run npm run build and npm test.
Constraints: upgrade only React, React DOM and their types, plus what React 19 strictly requires (ask me before any other upgrade); do not commit.
Deliverables: the changes, the build and test results, the list of what changed and of what still needs a manual check in the browser.
Language: English.
```

**[spring-boot-developer](skills/spring-boot-developer/SKILL.md)** : un bug sur un flux financier, reproduit avant d'être corrigé. Mode : **Agent**.
```text
Task: Fix bug PAY-1432: a transfer is sometimes debited twice.
Context: POST /api/transfers debits the account twice when the client retries after a timeout. Clients send an Idempotency-Key header that the service ignores. Production runs 3 replicas on PostgreSQL 15.
Inputs: @/src/main/java/com/acme/payments/transfer/TransferController.java and @/src/main/java/com/acme/payments/transfer/TransferService.java
Expected behaviour: a retry with the same Idempotency-Key returns the original result without a second debit, also when two replicas receive the retries at the same time.
Constraints: reproduce with a failing test first (Testcontainers, as in the project); smallest safe change, with a Flyway migration if a table or a constraint is needed; ask me before changing the public API; do not commit.
Deliverables: the test and the fix, the module tests run, and the technical report (cause, fix, risks, deployment notes).
Language: code in English; report in French.
```

**[sonarqube-java-angular](skills/sonarqube-java-angular/SKILL.md)** : un Quality Gate en échec sur la couverture. Mode : **Agent**.
```text
Task: Make the SonarQube Quality Gate pass on coverage on new code.
Context: gate condition "Coverage on New Code >= 80%", currently 62%, on payments-api (Java 21, Maven, JaCoCo) and payments-ui (Angular, LCOV). New code is the code changed since the tag v2.3.0.
Inputs: payments-api/target/site/jacoco/jacoco.xml and payments-ui/coverage/lcov.info (generated today); no SonarQube API access.
Constraints: only tests with meaningful assertions, following the existing test style; no coverage exclusions; no production code change except a small testability fix that you ask me first; do not commit.
Deliverables: the ranked list of the quickest real gains, the tests for the top five, the coverage before and after measured by rerunning the tests of the touched modules.
Language: English.
```

**[security-findings-remediation](skills/security-findings-remediation/SKILL.md)** : une release bloquée par Nexus IQ. Mode : **`security-remediator`**, le seul où ce skill est proposé.
```text
Task: Unblock the payments-api release blocked by Nexus IQ.
Context: the policy evaluation fails at the release stage on Security-High and License policies. Java 21, Spring Boot 3.3, Maven.
Inputs: the latest policy report in reports/nexus-iq-payments-api.json; the blocking thresholds in the nexus-iq job of @/.gitlab-ci.yml
Constraints: fix the reachable violations with the smallest upgrades (patch or minor; ask me before any major upgrade); never lower a policy or exclude a component; run the build and the tests after each upgrade; do not commit.
Deliverables: the triage table (fix, not exploitable, false positive, decision needed), the dependency changes, a waiver justification with an expiry date for each remaining violation, and what to rescan.
Language: English.
```

**[gitlab-ci-engineer](skills/gitlab-ci-engineer/SKILL.md)** : un pipeline en échec. Mode : **Agent**.
```text
Task: Find why the integration-test job fails and propose the minimal fix.
Context: pipeline https://gitlab.example.com/pay/payments-api/-/pipelines/48211 fails in integration-test since this morning; the same job passed yesterday on the same branch. The pipeline includes the central templates of pay/ci-templates.
Inputs: the job log saved in logs/integration-test-48211.log (glab is not configured) and @/.gitlab-ci.yml
Constraints: start from the first real error, not the last line; do not modify the central templates (if the cause is there, write the change to propose to their owners); never skip, disable or allow_failure a job; do not commit or push.
Deliverables: the cause with the log lines that prove it, the minimal fix as a diff, and how to verify it.
Language: English.
```

**[sql-database-engineer](skills/sql-database-engineer/SKILL.md)** : une requête lente en production. Mode : **Agent**.
```text
Task: Make the account statement query fast again.
Context: PostgreSQL 15; the transactions table holds about 80 million rows. The query takes 12 s in production; target under 300 ms. Flyway migrations are in src/main/resources/db/migration.
Inputs: the query in @/src/main/java/com/acme/payments/statement/TransactionRepository.java (method findStatement) and the production plan in @/docs/perf/statement-plan.txt (EXPLAIN (ANALYZE, BUFFERS))
Constraints: no access to the databases; keep the query's results identical; any index must be created without blocking writes; do not commit.
Deliverables: the plan explained, the chosen index or rewrite with its expected gain and cost, the Flyway migration, and how to verify it on staging.
Language: English.
```

**[argocd-gitops](skills/argocd-gitops/SKILL.md)** : une application Argo CD dégradée après une promotion. Mode : **Agent**.
```text
Task: Find why the Argo CD application payments-api-prod is OutOfSync and Degraded since the last promotion, and propose the fix.
Context: the GitOps repository is ./payments-deploy (Helm chart charts/payments-api, values-prod.yaml); CI promotes by bumping the image tag in the values file.
Access: argocd and kubectl are logged in with read-only rights on the namespace payments-prod.
Constraints: read-only commands only (argocd app get, diff, history; kubectl get, describe, logs, events); no sync, rollback or change on the cluster; the fix is a change in the GitOps repository, not committed.
Deliverables: the cause with its evidence, the Git change and its rendered diff, the expected effect of the sync, and the rollback plan.
Language: English.
```

**[ibm-cloud-platform](skills/ibm-cloud-platform/SKILL.md)** : sortir un secret de Git vers Secrets Manager. Mode : **Agent**.
```text
Task: Move the database password of payments-api from a Kubernetes Secret committed in Git to IBM Cloud Secrets Manager.
Context: enterprise account; Red Hat OpenShift on IBM Cloud, region eu-de, resource group payments-prod. The Secrets Manager instance payments-sm exists. Terraform is in infra/ibm, with its state in the Schematics workspace payments-prod.
Access: the ibmcloud CLI is logged in with read-only roles.
Constraints: read-only on the account (no terraform apply, no Schematics apply); least privilege (trusted profile or service ID); private endpoints only; do not commit.
Deliverables: the target design (how the secret reaches the pods, IAM, network), the Terraform changes, the migration and rollback steps, and how to remove the secret from the Git history.
Language: English.
```

**[merge-request-review](skills/merge-request-review/SKILL.md)** : la revue d'une MR. Sans cible, le skill revoit les changements locaux, puis la branche courante. Mode : **`tech-lead-reviewer`** (ou **Agent**).
```text
Task: Review merge request !482 of payments-api.
Context: the MR adds partial refunds; the business rules are in the ticket linked from the MR. It targets main and includes a database migration.
Access: glab is logged in (read only).
Focus: data integrity and transactions, security, backward compatibility of the public API and of the database migration.
Constraints: check suspected bugs with a test in a separate worktree (never change my working tree); do not post anything on GitLab.
Deliverables: the review: verdict, findings ranked by severity with file:line, failure scenario, suggested fix and verified or suspected status, questions for the author, what is good.
Language: English.
```

**[criticize-me](skills/criticize-me/SKILL.md)** : l'autocritique d'un commit avant de le montrer. Le commit est obligatoire. Mode : **`tech-lead-reviewer`** (ou **Agent**).
```text
Task: Criticize my last commit (HEAD) before I open the merge request.
Context: it adds a retry queue for failed transfer notifications (ticket PAY-1520).
Constraints: read-only; you may run the related unit tests; do not publish anything.
Deliverables: the critique in the skill's format: verdict, findings ranked by severity with evidence, the weakest decision, the questions I must be able to answer.
Language: English.
```

**[defend-me](skills/defend-me/SKILL.md)** : préparer la défense d'un commit avant une revue ou un CAB. Le commit est obligatoire. Mode : **`tech-lead-reviewer`** (ou **Agent**).
```text
Task: Prepare the defence of my last commit (HEAD) for tomorrow's architecture review.
Context: the commit adds a retry queue (a table and a poller) for failed transfer notifications instead of reusing the existing Quartz scheduler, because notifications must survive restarts and be sent by a single replica.
Objections to answer: "Why not reuse Quartz?", "Is the poller safe with 3 replicas?", "Why a new table?"
Constraints: no invented evidence; do not modify the code or commit.
Deliverables: each objection rebutted, mitigated or conceded with its evidence, the quick fixes worth doing before the review, and the MR description.
Language: English.
```

**[confluence-documentation](skills/confluence-documentation/SKILL.md)** : un runbook écrit à partir du code, en brouillon. Mode : **`tech-writer`**.
```text
Task: Write the runbook of the payments-api monthly statement batch.
Context: Confluence Cloud, space PAY, parent page Operations > Runbooks; readers are the on-call engineers.
Inputs: @/payments-api/src/main/java/com/acme/payments/statement/MonthlyStatementJob.java, the CronJob section of payments-deploy/charts/payments-api/values-prod.yaml and the alert rules in payments-deploy/alerts/statement.yaml
Access: the Atlassian MCP server is configured; search for an existing page before writing.
Constraints: every statement traceable to a source; no secret values; do not publish.
Deliverables: the draft page in docs/runbooks/monthly-statement.md, and whether to update an existing page or create a new one.
Language: English (the language of the PAY space).
```

**[design-system](skills/design-system/SKILL.md)** : l'audit du design system réel d'un frontend. Mode : **Agent**.
```text
Task: Extract and audit the real design system of the Angular portal.
Context: Nx monorepo; the portal uses Angular Material and SCSS; there are no brand guidelines and no Figma library.
Inputs: sources in apps/portal/src and libs/ui; exclude generated and third-party code.
Constraints: read-only on the sources.
Deliverables: in docs/design-system: the report (palette with near-duplicates, typography, spacing, token coverage, WCAG contrast failures), the palette preview, the draft tokens and a prioritised migration plan to design tokens.
Language: French.
```

**[web-accessibility-eu-fr](skills/web-accessibility-eu-fr/SKILL.md)** : l'audit RGAA d'un parcours. Mode : **Agent**.
```text
Task: Audit the accessibility of the account opening journey.
Context: public online service of a French bank, covered by the European Accessibility Act; reference RGAA 4.1.2. Angular 18 with Angular Material; the project has Playwright end-to-end tests with @axe-core/playwright.
Scope: /open-account and its four steps, including the error states, at 1280 px and 375 px wide.
Constraints: audit only (no code change); run the application locally and the axe scans; keep the raw results outside the source tree.
Deliverables: the report in docs/a11y/open-account: findings by priority mapped to the RGAA and WCAG criteria, the manual checks done and not done, and the prioritised fixes.
Language: French.
```

**[release-change-management](skills/release-change-management/SKILL.md)** : les documents d'une release, à partir des vrais changements. Mode : **Agent**.
```text
Task: Prepare release 2.4.0 of payments-api.
Context: range v2.3.0..main; production deployment on Saturday from 22:00 to 23:00 (Europe/Paris); use the templates in docs/release-templates if they exist.
Constraints: every statement traced to commits or merge requests; do not create the tag; do not submit the change request.
Deliverables: in docs/releases/2.4.0: version proposal, technical changelog, business release notes, ServiceNow change request (impact, risk, rollback plan), deployment runbook and go/no-go checklist.
Language: English, except the business release notes in French.
```

**[production-incident-investigation](skills/production-incident-investigation/SKILL.md)** : un incident de production en cours. Mode : **Agent**.
```text
Task: Help me investigate an ongoing production incident.
Context: since 14:05 UTC about 30% of payment requests fail with HTTP 504 on payments-api in production (namespace payments-prod, 3 pods). Severity SEV2. I am the incident commander; I post a status update every 30 minutes in the #inc-payments channel.
Access: kubectl and argocd with read-only rights.
Constraints: read-only commands only; propose mitigations with their risk and reversibility; execute nothing that changes production without my explicit approval.
Deliverables: what changed, the hypotheses ranked and tested, the mitigations, a UTC timeline, and the draft of the next status update.
Language: English.
```

**[project-playbook-java-angular](skills/project-playbook-java-angular/SKILL.md)** : le playbook d'onboarding de deux dépôts séparés, à coller dans Confluence. Ouvrez Bob dans le dossier qui contient les deux dépôts. Mode : **Agent** (les scripts du skill doivent pouvoir s'exécuter).
```text
Task: Generate the Confluence developer onboarding playbook of the payments application.
Context: two separate repositories in this folder: ./payments-api (Spring Boot backend) and ./payments-ui (Angular frontend). No playbook exists yet.
Output folder: payments-api/docs/playbook
Source links: payments-api=https://gitlab.example.com/pay/payments-api/-/blob/main, payments-ui=https://gitlab.example.com/pay/payments-ui/-/blob/main
Constraints: do not run builds or tests; do not publish to Confluence; do not commit.
Deliverables: the playbook pages and the HTML preview to copy and paste into Confluence Cloud.
Language: English.
```

**[cloud-migration-audit-java-angular](skills/cloud-migration-audit-java-angular/SKILL.md)** : l'audit de migration vers Kubernetes, avec la décision GO / CONDITIONAL GO / NO-GO. Ouvrez Bob dans le dossier qui contient les trois dépôts. Mode : **Agent** (le skill exécute ses scripts et lance des sous-agents).
```text
Task: Audit the cloud migration of the payments application.
Context: the application moved from two on-premise Tomcat servers to Kubernetes on IBM Cloud (Helm, Argo CD, GitLab CI, JFrog).
Repositories: backend ./payments-api, frontend ./payments-ui, CD/infrastructure ./payments-deploy
Access: repositories only, no live access.
Output folder: ./cloud-migration-audit
Constraints: read-only on the repositories; do not build them or run their scripts.
Deliverables: the five reports (Markdown report, HTML dashboard, findings JSON, action plan, checklist) and the GO / CONDITIONAL GO / NO-GO decision with its reasons.
Language: English.
```

**[sql-to-jpa-entities](skills/sql-to-jpa-entities/SKILL.md)** : la couche JPA d'un schéma existant. Mode : **Agent** (le skill exécute son moteur et compile le projet).
```text
Task: Generate the JPA entities, DTO records, MapStruct mappers and Spring Data repositories for the payments schema.
Context: Spring Boot 3.5 project in this workspace, Java 21, Oracle 19c. The schema is defined by the Flyway migrations; the project already uses MapStruct and does not use Lombok.
Inputs: the migrations folder src/main/resources/db/migration
Requirements: base package com.acme.payments; Oracle DATE columns hold dates only, except the columns ending in _at, which hold a time; no inverse collections other than the compositions.
Constraints: do not modify the migrations or any existing class; run nothing against a database; do not commit.
Deliverables: the sources under src/main/java, a successful ./mvnw -q -DskipTests compile, and the mapping report with the schema warnings and their SQL fixes.
Language: code in English; report in French.
```

### Économiser des bobcoins

Bob renvoie à chaque requête tout son contexte (prompt système, définitions des outils, skills, historique) et facture le contexte complet à chaque tour. Ce qui coûte, c'est donc la taille du contexte et le nombre de tours. Les skills bob-kit sont écrits pour rester courts, lire le code de façon ciblée et confier les lectures larges à des sous-agents (`spawn_subagent`), dont seul le résultat revient dans la tâche. De votre côté, d'après les [recommandations d'IBM](https://bob.ibm.com/docs/ide/core-concepts/context-window-management) :

- une tâche par objectif, et une nouvelle tâche (**+**) dès que le sujet change ;
- des prompts précis qui nomment les fichiers et les fonctions ; des mentions ciblées (`@/src/app/service.ts:45-67`) plutôt que des dossiers entiers ;
- un `AGENTS.md` et des règles courts, sans les répéter dans chaque prompt ;
- seulement les serveurs MCP utiles, configurés au niveau du projet, en désactivant les outils MCP inutilisés : leurs définitions sont envoyées à chaque requête ;
- de petites étapes validées plutôt qu'une longue exécution autonome.

#### Combien coûte un bobcoin ?

**1 bobcoin ≈ 500 000 tokens de contexte.** Mesuré avec Bob Shell 2.0.6 : le coût d'une requête est toujours égal à ses tokens de contexte × 0,000002. Une requête vide coûte déjà 10 000 à 17 000 tokens (≈ 0,02 à 0,03 bobcoin), et une tâche de 20 tours avec 50 000 tokens de contexte en moyenne consomme environ 1 million de tokens, soit 2 bobcoins.

| Offre Bob | Prix par mois | Bobcoins inclus | Prix d'un bobcoin | ≈ Prix d'un million de tokens |
| --- | --- | --- | --- | --- |
| Pro | 20 $ | 50 | 0,40 $ | 0,80 $ |
| Pro+ | 60 $ | 180 | 0,33 $ | 0,67 $ |
| Ultra | 200 $ | 1 000 | 0,20 $ | 0,40 $ |

Prix relevés en octobre 2026 sur [bob.ibm.com/pricing](https://bob.ibm.com/pricing).

## Sécurité

Les skills lisent des dépôts qui ne sont pas toujours de confiance (code d'un fournisseur, clone récent, branche d'un tiers). Les scripts et les hooks sont écrits pour qu'un dépôt piégé ne puisse ni exécuter une commande, ni faire lire un fichier situé hors du dépôt, ni glisser un lien actif dans un document généré.

| Risque | Protection | Où |
| --- | --- | --- |
| Commande exécutée par la configuration git du dépôt analysé (`core.fsmonitor`, hooks), dès un simple `git status` | git est toujours appelé avec `--no-optional-locks -c core.fsmonitor=false -c core.hooksPath=/dev/null` : la ligne de commande l'emporte sur la configuration du dépôt, git n'exécute rien et n'écrit aucun verrou d'index. Liste d'arguments, jamais de shell. | scripts de `cloud-migration-audit-java-angular`, `project-playbook-java-angular` et `release-change-management`, hooks `project_context` et `migration_guard` |
| Lecture de fichiers hors du dépôt via un lien symbolique (clés, configurations d'un autre projet) | les liens dont la cible réelle sort du dossier analysé sont ignorés | audit cloud, playbook, `design-system`, `sonarqube-java-angular`, hook `project_context`, export Confluence |
| Lien `javascript:` ou `data:` dans l'aperçu HTML copié dans Confluence | seuls les liens `http`, `https` et `mailto` sont conservés, quelle que soit la casse ou l'encodage HTML ; les autres deviennent du texte | `project-playbook-java-angular/scripts/confluence_export.py` |
| Paquet ou image téléchargé à la volée par une commande proposée | `npx --no -- ng` n'utilise que la CLI Angular du projet ; les outils `npx` sont épinglés (`esbuild-visualizer@0.7.0`, `depcheck@1.4.7`, `codemod@1.18.6`, `types-react-codemod@3.5.3`) ; l'image Docker de reproduction d'un job GitLab est désignée par son digest | `angular2-developer`, `react-developer`, `security-findings-remediation`, `gitlab-ci-engineer` |

`python3 tools/test_security.py` rejoue ces attaques sur un dépôt piégé (commande `core.fsmonitor`, liens symboliques vers l'extérieur, liens `javascript:`, `data:` et `vbscript:`, en majuscules ou encodés en entités HTML) et vérifie qu'elles restent sans effet tout en gardant les résultats attendus : 17 vérifications, dont 10 échouaient avec le code d'avant ces corrections.

### Scan des skills avec SkillSpector

[SkillSpector](https://github.com/NVIDIA/SkillSpector) (NVIDIA) analyse les skills d'agents : injection de prompt, exfiltration, commandes dangereuses, dépendances non épinglées, code obfusqué… Le kit l'utilise en mode statique (`--no-llm`) : rien n'est envoyé à un modèle, rien ne quitte la machine. Il faut Python 3.12 ou plus. Installez la version v2.13.0, celle qui a servi à établir les baselines (la CI l'installe depuis le commit de ce tag, qui ne peut pas être déplacé) :

```bash
pip install "skillspector @ git+https://github.com/NVIDIA/SkillSpector@v2.13.0"
```

```bash
python3 tools/scan_skills.py --out skillspector-reports
```

Le script scanne chaque skill séparément avec sa baseline `tools/skillspector/<skill>.yaml` (SkillSpector n'accepte pas de baseline dans un scan récursif), affiche le score, les constats actifs, les constats justifiés et la couverture de chaque skill, et échoue sur tout constat qu'aucune baseline ne justifie. Il signale aussi les règles qui ne correspondent plus à rien, pour qu'une baseline ne masque jamais plus que nécessaire.

Résultats avec SkillSpector v2.13.0 en `--no-llm` sur les 19 skills du kit au moment du durcissement :

| | Avant le durcissement | Après le durcissement | Avec les baselines |
| --- | --- | --- | --- |
| Constats | 66 (29 HIGH, 36 MEDIUM, 1 LOW) | 53 (29 HIGH, 24 MEDIUM) | 0 non justifié, 53 justifiés |
| Dépendances non épinglées (RP1) | 12 | 1 (limite du parseur, image épinglée par digest) | 0 |
| Skills avec un score de risque > 50 | 3 | 3 | 0 |

Les 53 constats restants sont des faux positifs ou des limites du mode statique, chacun justifié dans la baseline de sa skill :

- **Contrôles et motifs de détection** : l'audit cloud cherche lui-même `curl | sh`, `chmod 777`, `.npmrc` copié dans une image, `hostPath`, des jetons d'accès… Le scanner y lit les pratiques que le skill dénonce.
- **Interdictions et points de revue** : « never disable verification », « do not introduce a new library without asking », `bypassSecurityTrust*` à retirer, requêtes non bornées à signaler, kubeconfigs à ne jamais afficher.
- **Appels git en lecture** (AST4) : les appels `subprocess` passent par la commande git durcie décrite plus haut.
- **Pas de périmètre d'outils déclaré** (LP3) : Bob ne lit pas `allowed-tools` dans le frontmatter ; l'accès aux outils est réglé par les modes et les approbations de Bob.
- **Inspection partielle** (AE1) : en `--no-llm`, la couche déterministe s'arrête sur les scripts riches en expressions régulières et sur un long modèle de pages (couverture de 57 à 80 % pour `project-playbook-java-angular`, `cloud-migration-audit-java-angular` et `design-system`).

Une règle de baseline cible un identifiant de règle, un fichier et le texte trouvé (quand le constat en a un), avec une raison obligatoire ; jamais un identifiant seul. Un nouveau constat, même de même type dans un autre fichier, fait donc échouer le scan. Quand vous montez la version de SkillSpector, relancez le scan et revoyez les baselines.

Limites : SkillSpector ne remplace pas la revue. Les trois vulnérabilités corrigées plus haut (fsmonitor, liens symboliques, liens `javascript:`) n'étaient pas détectées par le scanner : elles ont été trouvées en relisant le code. Avant une release, complétez le scan statique par un scan avec LLM (`skillspector scan skills/<skill>` avec un fournisseur configuré, voir `skillspector scan --help`), qui inspecte aussi les fichiers que le mode statique ne couvre qu'en partie ; le contenu des skills est alors envoyé à ce fournisseur.

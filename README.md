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

Écrivez votre demande normalement : Bob choisit le skill d'après sa description. Un bon prompt nomme la cible (dossiers, fichiers, commit, MR, rapport), la langue des livrables et les limites (lecture seule, pas de commit, pas de publication) : chaque question que Bob doit poser coûte un tour. Les exemples ci-dessous sont en anglais et Bob répond dans la langue du prompt ; remplacez les noms (`payments-api`, `payments-ui`, `!482`…) par les vôtres.

**[angular2-developer](skills/angular2-developer/SKILL.md)** : une fonctionnalité dans une application existante, dans le style du projet.
```text
Add a paginated, sortable transactions table to the account detail page (src/app/accounts/account-detail), fed by GET /api/accounts/{id}/transactions. Follow the project's existing components, state management and test style, add unit tests and run them. Do not commit.
```

**[react-developer](skills/react-developer/SKILL.md)** : une montée de version de React.
```text
Upgrade this app from React 18 to React 19: run the official codemods, fix the type errors and the removed APIs, then run the build and the tests. List what changed and what still needs a manual check. Do not commit.
```

**[spring-boot-developer](skills/spring-boot-developer/SKILL.md)** : un bug sur un flux financier, reproduit avant d'être corrigé.
```text
Bug PAY-1432: POST /api/transfers sometimes debits the account twice when the client retries after a timeout. Reproduce it with a test, fix it with the smallest safe change, run the module's tests and give me the technical report. Do not commit.
```

**[sonarqube-java-angular](skills/sonarqube-java-angular/SKILL.md)** : un Quality Gate en échec sur la couverture.
```text
The SonarQube Quality Gate fails on new code coverage (62% instead of 80%) in payments-api and payments-ui. Use the existing reports target/site/jacoco/jacoco.xml and coverage/lcov.info, rank the quickest real coverage gains, write the tests for the top five and report the coverage before and after.
```

**[security-findings-remediation](skills/security-findings-remediation/SKILL.md)** : une release bloquée par Nexus IQ. À lancer dans le mode [security-remediator](modes/README.md), le seul où ce skill est proposé.
```text
The release is blocked by Nexus IQ: the policy report is in reports/nexus-iq-payments-api.json. Triage the violations, fix the reachable ones with the smallest dependency upgrades (ask me before any major upgrade), draft waiver justifications for the rest and tell me what to rescan.
```

**[gitlab-ci-engineer](skills/gitlab-ci-engineer/SKILL.md)** : un pipeline en échec.
```text
Pipeline https://gitlab.example.com/pay/payments-api/-/pipelines/48211 fails in the integration-test job since this morning. Find the first real error in the job log, explain the cause and propose the minimal fix. Do not modify the central templates and do not skip any security job.
```

**[sql-database-engineer](skills/sql-database-engineer/SKILL.md)** : une requête lente en production.
```text
The account statement query takes 12 s in production on PostgreSQL 15: the SQL is in TransactionRepository.findStatement and the EXPLAIN (ANALYZE, BUFFERS) output is in docs/perf/statement-plan.txt. Explain the plan, propose the index or the rewrite, and write the Flyway migration that creates the index without blocking writes.
```

**[argocd-gitops](skills/argocd-gitops/SKILL.md)** : une application Argo CD dégradée après une promotion.
```text
The Argo CD application payments-api-prod has been OutOfSync and Degraded since the last promotion. Find the cause with read-only argocd and kubectl commands, then propose the fix as a change in the GitOps repository. No change on the cluster.
```

**[ibm-cloud-platform](skills/ibm-cloud-platform/SKILL.md)** : sortir un secret de Git vers Secrets Manager.
```text
Our Spring Boot app on Red Hat OpenShift on IBM Cloud reads its database password from a Kubernetes Secret committed in Git. Propose how to move it to Secrets Manager (IAM, service ID or trusted profile, private endpoint) and write the Terraform changes in infra/ibm. Read-only on the account: do not apply anything.
```

**[merge-request-review](skills/merge-request-review/SKILL.md)** : la revue d'une MR. Sans cible, le skill revoit les changements locaux, puis la branche courante.
```text
Review !482 in payments-api. Focus on data integrity, security and API backward compatibility, and check suspected bugs with a test in a separate worktree. Do not post anything on GitLab.
```

**[criticize-me](skills/criticize-me/SKILL.md)** : l'autocritique d'un commit avant de le montrer. Le commit est obligatoire.
```text
Criticize commit 3f9c2ab. I want every real weakness before my team sees it.
```

**[defend-me](skills/defend-me/SKILL.md)** : préparer la défense d'un commit avant une revue ou un CAB. Le commit est obligatoire.
```text
Defend HEAD for tomorrow's architecture review: the reviewers will ask why I added a retry queue instead of reusing the existing scheduler. Prepare the rebuttals, the quick fixes worth doing before the review and the MR description.
```

**[confluence-documentation](skills/confluence-documentation/SKILL.md)** : un runbook écrit à partir du code, en brouillon.
```text
Write the runbook of the payments-api monthly statement batch (MonthlyStatementJob, its Helm values and alerts) for the PAY space, under Operations > Runbooks, in English. Look for an existing page first. Draft only: do not publish.
```

**[design-system](skills/design-system/SKILL.md)** : l'audit du design system réel d'un frontend.
```text
Extract and audit the real design system of the Angular portal (sources in apps/portal/src and libs/ui). I want the palette with its near-duplicates, the WCAG contrast failures and a prioritised plan to move to design tokens. Write the deliverables in docs/design-system, in French.
```

**[web-accessibility-eu-fr](skills/web-accessibility-eu-fr/SKILL.md)** : l'audit RGAA d'un parcours.
```text
Audit the accessibility of the account opening journey (/open-account, four steps, desktop and mobile) against RGAA 4.1.2. Use axe-core through the project's Playwright tests if available, then the manual checks. Read-only: write the report in docs/a11y, in French.
```

**[release-change-management](skills/release-change-management/SKILL.md)** : les documents d'une release, à partir des vrais changements.
```text
Prepare release 2.4.0 of payments-api from tag v2.3.0 to main: technical changelog, business release notes in French, version proposal, and the ServiceNow change request with risk, rollback plan and deployment runbook for the Saturday 22:00 window. Do not create the tag.
```

**[production-incident-investigation](skills/production-incident-investigation/SKILL.md)** : un incident de production en cours.
```text
Incident in progress: since 14:05 UTC about 30% of payment requests fail with HTTP 504 on payments-api in production. I am the incident commander. Help me find what changed and test hypotheses with read-only commands, propose mitigations with their risk, and keep a UTC timeline.
```

**[project-playbook-java-angular](skills/project-playbook-java-angular/SKILL.md)** : le playbook d'onboarding de deux dépôts séparés, à coller dans Confluence. Ouvrez Bob dans le dossier qui contient les deux dépôts.
```text
Generate the Confluence developer onboarding playbook for the payments application: backend ./payments-api (Spring Boot) and frontend ./payments-ui (Angular), two separate repositories. Language: English. Output folder: payments-api/docs/playbook. Do not run builds or tests, do not publish to Confluence, do not commit.
```

**[cloud-migration-audit-java-angular](skills/cloud-migration-audit-java-angular/SKILL.md)** : l'audit de migration vers Kubernetes, avec la décision GO / CONDITIONAL GO / NO-GO. Ouvrez Bob dans le dossier qui contient les trois dépôts.
```text
Audit the cloud migration of the payments application: backend ./payments-api, frontend ./payments-ui, CD/infrastructure ./payments-deploy (Helm, Argo CD, GitLab CI). Repositories only, no live access. Write the reports in English to ./cloud-migration-audit.
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

#### Bob et Claude Code : deux logiques de facturation

| | IBM Bob | Claude Code |
| --- | --- | --- |
| Ce que vous payez | Un abonnement avec un stock de bobcoins par mois, puis un dépassement optionnel | Un abonnement avec des limites d'usage (par fenêtre de 5 heures et par semaine), ou l'API à l'usage |
| Abonnements | Pro 20 $, Pro+ 60 $, Ultra 200 $ | Pro 20 $, Max à partir de 100 $ |
| Prix d'un million de tokens d'entrée | ≈ 0,40 à 0,80 $ selon l'offre | API : 2 $ (Sonnet 5.5) ou 4 $ (Opus 5.5) |
| Contexte renvoyé à chaque tour | Refacturé au même tarif | API : relu depuis le cache à 0,20 $ le million |
| Choix du modèle | Automatique (Bob choisit) | Au choix |

Dans les deux cas, réduire le contexte et le nombre de tours reste le levier principal. Prix relevés en octobre 2026 sur [bob.ibm.com/pricing](https://bob.ibm.com/pricing) et [claude.com/pricing](https://claude.com/pricing) ; le prix des tokens de sortie dans Bob n'est pas publié et n'a pas pu être mesuré.

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

[SkillSpector](https://github.com/NVIDIA/SkillSpector) (NVIDIA) analyse les skills d'agents : injection de prompt, exfiltration, commandes dangereuses, dépendances non épinglées, code obfusqué… Le kit l'utilise en mode statique (`--no-llm`) : rien n'est envoyé à un modèle, rien ne quitte la machine. Il faut Python 3.12 ou plus ; la version est épinglée par son commit, comme en CI :

```bash
pip install "skillspector @ git+https://github.com/NVIDIA/SkillSpector@091a509b3d6ba8ff5be528966e1f43c2e68cf214"
```

```bash
python3 tools/scan_skills.py --out skillspector-reports
```

Le script scanne chaque skill séparément avec sa baseline `tools/skillspector/<skill>.yaml` (SkillSpector n'accepte pas de baseline dans un scan récursif), affiche le score, les constats actifs, les constats justifiés et la couverture de chaque skill, et échoue sur tout constat qu'aucune baseline ne justifie. Il signale aussi les règles qui ne correspondent plus à rien, pour qu'une baseline ne masque jamais plus que nécessaire. Le job `skillspector` de la CI fait la même chose à chaque push et conserve les rapports JSON.

Résultats avec SkillSpector v2.13.0 en `--no-llm` sur les 19 skills :

| | Avant (commit `740eb7f`) | Après durcissement | Avec les baselines |
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

## Contribuer

Avant chaque commit, la validation du kit et les tests (hooks, moteur de l'audit cloud, sécurité) tournent automatiquement si vous activez le hook git du dépôt (une fois par clone) :

```bash
git config core.hooksPath tools/git-hooks
```

Les mêmes vérifications tournent en CI à chaque push (`.github/workflows/validate.yml`), avec en plus le scan SkillSpector. Pour les lancer à la main : `python3 tools/validate_kit.py`, `python3 tools/test_hooks.py`, `python3 tools/test_cloud_audit.py`, `python3 tools/test_security.py`, puis `python3 tools/scan_skills.py` si SkillSpector est installé.

Si vous modifiez un skill et que le scan signale un constat, corrigez le skill ; si c'est un faux positif, ajoutez une règle ciblée avec sa raison dans `tools/skillspector/<skill>.yaml`.

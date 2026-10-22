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
  release-change-management/
  production-incident-investigation/
modes/           # modes Bob personnalisés (custom_modes.yaml)
hooks/           # lifecycle hooks Bob (scripts Python + settings.example.json)
tools/           # validation du kit, tests des hooks, hook git pre-commit
```

## Skills

| Skill | Description |
|-------|-------------|
| [angular2-developer](skills/angular2-developer/SKILL.md) | Développer, revoir, déboguer et migrer des applications Angular (v18 → dernière version). Lit d'abord l'`AGENTS.md`, les règles, la configuration lint et le code existant du projet, et suit leurs conventions. Ne charge qu'un fichier annexe par tâche pour limiter la consommation de tokens, et ne commite jamais sans demande. |
| [react-developer](skills/react-developer/SKILL.md) | Développer, revoir, déboguer, tester et migrer des applications React 18 → dernière version (Vite, Next.js, React Router) en TypeScript. Lit d'abord les règles, la configuration lint et le code existant du projet ; tient compte des versions (API de React 19.x, React Compiler, API supprimées) ; un fichier annexe par tâche ; ne commite jamais sans demande. |
| [spring-boot-developer](skills/spring-boot-developer/SKILL.md) | Ingénieur Java 17–21 et Spring Boot de niveau Senior/Staff pour les systèmes d'entreprise et bancaires : fonctionnalités, corrections de bugs, refactoring sûr de code legacy, revue d'architecture et de code, tests JUnit 5/Mockito/Testcontainers, qualité SonarQube, performance JPA/SQL et migrations de versions. Adapte la rigueur à la tâche, suit les conventions du projet, ne commite jamais sans demande et termine par un rapport technique priorisé. |
| [sonarqube-java-angular](skills/sonarqube-java-angular/SKILL.md) | Améliore les résultats SonarQube des projets Java/Spring Boot et Angular avec le meilleur rapport impact/effort : d'abord le Quality Gate et les vrais risques de sécurité et de fiabilité, puis les gains de couverture rapides identifiés par `scripts/coverage_hotspots.py` (classement JaCoCo/LCOV), des corrections minimales et sûres des issues et la revue des hotspots, mesurés avant et après. Sans manipulation des métriques. |
| [security-findings-remediation](skills/security-findings-remediation/SKILL.md) | Trier et corriger les findings Fortify (SAST), Nexus IQ (dépendances, licences) et Sysdig (images, posture, runtime) : d'abord ce qui bloque les releases et ce qui est exploitable, des corrections en masse par montée de version des dépendances ou des images de base, des corrections de code minimales, des dérogations justifiées pour l'équipe sécurité et la preuve par un nouveau scan. Ne contourne jamais le scanner. |
| [gitlab-ci-engineer](skills/gitlab-ci-engineer/SKILL.md) | Diagnostiquer les pipelines GitLab en échec à partir des logs des jobs, et écrire ou améliorer le `.gitlab-ci.yml` des projets Java/Spring Boot, Angular/React et conteneurs : rules, DAG, caches, artifacts, templates/components, étapes de sécurité et promotion GitOps vers Argo CD. Respecte les templates centraux et la gouvernance ; ne contourne jamais les gates et ne divulgue aucun secret. |
| [sql-database-engineer](skills/sql-database-engineer/SKILL.md) | Oracle et PostgreSQL pour les applications Java d'entreprise : optimisation des requêtes à partir des plans d'exécution et indexation, migrations Flyway/Liquibase sans interruption de service, problèmes de verrous, de deadlocks et d'isolation, SQL et PL/SQL/PL/pgSQL, et migration d'Oracle vers PostgreSQL avec les pièges sémantiques qui changent les résultats en silence. Lecture seule sur les bases partagées, sauf demande. |
| [argocd-gitops](skills/argocd-gitops/SKILL.md) | Argo CD sur Kubernetes/OpenShift : diagnostiquer les applications OutOfSync, Degraded ou Progressing et les échecs de synchronisation ; écrire des Applications, des ApplicationSets, des values Helm et des overlays Kustomize ; promouvoir le même artefact d'un environnement à l'autre et revenir en arrière avec `git revert`. Bonnes pratiques pour les workloads Spring Boot et Angular. Modifie Git, pas le cluster ; accès au cluster en lecture seule, sauf demande. |
| [ibm-cloud-platform](skills/ibm-cloud-platform/SKILL.md) | IBM Cloud pour les applications Java/Angular d'entreprise : OpenShift/IKS, Code Engine, Registry, Databases for PostgreSQL, COS, Secrets Manager, Key Protect/HPCS, Event Streams, VPC, IAM, trusted profiles, context-based restrictions, Cloud Logs et Monitoring, via la CLI ibmcloud, Terraform et Schematics. Infrastructure as code d'abord, moindre privilège, privé par défaut, lecture seule sauf demande. |
| [merge-request-review](skills/merge-request-review/SKILL.md) | Revue de tech lead d'une MR GitLab (URL ou `!id`), d'un commit, d'une plage ou d'une URL de compare, d'un tag ou d'une plage de release, d'une branche ou des changements locaux non commités. Findings classés par gravité avec scénario d'échec et correction, vérifiés dans un worktree isolé si utile ; réutilise les checklists des autres skills ; ne publie sur GitLab que sur demande. |
| [criticize-me](skills/criticize-me/SKILL.md) | Autocritique impitoyable et logique d'un seul commit (obligatoire : SHA, `HEAD~n`, tag ou URL de commit). Attaque l'approche, la justesse, les tests et le commit lui-même ; chaque critique a une preuve, une conséquence et un niveau de confiance ; aucune formule d'adoucissement, aucun problème inventé ; lecture seule et jamais publiée nulle part. |
| [defend-me](skills/defend-me/SKILL.md) | Le pendant de criticize-me : la défense honnête la plus solide d'un seul commit (obligatoire) avant une revue de code, un CAB ou une revue d'architecture. Justifie les décisions par des preuves vérifiables, anticipe les objections (ou répond aux commentaires de revue fournis, ou à une critique de criticize-me) en les classant réfutées, atténuées ou concédées, propose des corrections rapides avant la revue, et rédige la description de la MR et les réponses. N'invente jamais de preuve. |
| [confluence-documentation](skills/confluence-documentation/SKILL.md) | Documentation technique dans Confluence (Cloud ou Data Center) : ADR, documents de conception, runbooks, guides d'intégration, onboarding, pages de release et de post-mortem, rédigés à partir du code et des systèmes réels. Cherche et met à jour les pages existantes avant d'en créer de nouvelles ; propriétés de page, labels et macros ; checklist avant publication ; brouillons d'abord, publication uniquement sur demande. |
| [design-system](skills/design-system/SKILL.md) | Extraire et auditer le design system réel d'un frontend existant (Angular, React, Vue ; CSS/SCSS, Tailwind, Material, PrimeNG, MUI) : palette avec regroupement des quasi-doublons (OKLab) et rôles, typographie, espacements, rayons, élévation, couverture en tokens, contrastes WCAG, composants. Fournit un rapport chiffré, un aperçu de la palette (HTML), des tokens W3C DTCG en brouillon et un plan de migration priorisé grâce à `scripts/extract_design_tokens.py`. Lecture seule. |
| [release-change-management](skills/release-change-management/SKILL.md) | Notes de release (métier et techniques), changelog, proposition de version, demande de changement ITIL/ServiceNow avec impact, risque et plan de retour arrière, runbook de déploiement, go/no-go et revue post-implémentation, construits à partir des vrais changements avec `scripts/release_changes.py` (plage git → changements groupés, MR, ruptures de compatibilité, fichiers à risque). Prépare ; ne soumet et ne tague jamais sans demande. |
| [production-incident-investigation](skills/production-incident-investigation/SKILL.md) | Support d'astreinte pour les incidents de production sur Java/Spring Boot, Angular/React, Kubernetes/OpenShift, Oracle/PostgreSQL et IBM Cloud : limiter l'impact d'abord, trouver ce qui a changé, tester les hypothèses à partir des métriques, des logs, des traces et des preuves JVM et base de données, proposer des mitigations sûres, tenir une chronologie en UTC, rédiger les points d'avancement et un post-mortem sans recherche de coupable. Lecture seule en production, sauf accord de l'incident commander. |

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

## Contribuer

Avant chaque commit, la validation du kit et les tests des hooks tournent automatiquement si vous activez le hook git du dépôt (une fois par clone) :

```bash
git config core.hooksPath tools/git-hooks
```

Les mêmes vérifications tournent en CI à chaque push (`.github/workflows/validate.yml`). Pour les lancer à la main : `python3 tools/validate_kit.py` puis `python3 tools/test_hooks.py`.

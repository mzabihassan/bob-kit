# Modes bob-kit

Des modes personnalisés pour IBM Bob, définis dans [`custom_modes.yaml`](custom_modes.yaml). Un mode fixe le rôle de Bob et les groupes d'outils qu'il peut utiliser ; le savoir-faire vient des skills bob-kit, installez-les donc aussi.

| Mode | Rôle | Groupes d'outils |
| --- | --- | --- |
| 🧭 `tech-lead-reviewer` | Revues (MR, commit, branche, plage de tags, changements locaux), audits, analyses d'impact et estimations, sans modifier le code | `read`, `edit` **uniquement pour les rapports de revue** (`reviews/*.md`, `docs/reviews/*.md`, `*REVIEW*.md`), `execute`, `mcp`, `skill`, `todo`, `mode` |
| 🛡️ `security-remediator` | Corrige les findings de sécurité Fortify, Nexus IQ, Sysdig et SonarQube | `read`, `edit` **sauf** les pipelines CI (`.gitlab-ci.yml`, `.gitlab/`, `.github/`, `Jenkinsfile`), la configuration des scanners et des politiques (`sonar-project.properties`, fichiers Fortify) et `.bob/`, `execute`, `mcp`, `skill`, `todo` |
| 📘 `tech-writer` | Rédige et met à jour la documentation du dépôt et de Confluence (via le serveur MCP), sans toucher au code | `read`, `edit` **uniquement pour la documentation** (Markdown, AsciiDoc, reStructuredText, diagrammes sous `docs/` ; jamais `AGENTS.md`, `CLAUDE.md` ni `.bob/`), `mcp`, `skill`, `todo`, `mode`. **Pas d'`execute`** : les commandes documentées sont marquées comme non vérifiées |

L'accès à Confluence pour `tech-writer` nécessite un serveur MCP Atlassian configuré dans Bob : le serveur MCP Rovo d'Atlassian pour Cloud, ou `mcp-atlassian` pour Cloud ou Data Center.

Les restrictions `fileRegex` sont testées sur des chemins d'exemple autorisés et refusés (`tools/mode_regex_cases.json`, vérifiés par `tools/validate_kit.py`).

## Installation

Modes du projet (partagés avec l'équipe via git) :

```bash
mkdir -p .bob && cp modes/custom_modes.yaml .bob/custom_modes.yaml   # ou fusionnez seulement les entrées voulues dans un fichier existant
```

Modes globaux : fusionnez les entrées dans `~/.bob/settings/custom_modes.yaml` (Paramètres → Modes → Edit Global Modes). Un mode du projet remplace un mode global de même slug. Des règles propres à un mode peuvent être ajoutées dans `.bob/rules-tech-lead-reviewer/`, `.bob/rules-security-remediator/` ou `.bob/rules-tech-writer/` (fichiers chargés par ordre alphabétique).

## Limiter les commandes

Un mode peut seulement autoriser ou refuser tout le groupe `execute` ; il ne peut pas choisir *quelles* commandes s'exécutent. `tech-lead-reviewer` et `security-remediator` ont besoin d'`execute` (pour récupérer les MR, builder, tester et scanner) : leurs instructions demandent donc de se limiter aux commandes de lecture, de build et de test. Pour l'imposer, utilisez les réglages d'approbation de Bob dans `~/.bob/settings/settings.json`. Ils s'appliquent à **tous les modes** : gardez-les compatibles avec votre travail habituel. Par exemple :

```json
"approval": {
  "allowed_permissions": ["read", "skill", "todo", "mode"],
  "allowedExecutors": [{
    "toolId": "execute_command",
    "approvedCommands": ["git status", "git log", "git show", "git diff", "git fetch", "git worktree",
                         "glab mr view", "glab mr diff", "glab ci status", "./mvnw", "mvn", "./gradlew", "npm test", "npm ls"],
    "deniedCommands": ["git push", "git commit", "git merge", "git rebase", "git reset", "glab mr merge", "glab mr approve",
                       "kubectl delete", "kubectl apply", "argocd app sync", "rm -rf"]
  }]
}
```

Dans cet exemple, `mcp` ne figure pas dans `allowed_permissions` : chaque appel MCP, y compris la création ou la mise à jour de pages Confluence par `tech-writer`, demande donc toujours une confirmation. Gardez ce réglage, sauf si vous acceptez des écritures sans relecture.

Les commandes approuvées s'exécutent sans confirmation ; toute autre commande demande votre accord ; les commandes refusées le sont toujours (le refus l'emporte). Vérifiez le schéma actuel dans la [documentation des réglages d'approbation](https://bob.ibm.com/docs/shell/configuration/approval-settings).

Pour un contrôle plus fin que ces préfixes de commande (par exemple bloquer `git push --force` mais pas `git push`), utilisez le hook [`command_guard`](../hooks/README.md).

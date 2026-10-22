# Hooks bob-kit

Des [lifecycle hooks](https://bob.ibm.com/docs/ide/configuration/lifecycle-hooks) pour IBM Bob. Là où les skills et les modes sont des **consignes** que le modèle suit, un hook est **déterministe** : un script exécuté à chaque événement, qui peut bloquer une action.

| Hook | Événement | Rôle |
| --- | --- | --- |
| `secret_guard.py` | `PreToolUse` (écritures de fichiers) et `UserPromptSubmit` | Bloque l'écriture d'un secret dans un fichier (clé privée, tokens GitLab, GitHub, Atlassian, Slack ou AWS, clé d'API IBM Cloud, JWT, identifiants dans une URL, mot de passe en clair dans un fichier de configuration) et bloque un prompt contenant un secret avant son envoi au modèle. La valeur n'est jamais réaffichée |
| `command_guard.py` | `PreToolUse` (`execute_command`) | Bloque les commandes irréversibles : force push, `git reset --hard`, `git clean -f`, `rm -rf` hors du projet, `terraform apply/destroy`, `kubectl`/`oc` en écriture (sauf `--dry-run`), `helm uninstall`, `argocd app delete`, suppressions IBM Cloud, `DROP`/`TRUNCATE`/`DELETE` sans `WHERE`, publication d'artefacts, `curl … \| sh`, `sudo` |
| `migration_guard.py` | `PreToolUse` (écritures de fichiers) | Interdit de modifier une migration Flyway versionnée (`V…__….sql`) déjà présente sur la branche par défaut. Créer une nouvelle migration, modifier une migration encore propre à la branche ou une migration répétable `R__` reste permis |
| `project_context.py` | `SessionStart` | Ajoute au contexte la branche, l'état git, les versions détectées (Java, Spring Boot, Angular, React, TypeScript, Node) et les fichiers d'instructions présents |
| `audit_log.py` | `PostToolUse` | Journal JSONL de chaque action de l'agent (heure UTC, outil, fichier, commande avec secrets masqués), dans `~/.bob/audit/<projet>.jsonl` ou `$BOBKIT_AUDIT_DIR`. Les sorties des outils ne sont pas enregistrées |
| `notify_done.py` | `Stop` | Notification de bureau quand Bob a terminé (macOS, Linux, Windows avec BurntToast) |

## Installation (2 minutes)

Prérequis : `python3` (bibliothèque standard uniquement).

Pour un projet :

```bash
mkdir -p .bob/hooks && cp hooks/*.py .bob/hooks/
```

Puis ajoutez le bloc `hooks` de [`settings.example.json`](settings.example.json) dans `.bob/settings.json` (fusionnez-le s'il existe déjà) et ne gardez que les hooks voulus.

Pour tous vos projets : copiez les scripts dans `~/.bob/hooks/`, ajoutez le bloc dans `~/.bob/settings/settings.json`, et remplacez `.bob/hooks/` par `~/.bob/hooks/` dans les commandes. Les hooks globaux s'exécutent toujours ; ceux du projet s'y ajoutent.

## Et si un hook ne fonctionne pas ?

**Il ne bloque pas Bob.** Seul le code de sortie `2` bloque une action, et seulement pour `PreToolUse` et `UserPromptSubmit`. Tout autre échec est journalisé puis ignoré. Ces scripts attrapent leurs propres erreurs et renvoient `0` : un bug laisse passer l'action, il ne la bloque pas. En contrepartie, un garde cassé ne protège plus : vérifiez-les avec les tests ci-dessous après chaque modification. Les messages de blocage sont écrits sur la sortie d'erreur, donc dans les logs de Bob.

## Personnaliser

- **Faux secret volontaire** (fixture de test) : ajoutez `bob-allow-secret` sur la ligne.
- **Règles de commandes** : la liste `RULES` en tête de `command_guard.py`.
- **Mode strict git** : avec `BOBKIT_STRICT_GIT=1` dans l'environnement de Bob, `git commit` et `git push` sont aussi bloqués.
- **Noms d'outils** : la doc Bob ne cite que `write_file`. Le matcher couvre aussi `write_to_file`, `apply_diff`, `search_and_replace` et `insert_content` ; ajustez-le si votre version de Bob utilise d'autres noms.

## Tester

```bash
python3 tools/test_hooks.py
```

Les tests envoient aux scripts les mêmes JSON que Bob et vérifient les codes de sortie : secrets en écriture et dans les prompts, commandes dangereuses et commandes légitimes, migrations dans un vrai dépôt git, contexte projet, masquage dans le journal d'audit, et comportement en cas d'entrée invalide (toujours `0`).

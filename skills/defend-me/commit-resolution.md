# Resolving the commit

## Accepted inputs

| Input | Resolution |
| --- | --- |
| SHA (full or ≥ 7 chars), `HEAD`, `HEAD~n`, branch tip, tag | `git rev-parse --verify --quiet "<ref>^{commit}"`: fails for unknown refs and for objects that are not commits |
| GitLab URL `…/<group>/<project>/-/commit/<sha>` or GitHub URL `…/<owner>/<repo>/commit/<sha>` | Take the SHA; if the project matches the local `origin`, `git fetch origin <sha>` when it is missing locally; otherwise read it through `glab api` / `gh api` (`/projects/:id/repository/commits/<sha>` and `/diff`, or `/repos/<owner>/<repo>/commits/<sha>`) |
| A range (`a..b`) or several SHAs | Not accepted as is: ask which single commit, or defend them one by one on request |
| Nothing, "my changes", a branch name meant as "everything on it" | Ask for one commit; do not guess |

## Reading the commit

```bash
c=$(git rev-parse --verify --quiet "<ref>^{commit}") || echo "not a commit"
git rev-list --parents -n 1 "$c"                     # number of parents: 0 = root, 1 = normal, 2+ = merge
git show --stat --format='%H%n%an <%ae>%n%ad%n%n%B' "$c"   # message and files
git show --format= "$c"                              # full diff (normal and root commits)
git diff "$c^1" "$c"                                 # merge commits: plain `git show` can print an EMPTY diff for a clean merge
git show "$c:path/to/File.java"                      # the file as it is in the commit
git log --oneline -10 -- path/to/File.java           # recent history of a touched file
git log -1 --format=%B "$c" | grep -iE 'refs?|fix(es)?|close[sd]?|#[0-9]+|[A-Z]+-[0-9]+'   # linked issue references
```

For a merge commit, defend what the merge brings into the first parent (conflict resolutions included) and say that this is what is defended.

To run tests or the build on the commit without touching the user's working tree:

```bash
git worktree add <scratch-dir>/defend-$c "$c"
# … run the relevant tests there …
git worktree remove <scratch-dir>/defend-$c
```

# Resolving what to review

All commands below are read-only for the user's working tree. Prefer `glab` when it is authenticated, the GitLab API with a token from the environment otherwise, and plain `git` for local data.

## Recognise the input

| Input | Example | Review |
| --- | --- | --- |
| MR URL | `https://gitlab.example.com/group/sub/app/-/merge_requests/123` | Project `group/sub/app`, MR `123` |
| MR reference | `!123`, "MR 123" | MR 123 in the current project (from `git remote get-url origin`) |
| Commit | `4f2c9e1…`, `…/-/commit/<sha>` | That commit (`git show <sha>`) |
| Range or compare | `a..b`, `a...b`, `…/-/compare/v1.2.0...main` | Commits in the range; diff from the merge base |
| Tag | `v1.4.0` | The tag against the previous tag: `git describe --tags --abbrev=0 v1.4.0^` |
| Tag range | `v1.3.0..v1.4.0` | Everything released between the two tags (pre-release review) |
| Branch | `feature/payment-limits`, `…/-/tree/<branch>` | The branch against its MR's target, or the default branch, from the merge base |
| Nothing | — | 1. Local changes (`git status`, `git diff`, `git diff --staged`, new untracked files). 2. If clean, the current branch against its open MR or the default branch. 3. If the current branch *is* the default branch with nothing local, ask |

If the URL's host or project does not match the local `origin`, work through `glab --repo <group/project>` or the API instead of the local clone.

## Merge requests

```bash
glab mr view 123 [--comments]          # title, description, target branch, labels, approvals, discussions
glab mr diff 123                       # the diff
glab ci status --branch <source-branch> # or the MR's pipelines
git fetch origin "merge-requests/123/head:refs/remotes/origin/mr/123"   # the MR's head without switching branches
git diff --stat origin/<target>...origin/mr/123   # three dots: diff from the merge base
```

API equivalents (`:id` is the numeric id or the URL-encoded project path): `GET /projects/:id/merge_requests/:iid`, `GET /projects/:id/merge_requests/:iid/diffs`, `GET /projects/:id/merge_requests/:iid/discussions`, `GET /projects/:id/merge_requests/:iid/pipelines`.

Read the existing discussions so that you do not repeat what other reviewers already raised, and check whether earlier threads were really addressed.

## Commits, ranges, tags and branches

```bash
git fetch --tags origin
git show --stat <sha>; git show <sha>
git log --oneline --no-merges A..B;  git diff --stat A...B
git log --oneline "$(git describe --tags --abbrev=0 v1.4.0^)"..v1.4.0
git diff --stat origin/main...origin/feature/x
```

For a release range, also list merged MRs (`git log --merges --oneline A..B`, or the MR references in commit messages) and flag the database migrations, configuration and dependency changes in that range.

## Checking code out safely

Never switch the user's branch or touch their uncommitted work. When you need to build or run tests:

```bash
git worktree add <scratch-dir>/review-123 origin/mr/123   # isolated checkout
# … build or test there …
git worktree remove <scratch-dir>/review-123
```

## Size and scope

- More than ~400 changed lines (excluding generated files, lockfiles and snapshots), or many unrelated concerns: say so, review commit by commit if the history is clean, and recommend splitting.
- Exclude generated code, lockfiles and vendored files from line-by-line review, but check that lockfile changes match the intended dependency changes.

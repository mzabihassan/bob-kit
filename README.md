# bob-kit — IBM Bob skills & modes

A collection of reusable **skills** and custom **modes** for [IBM Bob](https://www.ibm.com/products/bob).

## Layout

```
skills/          # one folder per skill, each with a SKILL.md entry point
  angular2-developer/
modes/           # custom Bob modes (coming soon)
```

## Skills

| Skill | Description |
|-------|-------------|
| [angular2-developer](skills/angular2-developer/SKILL.md) | Build, review, debug and migrate Angular applications (v18 → latest). Reads the project's `AGENTS.md`, rules, lint config and existing code first and follows their conventions. Loads one supporting file per task to keep token use low, and never commits unless asked. |

## Usage

Copy a skill folder into your project's `.bob/skills/` directory (or your global Bob skills directory):

```bash
cp -R skills/angular2-developer /path/to/project/.bob/skills/
```

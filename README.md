# IBM Bob — Skills & Modes

A collection of reusable **skills** and custom **modes** for [IBM Bob](https://www.ibm.com/products/bob).

## Layout

```
skills/          # one folder per skill, each with a SKILL.md entry point
  angular-expert/
modes/           # custom Bob modes (coming soon)
```

## Skills

| Skill | Description |
|-------|-------------|
| [angular-expert](skills/angular-expert/SKILL.md) | Build, review, debug and migrate Angular applications (v17 → v22): signals, Signal Forms, resources, zoneless/OnPush, SSR, Angular Aria and `ng update` upgrades. |

## Usage

Copy a skill folder into your project's `.bob/skills/` directory (or your global Bob skills directory):

```bash
cp -R skills/angular-expert /path/to/project/.bob/skills/
```

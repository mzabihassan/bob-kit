# bob-kit — IBM Bob skills & modes

A collection of reusable **skills** and custom **modes** for [IBM Bob](https://www.ibm.com/products/bob).

## Layout

```
skills/          # one folder per skill, each with a SKILL.md entry point
  angular2-developer/
  spring-boot-developer/
modes/           # custom Bob modes (coming soon)
```

## Skills

| Skill | Description |
|-------|-------------|
| [angular2-developer](skills/angular2-developer/SKILL.md) | Build, review, debug and migrate Angular applications (v18 → latest). Reads the project's `AGENTS.md`, rules, lint config and existing code first and follows their conventions. Loads one supporting file per task to keep token use low, and never commits unless asked. |
| [spring-boot-developer](skills/spring-boot-developer/SKILL.md) | Senior/Staff Java 17–21 and Spring Boot engineer for enterprise and banking systems: features, bug fixes, safe refactoring of legacy code, architecture and code review, JUnit 5/Mockito/Testcontainers testing, SonarQube quality, JPA/SQL performance and version migrations. Adapts rigour to the task, follows the project's conventions, never commits unless asked, and ends with a prioritised technical report. |

## Usage

Copy a skill folder into your project's `.bob/skills/` directory (or your global Bob skills directory):

```bash
cp -R skills/angular2-developer /path/to/project/.bob/skills/
```

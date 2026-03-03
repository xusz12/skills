---
name: obsidian-cli-operator
description: Use Obsidian CLI to inspect and operate vaults, notes, tasks, tags, properties, templates, plugins, themes, sync history, and workspace tabs. Trigger when the user asks to read, write, search, or manage Obsidian content from terminal, or asks for exact `obsidian` command syntax.
---

# Obsidian Cli Operator

Use the `obsidian` command-line interface to execute note and vault operations deterministically.

## Workflow

1. Detect target vault and scope.
   - If the user provides a vault name, append `vault="<name>"`.
   - If no vault is provided and the action is sensitive, run `obsidian vault` first.
2. Resolve note targets precisely.
   - Prefer `path=<folder/note.md>` for write or destructive operations.
   - Use `file=<name>` when the user refers to notes by title.
3. Discover options before uncommon actions.
   - Run `obsidian help <command>` for exact parameters.
   - Use `obsidian commands` and `obsidian command id=<command-id>` for command palette execution.
4. Apply read-first safety for mutations.
   - Inspect state first with `read`, `file`, `property:read`, or `tasks`.
   - Then run write operations such as `append`, `prepend`, `create`, `property:set`, or `task`.
5. Report result clearly.
   - Include command run, affected vault/path, and key output fields.
   - If a command fails, show the error and retry with corrected arguments.

## Argument Rules

- Use `key=value` syntax, for example `file="Project Plan"`.
- Quote values containing spaces.
- Use `\n` and `\t` inside `content=` values when needed.
- Remember: `file` resolves by note title, while `path` is exact path.
- Most commands default to active file when `file/path` is omitted; avoid relying on active file for automation unless user asks for it.

## Task Mapping

Use [command-groups.md](references/command-groups.md) for fast command selection.
Use [obsidian-help.txt](references/obsidian-help.txt) for the full command list captured from `obsidian help`.

Common mappings:

- Create or update notes: `create`, `append`, `prepend`, `rename`, `move`, `delete`
- Read or search content: `read`, `search`, `search:context`, `outline`, `wordcount`
- Link graph checks: `links`, `backlinks`, `orphans`, `deadends`, `unresolved`
- Metadata: `properties`, `property:read`, `property:set`, `property:remove`, `tags`, `tag`, `aliases`
- Tasks and daily notes: `tasks`, `task`, `daily`, `daily:*`
- Vault and filesystem: `vault`, `vaults`, `files`, `folders`, `folder`, `file`, `recents`
- Templates, themes, plugins, snippets: `template:*`, `templates`, `theme:*`, `themes`, `plugin:*`, `plugins`, `snippet:*`, `snippets`
- Sync and history: `sync:*`, `history:*`, `diff`
- Workspace and navigation: `open`, `tab:open`, `tabs`, `workspace`, `random`, `restart`, `reload`

## Execution Standards

- Prefer non-destructive commands first when intent is ambiguous.
- Confirm user intent before destructive operations such as `delete permanent`, `history:restore`, `sync:restore`, `plugin:uninstall`, or `theme:uninstall`.
- Return concise, structured results instead of large raw tables unless user requests raw output.
- Use developer commands (`dev:*`, `devtools`, `eval`) only when user explicitly asks for debugging or runtime inspection in Obsidian.

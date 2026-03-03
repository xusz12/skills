# Obsidian CLI Command Groups

Source: `obsidian help` snapshot saved in `references/obsidian-help.txt`.

## Global Syntax

- `obsidian <command> [options]`
- Optional global selector: `vault=<name>`
- Target resolution:
- `file=<name>` resolves by note name
- `path=<path>` is exact vault path

## Core Command Groups

- Help and discovery:
- `help`, `version`, `vault`, `vaults`, `commands`, `command`
- Notes and files:
- `create`, `read`, `open`, `append`, `prepend`, `rename`, `move`, `delete`
- `file`, `files`, `folder`, `folders`, `recents`, `random`, `random:read`
- `outline`, `wordcount`
- Search and links:
- `search`, `search:context`, `search:open`
- `links`, `backlinks`, `orphans`, `deadends`, `unresolved`
- Daily notes:
- `daily`, `daily:path`, `daily:read`, `daily:append`, `daily:prepend`
- Metadata:
- `aliases`, `tags`, `tag`
- `properties`, `property:read`, `property:set`, `property:remove`
- Tasks:
- `tasks`, `task`
- Templates:
- `templates`, `template:read`, `template:insert`
- Plugins:
- `plugins`, `plugins:enabled`, `plugins:restrict`
- `plugin`, `plugin:install`, `plugin:enable`, `plugin:disable`, `plugin:reload`, `plugin:uninstall`
- Themes and snippets:
- `themes`, `theme`, `theme:install`, `theme:set`, `theme:uninstall`
- `snippets`, `snippets:enabled`, `snippet:enable`, `snippet:disable`
- Sync and history:
- `sync`, `sync:status`, `sync:deleted`, `sync:history`, `sync:open`, `sync:read`, `sync:restore`
- `history`, `history:list`, `history:open`, `history:read`, `history:restore`, `diff`
- Workspace and tabs:
- `tab:open`, `tabs`, `workspace`, `reload`, `restart`
- Bases:
- `bases`, `base:views`, `base:query`, `base:create`
- Bookmarks and hotkeys:
- `bookmark`, `bookmarks`, `hotkey`, `hotkeys`

## Developer Command Group

- `devtools`, `eval`
- `dev:cdp`, `dev:console`, `dev:css`, `dev:debug`, `dev:dom`, `dev:errors`, `dev:mobile`, `dev:screenshot`

## Usage Pattern

1. Check command-specific options with `obsidian help <command>`.
2. Use `path=` for exact, high-safety operations.
3. Inspect first, mutate second.

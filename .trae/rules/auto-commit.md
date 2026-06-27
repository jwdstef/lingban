# Git Auto Commit Rules

After completing any code generation or modification task, you MUST automatically:

1. Stage all changed files using `git add` with specific file names (never use `git add -A` or `git add .`)
2. Create a meaningful commit message in Chinese that describes what was changed
3. Commit the changes
4. Push to the remote repository (push to current branch)

## Important Notes
- Do NOT ask the user whether to commit - just do it automatically after finishing the task
- Use `git status` first to identify changed files
- Use `git diff` to understand the changes before writing commit messages
- Group related changes into a single commit
- If push fails, report the error to the user
- Never force push unless explicitly asked

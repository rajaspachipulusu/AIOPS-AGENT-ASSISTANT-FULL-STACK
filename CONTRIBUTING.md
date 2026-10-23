# Contributing

Thanks for your interest in improving this project.

## Local setup

1. Follow README quick-start for backend and frontend.
2. Use Python 3.14+ and Node 20.9+.
3. Run tests and lint before submitting changes.

## Development workflow

1. Create a focused branch.
2. Keep pull requests small and scoped.
3. Add or update tests when behavior changes.
4. Update README/docs when commands or architecture change.

## Quality checks

Backend:

- cd backend
- source .venv/bin/activate
- pytest -q

Frontend:

- cd frontend
- npm run lint
- npm run build

## Pull request checklist

- [ ] Change is explained clearly in PR description
- [ ] Tests/lint/build are green
- [ ] No secrets or private data are included
- [ ] Docs updated when needed

## Security

If you find a security issue, do not open a public issue with exploit details.
Please contact the maintainer directly and include reproduction steps.

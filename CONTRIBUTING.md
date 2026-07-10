# Contributing to INDB

Thank you for your interest in contributing to INDB (Interpretative Neural Database)!

## Development Setup

### Prerequisites
- Python 3.11+
- pip or poetry
- Git

### Setup Steps

1. **Clone the repository**
```bash
git clone https://github.com/your-org/indb-web.git
cd indb-web/backend
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
pip install -r requirements-test.txt
```

4. **Install development tools**
```bash
pip install black flake8 mypy pre-commit
```

5. **Set up pre-commit hooks**
```bash
pre-commit install
```

6. **Copy environment template**
```bash
cp .env.example .env
```

7. **Run tests**
```bash
python3 run_tests.py
```

## Code Style

We use automated formatters and linters:

- **black**: Code formatting (line length: 100)
- **flake8**: Linting
- **mypy**: Type checking

### Format code before committing
```bash
black . --line-length=100
flake8 . --max-line-length=100 --extend-ignore=E203,W503
```

## Testing

### Run all tests
```bash
python3 run_tests.py
```

### Run specific test suite
```bash
pytest tests/unit/
pytest tests/integration/
pytest tests/protocols/
```

### Run with coverage
```bash
pytest --cov=core --cov=services --cov-report=html
```

## Pull Request Process

1. **Create a feature branch**
```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes**
- Write clean, documented code
- Add tests for new features
- Update documentation as needed

3. **Run quality checks**
```bash
black . --line-length=100
flake8 .
pytest
```

4. **Commit your changes**
```bash
git add .
git commit -m "feat: add your feature description"
```

5. **Push and create PR**
```bash
git push origin feature/your-feature-name
```

## Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting)
- `refactor:` Code refactoring
- `test:` Test changes
- `chore:` Build/tooling changes

Examples:
```
feat: add pagination to events endpoint
fix: resolve race condition in test_large_dataset
docs: update API documentation for v2 endpoints
```

## Project Structure

```
backend/
├── core/           # Core INDB engine
├── services/       # Business logic
├── protocols/      # Multi-protocol support
├── api/            # API routes
├── auth/           # Authentication
├── storage/        # Data persistence
├── tests/          # Test suites
└── docs/           # Documentation
```

## Adding New Features

### 1. Core Features
- Add to `core/` directory
- Write unit tests in `tests/unit/`
- Update `core/__init__.py` exports

### 2. API Endpoints
- Add to `main.py` or `api/routes/`
- Use `/api/v2/` prefix
- Add Pydantic models for request/response
- Write integration tests

### 3. Protocol Support
- Add to `protocols/` directory
- Implement protocol interface
- Add protocol tests in `tests/protocols/`

## Documentation

- Update `README.md` for user-facing changes
- Update `docs/API.md` for API changes
- Add docstrings to all functions/classes
- Update `CHANGELOG.md`

## Questions?

- Open an issue for bugs
- Start a discussion for feature requests
- Check existing issues before creating new ones

## License

By contributing, you agree that your contributions will be licensed under the project's license.

---

**Thank you for contributing to INDB! 🚀**

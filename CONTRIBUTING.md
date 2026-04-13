# Contributing to Securities Prediction Model

Thank you for your interest in contributing to the Securities Prediction Model! This document provides guidelines for contributing to the project.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Pull Request Process](#pull-request-process)
5. [Coding Standards](#coding-standards)
6. [Testing Guidelines](#testing-guidelines)
7. [Documentation](#documentation)
8. [Future Development](#future-development)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of experience level, background, or identity.

### Expected Behavior

- Be respectful and constructive in all interactions
- Welcome newcomers and help them get started
- Focus on what is best for the project and community
- Accept constructive criticism gracefully

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Trolling, insulting, or derogatory remarks
- Publishing others' private information without permission
- Any conduct that would be inappropriate in a professional setting

---

## Getting Started

### Prerequisites

Before contributing, ensure you have:

1. **Git** installed and configured
2. **Python 3.10+** for backend development
3. **Node.js** (optional, for frontend tooling)
4. **PostgreSQL 15+** for local development
5. Read the [SETUP_GUIDE.md](docs/setup/SETUP_GUIDE.md) for local environment setup

### Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/data-acq-functional-SophistryDude.git
cd data-acq-functional-SophistryDude/AlphaBreak

# Add upstream remote
git remote add upstream https://github.com/SophistryDude/data-acq-functional-SophistryDude.git
```

### Set Up Development Environment

```bash
# Install Python dependencies
cd flask_app
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies (linters, formatters)

# Configure environment
cp .env.example .env
# Edit .env with your local database credentials
```

---

## Development Workflow

### Branch Strategy

We use a simplified Git workflow:

- **`main`**: Production branch (deployed to EC2)
- **`localhost-dev`**: Local development branch (for localhost testing)
- **Feature branches**: `feature/your-feature-name`
- **Bug fix branches**: `fix/bug-description`
- **Hotfix branches**: `hotfix/critical-fix`

### Creating a Feature Branch

```bash
# Update your local main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name

# Make your changes...
git add .
git commit -m "Add feature: your feature description"

# Push to your fork
git push origin feature/your-feature-name
```

### Commit Message Guidelines

Follow these conventions for clear commit history:

**Format**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring (no feature change)
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks (dependencies, build scripts)

**Examples**:
```bash
# Good commit messages
git commit -m "feat(forex): add DXY correlation analysis"
git commit -m "fix(options): correct Black-Scholes volatility calculation"
git commit -m "docs(api): update authentication endpoint documentation"

# Bad commit messages (avoid these)
git commit -m "fixed stuff"
git commit -m "WIP"
git commit -m "asdf"
```

---

## Pull Request Process

### Before Submitting

1. **Update Documentation**:
   - Update relevant `.md` files in `docs/`
   - Add entries to [CHANGELOG.md](CHANGELOG.md) under `[Unreleased]`
   - Update API documentation if endpoints changed

2. **Test Your Changes**:
   - Run unit tests: `pytest`
   - Test manually in browser (if frontend changes)
   - Verify no breaking changes

3. **Code Quality**:
   - Run linter: `flake8 flask_app/`
   - Format code: `black flask_app/`
   - Check for security issues: `bandit -r flask_app/`

### Submitting a Pull Request

1. **Push to Your Fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create Pull Request** on GitHub:
   - Go to the original repository
   - Click "New Pull Request"
   - Select your branch
   - Fill out the PR template

3. **PR Title Format**:
   ```
   [TYPE] Brief description of changes
   ```
   Examples:
   - `[FEAT] Add WebSocket support for real-time prices`
   - `[FIX] Resolve database connection timeout`
   - `[DOCS] Update deployment guide with SSL setup`

4. **PR Description Template**:
   ```markdown
   ## Description
   Brief description of what this PR does and why.

   ## Changes
   - Change 1
   - Change 2
   - Change 3

   ## Type of Change
   - [ ] Bug fix (non-breaking change which fixes an issue)
   - [ ] New feature (non-breaking change which adds functionality)
   - [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
   - [ ] Documentation update

   ## Testing
   - [ ] Unit tests pass
   - [ ] Manual testing completed
   - [ ] No breaking changes

   ## Screenshots (if applicable)
   Add screenshots or GIFs demonstrating the changes.

   ## Checklist
   - [ ] Code follows project style guidelines
   - [ ] Documentation updated (README, CHANGELOG, etc.)
   - [ ] No new warnings or errors
   - [ ] Tested on local environment
   ```

### Review Process

1. **Automated Checks**: CI/CD pipeline runs tests and linters
2. **Code Review**: Maintainers review your code
3. **Address Feedback**: Make requested changes and push updates
4. **Approval**: Once approved, maintainers will merge your PR

### After Merge

```bash
# Update your local repository
git checkout main
git pull upstream main

# Delete feature branch
git branch -d feature/your-feature-name
git push origin --delete feature/your-feature-name
```

---

## Coding Standards

### Python (Backend)

**Style Guide**: PEP 8

```python
# Good: Clear function names, type hints, docstrings
def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI) indicator.

    Args:
        prices: Series of closing prices
        period: RSI period (default: 14)

    Returns:
        Series of RSI values (0-100)
    """
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


# Bad: No type hints, unclear variable names, no documentation
def calc(p, n=14):
    d = p.diff()
    g = d.where(d > 0, 0)
    l = -d.where(d < 0, 0)
    ag = g.rolling(window=n).mean()
    al = l.rolling(window=n).mean()
    return 100 - (100 / (1 + ag / al))
```

**Key Conventions**:
- Use type hints for all function parameters and return values
- Write docstrings for all public functions (Google style)
- Keep functions under 50 lines (split if longer)
- Use meaningful variable names (no single-letter names except loop counters)
- Avoid deeply nested code (max 3 levels)

### JavaScript (Frontend)

**Style Guide**: Airbnb JavaScript Style Guide (adapted)

```javascript
// Good: Clear function names, JSDoc comments, modern ES6+ syntax
/**
 * Fetch forex data for a specific currency pair
 * @param {string} pair - Currency pair (e.g., 'EUR/USD')
 * @param {number} days - Number of days of historical data
 * @returns {Promise<Object>} Forex data with OHLCV
 */
async function fetchForexData(pair, days = 365) {
    const pairParam = pair.replace('/', '_');
    const response = await apiRequest(`/api/forex/data/${pairParam}?days=${days}`, 'GET');
    return response;
}

// Bad: No comments, unclear names, old syntax
function get(p, d) {
    var pp = p.replace('/', '_');
    return apiRequest('/api/forex/data/' + pp + '?days=' + d, 'GET');
}
```

**Key Conventions**:
- Use `const` and `let` (never `var`)
- Use arrow functions for callbacks
- Use template literals for string interpolation
- Write JSDoc comments for complex functions
- Use async/await (not `.then()` chains)

### SQL

```sql
-- Good: Clear formatting, comments
-- Fetch trend breaks with 80%+ probability from last 30 days
SELECT
    tb.ticker,
    tb.signal_date,
    tb.probability,
    tb.direction,
    tm.company_name,
    tm.sector
FROM trend_breaks tb
JOIN ticker_metadata tm ON tb.ticker = tm.ticker
WHERE tb.probability >= 80
  AND tb.signal_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY tb.probability DESC, tb.signal_date DESC;

-- Bad: No formatting, hard to read
select * from trend_breaks where probability>=80 and signal_date>=CURRENT_DATE-INTERVAL'30days' order by probability desc;
```

---

## Testing Guidelines

### Unit Tests (Python)

Location: `flask_app/tests/`

```python
import pytest
from app.services.technical_indicators import calculate_rsi

def test_rsi_calculation():
    """Test RSI calculation with known values"""
    prices = pd.Series([44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41, 46.22, 45.64])
    rsi = calculate_rsi(prices, period=14)

    # RSI should be between 0 and 100
    assert (rsi >= 0).all() and (rsi <= 100).all()

    # Last RSI value should be approximately 51.78 (from reference)
    assert abs(rsi.iloc[-1] - 51.78) < 1.0
```

**Run Tests**:
```bash
# All tests
pytest

# Specific test file
pytest flask_app/tests/test_technical_indicators.py

# With coverage
pytest --cov=flask_app --cov-report=html
```

### Manual Testing

Before submitting PR, manually test:

1. **Frontend Changes**:
   - Test in Chrome, Firefox, Safari
   - Test on mobile (Chrome DevTools mobile view)
   - Verify all links and buttons work
   - Check console for JavaScript errors

2. **API Changes**:
   - Test all affected endpoints with `curl` or Postman
   - Verify response formats match API documentation
   - Test error cases (invalid input, missing data)

3. **Database Changes**:
   - Test migrations on fresh database
   - Verify data integrity
   - Check query performance (use `EXPLAIN ANALYZE`)

---

## Documentation

### When to Update Documentation

Update docs whenever you:

- Add a new feature → Update [COMPLETED_FEATURES.md](docs/COMPLETED_FEATURES.md), [README.md](README.md)
- Change API → Update [API_DOCUMENTATION.md](docs/api/API_DOCUMENTATION.md)
- Modify architecture → Update [ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Change deployment → Update [DEPLOYMENT.md](docs/DEPLOYMENT.md)
- Add dependencies → Update [SETUP_GUIDE.md](docs/setup/SETUP_GUIDE.md)

### Documentation Style

- Use clear, concise language
- Include code examples
- Add screenshots for UI changes
- Keep tables and lists organized
- Cross-reference related documents

---

## Future Development

### Roadmap

For planned features and development priorities, see [ROADMAP.md](docs/ROADMAP.md).

The roadmap is organized by quarter and includes:
- **Q1 2026**: Documentation, stability, performance
- **Q2 2026**: Security (SSL), scalability (Redis), UX improvements
- **Q3 2026**: Monitoring (Prometheus/Grafana), K8s migration, mobile app
- **Q4 2026**: Premium features, platform integrations, real-time data

### Feature Requests

To propose a new feature:

1. **Check Roadmap**: See if it's already planned in [ROADMAP.md](docs/ROADMAP.md)
2. **Open Issue**: Create a GitHub issue with the "feature request" label
3. **Describe Use Case**: Explain who benefits and why
4. **Community Vote**: Features with most upvotes get prioritized
5. **Discussion**: Maintainers will discuss feasibility and timeline

### Contributing to Roadmap

The roadmap is a living document. If you want to work on a planned feature:

1. Comment on the related GitHub issue (or create one)
2. Discuss implementation approach with maintainers
3. Get approval before starting significant work
4. Follow the Pull Request Process above

---

## Questions?

- **Technical Questions**: Open a GitHub issue with the "question" label
- **Security Issues**: Email security@example.com (do NOT open public issue)
- **General Discussion**: Use GitHub Discussions

---

## License

By contributing to this project, you agree that your contributions will be licensed under the same license as the project (MIT).

---

**Thank you for contributing to Securities Prediction Model!** 🎉

Your contributions help make quantitative trading analysis accessible to everyone.

---

**Last Updated**: February 2, 2026
**Maintained By**: Project Maintainers
**Review Cycle**: Updated as needed

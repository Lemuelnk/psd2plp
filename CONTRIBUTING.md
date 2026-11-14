# Contribuer à psd2plp

## Signaler un bug

Ouvre une issue avec :
- Le fichier source (ou un extrait minimal qui reproduit)
- La sortie de `python -m psd2plp.cli convert ... 2>&1`
- Ta version Python et ton OS

## Proposer une PR

1. Fork le repo
2. Crée une branche `feat/ma-feature` ou `fix/mon-bug`
3. Vérifie que `pip install -e ".[dev]"` passe
4. Commit avec des messages clairs (voir plus bas)
5. PR vers `main`

## Convention de commit

- `feat:` nouvelle fonctionnalité
- `fix:` correction de bug
- `docs:` documentation
- `chore:` maintenance
- `refactor:` refactorisation sans changement de comportement

## Style de code

- Python 3.10+
- Type hints sur les fonctions publiques
- Pas de dépendances externes non listées dans `pyproject.toml`

## Licence

En contribuant, tu acceptes que ton code soit publié sous Apache 2.0.

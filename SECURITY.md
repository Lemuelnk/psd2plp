# Security Policy

## Signaler une vulnérabilité

Merci de **ne pas** ouvrir d'issue publique pour les problèmes de sécurité.

Utilise le formulaire GitHub "Private vulnerability reporting" :
https://github.com/Lemuelnk/psd2plp/security/advisories/new

Ou envoie un email à l'adresse du mainteneur (voir `pyproject.toml`).

## Versions supportées

| Version | Support |
|---------|---------|
| 0.1.x   | Oui     |

## Portée

Ce projet est un convertisseur de fichiers **local**. Il ne fait aucun
appel réseau. Les risques principaux concernent :

- L'analyse de fichiers PSD/SVG malformés (déni de service, crash)
- L'écriture de fichiers non contrôlés (chemin de sortie)

Les rapports sur ces aspects sont bienvenus.

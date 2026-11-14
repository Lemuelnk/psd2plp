# Setup

## Termux (Android)

Prérequis système :

    pkg update
    pkg upgrade -y
    pkg install python python-pip python-numpy
    pkg install tur-repo
    pkg install python-scikit-image

Dépendances Python :

    pip install psd-tools Pillow

Note : psd-tools exige numpy et scikit-image pour le compositing.
Sur Termux, ces paquets doivent venir de pkg (compilés pour Android),
pas de pip (qui tenterait une compilation qui échoue).

## Linux / Desktop

    pip install psd-tools Pillow scikit-image

## Vérification

    python -c "import numpy, skimage, psd_tools, PIL; print('OK')"

## Pièges connus

- libc++ doit être à jour : pkg upgrade -y puis pkg reinstall libc++ python-numpy
- Si numpy plante avec 'cannot locate symbol _ZNSt6...', c'est libc++ obsolète.
- scikit-image n'est pas sur PyPI pour Termux : passer par tur-repo (voir plus haut).

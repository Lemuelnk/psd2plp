# Commandes

## CLI psd2plp

    # Convertir un PSD en PLP
    python -m psd2plp.cli convert mon.psd -o output/mon.plp

    # Avec un nom de preset interne différent
    python -m psd2plp.cli convert mon.psd -o output/mon.plp --name "Mon Visuel"

    # Inspecter un PSD (JSON)
    python -m psd2plp.cli inspect mon.psd > inspect.json

## Tests manuels

### Round-trip PLP

    python -c "
    import sys; sys.path.insert(0, 'src')
    from psd2plp.pixellab.reader import read_plp
    from psd2plp.pixellab.writer import write_plp
    p = read_plp('examples/plp/Vdjdkdk.plp')
    write_plp(p, 'output/rt.plp')
    p2 = read_plp('output/rt.plp')
    print('in:', p.width, p.height, len(p.objects))
    print('out:', p2.width, p2.height, len(p2.objects))
    "

### Vérifier un PLP (JSON)

    python -c "
    import zipfile, json
    with zipfile.ZipFile('output/food_A.plp') as z:
        d = json.loads(z.read('data.plab'))
    print('size:', d['bgWidth'], d['bgHeight'])
    print('objects:', d['objectsIds'])
    "

## Déployer dans PixelLab

REGLE : on n'ecrit JAMAIS dans `pixelLab/presets/`. Tous les PLP
generes vont dans `/storage/emulated/0/pixelLab/psd2plp_out/` (racine
de pixelLab). L'utilisateur copie manuellement vers presets/ quand il
veut tester dans l'app.

Script helper `push.sh` (à la racine du projet) :

    bash push.sh                 # archive tous les output/*.plp
    bash push.sh mon.plp         # archive un fichier nomme

## Format du thumb

Le thumb du PLP est généré avec un test de transparence (voir
psd_to_plp.py, section "Thumb : composite global") :

- Composite PSD avec alpha < 255 → PNG RGBA (PixelLab affiche son
  damier de transparence)
- Composite opaque → JPEG (format natif, plus léger)

Ne jamais forcer RGB sans tester alpha : ça noircit les zones
transparentes.

## Git

    git status
    git add -A
    git commit -m "type: message"
    git push origin main

Convention : feat:, fix:, docs:, chore:, refactor:.

## Comparer deux PLP

Utile pour voir ce que PixelLab ajoute/corrige à la sauvegarde :

    python -c "
    import zipfile, json
    a = 'output/food_B.plp'
    b = '/storage/emulated/0/pixelLab/compare/food_B (2).plp'
    def load(p):
        with zipfile.ZipFile(p) as z:
            return json.loads(z.read('data.plab'))
    da, db = load(a), load(b)
    print('gen:', da['objectsIds'])
    print('sav:', db['objectsIds'])
    "

## REGLE ABSOLUE : jamais dans presets/

`pixelLab/presets/` est reserve a PixelLab/LNK Studio pour ses propres
projets. Nos PLP generes vont TOUJOURS dans :

    /storage/emulated/0/pixelLab/psd2plp_out/

Le helper `scripts/push-to-pixellab.sh` fait deja ca. Ne jamais copier
manuellement vers `presets/`.

Deux dossiers existent a la racine de pixelLab :
- `psd2plp/`     : ancien, obsolete
- `psd2plp_out/` : archive active

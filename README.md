# Bicing per al Home Assistant


## Què és?
Una integració per a monitorar l'estat del servei del Bicing al Home Assistant. El motiu que m'ha portat a desenvolupar-lo és per, a banda d'aprendre com funcionen les integracions del Home Assistant, saber quantes bicicletes elèctriques hi ha abans de sortir per anar a treballar.


## Instal·lació

### Usant _My Home Assistant_
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=oscarsanchezdm&repository=bicing-hassio&category=integration)

## Versions i actualitzacions

Les versions es publiquen com a [GitHub Releases](https://github.com/oscarsanchezdm/bicing-hassio/releases) amb tags `vX.Y.Z` (han de coincidir amb `version` a `custom_components/bicing/manifest.json`).

- Historial de canvis: [CHANGELOG.md](CHANGELOG.md)
- HACS pot actualitzar a una release concreta; així és més fàcil saber quina versió tens instal·lada.

Per publicar una versió nova:

1. Actualitza `version` al `manifest.json` i l’entrada a `CHANGELOG.md`.
2. Fusiona els canvis a `main`.
3. Crea i puja el tag: `git tag vX.Y.Z && git push origin vX.Y.Z`.
4. El workflow [Release](.github/workflows/release.yml) crea automàticament la GitHub Release amb notes generades.

## Configuració
Et farà falta generar un token del servei de dades obertes de l'Ajuntament de Barcelona. Pots obtenir-ne un de forma completament gratuïta des d'[aquest enllaç](https://opendata-ajuntament.barcelona.cat/ca/tokens)

Un cop tinguis el token, caldrà que afegeixis una entrada des de la pantalla d'integracions del Home Assistant. A continuació, enganxa el token obtingut i selecciona les estacions del Bicing que vulguis monitorar. Més tard podràs afegir-ne més usant el botó de reconfigurar.

Es crearà una entitat per a cadascuna de les estacions. El valor de l'entitat serà el nombre total de bicicletes disponibles a l'estació i, els atributs seran els següents:
-  Bicicletes elèctriques disponibles
-  Bicicletes mecàniques disponibles
-  Ancoratges disponibles

Amb aquestes dades, podràs crear automatitzacions perquè et notifiqui si queden bicicletes o no, ancoratges, etc.

![Chart](images/notification.png)

## Origen de les dades
[Informació de les estacions del Bicing](https://opendata-ajuntament.barcelona.cat/data/ca/dataset/informacio-estacions-bicing)
[Estat de les estacions del Bicing](https://opendata-ajuntament.barcelona.cat/data/ca/dataset/estat-estacions-bicing)



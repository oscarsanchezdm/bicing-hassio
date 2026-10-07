# Changelog

Totes les versions notables d’aquesta integració. Les releases de GitHub (`vX.Y.Z`) són la referència traçable per a HACS i actualitzacions.

El format es basa en [Keep a Changelog](https://keepachangelog.com/ca/1.0.0/),
i el projecte segueix [Semantic Versioning](https://semver.org/lang/ca/).

## [Unreleased]

## [0.3.2] - 2026-10-07

### Added
- Detecció del challenge anti-bot d’Open Data BCN (`/challenge` / hCaptcha).
- Repair de Home Assistant amb enllaç al challenge i instruccions per resoldre’l des de la **mateixa IP pública** que Home Assistant.
- Consell de reiniciar el router si el bloqueig de la IP continua.

### Changed
- Els challenges i errors temporals ja no es confonen amb token invàlid (sense reauth fals).
- Només HTTP 401/403 disparen reautenticació del token.

## [0.3.1] - 2026-08-06

### Changed
- Si l’API falla de forma temporal, es manté l’últim estat conegut del sensor fins a 1 hora.
- Passades 1 hora sense actualització correcta, l’entitat passa a desconegut.

## [0.3.0] - 2026-05-18

### Fixed
- Errors temporals de l’API (timeouts, XML/HTML inesperat) ja no forcen reautenticació.
- Reintent controlat en desconnexions puntuals en obtenir l’estat de les estacions.

[Unreleased]: https://github.com/oscarsanchezdm/bicing-hassio/compare/v0.3.2...HEAD
[0.3.2]: https://github.com/oscarsanchezdm/bicing-hassio/releases/tag/v0.3.2
[0.3.1]: https://github.com/oscarsanchezdm/bicing-hassio/releases/tag/v0.3.1
[0.3.0]: https://github.com/oscarsanchezdm/bicing-hassio/releases/tag/v0.3.0

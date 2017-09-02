# Python wrapper for omppc
This is a Python 3 wrapper that lets you use [omppc](https://github.com/semyon422/omppc) as a Python class.
[omppc](https://github.com/semyon422/omppc) is a osu!mania performance points (and starrate) calculator made by [semyon422](https://github.com/semyon422)
This is used in [LETS](https://github.com/osuripple/lets) as mania pp calculator.

## Requirements
- lua 5.2 (required by lupa)
- lua 5.2 dev (required by lupa)
- lupa

## Usage
```
>>> import omppc
>>> calc = omppc.Calculator("beatmap.osu", score=1000000, mods=0, accuracy=100)
>>> calc.calculate_pp()
(103.0620415888816, 71.45130296276501, 27.319529885105837)
>>> calc.calculate_stars()
3.244000748543411
```

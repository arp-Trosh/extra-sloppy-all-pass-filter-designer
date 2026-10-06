# Extra Sloppy All Pass Filter Designer

A modern, cross-platform (Linux / Windows 10 / Windows 11) re-implementation of the
J-Tek **All Pass Filter Designer** by Lawrence Woolf, GJ3RAX. The tool designs and analyses
the 90° phase-difference all-pass networks used in phasing-type SSB transmitters and receivers.

The original is a 2002 Visual Basic 6 program that is no longer maintained and whose source
code is lost (<https://www.gj3rax.com/apf.htm>). This project is a **clean-room
re-implementation**. It is built from the published mathematics (R. Oppelt, DB2NP,
*VHF Communications* 2/1987) and checked against the original program running under Wine.
No code from the original is used.

> **Status:** planning complete; implementation not started. See [ROADMAP.md](ROADMAP.md).

## Reference material

The original executable, web pages and the 1987 article are copyright their authors and are
not included in this repository. To download them locally:

```sh
reference/fetch.sh
```

## Credits

- Lawrence Woolf, GJ3RAX: original *All Pass Filter Designer* (J-Tek, 2002–2004)
- Dr. (Eng.) Ralph Oppelt, DB2NP: design equations, *VHF Communications* 2/1987, pp. 66–72

## Licence

GPL-3.0-only. See [LICENSE](LICENSE).

# punipuni_eng — English Half-Width DLL

Modified version of `punipuni.dll` for English translation with half-width text support.

## What Changed vs. Original (`../punipuni/`)

| File | Change |
|------|--------|
| `HOOK_main.cpp` | Font → Arial, charset → ANSI_CHARSET, uses half-width hook |
| `dllmain.cpp` | Removed Chinese startup message |
| `text_process.cpp` | Removed ~200 hardcoded Chinese `addSjisReplaceMap()` calls, kept file-path redirect and inline ASM hooks |
| `textReplacer_halfwidth.cpp` | **NEW** — Modified `GetGlyphOutlineA` hook that halves `gmCellIncX` for ASCII characters |
| `textReplacer_halfwidth.h` | Header for the above |

## How Half-Width Works

The CAGE engine calls `GetGlyphOutlineA` to get glyph bitmaps and metrics. The `GLYPHMETRICS` struct returned by this function contains `gmCellIncX` — the horizontal advance width (how many pixels the cursor moves after drawing a character).

For CJK characters, this is typically the full cell width (e.g. 24px). For English text to render at half-width, the hook:

1. Detects if the character is single-byte ASCII (`bytes[0] == 0x00`)
2. Calls the original `GetGlyphOutlineA`
3. **Halves `gmCellIncX`** in the returned `GLYPHMETRICS`
4. Returns normally — the engine advances the cursor by half the usual amount

This means two English characters fit in the space of one Japanese character.

## Build Instructions

1. Open `gamehook.sln` in Visual Studio 2022
2. Add this project: Right-click Solution → Add → Existing Project → select `punipuni_eng.vcxproj`
3. Build configuration: **Release | Win32**
4. Output: `Release\punipuni_eng\punipuni.dll`

## Deployment

Copy the built `punipuni.dll` into the game's release folder, replacing the original.

The `trans/data.bin` file is still used for any non-ASCII character substitutions (if present). For a pure English translation, `data.bin` may be empty or contain no mappings.

## Tuning

If the half-width spacing is too narrow or too wide, adjust the divisor in `textReplacer_halfwidth.cpp`:

```cpp
// Current: exactly half
lpgm->gmCellIncX = static_cast<short>(lpgm->gmCellIncX / 2);

// Alternative: 60% width (slightly wider than half)
lpgm->gmCellIncX = static_cast<short>(lpgm->gmCellIncX * 60 / 100);
```

If the engine ignores `gmCellIncX` and uses its own fixed-width positioning, this approach won't work. In that case, the fallback is the "two-chars-per-glyph" packing approach in the Python toolchain (see `ENGLISH_TRANSLATION_GUIDE_v2.md`).

# assets

## gcp-icons/

Google's Cloud architecture icon set: one folder per product, `<product>/<product>.svg`.
Google publishes it for architecture diagrams, which is what the schematic layer draws, so use
it rather than a hand-drawn service glyph.

The icons are not in this repository. Download them once:

```sh
assets/fetch-icons.sh
```

`vanim.gicon(name)` reads `assets/gcp-icons/` by default. Set `VANIM_ICONS` to use another
folder.

Loading one by hand:

```python
icon = SVGMobject("assets/gcp-icons/cloud_run/cloud_run.svg")
icon.set_stroke(width=0)      # the loader leaves manim's default strokes on
icon.set_height(0.42)
```

Two things measured on load:

- Submobject counts are 1 to 12, so an icon is cheap per frame.
- Brand fills survive, because manim resolves the `<style>` classes. **Strokes do not
  survive**: the paths come back with manim defaults (`#FFFFFF`, `#58C4DD`), so set
  `stroke_width=0` and let fill carry the shape.

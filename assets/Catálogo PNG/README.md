# Catálogo PNG

Una imagen individual por mueble real (no para elementos decorativos, que
siguen usando `assets/muebles/` + `data/imagenes_mueble.yaml`).

## Convención de nombres

`{código exacto del mueble}.png` — el mismo código que usa SketchUp/el
catálogo (columna `Name` del CSV), sin sufijos de posición ni variantes.

Ejemplos:
```
B608035.png
H1.60.png
EOV9060.png
```

Si existe un archivo con el nombre exacto del mueble aquí, se usa esa imagen.
Si no existe, `modulo_b._imagen_mueble()` cae automáticamente al sistema
anterior de `assets/muebles/` (por prefijo).

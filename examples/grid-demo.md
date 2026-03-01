# Grid Layout Demo

Ejemplos de la sintaxis `<!-- $grid(N) -->` para distribuir contenido en columnas.

---

## Dos columnas — comparación

<!-- $grid(2) -->

### Enfoque A
- Simple de implementar
- Bajo acoplamiento
- Fácil de testear

-----

### Enfoque B
- Mayor flexibilidad
- Requiere más configuración
- Mejor para proyectos grandes

<!-- $grid/ -->

---

## Tres columnas — tarjetas de resumen

<!-- $grid(3) -->

### Velocidad
Procesamiento en menos de **200 ms** para presentaciones de hasta 100 diapositivas.

-----

### Compatibilidad
Funciona en Chrome, Firefox, Safari y Edge sin dependencias adicionales.

-----

### Extensibilidad
Agrega procesadores nuevos subclasificando `SlideProcessor` sin tocar código existente.

<!-- $grid/ -->

---

## Dos columnas — código y explicación

<!-- $grid(2) -->

### Sintaxis

```markdown
<!-- $grid(2) -->

Columna izquierda

-----

Columna derecha

<!-- $grid/ -->
```

-----

### Reglas clave

- `<!-- $grid(N) -->` abre el grid con **N** columnas
- `-----` (5 guiones) separa los items
- `<!-- $grid/ -->` cierra el bloque
- Sin `<!-- $grid/ -->`, el slide no se modifica

<!-- $grid/ -->

---

## Cuatro columnas — pipeline de procesamiento

<!-- $grid(4) -->

### 1. Parseo
`markdown-it-py` convierte el texto a HTML con soporte de tablas y fenced blocks.

-----

### 2. Grid
`GridProcessor` detecta los comentarios y reestructura el DOM antes que cualquier otro procesador.

-----

### 3. Imágenes
`ImageProcessor` copia archivos locales y reescribe los atributos `src`.

-----

### 4. Render
`TemplateRenderer` inyecta el HTML final en la plantilla Jinja2 de Reveal.js.

<!-- $grid/ -->

---

## Contenido mixto dentro de un item

El contenido de cada celda puede ser cualquier Markdown válido.

<!-- $grid(2) -->

### Tabla de referencia

| Separador | Uso |
|---|---|
| `---` | Separador de slides |
| `-----` | Separador de items en grid |

> [info] El separador de slides usa exactamente 3 guiones. El de items usa 5, por lo que no hay colisión.

-----

### Lista con fragmentos

Los items de lista siguen recibiendo la clase `.fragment` si los fragmentos están habilitados en la configuración.

1. Primer punto
2. Segundo punto
3. Tercer punto

<!-- $grid/ -->

---

# Fin de la demo

Vuelve a cualquier diapositiva para revisar los ejemplos.

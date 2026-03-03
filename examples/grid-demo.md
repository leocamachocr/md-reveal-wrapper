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

## Celda expandida — `$grid-cell(cols, rows)`

Coloca `<!-- $grid-cell(cols, rows) -->` como primera línea de una celda para que ocupe más de una columna o fila.

<!-- $grid(3) -->

### Normal
Ocupa 1 col × 1 fila (comportamiento por defecto).

-----
<!-- $grid-cell(2,1) -->

### Expandida en 2 columnas
Esta celda ocupa **2 columnas** con `<!-- $grid-cell(2,1) -->`.

Útil para destacar contenido principal frente a columnas auxiliares.

<!-- $grid/ -->

---

## Expansión en filas — `$grid-cell(1,2)`

<!-- $grid(2) -->

<!-- $grid-cell(1,2) -->

### Panel lateral alto
Esta celda se extiende hacia abajo ocupando **2 filas** con `<!-- $grid-cell(1,2) -->`.

Puede contener una lista larga, una imagen o un bloque de código.

-----

### Fila superior
Contenido de la primera fila a la derecha.

-----

### Fila inferior
Contenido de la segunda fila a la derecha.

<!-- $grid/ -->

---

## Sintaxis completa de spanning

<!-- $grid(2) -->

### Referencia rápida

| Sintaxis | Efecto |
|---|---|
| *(sin comentario)* | 1 col × 1 fila |
| `$grid-cell(2,1)` | 2 cols × 1 fila |
| `$grid-cell(1,2)` | 1 col × 2 filas |
| `$grid-cell(2,2)` | 2 cols × 2 filas |

> [info] El comentario debe ser la **primera línea** del contenido de la celda, justo después del separador `-----`.

-----

### Reglas clave

- `<!-- $grid-cell(C,R) -->` va **dentro** del bloque `<!-- $grid(N) -->…<!-- $grid/ -->`
- Aparece después del separador `-----` de esa celda
- Sin `<!-- $grid-cell -->`, la celda ocupa 1×1 (comportamiento anterior)
- Celdas sin comentario conviven con celdas expandidas en el mismo grid

<!-- $grid/ -->

---

# Fin de la demo

Vuelve a cualquier diapositiva para revisar los ejemplos.

"""Herramientas del agente. Cada una es una función pequeña, con descripción y parámetros explícitos.
Todas operan DENTRO del directorio de trabajo (sandbox)."""
import ast, pathlib, subprocess, re


class Herramientas:
    def __init__(self, raiz: str):
        self.raiz = pathlib.Path(raiz).resolve()

    # --- utilidades ---
    def _ruta(self, ruta: str) -> pathlib.Path:
        p = (self.raiz / ruta).resolve()
        if self.raiz not in p.parents and p != self.raiz:
            raise PermissionError(f"Ruta fuera del sandbox: {ruta}")
        return p

    def catalogo(self) -> dict:
        """Descripción de las herramientas que se envía al modelo (como en un MCP server)."""
        return {
            "listar_archivos": "listar_archivos(carpeta='.'): lista los archivos .py y .md",
            "leer_archivo": "leer_archivo(ruta): devuelve el contenido con números de línea",
            "buscar": "buscar(patron): busca una expresión regular en los archivos .py",
            "ejecutar_pruebas": "ejecutar_pruebas(): ejecuta pytest y devuelve el resumen",
            "editar_archivo": "editar_archivo(ruta, antes, despues): reemplaza un fragmento exacto (una sola vez)",
            "ver_cambios": "ver_cambios(): muestra el diff respecto de la versión original",
            "ejecutar_comando": "ejecutar_comando(comando): ejecuta un comando de shell (sujeto a la política)",
            "mapa_repo": "mapa_repo(carpeta='.'): por cada archivo .py, sus clases y funciones con parámetros y la "
                         "primera línea del docstring; no muestra el cuerpo. Úsala antes de leer archivos completos",
            "anotar": "anotar(texto): guarda una nota breve (hipótesis, archivo revisado) en notas.md; devuelve el número de notas",
            "leer_notas": "leer_notas(): devuelve las notas guardadas en notas.md, o '(sin notas)'",
        }

    # --- herramientas ---
    def listar_archivos(self, carpeta="."):
        base = self._ruta(carpeta)
        return "\n".join(sorted(str(p.relative_to(self.raiz)) for p in base.rglob("*")
                                if p.suffix in (".py", ".md") and "__pycache__" not in p.parts))

    def leer_archivo(self, ruta):
        lineas = self._ruta(ruta).read_text(encoding="utf-8").splitlines()
        return "\n".join(f"{i:3d}| {l}" for i, l in enumerate(lineas, 1))

    def buscar(self, patron):
        rx, hallazgos = re.compile(patron), []
        for p in sorted(self.raiz.rglob("*.py")):
            for i, l in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if rx.search(l):
                    hallazgos.append(f"{p.relative_to(self.raiz)}:{i}: {l.strip()}")
        return "\n".join(hallazgos) or "(sin resultados)"

    def ejecutar_pruebas(self):
        r = subprocess.run(["python", "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider"],
                           cwd=self.raiz, capture_output=True, text=True, timeout=120)
        salida = (r.stdout + r.stderr).strip().splitlines()
        fallos = [l for l in salida if l.startswith(("FAILED", "E "))][:6]
        return "\n".join(fallos + salida[-1:])

    def editar_archivo(self, ruta, antes, despues):
        p = self._ruta(ruta)
        texto = p.read_text(encoding="utf-8")
        if texto.count(antes) != 1:
            return f"ERROR: el fragmento aparece {texto.count(antes)} veces; debe aparecer exactamente 1"
        p.write_text(texto.replace(antes, despues), encoding="utf-8")
        return f"OK: {ruta} modificado"

    def ver_cambios(self, original="../trabajo_original"):
        import difflib
        base, salida = self._ruta_libre(original), []
        for p in sorted(self.raiz.rglob("*.py")):
            rel = p.relative_to(self.raiz); q = base / rel
            a = q.read_text(encoding="utf-8").splitlines() if q.exists() else []
            salida += difflib.unified_diff(a, p.read_text(encoding="utf-8").splitlines(),
                                           f"a/{rel}", f"b/{rel}", lineterm="", n=1)
        return "\n".join(salida) or "(sin cambios)"

    def _ruta_libre(self, ruta):
        return (self.raiz / ruta).resolve()

    def ejecutar_comando(self, comando):
        r = subprocess.run(comando, shell=True, cwd=self.raiz, capture_output=True, text=True, timeout=60)
        return (r.stdout + r.stderr).strip()[-2000:]

    def mapa_repo(self, carpeta="."):
        lineas = []
        for p in sorted(self._ruta(carpeta).rglob("*.py")):
            if "__pycache__" in p.parts:
                continue
            arbol = ast.parse(p.read_text(encoding="utf-8"))
            firmas = []
            for n in arbol.body:
                if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
                    firmas.append(self._firma(n, ""))
                if isinstance(n, ast.ClassDef):
                    firmas += [self._firma(m, "    ") for m in n.body if isinstance(m, ast.FunctionDef)]
            if firmas:
                lineas.append(f"{p.relative_to(self.raiz)}:")
                lineas += firmas
        return "\n".join(lineas) or "(sin archivos .py)"

    @staticmethod
    def _firma(nodo, sangria):
        doc = (ast.get_docstring(nodo) or "").split("\n")[0]
        if isinstance(nodo, ast.ClassDef):
            cabecera = f"class {nodo.name}"
        else:
            cabecera = f"def {nodo.name}({', '.join(a.arg for a in nodo.args.args)}) [línea {nodo.lineno}]"
        return f"  {sangria}{cabecera}" + (f"  # {doc}" if doc else "")

    def anotar(self, texto):
        notas = self.raiz / "notas.md"
        previas = notas.read_text(encoding="utf-8").splitlines() if notas.exists() else []
        notas.write_text("\n".join(previas + [f"- {str(texto).strip()}"]) + "\n", encoding="utf-8")
        return f"OK: {len(previas) + 1} nota(s) en notas.md"

    def leer_notas(self):
        notas = self.raiz / "notas.md"
        return notas.read_text(encoding="utf-8").strip() if notas.exists() else "(sin notas)"

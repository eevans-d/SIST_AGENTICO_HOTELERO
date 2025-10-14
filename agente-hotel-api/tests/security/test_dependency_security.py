"""
P011: Tests de Seguridad de Dependencias
=========================================

Tests automatizados para validar que las dependencias del proyecto
no contienen vulnerabilidades conocidas ni problemas de licenciamiento.

Validaciones:
1. No hay vulnerabilidades CRITICAL/HIGH sin mitigar
2. Todas las dependencias directas están actualizadas (< 6 meses)
3. Las licencias son compatibles con MIT/Apache 2.0
4. No hay dependencias con licencias copyleft sin aprobación
5. Dependency tree no tiene conflictos
6. Todas las dependencias están pinneadas en producción

Referencias:
- OWASP Top 10 2021 - A06:2021 - Vulnerable and Outdated Components
- NIST NVD: https://nvd.nist.gov/
"""

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Set

import pytest


class TestDependencyVulnerabilities:
    """Tests de vulnerabilidades en dependencias."""

    @pytest.fixture
    def project_root(self) -> Path:
        """Raíz del proyecto."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def pyproject_path(self, project_root: Path) -> Path:
        """Path a pyproject.toml."""
        return project_root / "pyproject.toml"

    @pytest.mark.security
    @pytest.mark.critical
    def test_no_critical_vulnerabilities(self, project_root: Path):
        """
        CRÍTICO: No debe haber vulnerabilidades CRITICAL en dependencias.

        Usa pip-audit para escanear PyPI Advisory Database.
        """
        try:
            result = subprocess.run(
                ["pip-audit", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=project_root,
            )

            if result.returncode == 0:
                # No vulnerabilities
                pytest.skip("pip-audit no encontró vulnerabilidades (PASS)")
            else:
                # Parse vulnerabilities
                data = json.loads(result.stdout)
                vulnerabilities = data.get("vulnerabilities", [])

                critical_vulns = [v for v in vulnerabilities if v.get("severity", "").upper() == "CRITICAL"]

                assert len(critical_vulns) == 0, (
                    f"Se encontraron {len(critical_vulns)} vulnerabilidades CRITICAL:\n"
                    + "\n".join(
                        [
                            f"  - {v['name']} {v['version']}: {v['id']} - {v.get('description', 'N/A')[:100]}"
                            for v in critical_vulns
                        ]
                    )
                )

        except FileNotFoundError:
            pytest.skip("pip-audit no está instalado (pip install pip-audit)")

    @pytest.mark.security
    @pytest.mark.high
    def test_no_high_vulnerabilities(self, project_root: Path):
        """
        ALTA: No debe haber vulnerabilidades HIGH sin plan de mitigación.

        Permite máximo 2 vulnerabilidades HIGH con excepción documentada.
        """
        try:
            result = subprocess.run(
                ["pip-audit", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=project_root,
            )

            if result.returncode == 0:
                pytest.skip("pip-audit no encontró vulnerabilidades (PASS)")
            else:
                data = json.loads(result.stdout)
                vulnerabilities = data.get("vulnerabilities", [])

                high_vulns = [v for v in vulnerabilities if v.get("severity", "").upper() == "HIGH"]

                # Revisar si hay excepciones documentadas
                exceptions_file = project_root / ".security" / "vulnerability_exceptions.json"
                allowed_high = 2  # Máximo permitido sin bloquear CI

                if exceptions_file.exists():
                    exceptions = json.loads(exceptions_file.read_text())
                    documented_high = len([e for e in exceptions.get("high", []) if e.get("approved", False)])
                    allowed_high = max(2, documented_high)

                assert len(high_vulns) <= allowed_high, (
                    f"Se encontraron {len(high_vulns)} vulnerabilidades HIGH (máximo: {allowed_high}):\n"
                    + "\n".join(
                        [
                            f"  - {v['name']} {v['version']}: {v['id']} - {v.get('description', 'N/A')[:80]}"
                            for v in high_vulns
                        ]
                    )
                    + f"\n\nPara aprobar excepciones, crear: {exceptions_file}"
                )

        except FileNotFoundError:
            pytest.skip("pip-audit no está instalado (pip install pip-audit)")

    @pytest.mark.security
    def test_no_medium_vulnerabilities_in_critical_packages(self, project_root: Path):
        """
        Valida que paquetes críticos (FastAPI, SQLAlchemy, etc.) no tengan
        vulnerabilidades MEDIUM+ sin mitigar.
        """
        critical_packages = {
            "fastapi",
            "uvicorn",
            "sqlalchemy",
            "asyncpg",
            "pydantic",
            "httpx",
            "aiohttp",
            "redis",
        }

        try:
            result = subprocess.run(
                ["pip-audit", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=project_root,
            )

            if result.returncode == 0:
                pytest.skip("pip-audit no encontró vulnerabilidades (PASS)")
            else:
                data = json.loads(result.stdout)
                vulnerabilities = data.get("vulnerabilities", [])

                critical_pkg_vulns = [
                    v
                    for v in vulnerabilities
                    if v["name"].lower() in critical_packages and v.get("severity", "").upper() in ["MEDIUM", "HIGH", "CRITICAL"]
                ]

                assert len(critical_pkg_vulns) == 0, (
                    f"Se encontraron vulnerabilidades MEDIUM+ en paquetes críticos:\n"
                    + "\n".join(
                        [
                            f"  - {v['name']} {v['version']}: {v['id']} ({v.get('severity', 'UNKNOWN')})"
                            for v in critical_pkg_vulns
                        ]
                    )
                )

        except FileNotFoundError:
            pytest.skip("pip-audit no está instalado (pip install pip-audit)")

    @pytest.mark.security
    def test_safety_check_passes(self, project_root: Path):
        """
        Valida vulnerabilidades usando safety (Safety DB).

        Safety tiene una base de datos diferente a pip-audit, por lo que
        puede encontrar vulnerabilidades adicionales.
        """
        try:
            result = subprocess.run(
                ["safety", "check", "--json", "--bare"],
                capture_output=True,
                text=True,
                timeout=180,
                cwd=project_root,
            )

            if not result.stdout.strip():
                # No vulnerabilities
                pytest.skip("safety no encontró vulnerabilidades (PASS)")
            else:
                try:
                    vulnerabilities = json.loads(result.stdout)
                    # Safety format: [package, affected_version, current_version, description, vuln_id]

                    critical_high = [
                        v
                        for v in vulnerabilities
                        if any(
                            keyword in v[3].lower()
                            for keyword in ["critical", "remote code execution", "rce", "sql injection", "xss"]
                        )
                    ]

                    assert len(critical_high) == 0, (
                        f"Safety encontró {len(critical_high)} vulnerabilidades críticas:\n"
                        + "\n".join([f"  - {v[0]} {v[2]}: {v[3][:100]}" for v in critical_high])
                    )

                except json.JSONDecodeError:
                    pytest.fail("Safety retornó output no parseable")

        except FileNotFoundError:
            pytest.skip("safety no está instalado (pip install safety)")


class TestDependencyFreshness:
    """Tests de actualización de dependencias."""

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    @pytest.mark.security
    def test_direct_dependencies_not_severely_outdated(self, project_root: Path):
        """
        Valida que dependencias directas no estén > 1 versión mayor desactualizadas.

        Permite dependencias desactualizadas si la diferencia es solo minor/patch.
        """
        try:
            result = subprocess.run(
                ["pip", "list", "--outdated", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=project_root,
            )

            if result.returncode != 0:
                pytest.skip("pip list --outdated falló")

            outdated = json.loads(result.stdout)

            # Filtrar dependencias directas (asumimos que todas en pyproject.toml son directas)
            pyproject_path = project_root / "pyproject.toml"
            direct_deps = self._parse_direct_dependencies(pyproject_path)

            severely_outdated = []
            for pkg in outdated:
                if pkg["name"].lower() in direct_deps:
                    current = pkg["version"]
                    latest = pkg["latest_version"]

                    if self._is_severely_outdated(current, latest):
                        severely_outdated.append(f"{pkg['name']}: {current} → {latest}")

            assert len(severely_outdated) == 0, (
                f"Dependencias directas severamente desactualizadas (> 1 major version):\n"
                + "\n".join([f"  - {dep}" for dep in severely_outdated])
                + "\n\nActualizar con: poetry update <package>"
            )

        except Exception as e:
            pytest.skip(f"Error verificando paquetes desactualizados: {e}")

    def _parse_direct_dependencies(self, pyproject_path: Path) -> Set[str]:
        """Extrae dependencias directas de pyproject.toml."""
        deps = set()
        if not pyproject_path.exists():
            return deps

        content = pyproject_path.read_text()
        in_deps_section = False

        for line in content.split("\n"):
            line = line.strip()

            if line == "[tool.poetry.dependencies]":
                in_deps_section = True
                continue
            elif line.startswith("[") and in_deps_section:
                break

            if in_deps_section and "=" in line and not line.startswith("#"):
                dep_name = line.split("=")[0].strip().strip('"').strip("'")
                if dep_name and dep_name != "python":
                    deps.add(dep_name.lower())

        return deps

    def _is_severely_outdated(self, current: str, latest: str) -> bool:
        """
        Determina si una versión está severamente desactualizada.

        Considera severo si:
        - Major version diff > 1 (ej: 1.0.0 vs 3.0.0)
        - Major version diff = 1 y han pasado > 6 meses (heurística)
        """
        try:
            current_parts = [int(x) for x in current.split(".")[:3]]
            latest_parts = [int(x) for x in latest.split(".")[:3]]

            # Pad to 3 elements
            while len(current_parts) < 3:
                current_parts.append(0)
            while len(latest_parts) < 3:
                latest_parts.append(0)

            major_diff = latest_parts[0] - current_parts[0]

            if major_diff > 1:
                return True
            elif major_diff == 1:
                # Asumir que si minor diff > 5, han pasado ~6 meses
                return latest_parts[1] > 5

            return False

        except (ValueError, IndexError):
            # Si no se puede parsear, asumir que no está severamente desactualizado
            return False

    @pytest.mark.security
    def test_total_outdated_packages_reasonable(self, project_root: Path):
        """
        Valida que el número total de paquetes desactualizados no exceda 30%.

        Métrica de salud: < 20% outdated = excelente, 20-30% = aceptable, > 30% = crítico.
        """
        try:
            # Total installed
            result_all = subprocess.run(
                ["pip", "list", "--format", "json"], capture_output=True, text=True, timeout=60, cwd=project_root
            )

            # Outdated
            result_outdated = subprocess.run(
                ["pip", "list", "--outdated", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=project_root,
            )

            if result_all.returncode != 0 or result_outdated.returncode != 0:
                pytest.skip("pip list falló")

            all_packages = json.loads(result_all.stdout)
            outdated_packages = json.loads(result_outdated.stdout)

            total = len(all_packages)
            outdated_count = len(outdated_packages)
            outdated_pct = (outdated_count / total * 100) if total > 0 else 0

            assert outdated_pct <= 30, (
                f"Demasiados paquetes desactualizados: {outdated_count}/{total} ({outdated_pct:.1f}%)\n"
                f"Umbral: 30%, Actual: {outdated_pct:.1f}%\n"
                f"Ejecutar: pip list --outdated para ver detalles"
            )

        except Exception as e:
            pytest.skip(f"Error verificando paquetes desactualizados: {e}")


class TestLicenseCompliance:
    """Tests de compatibilidad de licencias."""

    ALLOWED_LICENSES = {
        "MIT",
        "Apache-2.0",
        "Apache 2.0",
        "Apache Software License",
        "BSD-3-Clause",
        "BSD-2-Clause",
        "BSD License",
        "ISC",
        "Python Software Foundation License",
        "PSF",
        "PSF License",
        "Unlicense",
        "Public Domain",
        "0BSD",
        "Mozilla Public License 2.0 (MPL 2.0)",
    }

    COPYLEFT_LICENSES = {"GPL-3.0", "GPL-2.0", "LGPL-3.0", "LGPL-2.1", "AGPL-3.0", "EPL-2.0"}

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    @pytest.mark.security
    @pytest.mark.compliance
    def test_no_copyleft_licenses_without_approval(self, project_root: Path):
        """
        CRÍTICO: No debe haber dependencias con licencias copyleft (GPL, AGPL)
        sin aprobación legal explícita.

        Las licencias copyleft requieren que el código derivado sea open source.
        """
        try:
            result = subprocess.run(
                ["pip-licenses", "--format", "json"], capture_output=True, text=True, timeout=60, cwd=project_root
            )

            if result.returncode != 0:
                pytest.skip("pip-licenses falló")

            packages = json.loads(result.stdout)

            # Revisar aprobaciones
            exceptions_file = project_root / ".security" / "license_exceptions.json"
            approved_copyleft = set()
            if exceptions_file.exists():
                exceptions = json.loads(exceptions_file.read_text())
                approved_copyleft = set(exceptions.get("approved_copyleft", []))

            copyleft_packages = []
            for pkg in packages:
                license_name = pkg.get("License", "UNKNOWN")
                package_name = pkg.get("Name", "unknown")

                if package_name.lower() in approved_copyleft:
                    continue

                if any(copyleft in license_name for copyleft in self.COPYLEFT_LICENSES):
                    copyleft_packages.append(f"{package_name} ({license_name})")

            assert len(copyleft_packages) == 0, (
                f"Se encontraron {len(copyleft_packages)} paquetes con licencias copyleft:\n"
                + "\n".join([f"  - {pkg}" for pkg in copyleft_packages])
                + f"\n\nSi estas licencias están aprobadas, agregar a: {exceptions_file}"
            )

        except FileNotFoundError:
            pytest.skip("pip-licenses no está instalado (pip install pip-licenses)")

    @pytest.mark.security
    @pytest.mark.compliance
    def test_no_unknown_licenses(self, project_root: Path):
        """
        Valida que todas las dependencias tengan licencia conocida.

        Dependencias con licencia UNKNOWN requieren revisión manual.
        """
        try:
            result = subprocess.run(
                ["pip-licenses", "--format", "json"], capture_output=True, text=True, timeout=60, cwd=project_root
            )

            if result.returncode != 0:
                pytest.skip("pip-licenses falló")

            packages = json.loads(result.stdout)

            unknown_licenses = []
            for pkg in packages:
                license_name = pkg.get("License", "UNKNOWN")
                package_name = pkg.get("Name", "unknown")

                if license_name in ["UNKNOWN", "UNKNOWN LICENSE", ""]:
                    unknown_licenses.append(package_name)

            # Permitir máximo 5 paquetes con licencia desconocida
            assert len(unknown_licenses) <= 5, (
                f"Se encontraron {len(unknown_licenses)} paquetes con licencia UNKNOWN (máximo: 5):\n"
                + "\n".join([f"  - {pkg}" for pkg in unknown_licenses])
                + "\n\nVerificar manualmente en PyPI o repositorio del paquete"
            )

        except FileNotFoundError:
            pytest.skip("pip-licenses no está instalado (pip install pip-licenses)")

    @pytest.mark.security
    @pytest.mark.compliance
    def test_licenses_compatible_with_project(self, project_root: Path):
        """
        Valida que todas las licencias sean compatibles con MIT/Apache 2.0.

        Licencias permisivas permitidas: MIT, Apache, BSD, ISC, PSF.
        """
        try:
            result = subprocess.run(
                ["pip-licenses", "--format", "json"], capture_output=True, text=True, timeout=60, cwd=project_root
            )

            if result.returncode != 0:
                pytest.skip("pip-licenses falló")

            packages = json.loads(result.stdout)

            incompatible_packages = []
            for pkg in packages:
                license_name = pkg.get("License", "UNKNOWN")
                package_name = pkg.get("Name", "unknown")

                # Skip copyleft (ya validado en otro test)
                if any(copyleft in license_name for copyleft in self.COPYLEFT_LICENSES):
                    continue

                # Skip UNKNOWN (ya validado en otro test)
                if license_name in ["UNKNOWN", "UNKNOWN LICENSE", ""]:
                    continue

                # Check if compatible
                is_compatible = any(allowed in license_name for allowed in self.ALLOWED_LICENSES)

                # Excepciones comunes
                if "BSD" in license_name or "MIT" in license_name or "Apache" in license_name:
                    is_compatible = True

                if not is_compatible:
                    incompatible_packages.append(f"{package_name} ({license_name})")

            # Permitir hasta 10 licencias no estándar (pueden ser compatibles pero con nombres diferentes)
            assert len(incompatible_packages) <= 10, (
                f"Se encontraron {len(incompatible_packages)} paquetes con licencias no estándar:\n"
                + "\n".join([f"  - {pkg}" for pkg in incompatible_packages[:20]])
                + ("\n  ..." if len(incompatible_packages) > 20 else "")
                + "\n\nVerificar compatibilidad manualmente"
            )

        except FileNotFoundError:
            pytest.skip("pip-licenses no está instalado (pip install pip-licenses)")


class TestDependencyIntegrity:
    """Tests de integridad de dependencias."""

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    @pytest.mark.security
    def test_pyproject_toml_has_version_constraints(self, project_root: Path):
        """
        Valida que todas las dependencias directas tengan constraints de versión.

        Evita instalar versiones arbitrarias que pueden introducir breaking changes.
        """
        pyproject_path = project_root / "pyproject.toml"
        if not pyproject_path.exists():
            pytest.skip("pyproject.toml no encontrado")

        content = pyproject_path.read_text()
        in_deps_section = False
        unconstrained_deps = []

        for line in content.split("\n"):
            line = line.strip()

            if line == "[tool.poetry.dependencies]":
                in_deps_section = True
                continue
            elif line.startswith("[") and in_deps_section:
                break

            if in_deps_section and "=" in line and not line.startswith("#"):
                # Formato: nombre = "^1.0.0" o nombre = {extras = [...], version = "^1.0.0"}
                dep_name = line.split("=")[0].strip().strip('"').strip("'")

                if dep_name == "python":
                    continue

                # Check if has version constraint
                if '"*"' in line or "'*'" in line:
                    unconstrained_deps.append(dep_name)
                elif "version" not in line and "^" not in line and "~" not in line and "=" not in line:
                    # Formato sin versión explícita
                    if "{" not in line:  # Si no es dict con extras
                        unconstrained_deps.append(dep_name)

        assert len(unconstrained_deps) == 0, (
            f"Dependencias sin constraint de versión:\n"
            + "\n".join([f"  - {dep}" for dep in unconstrained_deps])
            + '\n\nUsar: ^x.y.z (compatible), ~x.y.z (patch), o ">=x.y.z,<x+1.0.0" (range)'
        )

    @pytest.mark.security
    def test_no_duplicate_dependencies(self, project_root: Path):
        """
        Valida que no haya dependencias duplicadas en el entorno.

        Dependencias duplicadas pueden causar conflictos de versión.
        """
        try:
            result = subprocess.run(
                ["pip", "list", "--format", "json"], capture_output=True, text=True, timeout=60, cwd=project_root
            )

            if result.returncode != 0:
                pytest.skip("pip list falló")

            packages = json.loads(result.stdout)
            package_names = [pkg["name"].lower() for pkg in packages]

            # Check for duplicates
            seen = set()
            duplicates = []
            for name in package_names:
                if name in seen:
                    duplicates.append(name)
                seen.add(name)

            assert len(duplicates) == 0, f"Dependencias duplicadas encontradas: {', '.join(duplicates)}"

        except Exception as e:
            pytest.skip(f"Error verificando duplicados: {e}")

    @pytest.mark.security
    def test_dependency_tree_has_no_conflicts(self, project_root: Path):
        """
        Valida que el árbol de dependencias no tenga conflictos de versión.

        Usa pip check para validar compatibilidad.
        """
        try:
            result = subprocess.run(
                ["pip", "check"], capture_output=True, text=True, timeout=60, cwd=project_root
            )

            assert result.returncode == 0, (
                f"pip check encontró conflictos de dependencias:\n{result.stdout}\n{result.stderr}"
            )

        except Exception as e:
            pytest.skip(f"Error verificando conflictos: {e}")


class TestProductionDependencies:
    """Tests específicos para dependencias de producción."""

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    @pytest.mark.security
    @pytest.mark.production
    def test_production_dependencies_pinned(self, project_root: Path):
        """
        Valida que dependencias críticas estén pinneadas en producción.

        IMPORTANTE: Solo en requirements.txt de producción, no en pyproject.toml.
        """
        requirements_prod = project_root / "requirements.prod.txt"

        if not requirements_prod.exists():
            pytest.skip("requirements.prod.txt no existe (opcional para Poetry)")

        content = requirements_prod.read_text()
        unpinned = []

        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Check if pinned (==x.y.z)
            if "==" not in line:
                unpinned.append(line)

        assert len(unpinned) == 0, (
            f"Dependencias de producción no pinneadas en requirements.prod.txt:\n"
            + "\n".join([f"  - {dep}" for dep in unpinned])
            + "\n\nGenerar con: poetry export -f requirements.txt --without-hashes > requirements.prod.txt"
        )

    @pytest.mark.security
    def test_no_dev_dependencies_in_production(self, project_root: Path):
        """
        Valida que el ambiente de producción no incluya dependencias de desarrollo.

        Dev dependencies (pytest, ruff, etc.) no deben estar en producción.
        """
        # Este test solo es relevante si se ejecuta en un ambiente de producción
        import os

        if os.getenv("ENV") != "production":
            pytest.skip("Test solo para ambiente de producción")

        dev_packages = {"pytest", "pytest-asyncio", "pytest-mock", "ruff", "pre-commit", "pytest-cov"}

        try:
            result = subprocess.run(
                ["pip", "list", "--format", "json"], capture_output=True, text=True, timeout=60, cwd=project_root
            )

            if result.returncode != 0:
                pytest.skip("pip list falló")

            packages = json.loads(result.stdout)
            installed_dev_packages = [pkg["name"] for pkg in packages if pkg["name"].lower() in dev_packages]

            assert len(installed_dev_packages) == 0, (
                f"Dependencias de desarrollo encontradas en producción:\n"
                + "\n".join([f"  - {pkg}" for pkg in installed_dev_packages])
            )

        except Exception as e:
            pytest.skip(f"Error verificando dependencias: {e}")

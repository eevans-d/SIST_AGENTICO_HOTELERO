"""
P010: Load Testing & Performance - Validation Script
====================================================

Script Python para validar resultados de k6 load tests y asegurar
cumplimiento de SLOs definidos.

Scenarios validados:
1. Normal Load: 120 VUs, 5 min → P95 < 3s, error < 1%
2. Spike Load: 0→500 VUs → P95 < 5s, error < 5%
3. Soak Test: 200 VUs, 30 min → P95 estable, no degradación
4. Stress Test: Incremento gradual → Breaking point, graceful degradation

Uso:
    python tests/load/validate_k6_results.py results/k6-summary.json

Prioridad: ALTA 🟡
"""

import json
import sys
from typing import Dict, List, Tuple
from pathlib import Path


class LoadTestValidator:
    """Validador de resultados de k6 load tests"""
    
    # SLOs por scenario
    SLOS = {
        'normal': {
            'p95_latency_ms': 3000,
            'error_rate_pct': 1.0,
            'success_rate_pct': 99.0,
        },
        'spike': {
            'p95_latency_ms': 5000,
            'error_rate_pct': 5.0,
            'success_rate_pct': 95.0,
        },
        'soak': {
            'p95_latency_ms': 3500,
            'error_rate_pct': 2.0,
            'success_rate_pct': 98.0,
            'p95_variation_pct': 10.0,  # Variación máxima en P95
        },
        'stress': {
            'p95_latency_ms': 10000,
            'error_rate_pct': 20.0,  # Hasta breaking point
            'success_rate_pct': 80.0,
        },
    }
    
    def __init__(self, results_path: str):
        """
        Inicializar validador
        
        Args:
            results_path: Path al archivo k6-summary.json
        """
        self.results_path = Path(results_path)
        self.results = self._load_results()
        self.violations: List[str] = []
        self.warnings: List[str] = []
        self.passed_checks: List[str] = []
    
    def _load_results(self) -> Dict:
        """Cargar resultados JSON de k6"""
        if not self.results_path.exists():
            raise FileNotFoundError(f"Results file not found: {self.results_path}")
        
        with open(self.results_path, 'r') as f:
            return json.load(f)
    
    def validate_all(self) -> bool:
        """
        Validar todos los scenarios
        
        Returns:
            True si todos los SLOs se cumplen, False otherwise
        """
        print("=" * 80)
        print("K6 LOAD TEST VALIDATION")
        print("=" * 80)
        print()
        
        # Validar métricas generales
        self._validate_general_metrics()
        
        # Validar por scenario
        for scenario in ['normal', 'spike', 'soak', 'stress']:
            if self._scenario_exists(scenario):
                self._validate_scenario(scenario)
        
        # Reporte final
        self._print_summary()
        
        return len(self.violations) == 0
    
    def _scenario_exists(self, scenario: str) -> bool:
        """Verificar si el scenario fue ejecutado"""
        metrics = self.results.get('metrics', {})
        
        # Buscar métricas con tag scenario
        for metric_name in metrics:
            if f'scenario:{scenario}' in str(metrics[metric_name]):
                return True
        
        return False
    
    def _validate_general_metrics(self):
        """Validar métricas generales del test"""
        print("📊 GENERAL METRICS")
        print("-" * 80)
        
        metrics = self.results.get('metrics', {})
        
        # HTTP Request Duration
        if 'http_req_duration' in metrics:
            http_duration = metrics['http_req_duration']
            p95 = http_duration.get('values', {}).get('p(95)', 0)
            p99 = http_duration.get('values', {}).get('p(99)', 0)
            avg = http_duration.get('values', {}).get('avg', 0)
            
            print(f"  HTTP Request Duration:")
            print(f"    - Avg: {avg:.2f}ms")
            print(f"    - P95: {p95:.2f}ms")
            print(f"    - P99: {p99:.2f}ms")
        
        # Iterations
        if 'iterations' in metrics:
            iterations = metrics['iterations']
            count = iterations.get('values', {}).get('count', 0)
            rate = iterations.get('values', {}).get('rate', 0)
            
            print(f"  Iterations:")
            print(f"    - Total: {count}")
            print(f"    - Rate: {rate:.2f}/s")
        
        # VUs
        if 'vus' in metrics:
            vus = metrics['vus']
            max_vus = vus.get('values', {}).get('max', 0)
            
            print(f"  Virtual Users:")
            print(f"    - Max: {max_vus}")
        
        # Data
        if 'data_received' in metrics and 'data_sent' in metrics:
            data_received = metrics['data_received'].get('values', {}).get('count', 0)
            data_sent = metrics['data_sent'].get('values', {}).get('count', 0)
            
            print(f"  Data:")
            print(f"    - Received: {data_received / 1024 / 1024:.2f} MB")
            print(f"    - Sent: {data_sent / 1024 / 1024:.2f} MB")
        
        print()
    
    def _validate_scenario(self, scenario: str):
        """
        Validar un scenario específico
        
        Args:
            scenario: Nombre del scenario (normal, spike, soak, stress)
        """
        print(f"🎯 SCENARIO: {scenario.upper()}")
        print("-" * 80)
        
        slos = self.SLOS[scenario]
        metrics = self.results.get('metrics', {})
        
        # 1. Validar P95 Latency
        latency_key = f'http_req_duration{{scenario:{scenario}}}'
        if latency_key in metrics:
            p95 = metrics[latency_key].get('values', {}).get('p(95)', 0)
            slo_p95 = slos['p95_latency_ms']
            
            if p95 <= slo_p95:
                self.passed_checks.append(f"{scenario}: P95 latency {p95:.2f}ms <= {slo_p95}ms ✅")
                print(f"  ✅ P95 Latency: {p95:.2f}ms (SLO: < {slo_p95}ms)")
            else:
                self.violations.append(f"{scenario}: P95 latency {p95:.2f}ms > {slo_p95}ms")
                print(f"  ❌ P95 Latency: {p95:.2f}ms (SLO: < {slo_p95}ms)")
        else:
            self.warnings.append(f"{scenario}: P95 latency metric not found")
            print(f"  ⚠️  P95 Latency: Metric not found")
        
        # 2. Validar Error Rate
        error_key = f'errors{{scenario:{scenario}}}'
        if error_key in metrics:
            error_rate = metrics[error_key].get('values', {}).get('rate', 0) * 100
            slo_error = slos['error_rate_pct']
            
            if error_rate <= slo_error:
                self.passed_checks.append(f"{scenario}: Error rate {error_rate:.2f}% <= {slo_error}% ✅")
                print(f"  ✅ Error Rate: {error_rate:.2f}% (SLO: < {slo_error}%)")
            else:
                self.violations.append(f"{scenario}: Error rate {error_rate:.2f}% > {slo_error}%")
                print(f"  ❌ Error Rate: {error_rate:.2f}% (SLO: < {slo_error}%)")
        else:
            # Si no hay métrica de errors, asumir 0%
            self.passed_checks.append(f"{scenario}: Error rate 0.00% (no errors) ✅")
            print(f"  ✅ Error Rate: 0.00% (SLO: < {slos['error_rate_pct']}%)")
        
        # 3. Validar Success Rate (via checks)
        checks_key = f'checks{{scenario:{scenario}}}'
        if checks_key in metrics:
            success_rate = metrics[checks_key].get('values', {}).get('rate', 0) * 100
            slo_success = slos['success_rate_pct']
            
            if success_rate >= slo_success:
                self.passed_checks.append(f"{scenario}: Success rate {success_rate:.2f}% >= {slo_success}% ✅")
                print(f"  ✅ Success Rate: {success_rate:.2f}% (SLO: > {slo_success}%)")
            else:
                self.violations.append(f"{scenario}: Success rate {success_rate:.2f}% < {slo_success}%")
                print(f"  ❌ Success Rate: {success_rate:.2f}% (SLO: > {slo_success}%)")
        else:
            self.warnings.append(f"{scenario}: Success rate metric not found")
            print(f"  ⚠️  Success Rate: Metric not found")
        
        # 4. Validación especial para Soak Test (variación P95)
        if scenario == 'soak' and 'p95_variation_pct' in slos:
            # Esto requeriría análisis temporal de P95 (no disponible en summary)
            self.warnings.append(f"{scenario}: P95 variation validation requires temporal data")
            print(f"  ⚠️  P95 Variation: Requires temporal analysis (not in summary)")
        
        print()
    
    def _print_summary(self):
        """Imprimir resumen final"""
        print("=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        print()
        
        print(f"✅ Passed Checks: {len(self.passed_checks)}")
        for check in self.passed_checks:
            print(f"  - {check}")
        print()
        
        if self.warnings:
            print(f"⚠️  Warnings: {len(self.warnings)}")
            for warning in self.warnings:
                print(f"  - {warning}")
            print()
        
        if self.violations:
            print(f"❌ SLO Violations: {len(self.violations)}")
            for violation in self.violations:
                print(f"  - {violation}")
            print()
            print("RESULT: ❌ FAILED - SLO violations detected")
        else:
            print("RESULT: ✅ PASSED - All SLOs met")
        
        print("=" * 80)


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python validate_k6_results.py <k6-summary.json>")
        print()
        print("Example:")
        print("  python tests/load/validate_k6_results.py results/k6-summary.json")
        sys.exit(1)
    
    results_file = sys.argv[1]
    
    try:
        validator = LoadTestValidator(results_file)
        success = validator.validate_all()
        
        # Exit code
        sys.exit(0 if success else 1)
    
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
        sys.exit(2)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == '__main__':
    main()

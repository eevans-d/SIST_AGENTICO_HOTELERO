#!/bin/bash
# Benchmark Comparison Script
# Compares current performance with baseline

set -e

echo "🔍 Comparando benchmarks con baseline..."

# Create benchmarks directory if it doesn't exist
mkdir -p .benchmarks

# Run benchmarks and save results
echo "📊 Ejecutando benchmarks..."
docker compose -f docker-compose.dev.yml exec -T agente-api \
    python -m pytest tests/benchmarks/ \
    --benchmark-only \
    --benchmark-json=.benchmarks/current.json

# If baseline exists, compare
if [ -f .benchmarks/baseline.json ]; then
    echo "📊 Comparando con baseline..."

    # Extract key metrics using Python
    docker compose -f docker-compose.dev.yml exec -T agente-api python << 'EOF'
import json

with open('.benchmarks/baseline.json', 'r') as f:
    baseline = json.load(f)

with open('.benchmarks/current.json', 'r') as f:
    current = json.load(f)

print("\n╔════════════════════════════════════════════════╗")
print("║     📊 BENCHMARK COMPARISON REPORT            ║")
print("╚════════════════════════════════════════════════╝\n")

for curr_bench in current['benchmarks']:
    name = curr_bench['name']
    curr_mean = curr_bench['stats']['mean']

    # Find matching baseline
    baseline_bench = next((b for b in baseline['benchmarks'] if b['name'] == name), None)

    if baseline_bench:
        base_mean = baseline_bench['stats']['mean']
        diff = ((curr_mean - base_mean) / base_mean) * 100

        status = "✅" if diff < 10 else "⚠️" if diff < 20 else "❌"

        print(f"{status} {name}")
        print(f"   Baseline: {base_mean*1000:.2f}ms")
        print(f"   Current:  {curr_mean*1000:.2f}ms")
        print(f"   Change:   {diff:+.1f}%\n")
    else:
        print(f"🆕 {name} (new benchmark)")
        print(f"   Mean: {curr_mean*1000:.2f}ms\n")

EOF

    echo "✅ Comparación guardada"
else
    echo "⚠️  No existe baseline - guardando como referencia"
    cp .benchmarks/current.json .benchmarks/baseline.json
    echo "✅ Baseline establecido"
fi
